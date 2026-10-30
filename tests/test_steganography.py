"""Tests for image LSB embedding and extraction."""

import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from steganography import compare_images, extract_message, hide_message  # noqa: E402


class SteganographyTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = Path(self.directory.name) / "source.png"
        self.destination = Path(self.directory.name) / "stego.png"
        Image.new("RGB", (100, 100), color=(120, 160, 200)).save(self.source)

    def test_round_trip_unicode(self):
        message = "Hello, steganography! Привет"
        hide_message(self.source, self.destination, message)
        self.assertEqual(extract_message(self.destination), message)

    def test_capacity_limit(self):
        with self.assertRaises(ValueError):
            hide_message(self.source, self.destination, "A" * 5000)

    def test_changes_are_at_most_one_value(self):
        hide_message(self.source, self.destination, "small secret")
        changed, maximum_delta, total = compare_images(self.source, self.destination)
        self.assertGreater(changed, 0)
        self.assertEqual(maximum_delta, 1)
        self.assertEqual(total, 100 * 100)

    def test_plain_image_has_no_message(self):
        self.assertIsNone(extract_message(self.source))

    def test_empty_message_round_trip(self):
        hide_message(self.source, self.destination, "")
        self.assertEqual(extract_message(self.destination), "")


if __name__ == "__main__":
    unittest.main()
