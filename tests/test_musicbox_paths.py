"""Unit tests for code/musicbox_paths.py."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_CODE = Path(__file__).resolve().parent.parent / "code"
if str(_CODE) not in sys.path:
    sys.path.insert(0, str(_CODE))

import musicbox_paths  # noqa: E402


def _env_without(*keys: str) -> dict[str, str]:
    return {k: v for k, v in os.environ.items() if k not in keys}


class TestMusicRoot(unittest.TestCase):
    def test_default_uses_home_dropbox_music(self):
        with patch("musicbox_paths.Path.home", return_value=Path("/tmp/musicbox_test_home")):
            with patch.dict(os.environ, _env_without("MUSICBOX_MUSIC_DIR"), clear=True):
                got = musicbox_paths.music_root()
        self.assertEqual(got, Path("/tmp/musicbox_test_home/Dropbox/Music").resolve())

    def test_musicbox_music_dir_overrides(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            merged = {**os.environ, "MUSICBOX_MUSIC_DIR": str(tmp_path)}
            with patch.dict(os.environ, merged, clear=True):
                got = musicbox_paths.music_root()
        self.assertEqual(got, tmp_path.resolve())

    def test_musicbox_music_dir_expands_tilde_via_home(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            target = home / "custom" / "Music"
            target.mkdir(parents=True)
            merged = {
                **os.environ,
                "HOME": str(home),
                "MUSICBOX_MUSIC_DIR": "~/custom/Music",
            }
            with patch.dict(os.environ, merged, clear=True):
                got = musicbox_paths.music_root()
        self.assertEqual(got, target.resolve())


class TestScannerAndBluetooth(unittest.TestCase):
    def test_scanner_default(self):
        with patch.dict(os.environ, _env_without("MUSICBOX_SCANNER_DEVICE"), clear=True):
            self.assertEqual(
                musicbox_paths.scanner_device_path(),
                "/dev/input/by-id/usb-Netum._HIDKB_18502-event-kbd",
            )

    def test_scanner_override(self):
        merged = {**os.environ, "MUSICBOX_SCANNER_DEVICE": "/dev/input/by-id/usb-test"}
        with patch.dict(os.environ, merged, clear=True):
            self.assertEqual(musicbox_paths.scanner_device_path(), "/dev/input/by-id/usb-test")

    def test_bluetooth_default(self):
        with patch.dict(os.environ, _env_without("MUSICBOX_BLUETOOTH_INPUT"), clear=True):
            self.assertEqual(musicbox_paths.bluetooth_input_device(), "/dev/input/event1")

    def test_bluetooth_override(self):
        merged = {**os.environ, "MUSICBOX_BLUETOOTH_INPUT": "/dev/input/event7"}
        with patch.dict(os.environ, merged, clear=True):
            self.assertEqual(musicbox_paths.bluetooth_input_device(), "/dev/input/event7")


if __name__ == "__main__":
    unittest.main()
