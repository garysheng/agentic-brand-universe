"""`add-entity visual-metaphor --state ...` scaffolds THIS kind's matrix, not a room's.

Earned 2026-08-03 on nation-of-fire `the-shelter-he-held-up` (What a Relief).

SPEC 12 defines a visual-metaphor as "a locked master plus `state` plates". The scaffolder
emitted a SETTING instead: room slots (`empty-c1`, `scale`) in prompts.md, a
`structured.houseRules` block (the rule set a BUILDING hands down to rooms nested inside
it), and no `structured.sheets` at all, which is the one key the compiler resolves plates
from. There was no way to declare a STATE, which is the only thing this kind has, so every
state, sheet key, pose selector and invariant was hand-authored in a throwaway script. The
residue is visible across the reference universe: five visual-metaphors carry hand-written
state blocks and their prompts.md files still hold orphan `empty-c1` sections.

The tests pin the four things that had to be typed by hand, plus the parser coupling that
made the hand-authored file unshootable: a level-2 prose heading is read as a shot.
"""
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agenticstory.authoring import scaffold_entity, prompts_skeleton, lock_shot
from agenticstory.model import setting_contract_gaps

STATES = ["strained", "beside-the-house", "let-go"]


def vm(states=STATES):
    return scaffold_entity("visual-metaphor", "a-shelter", "A Shelter",
                           origin_story="s", states=states)


class TestStatesAreDeclarable(unittest.TestCase):
    def test_contract_states_lists_the_blueprint_master_and_every_state(self):
        self.assertEqual(vm()["contract"]["states"],
                         ["blueprint", "master"] + STATES)

    def test_every_state_gets_a_null_sheet_key(self):
        """`structured.sheets` is what the compiler resolves plates from. A contract-only
        entity is the v0.30 LOCKED-BUT-NO-SHEETS defect built in at birth: it looks
        finished and compose-spec reports `available: NONE` mid-book."""
        sheets = vm()["structured"]["sheets"]
        self.assertEqual(sorted(sheets), sorted(["blueprint", "master"] + STATES))
        self.assertEqual(set(sheets.values()), {None})

    def test_every_state_gets_a_render_pose_that_passes_its_own_plate(self):
        """A spread naming a pose the entity does not declare is a hard refusal in the
        compiler, so a state with no pose is a state no spread can select."""
        poses = vm()["structured"]["render"]["poses"]
        self.assertEqual(sorted(poses), sorted(["master"] + STATES))
        for k, p in poses.items():
            self.assertEqual(p["sheets"], [k])
        # no `bake` stub: a TODO sentence here would reach a real prompt
        self.assertNotIn("bake", poses["master"])

    def test_the_declared_state_count_gates_promotion(self):
        """SPEC v0.29's `emptyPlatesExpected`. Without it a three-state object promotes
        itself to `locked` after ONE state plate, and the two nobody shot get improvised
        at render time, differently every spread."""
        ent = vm()
        self.assertEqual(ent["contract"]["emptyPlatesExpected"], 3)
        ent["contract"].update({"map": "m", "blocking": "b", "dressing": "d"})
        for shot in ("blueprint", "master", "strained"):
            lock_shot(ent, shot, f"reference/a-shelter/{shot}.png")
        self.assertNotEqual(ent["status"], "locked")
        self.assertTrue(setting_contract_gaps(ent["contract"]))
        for shot in ("beside-the-house", "let-go"):
            lock_shot(ent, shot, f"reference/a-shelter/{shot}.png")
        self.assertEqual(ent["status"], "locked")
        self.assertEqual(ent["contract"]["turnaround"], "reference/a-shelter/master.png")

    def test_no_house_rules_and_no_part_of(self):
        """Both are ROOM concepts. An object has no rooms nested inside it, and
        scaffolding the fields invites an author to fill something nothing inherits."""
        ent = vm()
        self.assertNotIn("houseRules", ent["structured"])
        self.assertNotIn("partOf", ent)

    def test_a_setting_is_unchanged(self):
        """The setting scaffold is the one this kind was wrongly borrowing. It keeps
        every field it had."""
        s = scaffold_entity("setting", "a-room", "A Room", origin_story="s")
        self.assertIn("houseRules", s["structured"])
        self.assertIn("partOf", s)
        self.assertNotIn("states", s["contract"])

    def test_states_are_optional_and_deduped(self):
        ent = scaffold_entity("visual-metaphor", "x", "X", states=None)
        self.assertEqual(ent["contract"]["states"], ["blueprint", "master"])
        self.assertNotIn("emptyPlatesExpected", ent["contract"])
        self.assertEqual(scaffold_entity("visual-metaphor", "x", "X",
                                         states=["a", "a", "b"])["contract"]["states"],
                         ["blueprint", "master", "a", "b"])


class TestPromptsSkeleton(unittest.TestCase):
    def md(self, states=STATES):
        return prompts_skeleton(vm(states), {"name": "r", "anchor": "a.png"})

    def test_one_section_per_state_and_no_room_slots(self):
        md = self.md()
        for s in ["blueprint", "master"] + STATES:
            self.assertIn(f"## {s}  -> reference/a-shelter/{s}.png", md)
        self.assertNotIn("empty-c1", md)
        self.assertNotIn("## scale", md)

    def test_every_level_two_heading_is_a_shot(self):
        """The parser coupling. `chain_matrix` reads level-2 headings AS SHOTS, so a
        prose section at `##` is planned and shot as garbage; the hand-authored file's
        own `## SHOOT ORDER` refused the chain until it was demoted by hand."""
        md = self.md()
        h2 = [l[3:].split("  ->")[0].strip()
              for l in md.splitlines() if l.startswith("## ")]
        self.assertEqual(sorted(h2), sorted(["blueprint", "master"] + STATES))

    def test_the_prose_sections_are_level_three(self):
        md = self.md()
        self.assertIn("### SHOOT ORDER", md)
        self.assertIn("### WHAT MUST NOT DRIFT", md)

    def test_it_says_the_blueprint_is_code_drawn(self):
        """The one instruction that saves a geometry seed from being painted over."""
        md = self.md()
        self.assertIn("abu elevation", md)
        self.assertIn("CODE-DRAWN", md)

    def test_it_says_to_star_the_states(self):
        self.assertIn("--star", self.md())

    def test_a_setting_skeleton_still_describes_cameras(self):
        md = prompts_skeleton(scaffold_entity("setting", "a-room", "A Room"),
                              {"name": "r", "anchor": "a.png"})
        self.assertIn("## empty-c1", md)
        self.assertIn("## scale", md)
        self.assertNotIn("### SHOOT ORDER", md)


if __name__ == "__main__":
    unittest.main()
