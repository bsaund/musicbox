#!/usr/bin/env python3

import evdev
import pathlib
import json
import urllib.parse
from mopidy_json_client import MopidyClient
import time
from os import path

# BARCODE_SCANNER_FILEPATH = '/dev/input/by-id/usb-GD_USB_Keyboard_V1.0-9c6d-event-kbd'  # Wired scanner
BARCODE_SCANNER_FILEPATH = '/dev/input/by-id/usb-Netum._HIDKB_18502-event-kbd'  # Wireless scanner

BASE_FP = "/home/pi/Dropbox/Music"
CONFIG_FILENAME = ".barcode_config"
MUSIC_EXTENSIONS = [".mp3", ".m4a"]

mp = MopidyClient()

BARCODE_CONTROLS = {
    "Pause": lambda playback: playback.pause(),
    "Play": lambda playback: playback.play(),
    "Previous": lambda playback: playback.previous(),
    "Next": lambda playback: playback.next(),
}


def load_config_file():
    fp = pathlib.Path(BASE_FP) / CONFIG_FILENAME
    if not fp.exists():
        return {}
    with fp.open() as f:
        cfg = json.load(f)
    return {int(k): v for k, v in cfg.items()}


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
    print(f"Running command: {command}")
    BARCODE_CONTROLS[command](mp.playback)


def play_latest_scan():
    while not path.exists(BARCODE_SCANNER_FILEPATH):
        time.sleep(0.1)

    scanner = None
    while scanner is None:
        try:
            scanner = Scanner(BARCODE_SCANNER_FILEPATH)
        except Exception as e:
            print(e)

    cfg = load_config_file()
    while True:
        barcode_id = scanner.read_scan()
        barcode_command = cfg[barcode_id]
        if barcode_command.startswith("Controls/"):
            barcode_command = barcode_command.lstrip("Controls/")
            handle_control_scan(barcode_command)
            continue
        print(f"Playing {barcode_command}")
        mp.tracklist.clear()
        add_all_songs_from_folder(barcode_command)
        mp.playback.play()


if __name__ == "__main__":
    play_latest_scan()
