#!/usr/bin/env python3
"""
rip_cd.py — Rip a CD to MP3 with album art from MusicBrainz/Cover Art Archive.

Workflow:
  1. Finds the CD drive that has a disc (fails clearly if ambiguous).
  2. Reads the disc TOC and looks up the release on MusicBrainz.
  3. Downloads front cover art from the Cover Art Archive.
  4. Rips each track via cdparanoia, encodes to MP3 via lame with ID3 tags.
  5. Saves everything to <music_root>/Unsorted/<Artist> - <Album>/.
  6. Ejects the CD when done.

System dependencies (install once):
  sudo apt install cdparanoia lame eject libdiscid0 libcdio-utils

Python dependencies:
  sudo pip3 install discid musicbrainzngs requests
"""

from __future__ import annotations

import fcntl
import glob
import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from musicbox_paths import music_root  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)

# ioctl constant for CDROM_DRIVE_STATUS
_CDROM_DRIVE_STATUS = 0x5326
_CDS_DISC_OK = 4

APP_NAME = "musicbox-ripper"
APP_VERSION = "1.0"
APP_CONTACT = "https://github.com/bsaund/musicbox"


def _check_tool(name: str) -> None:
    if not shutil.which(name):
        raise SystemExit(
            f"Required tool '{name}' not found. Install with: sudo apt install {name}"
        )


def check_dependencies() -> None:
    for tool in ("cdparanoia", "lame", "eject"):
        _check_tool(tool)
    try:
        import discid  # noqa: F401
    except ImportError:
        raise SystemExit("Python package 'discid' not found. Install: sudo pip3 install discid")
    try:
        import musicbrainzngs  # noqa: F401
    except ImportError:
        raise SystemExit(
            "Python package 'musicbrainzngs' not found. Install: sudo pip3 install musicbrainzngs"
        )
    try:
        import requests  # noqa: F401
    except ImportError:
        raise SystemExit(
            "Python package 'requests' not found. Install: sudo pip3 install requests"
        )


def find_cd_drives() -> list[str]:
    drives = sorted(glob.glob("/dev/sr*"))
    if not drives and Path("/dev/cdrom").exists():
        drives = [str(Path("/dev/cdrom").resolve())]
    return drives


def disc_status(device: str) -> int:
    try:
        fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
        status = fcntl.ioctl(fd, _CDROM_DRIVE_STATUS)
        os.close(fd)
        return status
    except OSError:
        return 0


def find_drive_with_disc() -> str:
    drives = find_cd_drives()
    if not drives:
        raise SystemExit("No CD drives found on this system.")
    loaded = [d for d in drives if disc_status(d) == _CDS_DISC_OK]
    if not loaded:
        raise SystemExit(
            f"No disc found in any of: {drives}\n"
            "Make sure the CD is inserted and the tray is closed."
        )
    if len(loaded) > 1:
        raise SystemExit(
            f"Multiple drives contain discs: {loaded}\n"
            "Remove all but one disc so the target drive is unambiguous."
        )
    return loaded[0]


def read_disc(device: str):
    """Read the disc TOC and return a discid object."""
    import discid
    logger.info("Reading disc TOC from %s ...", device)
    disc = discid.read(device)
    logger.info("Disc ID: %s", disc.id)
    return disc


def read_cdtext(device: str) -> dict:
    """
    Try to read CD-Text embedded in the disc itself.

    CD-Text is an optional extension (1996) that some commercial CDs include,
    storing album title, artist, and per-track titles in the disc's subcode data.
    Requires the 'cd-info' tool from the libcdio-utils package.

    Returns a dict with keys:
      'album'   : str or None
      'artist'  : str or None
      'tracks'  : list of str (track titles, 1-indexed so index 0 == track 1)
    """
    empty = {"album": None, "artist": None, "tracks": []}

    if not shutil.which("cd-info"):
        logger.debug("cd-info not found; skipping CD-Text read (apt install libcdio-utils)")
        return empty

    try:
        result = subprocess.run(
            ["cd-info", "--no-header", "--no-device-info", "--no-disc-mode",
             "--cdtext", "-C", device],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout
    except Exception as exc:
        logger.debug("cd-info failed: %s", exc)
        return empty

    album, artist = None, None
    tracks: list[str] = []

    for line in output.splitlines():
        line = line.strip()
        # Disc-level CD-Text
        if line.startswith("CD-Text for Disc:") or line.startswith("Disc"):
            pass
        if "TITLE:" in line and "Track" not in line:
            album = line.split("TITLE:", 1)[1].strip().strip("'\"")
        if "PERFORMER:" in line and "Track" not in line:
            artist = line.split("PERFORMER:", 1)[1].strip().strip("'\"")
        # Track-level CD-Text:  "  3: TITLE: ..."
        if line and line[0].isdigit() and "TITLE:" in line:
            title = line.split("TITLE:", 1)[1].strip().strip("'\"")
            if title:
                tracks.append(title)

    if album or artist or tracks:
        logger.info(
            "CD-Text found: album=%r artist=%r tracks=%d",
            album, artist, len(tracks),
        )
    else:
        logger.info("No CD-Text found on this disc.")

    return {"album": album, "artist": artist, "tracks": tracks}


def lookup_release(disc) -> dict | None:
    """Look up the disc on MusicBrainz. Returns release dict or None if not found."""
    import musicbrainzngs

    musicbrainzngs.set_useragent(APP_NAME, APP_VERSION, APP_CONTACT)

    try:
        result = musicbrainzngs.get_releases_by_discid(
            disc.id,
            includes=["artists", "recordings", "release-groups"],
        )
    except musicbrainzngs.ResponseError as exc:
        if hasattr(exc, "cause") and getattr(exc.cause, "code", None) == 404:
            return None
        raise

    releases = result.get("disc", {}).get("release-list", [])
    if not releases:
        return None

    if len(releases) > 1:
        logger.warning(
            "%d releases found for this disc. Using first: '%s'",
            len(releases),
            releases[0].get("title"),
        )
    return releases[0]


def get_track_list(release: dict, disc_id: str) -> list[dict]:
    """Return the track list for the matching disc within a (possibly multi-disc) release."""
    for medium in release.get("medium-list", []):
        for d in medium.get("disc-list", []):
            if d.get("id") == disc_id:
                return medium.get("track-list", [])
    # Fall back to the first medium if the disc id didn't match (can happen with redirects)
    if release.get("medium-list"):
        logger.warning("Could not match disc ID to a medium; using first medium track list.")
        return release["medium-list"][0].get("track-list", [])
    return []


def fetch_cover_art(release_id: str) -> bytes | None:
    """Download front cover art for the release. Returns bytes or None."""
    import musicbrainzngs
    import requests

    musicbrainzngs.set_useragent(APP_NAME, APP_VERSION, APP_CONTACT)

    try:
        data = musicbrainzngs.get_image_front(release_id)
        if data:
            logger.info("Cover art fetched from Cover Art Archive (musicbrainzngs).")
            return data
    except Exception:
        pass

    # Direct HTTP fallback with redirect following
    url = f"https://coverartarchive.org/release/{release_id}/front"
    try:
        resp = requests.get(url, timeout=20, allow_redirects=True)
        if resp.ok and resp.content:
            logger.info("Cover art fetched via direct CAA URL.")
            return resp.content
    except requests.RequestException as exc:
        logger.debug("Direct cover art fetch failed: %s", exc)

    return None


def sanitize(name: str) -> str:
    """Strip characters that are unsafe in filesystem paths."""
    for ch in r'\/:*?"<>|':
        name = name.replace(ch, "_")
    return name.strip(". ")


def rip_track(device: str, track_num: int, output_wav: str) -> None:
    logger.info("  cdparanoia: ripping track %d ...", track_num)
    subprocess.run(
        ["cdparanoia", "-d", device, str(track_num), output_wav],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def encode_mp3(
    wav_path: Path,
    mp3_path: Path,
    title: str,
    artist: str,
    album: str,
    track_num: int,
    total_tracks: int,
    year: str | None,
) -> None:
    cmd = [
        "lame",
        "--preset", "standard",
        "--tt", title,
        "--ta", artist,
        "--tl", album,
        "--tn", f"{track_num}/{total_tracks}",
    ]
    if year:
        cmd += ["--ty", year]
    cmd += [str(wav_path), str(mp3_path)]
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def rip_cd() -> None:
    check_dependencies()

    device = find_drive_with_disc()
    logger.info("Using CD drive: %s", device)

    disc = read_disc(device)
    release = lookup_release(disc)

    if release is None:
        logger.warning(
            "Disc not found in MusicBrainz (disc id=%s). "
            "You can submit it at: https://musicbrainz.org/cdtoc/attach?id=%s",
            disc.id, disc.id,
        )
        cdtext = read_cdtext(device)
        artist = cdtext["artist"] or "Unknown Artist"
        album_title = cdtext["album"] or "Unknown Album"
        year = None
        track_list = cdtext["tracks"]  # plain strings, handled below
        if cdtext["artist"] or cdtext["album"]:
            logger.info("Using CD-Text for metadata: artist=%r album=%r", artist, album_title)
        else:
            logger.warning(
                "No CD-Text on disc either. "
                "Tracks will be named 'Track 01', 'Track 02', etc. "
                "Cover art will not be available."
            )
    else:
        artist = release.get("artist-credit-phrase") or "Unknown Artist"
        album_title = release.get("title") or "Unknown Album"
        year = (release.get("date") or "")[:4] or None
        track_list = get_track_list(release, disc.id)

    logger.info("Album:  %s", album_title)
    logger.info("Artist: %s", artist)
    logger.info("Year:   %s", year or "unknown")

    total_tracks = disc.last_track_num - disc.first_track_num + 1

    dest_folder = music_root() / "Unsorted" / sanitize(f"{artist} - {album_title}")
    dest_folder.mkdir(parents=True, exist_ok=True)
    logger.info("Output folder: %s", dest_folder)

    # Cover art
    if release is not None:
        cover_art = fetch_cover_art(release["id"])
        if cover_art:
            cover_path = dest_folder / "cover.jpg"
            cover_path.write_bytes(cover_art)
            logger.info("Saved cover art (%d KB) -> %s", len(cover_art) // 1024, cover_path)
        else:
            logger.warning("No cover art found for this release.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        for track_num in range(disc.first_track_num, disc.last_track_num + 1):
            idx = track_num - disc.first_track_num
            track_title = f"Track {track_num:02d}"
            if idx < len(track_list):
                entry = track_list[idx]
                if isinstance(entry, str):
                    # CD-Text track list is plain strings
                    track_title = entry or track_title
                else:
                    # MusicBrainz track list is dicts
                    recording = entry.get("recording", {})
                    track_title = (
                        recording.get("title")
                        or entry.get("title")
                        or track_title
                    )

            logger.info("Track %d/%d: %s", track_num, total_tracks, track_title)

            wav = tmp / f"track{track_num:02d}.wav"
            mp3_name = sanitize(f"{track_num:02d} {track_title}.mp3")
            mp3 = dest_folder / mp3_name

            rip_track(device, track_num, str(wav))
            encode_mp3(
                wav,
                mp3,
                title=track_title,
                artist=artist,
                album=album_title,
                track_num=track_num,
                total_tracks=total_tracks,
                year=year,
            )
            logger.info("  -> %s", mp3.name)

    logger.info("All tracks done. Ejecting disc from %s ...", device)
    subprocess.run(["eject", device], check=True)
    logger.info("Done! Album saved to:\n  %s", dest_folder)


if __name__ == "__main__":
    rip_cd()
