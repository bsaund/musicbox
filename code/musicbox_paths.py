"""
Shared paths for musicbox scripts.

Default music library: ~/Dropbox/Music (works on laptop and Pi without editing usernames).

When the process runs as root (typical systemd unit without User=), Path.home() is /root.
If /home/pi/Dropbox/Music exists, that directory is used so the Pi matches the old hardcoded path
and Dropbox-synced .barcode_config is found.

Override when needed:
  MUSICBOX_MUSIC_DIR   — absolute path to the music folder (Dropbox sync root)
  MUSICBOX_SCANNER_DEVICE — barcode scanner evdev path (default: Netum wireless)
  MUSICBOX_BLUETOOTH_INPUT — bluetooth remote evdev path (default: event1)
"""

from __future__ import annotations

import os
from pathlib import Path

_DEFAULT_SCANNER = "/dev/input/by-id/usb-Netum._HIDKB_18502-event-kbd"
_DEFAULT_BLUETOOTH = "/dev/input/event1"


def music_root() -> Path:
    override = os.environ.get("MUSICBOX_MUSIC_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    home = Path.home()
    if home == Path("/root"):
        pi_music = Path("/home/pi/Dropbox/Music")
        if pi_music.is_dir():
            return pi_music.resolve()
    return (home / "Dropbox" / "Music").resolve()


def scanner_device_path() -> str:
    return os.environ.get("MUSICBOX_SCANNER_DEVICE", _DEFAULT_SCANNER)


def bluetooth_input_device() -> str:
    return os.environ.get("MUSICBOX_BLUETOOTH_INPUT", _DEFAULT_BLUETOOTH)
