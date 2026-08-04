"""`master` must lock into a visual-metaphor's contract.turnaround.

Earned 2026-08-03 on nation-of-fire `the-shelter-he-held-up` (What a Relief).

SPEC 12 defines the visual-metaphor matrix as "a locked master plus `state` plates", so
`master` is the anchor plate that kind's contract calls `turnaround`. `lock_shot` had no
entry for it, so `abu lock-shot <universe> <vm> master <path>` filed the anchor into
`contract.emptyPlates`, left `contract.turnaround` null, and could therefore never clear
`setting_contract_gaps`. A complete and correct four-plate shoot ended at
`status: unlocked` with no error anywhere, and the repair was hand-editing the JSON to
match an earlier sibling that had been hand-edited the same way.

Third member of the family `test_scale_alias.py` opened: the vocabulary the SPEC and the
scaffolder hand the author is not the vocabulary the locker accepts. The tests pin both
ends, the name the author is told to use and where that name lands.
"""
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agenticstory.authoring import scaffold_entity, lock_shot
from agenticstory.model import setting_contract_gaps

MASTER = "reference/a-shelter/master.png"


def _vm(**contract):
    """A visual-metaphor with every non-plate descriptor filled, so the only thing in
    question is where a locked plate lands."""
    ent = scaffold_entity("visual-metaphor", "a-shelter", "A Shelter", origin_story="s")
    ent["contract"].update({"map": "m", "blocking": "b", "dressing": "d", "scale": "s"})
    ent["contract"].update(contract)
    return ent


class TestMasterAlias(unittest.TestCase):
    def test_master_sets_turnaround(self):
        ent = _vm()
        lock_shot(ent, "master", MASTER)
        self.assertEqual(ent["contract"]["turnaround"], MASTER)

    def test_master_is_not_filed_as_an_empty_plate(self):
        """The defect's visible symptom: the anchor sitting in the state-plate list."""
        ent = _vm()
        lock_shot(ent, "master", MASTER)
        self.assertNotIn(MASTER, ent["contract"].get("emptyPlates") or [])

    def test_master_still_reaches_the_sheet_selector(self):
        """`structured.sheets` is keyed by the SHOT name, never by the contract slot: a
        prompts.md `REFS: <id>@master` selector and compose-spread's plate picker both
        look up `master`. Aliasing the contract slot must not rename the sheet."""
        ent = _vm()
        lock_shot(ent, "master", MASTER)
        self.assertEqual(ent["structured"]["sheets"]["master"], MASTER)

    def test_a_state_plate_still_lands_in_emptyPlates(self):
        """The alias is for the anchor only. States are the rest of the matrix."""
        ent = _vm()
        lock_shot(ent, "strained", "reference/a-shelter/strained.png")
        self.assertIn("reference/a-shelter/strained.png", ent["contract"]["emptyPlates"])
        self.assertIsNone(ent["contract"]["turnaround"])

    def test_shooting_master_plus_states_reaches_locked(self):
        """The whole point. Shoot the matrix SPEC 12 describes for this kind and the
        entity promotes itself, with no hand-edit of the JSON."""
        ent = _vm()
        for shot in ("blueprint", "master", "strained", "beside-the-house", "let-go"):
            lock_shot(ent, shot, f"reference/a-shelter/{shot}.png")
        self.assertEqual(setting_contract_gaps(ent["contract"]), [])
        self.assertEqual(ent["status"], "locked")

    def test_a_setting_is_untouched_by_the_alias(self):
        """A `setting`'s matrix has no `master` (SPEC 12: turnaround + per-angle empty
        plates + blueprint). Promoting one to its turnaround would invent a slot the spec
        does not give that kind, so the alias is scoped to the visual-metaphor."""
        ent = scaffold_entity("setting", "a-room", "A Room", origin_story="s")
        ent["contract"].update({"map": "m", "blocking": "b", "dressing": "d", "scale": "s"})
        lock_shot(ent, "master", "reference/a-room/master.png")
        self.assertIsNone(ent["contract"]["turnaround"])
        self.assertIn("reference/a-room/master.png", ent["contract"]["emptyPlates"])


if __name__ == "__main__":
    unittest.main()
