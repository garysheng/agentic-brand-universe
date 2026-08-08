#!/usr/bin/env python3
"""NECK_ROTATION_GUARD (v0.38): a head turns ~60 degrees past the shoulders, no more.

Earned 2026-08-08 on the-introducer spread 03: a man climbing a stoop with 'his
face turned back over the street' rendered chin-past-shoulder on a torso still
climbing. Operator: 'This head position looks really uncomfortable... Why are
you distorting yourself like an exorcist?' The motion case of the
torso-follows-head rule: to look behind, the upper body rotates or the figure
stops; the face never points opposite the chest.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import NECK_ROTATION_GUARD, _has_look_back  # noqa: E402


class TestDetector(unittest.TestCase):
    def test_fires_on_the_scene_that_earned_it(self):
        self.assertTrue(_has_look_back(
            "David climbs the steps of a brownstone stoop, two grocery bags in his "
            "arms, his face turned back over the street with his warm grin."))

    def test_fires_on_ordinary_look_backs(self):
        for s in ("she walks ahead, glancing back at the group",
                  "he looks back at the door as he leaves",
                  "laughing at something over her shoulder"):
            self.assertTrue(_has_look_back(s), s)

    def test_silent_when_nobody_looks_behind(self):
        for s in ("he walks toward the door, eyes on the handle",
                  "two friends face each other across the table",
                  "she stands at the rail facing the camera"):
            self.assertFalse(_has_look_back(s), s)

    def test_the_guard_states_the_anatomy_and_the_two_legal_fixes(self):
        joined = NECK_ROTATION_GUARD
        self.assertIn("SIXTY DEGREES", joined)
        self.assertIn("SHOULDERS AND CHEST", joined)
        self.assertIn("pause the figure", joined)
        self.assertIn("sideways glance", joined)


if __name__ == "__main__":
    unittest.main()
