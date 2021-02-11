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


def load_config_file():
    fp = pathlib.Path(BASE_FP) / CONFIG_FILENAME
    if not fp.exists():
        return {}
    with fp.open() as f:
        cfg = json.load(f)
    return {int(k): v for k, v in cfg.items()}


def add_all_songs_from_folder(folder):
    d = pathlib.Path(BASE_FP) / folder
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


# scanner = evdev.InputDevice('/dev/input/by-id/usb-GD_USB_Keyboard_V1.0-9c6d-event-kbd')
# scanner.grab()
#
# for event in scanner.read_loop():

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
        print(f"Playing {cfg[barcode_id]}")
        mp.tracklist.clear()
        add_all_songs_from_folder(cfg[barcode_id])
        mp.playback.play()


if __name__ == "__main__":
    play_latest_scan()
