#!/usr/bin/env python3
"""`pose: X` with `altLooks[X]` declared and no `look` must refuse, not render silently.

`pose` selects a render block; `look` is what resolves `structured.altLooks[<key>]` and
therefore what PASSES that look's own sheets and applies its `dropSheets`. When an entity
declares both under the same key, which is how every wardrobe capsule is wired, setting
only `pose` assembles cleanly and renders the DEFAULT wardrobe: the pose's bake says
"matching FIGURE 2 FROM THE LEFT on the supplied capsule reference sheet" while the
capsule sheet is not among the refs at all.

Earned 2026-08-04 on Why We Are the Luckiest Generation. Seven spreads cast `jerry-man`
with pose "ql-cardigan" and no look; the dry run showed the capsule sheet absent and
nothing errored. Two spreads were paid for before a crop-zoom showed the pendant had come
back as a plain Latin cross, which is a canon violation the unread capsule sheet forbids.
"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from assemble_prompt import Refuse, _pose_without_look_guard

# The real shape that earned this: a pose and an altLook under the SAME key, where the
# altLook is the only thing that passes the capsule sheet the pose's bake refers to.
WARDROBE_CHARACTER = {
    "id": "jerry-man",
    "kind": "character",
    "structured": {
        "sheets": {"man": "reference/j/man.png", "face": "reference/j/face.png",
                   "quietLuxuryCapsule2": "reference/j/capsule2.png"},
        "render": {"poses": {
            "front": {"sheets": ["man", "face"]},
            "ql-cardigan": {"sheets": ["face"],
                            "bake": "matching FIGURE 2 FROM THE LEFT on the supplied capsule sheet"},
        }},
        "altLooks": {"ql-cardigan": {"sheets": {"capsule": "reference/j/capsule2.png"},
                                     "dropSheets": ["man"]}},
    },
}

# A character with poses but NO altLooks: every pose here is safe on its own.
PLAIN_CHARACTER = {
    "id": "paul-apostle",
    "kind": "character",
    "structured": {
        "sheets": {"master": "reference/p/master.png"},
        "render": {"poses": {"teaching": {}, "standing": {}}},
    },
}


class TestPoseWithoutLookGuard(unittest.TestCase):
    def test_pose_naming_an_altlook_without_look_refuses(self):
        with self.assertRaises(Refuse) as cm:
            _pose_without_look_guard(
                {"id": "jerry-man", "pose": "ql-cardigan"}, WARDROBE_CHARACTER, "spread-12")
        msg = str(cm.exception)
        self.assertIn("\"look\": 'ql-cardigan'", msg,
                      "the refusal must name the exact fix, not just complain")
        self.assertIn("spread-12", msg)
        self.assertIn("allowPoseOnly", msg, "the refusal must name its escape hatch")

    def test_pose_with_matching_look_passes(self):
        _pose_without_look_guard(
            {"id": "jerry-man", "pose": "ql-cardigan", "look": "ql-cardigan"},
            WARDROBE_CHARACTER, "spread-12")

    def test_pose_with_a_different_look_passes(self):
        """An author who deliberately pairs a pose with another look is not second-guessed."""
        _pose_without_look_guard(
            {"id": "jerry-man", "pose": "ql-cardigan", "look": "work"},
            WARDROBE_CHARACTER, "spread-12")

    def test_allow_pose_only_is_the_escape_hatch(self):
        _pose_without_look_guard(
            {"id": "jerry-man", "pose": "ql-cardigan", "allowPoseOnly": True},
            WARDROBE_CHARACTER, "spread-12")

    def test_pose_with_no_matching_altlook_passes(self):
        """`front` is a pose and nothing else, so it needs no look."""
        _pose_without_look_guard(
            {"id": "jerry-man", "pose": "front"}, WARDROBE_CHARACTER, "spread-01")

    def test_entity_with_no_altlooks_at_all_passes(self):
        _pose_without_look_guard(
            {"id": "paul-apostle", "pose": "teaching"}, PLAIN_CHARACTER, "spread-11")

    def test_no_pose_at_all_passes(self):
        _pose_without_look_guard({"id": "jerry-man"}, WARDROBE_CHARACTER, "spread-01")


if __name__ == "__main__":
    unittest.main()
