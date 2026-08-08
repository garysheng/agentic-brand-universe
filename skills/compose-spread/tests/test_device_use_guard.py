#!/usr/bin/env python3
"""DEVICE_USE_GUARD (v0.38): a device someone is USING faces its user.

Earned 2026-08-08 on the-introducer spread 05, which failed BOTH ways in one day.
Roll 1 satisfied the user and hid the screen from the viewer (back of the lid to
camera). Roll 2, correcting that, rotated the laptop toward the lens so a man was
typing on a keyboard he could not see. Gary named the missing rule and, crucially,
its resolution: check the device is genuinely in front of the person, and remember
that over-the-shoulder shots are OK. A guard that only bans gets the other defect,
so this one names the legal camera too.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import DEVICE_USE_GUARD, _has_device_use  # noqa: E402


class TestDetector(unittest.TestCase):
    def test_fires_on_the_scene_that_earned_it(self):
        self.assertTrue(_has_device_use(
            "David sits at the desk, one hand at the keys of his glowing laptop, "
            "eyes up, mid-decision."))

    def test_fires_on_ordinary_device_use(self):
        for s in ("she is typing on a laptop at the kitchen table",
                  "he sits at the monitor reading the screen",
                  "a founder working at her laptop by the window"):
            self.assertTrue(_has_device_use(s), s)

    def test_a_device_merely_PRESENT_does_not_fire(self):
        """An unused device is furniture; the guard would be noise."""
        for s in ("an empty chair beside a glowing laptop on the desk",
                  "the closed laptop sits under a slap of sticky notes",
                  "a warm room with bookshelves and a lamp"):
            self.assertFalse(_has_device_use(s), s)

    def test_the_guard_names_the_LEGAL_camera_not_only_the_ban(self):
        """The over-the-shoulder resolution is the half that prevents the
        opposite defect, so it must be in the text."""
        self.assertIn("OVER THE USER'S SHOULDER", DEVICE_USE_GUARD)
        self.assertIn("faces the USER", DEVICE_USE_GUARD.replace("\n", " "))


if __name__ == "__main__":
    unittest.main()
