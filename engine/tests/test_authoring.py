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

    def test_a_refused_lock_does_not_mutate_the_entity(self):
        """Validation runs before the authority stamp, so a rejected lock leaves no
        trace. Otherwise a typo'd look key still moved authority.lockedOn and warned
        about an approver for an operation that never happened."""
        e = self._char()
        with self.assertRaises(ValueError):
            lock_shot(e, "forward-fullbody", "reference/beef/x.png", look="era-2031")
        self.assertNotIn("authority", e)
        self.assertNotIn("sheets", e["structured"]["altLooks"]["era-2030"])

    def test_default_path_is_unchanged_when_no_look_is_passed(self):
        e = self._char()
        lock_shot(e, "forward-fullbody", "reference/beef/forward-fullbody.png")
        self.assertEqual(e["structured"]["sheets"]["forward-fullbody"],
                         "reference/beef/forward-fullbody.png")
        self.assertEqual(sorted(e["structured"]["requiredForRender"]),
                         ["face-neutral", "forward-fullbody"])


if __name__ == "__main__":
    unittest.main()


class PromptsSkeletonTest(unittest.TestCase):
    """add-entity must emit the prompts.md that shoot-references reads as input.

    Nothing wrote it before, so the step between scaffolding an entity and shooting
    it was hand-rolled in every universe (ten times in one sitting on 2026-07-26).
    """

    def test_has_a_section_per_matrix_slot(self):
        from agenticstory.authoring import scaffold_entity, prompts_skeleton
        ent = scaffold_entity("character", "jo-tester", "Jo Tester")
        md = prompts_skeleton(ent, {"anchor": "reference/style/hero.png",
                                    "name": "soft painterly storybook realism",
                                    "rejectedPoles": ["photoreal", "anime"]})
        for shot in ent["structured"]["sheets"]:
            self.assertIn(f"## {shot}  -> reference/jo-tester/{shot}.png", md)
        self.assertIn("reference/style/hero.png", md)
        self.assertIn("photoreal, anime", md)
        self.assertIn("REQUIRED before any render", md)

    def test_refuses_when_the_register_is_unlocked(self):
        from agenticstory.authoring import scaffold_entity, prompts_skeleton
        md = prompts_skeleton(scaffold_entity("prop", "thing", "Thing"), {"anchor": None})
        self.assertIn("STOP", md)

    def test_uses_contract_slots_for_a_setting(self):
        from agenticstory.authoring import scaffold_entity, prompts_skeleton
        md = prompts_skeleton(scaffold_entity("setting", "room", "Room"), {"anchor": "a.png"})
        for slot in ("turnaround", "blueprint", "empty-c1", "scale"):
            self.assertIn(f"## {slot}  -> reference/room/{slot}.png", md)


class RequiredSetOverrideTest(unittest.TestCase):
    """SPEC v0.11: an entity may demand a STRICTER gate than its kind's minimum.

    Four entities in nation-of-fire had independently invented
    `requiredForRenderOnLock` before anything read it, so the stricter intent was
    silently dropped and lock_shot clobbered it back to the kind default.
    """

    def _char(self, override=None):
        from agenticstory.authoring import scaffold_entity
        ent = scaffold_entity("character", "c", "C")
        if override is not None:
            ent["structured"]["requiredForRenderOnLock"] = override
        return ent

    def test_defaults_to_the_kind_minimum(self):
        from agenticstory.authoring import required_set_for
        self.assertEqual(set(required_set_for(self._char())),
                         {"forward-fullbody", "face-neutral"})

    def test_honours_a_stricter_override(self):
        from agenticstory.authoring import required_set_for
        ent = self._char(["face-neutral", "face-3q", "forward-fullbody"])
        self.assertEqual(set(required_set_for(ent)),
                         {"face-neutral", "face-3q", "forward-fullbody"})

    def test_can_never_drop_below_the_kind_minimum(self):
        from agenticstory.authoring import required_set_for
        self.assertIn("forward-fullbody", required_set_for(self._char(["face-neutral"])))

    def test_rejects_a_shot_outside_the_matrix(self):
        from agenticstory.authoring import required_set_for
        with self.assertRaises(ValueError):
            required_set_for(self._char(["face-neutral", "not-a-real-shot"]))

    def test_lock_shot_no_longer_clobbers_the_override(self):
        from agenticstory.authoring import lock_shot, required_set_for
        ent = self._char(["face-neutral", "face-3q", "forward-fullbody"])
        for shot in ("face-neutral", "face-3q", "forward-fullbody"):
            lock_shot(ent, shot, f"reference/c/{shot}.png")
        self.assertEqual(set(ent["structured"]["requiredForRender"]),
                         {"face-neutral", "face-3q", "forward-fullbody"})
