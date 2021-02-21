#!/usr/bin/env python3

"""
This is an interface for mopidy using a bluetooth remote controller
I have it running on a raspberry pi that is connected via bluetooth to a speaker with a remote control
"""

import evdev
from mopidy_json_client import MopidyClient
import time
from os import path

BLUETOOTH_FILE = '/dev/input/event1'

mp = MopidyClient()


def handle_remote_control_key(mp, key_event):
    key_down_events = {"KEY_PAUSECD": mp.playback.pause,
                       "KEY_PLAYCD": mp.playback.play,
                       "KEY_PREVIOUSSONG": mp.playback.previous,
                       "KEY_NEXTSONG": mp.playback.next}

    e = evdev.categorize(key_event)
    print(f"keys are {e.keystate}, {e.key_down}, {e.key_up}, {e.keycode}, {e.event}, {e.scancode}")
    if e.keystate == e.key_down:
        if e.keycode in key_down_events:
            key_down_events[e.keycode]()

    print(e)


def listen_on_bluetooth():
    first_pass = True
    while True:
        if not path.exists(BLUETOOTH_FILE):
            time.sleep(0.1)
            if first_pass:
                print("No bluetooth connection...")
                first_pass = False
            continue

        try:
            device = evdev.InputDevice(BLUETOOTH_FILE)
            print(device)
            for event in device.read_loop():
                if event.type == evdev.ecodes.EV_KEY:
                    handle_remote_control_key(mp, event)
        except OSError as e:
            print("Bluetooth disconnected")

        first_pass = True


if __name__ == "__main__":
    listen_on_bluetooth()
