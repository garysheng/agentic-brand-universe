#!/usr/bin/env python3
"""A `bake` that is really a SHEET/POSE selector must refuse, not render silently.

`plate` (non-characters) and `pose` (characters) SELECT which locked reference is
passed; `bake` is FREE PROSE appended to the entity's block. Nation of Fire's retired
local compiler used `bake` as the selector, so every spec in that dialect, and every new
spec copied from one as a template, names a state this assembler treats as a stray
sentence fragment.

Nothing errored, which was the whole problem: the state plate was never passed, the
spread rendered off the style anchor alone, and the raw slug was pasted into the prompt
as text. Earned 2026-07-31 on `looked-like-hate`, whose three-state spine object
assembled with ZERO of its locked plates. Caught only by dumping the refs by hand.
"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from assemble_prompt import Refuse, _selector_bake_guard

METAPHOR = {
    "id": "the-candle-against-the-sun",
    "kind": "visual-metaphor",
    "structured": {"sheets": {
        "blueprint": "reference/c/blueprint.png",
        "aloneInTheDark": "reference/c/alone-in-the-dark.png",
        "againstTheLight": "reference/c/against-the-light.png",
        "onTheSill": "reference/c/on-the-sill.png",
    }},
}

CHARACTER = {
    "id": "jerry-man",
    "kind": "character",
    "structured": {
        "sheets": {"man": "reference/j/man.png"},
        "render": {"poses": {"front": {}, "work-back": {}}},
    },
}


class TestSelectorBakeGuard(unittest.TestCase):
    def test_slug_matching_a_camelcase_sheet_refuses(self):
        """The exact defect: bake='against-the-light' vs sheet key 'againstTheLight'."""
        with self.assertRaises(Refuse) as cm:
            _selector_bake_guard(
                {"id": "the-candle-against-the-sun", "bake": "against-the-light"},
                METAPHOR, "spread-04")
        msg = str(cm.exception)
        self.assertIn('"plate": "againstTheLight"', msg,
                      "the refusal must name the exact fix, not just complain")
        self.assertIn("spread-04", msg)

    def test_exact_sheet_key_refuses(self):
        with self.assertRaises(Refuse):
            _selector_bake_guard(
                {"id": "the-candle-against-the-sun", "bake": "onTheSill"},
                METAPHOR, "plate-0")

    def test_slug_matching_a_pose_refuses_and_names_pose_not_plate(self):
        with self.assertRaises(Refuse) as cm:
            _selector_bake_guard({"id": "jerry-man", "bake": "work-back"},
                                 CHARACTER, "spread-20")
        self.assertIn('"pose": "work-back"', str(cm.exception))

    def test_real_prose_bake_is_untouched(self):
        """A sentence is a legitimate bake even when it mentions a state by name."""
        _selector_bake_guard(
            {"id": "the-candle-against-the-sun",
             "bake": "Render the candle in exactly one state, the against-the-light "
                     "state shown in its reference plate, and no other."},
            METAPHOR, "spread-04")

    def test_bake_naming_nothing_this_entity_owns_is_untouched(self):
        _selector_bake_guard({"id": "the-candle-against-the-sun", "bake": "guttering"},
                             METAPHOR, "spread-04")

    def test_absent_bake_is_untouched(self):
        _selector_bake_guard({"id": "the-candle-against-the-sun"}, METAPHOR, "spread-03")
        _selector_bake_guard({"id": "the-candle-against-the-sun", "bake": ""},
                             METAPHOR, "spread-03")

    def test_correct_descriptor_shape_passes(self):
        """plate selects, bake is prose: the shape the refusal tells you to write."""
        _selector_bake_guard(
            {"id": "the-candle-against-the-sun", "plate": "againstTheLight",
             "bake": "The candle is unchanged and only looks black."},
            METAPHOR, "spread-04")


if __name__ == "__main__":
    unittest.main()
