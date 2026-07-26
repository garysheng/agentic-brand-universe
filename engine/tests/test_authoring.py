"""lock_shot must write a shot into the schema its KIND actually uses.

Regression, found live on encounter-school in nation-of-fire 2026-07-25: lock_shot
wrote every kind into `structured.sheets`, but settings and visual-metaphors are
matrixed via their `contract` (see matrix.py and refs.resolve_setting). So a setting
could be "locked" shot by shot, print success each time, and still be refused by
assert_story because contract.turnaround stayed null. A silent wrong-schema write is
worse than a crash: nothing in the pipeline reports it.

NOTE: these are unittest TestCases on purpose. run-tests.sh drives the engine with
`unittest discover`, which does not collect bare pytest-style functions, so a
pytest-shaped test here would "pass" by never running at all.
"""
import unittest

from agenticstory.authoring import lock_shot


def _setting():
    return {
        "id": "a-school", "kind": "setting", "status": "unlocked",
        "contract": {"turnaround": None, "emptyPlates": [], "blueprint": None,
                     "scalePlate": None, "map": "m", "blocking": "b",
                     "dressing": "d", "scale": "s"},
    }


class TestLockShotSettingContract(unittest.TestCase):
    def test_named_slots_land_in_the_contract(self):
        e = _setting()
        lock_shot(e, "turnaround", "reference/a-school/turnaround.png")
        self.assertEqual(e["contract"]["turnaround"], "reference/a-school/turnaround.png")
        self.assertEqual(e["structured"]["sheets"]["turnaround"],
                         "reference/a-school/turnaround.png",
                         "the renderer selects plates by sheet key, so a setting needs both")

    def test_unnamed_shots_accumulate_as_empty_plates(self):
        e = _setting()
        lock_shot(e, "empty-a1-yard", "reference/a-school/a1.png")
        lock_shot(e, "empty-a2-room", "reference/a-school/a2.png")
        self.assertEqual(e["contract"]["emptyPlates"],
                         ["reference/a-school/a1.png", "reference/a-school/a2.png"])

    def test_relocking_a_plate_does_not_duplicate_it(self):
        e = _setting()
        lock_shot(e, "empty-a1-yard", "reference/a-school/a1.png")
        lock_shot(e, "empty-a1-yard", "reference/a-school/a1.png")
        self.assertEqual(len(e["contract"]["emptyPlates"]), 1)

    def test_scale_plate_alias_maps_to_scalePlate(self):
        e = _setting()
        lock_shot(e, "scale-plate", "reference/a-school/scale.png")
        self.assertEqual(e["contract"]["scalePlate"], "reference/a-school/scale.png")

    def test_partial_art_never_opens_the_gate(self):
        e = _setting()
        lock_shot(e, "turnaround", "reference/a-school/turnaround.png")
        lock_shot(e, "empty-a1-yard", "reference/a-school/a1.png")
        self.assertEqual(e["status"], "unlocked")

    def test_a_complete_contract_promotes_the_setting(self):
        e = _setting()
        lock_shot(e, "turnaround", "reference/a-school/turnaround.png")
        lock_shot(e, "empty-a1-yard", "reference/a-school/a1.png")
        lock_shot(e, "blueprint", "reference/a-school/blueprint.png")
        self.assertEqual(e["status"], "unlocked", "scalePlate still missing")
        lock_shot(e, "scale-plate", "reference/a-school/scale.png")
        self.assertEqual(e["status"], "locked")

    def test_a_missing_descriptor_still_blocks_promotion(self):
        e = _setting()
        e["contract"]["dressing"] = ""
        for shot, p in (("turnaround", "t.png"), ("empty-a1", "a1.png"),
                        ("blueprint", "b.png"), ("scale-plate", "s.png")):
            lock_shot(e, shot, p)
        self.assertEqual(e["status"], "unlocked",
                         "prose descriptors are part of the contract, not decoration")

    def test_empty_plates_are_also_addressable_as_sheets(self):
        """The compiler picks a plate by key; the gate counts them in emptyPlates."""
        e = _setting()
        lock_shot(e, "empty-a2-classroom", "reference/a-school/a2.png")
        self.assertIn("reference/a-school/a2.png", e["contract"]["emptyPlates"])
        self.assertEqual(e["structured"]["sheets"]["empty-a2-classroom"],
                         "reference/a-school/a2.png")

    def test_visual_metaphor_uses_the_contract_too(self):
        e = _setting()
        e["kind"] = "visual-metaphor"
        lock_shot(e, "turnaround", "reference/a-school/turnaround.png")
        self.assertEqual(e["contract"]["turnaround"], "reference/a-school/turnaround.png")


class TestLockStampsApproval(unittest.TestCase):
    """Locking is the approval act, so it is the only moment the approver is guaranteed
    knowable. Caught twice in one session, the second time on a motif created that hour by
    the person who had just fixed the first one."""

    def test_locking_stamps_the_date(self):
        e = {"id": "e", "kind": "motif", "structured": {"sheets": {}, "requiredForRender": []}}
        lock_shot(e, "hero", "reference/e/hero.png")
        self.assertTrue(e["authority"]["lockedOn"], "a lock with no date cannot be audited")

    def test_locking_does_not_overwrite_an_existing_date(self):
        e = {"id": "e", "kind": "motif", "authority": {"lockedOn": "2026-01-01"},
             "structured": {"sheets": {}, "requiredForRender": []}}
        lock_shot(e, "hero", "reference/e/hero.png")
        self.assertEqual(e["authority"]["lockedOn"], "2026-01-01")

    def test_a_real_approver_is_left_alone(self):
        e = {"id": "e", "kind": "motif", "authority": {"lockedBy": "gary"},
             "structured": {"sheets": {}, "requiredForRender": []}}
        lock_shot(e, "hero", "reference/e/hero.png")
        self.assertEqual(e["authority"]["lockedBy"], "gary")


class TestLockShotMatrixedKinds(unittest.TestCase):
    def test_motif_still_uses_sheets_and_promotes_required(self):
        e = {"id": "a-motif", "kind": "motif",
             "structured": {"sheets": {}, "requiredForRender": []}}
        lock_shot(e, "hero", "reference/a-motif/hero.png")
        self.assertEqual(e["structured"]["sheets"]["hero"], "reference/a-motif/hero.png")
        self.assertEqual(e["structured"]["requiredForRender"], ["hero"])
        self.assertNotIn("contract", e)

    def test_character_required_set_waits_for_both_shots(self):
        e = {"id": "a-person", "kind": "character",
             "structured": {"sheets": {}, "requiredForRender": []}}
        lock_shot(e, "face-neutral", "reference/a-person/face-neutral.png")
        self.assertEqual(e["structured"]["requiredForRender"], ["face-neutral"])
        lock_shot(e, "forward-fullbody", "reference/a-person/forward-fullbody.png")
        self.assertEqual(sorted(e["structured"]["requiredForRender"]),
                         ["face-neutral", "forward-fullbody"])


class TestLockShotIntoAnAltLook(unittest.TestCase):
    """SPEC v0.10 declared-future eras needed art, and there was no verb for it:
    `altLooks` could declare a different body but only `structured.sheets` could be
    locked, so registering an era plate meant hand-editing the entity JSON."""

    def _char(self):
        return {"id": "beef", "kind": "character",
                "structured": {"sheets": {"face-neutral": "reference/beef/face.png"},
                               "requiredForRender": ["face-neutral"],
                               "altLooks": {"era-2030": {"keepSheets": ["face-neutral"]}}}}

    def test_locks_into_the_look_not_the_default_matrix(self):
        e = self._char()
        lock_shot(e, "forward-fullbody", "reference/beef/era-2030/forward-fullbody.png",
                  look="era-2030")
        al = e["structured"]["altLooks"]["era-2030"]
        self.assertEqual(al["sheets"]["forward-fullbody"],
                         "reference/beef/era-2030/forward-fullbody.png")
        self.assertNotIn("forward-fullbody", e["structured"]["sheets"])

    def test_never_touches_required_for_render(self):
        """requiredForRender is the DEFAULT look's gate. An era plate must not be
        able to satisfy it, or a character with no present-day body sheet would
        render as gate-real off a future one."""
        e = self._char()
        lock_shot(e, "forward-fullbody", "reference/beef/era-2030/forward-fullbody.png",
                  look="era-2030")
        self.assertEqual(e["structured"]["requiredForRender"], ["face-neutral"])

    def test_unknown_look_is_refused(self):
        """A typo would otherwise mint a look nothing selects and no read-back checks."""
        e = self._char()
        with self.assertRaises(ValueError) as cm:
            lock_shot(e, "forward-fullbody", "reference/beef/x.png", look="era-2031")
        self.assertIn("era-2031", str(cm.exception))
        self.assertIn("era-2030", str(cm.exception))

    def test_default_path_is_unchanged_when_no_look_is_passed(self):
        e = self._char()
        lock_shot(e, "forward-fullbody", "reference/beef/forward-fullbody.png")
        self.assertEqual(e["structured"]["sheets"]["forward-fullbody"],
                         "reference/beef/forward-fullbody.png")
        self.assertEqual(sorted(e["structured"]["requiredForRender"]),
                         ["face-neutral", "forward-fullbody"])


if __name__ == "__main__":
    unittest.main()
