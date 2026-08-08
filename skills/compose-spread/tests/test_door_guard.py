#!/usr/bin/env python3
"""DOOR_GUARD (v0.38): a door being used obeys American door mechanics.

Earned 2026-08-08 on the-introducer spread 07: a man reaching for a door whose
round knob sat at THIGH height, jammed against the very edge of the jamb, on a
leaf too narrow for the man beside it. Operator: "think about how american doors
work." Doors are the hands of architecture: so familiar that every error is
instantly visible, with a prior loose enough that the model errs constantly.
"""
import os, sys, unittest

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import DOOR_GUARD, _has_door_interaction  # noqa: E402


class TestDetector(unittest.TestCase):
    def test_fires_on_the_scene_that_earned_it(self):
        self.assertTrue(_has_door_interaction(
            "David walks toward a plain terracotta door, one hand reaching for the "
            "round brass knob."))

    def test_fires_on_ordinary_door_use(self):
        for s in ("she pulls open the shop door",
                  "he steps through the doorway into morning light",
                  "a child stands at the threshold of the barn door"):
            self.assertTrue(_has_door_interaction(s), s)

    def test_scenery_doors_do_not_fire(self):
        """A closed background door nobody touches is set dressing."""
        for s in ("a warm hall with folding chairs and a door at the far end",
                  "bookshelves line the wall beside the closed door",
                  "the study is dim: a lamp, a rug, a paneled door"):
            self.assertFalse(_has_door_interaction(s), s)

    def test_the_guard_states_the_numbers(self):
        """Waist height and leaf proportions are the checkable half; without the
        numbers the guard is 'draw doors well', which is not a guard."""
        for token in ("36 to 40 inches", "3 ft wide", "80 in tall", "OPPOSITE the hinges"):
            self.assertIn(token, DOOR_GUARD)


if __name__ == "__main__":
    unittest.main()
