#!/usr/bin/env python3
"""EYE_CONTACT_GUARD (v0.38): people in conversation look at each other, not the lens.

Earned 2026-08-08 on the-introducer spreads 05, 08 and 10 in one batch: a man
mid-decision at his laptop, a man gesturing at a wall, and a founder laughing over
her shoulder all rendered with eyes on the camera. The operator's words are the
rule: "if the camera is not representing your interlocutor's eyes, why are you
looking at it?" A scene that hands the camera the interlocutor's role is the
carve-out and must NOT fire the guard.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import EYE_CONTACT_GUARD, _has_conversation  # noqa: E402


class TestDetector(unittest.TestCase):
    def test_fires_on_the_scenes_that_earned_it(self):
        self.assertTrue(_has_conversation(
            "MAYA is the subject, mid-stride through the door, laughing at something "
            "over her shoulder."))
        self.assertTrue(_has_conversation(
            "David is mid-grin, gesturing at the wall with a pencil."))
        self.assertTrue(_has_conversation(
            "Two founders lean in as David sits at the table's head, one open hand "
            "presenting a small coral sub-agent."))

    def test_fires_on_plain_conversation(self):
        self.assertTrue(_has_conversation("Two friends chatting over lunch at a cafe."))
        self.assertTrue(_has_conversation("She is telling him about the harvest."))

    def test_camera_address_is_the_carve_out(self):
        self.assertFalse(_has_conversation(
            "DAVID alone, waist-up, facing the VIEWER directly: the reader is the "
            "person he is meeting. His open hand reaches toward the camera."))
        self.assertFalse(_has_conversation(
            "She stands at the rail facing the camera, wind in her hair."))

    def test_silent_on_a_scene_with_no_engagement(self):
        self.assertFalse(_has_conversation("An empty chair before a glowing laptop."))
        self.assertFalse(_has_conversation("A man walks alone down a hillside path."))

    def test_guard_text_states_the_rule(self):
        self.assertIn("LOOK AT EACH OTHER", EYE_CONTACT_GUARD)
        self.assertIn("camera", EYE_CONTACT_GUARD)


if __name__ == "__main__":
    unittest.main()
