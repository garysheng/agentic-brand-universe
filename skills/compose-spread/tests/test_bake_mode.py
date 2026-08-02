#!/usr/bin/env python3
"""A setting's `bake` must not delete the room (v0.29).

`bake` REPLACES the derived block, which is right for a multi-state prop whose derived
prose describes every state it documents. A SETTING's derived block is not states: it is
map + blocking + dressing + scale, which is what the place IS, which way round it is and
how big. Replacing that deletes the room.

Measured on the-lit-pulpit (movies-are-sermons, 2026-08-02): five spreads plus the cover
each carried a state bake, and `contract.map` reached the model on NONE of them. It only
rendered right because the author had also written the auditorium into every scene by
hand, which is the duplication canon exists to remove. Nothing warned.

A sweep of every render-spec in nation-of-fire found 62 bakes on non-characters, and all
62 were visual-metaphors in nine SHIPPED books. So `setting` changes default (zero blast
radius) and `visual-metaphor` keeps replace but now warns, with `bakeMode` to settle it
explicitly either way.
"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from assemble_prompt import entity_block

GEO = "A dark auditorium. Camera straight on. Fifteen feet tall."
BAKE = "STATE SCREEN, and no other state."


class TestSettingKeepsItsGeometry(unittest.TestCase):
    def test_setting_appends_geometry_then_bake(self):
        out = entity_block("a-room", GEO, BAKE, kind="setting")
        self.assertEqual(out, f"{GEO} {BAKE}")
        self.assertIn("Camera straight on", out, "the room must survive the bake")

    def test_setting_with_no_bake_is_unchanged(self):
        self.assertEqual(entity_block("a-room", GEO, None, kind="setting"), GEO)

    def test_setting_with_no_derived_is_just_the_bake(self):
        self.assertEqual(entity_block("a-room", None, BAKE, kind="setting"), BAKE)

    def test_setting_does_not_warn_because_it_drops_nothing(self):
        w = []
        entity_block("a-room", GEO, BAKE, kind="setting", warnings=w)
        self.assertEqual(w, [])


class TestVisualMetaphorKeepsReplaceButWarns(unittest.TestCase):
    """Nine shipped books authored 62 of these expecting replacement."""
    def test_replace_is_still_the_default(self):
        self.assertEqual(entity_block("obj", GEO, BAKE, kind="visual-metaphor"), BAKE)

    def test_it_warns_and_names_the_escape_hatch(self):
        w = []
        entity_block("obj", GEO, BAKE, kind="visual-metaphor", warnings=w)
        self.assertEqual(len(w), 1)
        self.assertIn("obj", w[0])
        self.assertIn("bakeMode", w[0], "the warning must name the fix")

    def test_no_warning_when_there_was_no_geometry_to_drop(self):
        w = []
        entity_block("obj", None, BAKE, kind="visual-metaphor", warnings=w)
        self.assertEqual(w, [])


class TestExplicitBakeMode(unittest.TestCase):
    def test_append_on_a_visual_metaphor(self):
        w = []
        out = entity_block("obj", GEO, BAKE, kind="visual-metaphor", mode="append", warnings=w)
        self.assertEqual(out, f"{GEO} {BAKE}")
        self.assertEqual(w, [], "an explicit choice is not a defect")

    def test_replace_on_a_setting(self):
        out = entity_block("a-room", GEO, BAKE, kind="setting", mode="replace")
        self.assertEqual(out, BAKE)


class TestUnrelatedBehaviourIsUnchanged(unittest.TestCase):
    def test_props_and_motifs_still_replace(self):
        for kind in ("prop", "motif"):
            self.assertEqual(entity_block("p", GEO, BAKE, kind=kind), BAKE)

    def test_setting_rule_still_appends_last(self):
        out = entity_block("a-room", GEO, BAKE, kind="setting",
                           setting_rule={"a-room": "RULE."})
        self.assertTrue(out.endswith("RULE."))
        self.assertIn(BAKE, out)

    def test_setting_rule_applies_with_no_bake(self):
        out = entity_block("a-room", GEO, None, kind="setting",
                           setting_rule={"a-room": "RULE."})
        self.assertEqual(out, f"{GEO} RULE.")


if __name__ == "__main__":
    unittest.main()
