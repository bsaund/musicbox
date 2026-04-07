#!/usr/bin/env python3

import evdev
import json
import logging
import pathlib
import sys
import time
import urllib.parse
from os import path

from mopidy_json_client import MopidyClient

from musicbox_paths import music_root, scanner_device_path

if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stderr,
    )
logger = logging.getLogger(__name__)

BARCODE_SCANNER_FILEPATH = scanner_device_path()

BASE_FP = music_root()
CONFIG_FILENAME = ".barcode_config"
MUSIC_EXTENSIONS = [".mp3", ".m4a"]

try:
    mp = MopidyClient()
except Exception:
    logger.exception("Failed to create Mopidy client (is Mopidy running?)")
    raise

BARCODE_CONTROLS = {
    "Pause": lambda playback: playback.pause(),
    "Play": lambda playback: playback.play(),
    "Previous": lambda playback: playback.previous(),
    "Next": lambda playback: playback.next(),
}


def load_config_file():
    fp = pathlib.Path(BASE_FP) / CONFIG_FILENAME
    if not fp.exists():
        logger.warning("Config file does not exist: %s", fp)
        return {}
    with fp.open() as f:
        cfg = json.load(f)
    out = {int(k): v for k, v in cfg.items()}
    logger.info("Loaded %d barcode entries from %s", len(out), fp)
    return out


def add_all_songs_from_folder(folder):
    d = pathlib.Path(BASE_FP) / folder
    # Specific handling for radio streams
    if (d / "stream.txt").exists():
        with (d / "stream.txt").open() as f:
            mp.tracklist.mopidy_request('core.tracklist.add', uris=[f.readline()])
        return

    uris = sorted(['file://' + urllib.parse.quote(fp.as_posix()) for fp in d.glob('[!._]*')])
    uris = [uri for uri in uris if pathlib.Path(uri).suffix in MUSIC_EXTENSIONS]
    mp.tracklist.mopidy_request('core.tracklist.add', uris=uris)


class Scanner:
    def __init__(self, device_path):
        self.input = evdev.InputDevice(device_path)
        self.input.grab()

    def __del__(self):
        self.input.ungrab()

    def read_scan(self):
        chars = ''
        for event in self.input.read_loop():
            if event.type == evdev.ecodes.EV_KEY:
                e = evdev.categorize(event)
                if e.keystate != e.key_down:
                    continue
                # print(f"keys are {e.keystate}, {e.key_down}, {e.key_up}, {e.keycode}, {e.event}, {e.scancode}")
                key = e.keycode[4:]
                if key == "ENTER":
                    return int(chars[:-1])  # remove checksum key
                chars += key


def handle_control_scan(command):
    logger.info("Control command: %s", command)
    try:
        BARCODE_CONTROLS[command](mp.playback)
    except KeyError:
        logger.error(
            "Unknown control command %r; expected one of %s",
            command,
            sorted(BARCODE_CONTROLS),
        )


def play_latest_scan():
    logger.info(
        "Starting barcode scanner service (music_root=%s, scanner_device=%s)",
        BASE_FP,
        BARCODE_SCANNER_FILEPATH,
    )
    while not path.exists(BARCODE_SCANNER_FILEPATH):
        time.sleep(0.1)

    scanner = None
    while scanner is None:
        try:
            scanner = Scanner(BARCODE_SCANNER_FILEPATH)
        except Exception:
            logger.exception(
                "Could not open scanner device %s; retrying",
                BARCODE_SCANNER_FILEPATH,
            )

    logger.info("Scanner device ready: %s", BARCODE_SCANNER_FILEPATH)

    cfg = load_config_file()
    while True:
        try:
            barcode_id = scanner.read_scan()
            if barcode_id not in cfg:
                logger.error(
                    "Unknown barcode id %s — not in config %s (%d entries loaded)",
                    barcode_id,
                    pathlib.Path(BASE_FP) / CONFIG_FILENAME,
                    len(cfg),
                )
                continue
            barcode_command = cfg[barcode_id]
            if barcode_command.startswith("Controls/"):
                barcode_command = barcode_command.lstrip("Controls/")
                handle_control_scan(barcode_command)
                continue
            logger.info("Playing folder: %s", barcode_command)
            mp.tracklist.clear()
            add_all_songs_from_folder(barcode_command)
            mp.playback.play()
        except KeyboardInterrupt:
            raise
        except Exception:
            logger.exception("Error while handling scan")


if __name__ == "__main__":
    try:
        play_latest_scan()
    except KeyboardInterrupt:
        logger.info("Exiting on keyboard interrupt")
        raise
    except Exception:
        logger.exception("Fatal error; scanner service exiting")
        raise
