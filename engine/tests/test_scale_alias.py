"""`scale` must lock into contract.scalePlate, because the scaffold calls it `scale`.

Earned 2026-08-02 on the-lit-pulpit (Movies Are Sermons, Nation of Fire).

`prompts_skeleton` writes a setting/visual-metaphor prompts.md whose slot list is
["turnaround", "blueprint", "empty-c1", "scale"], so the author is TOLD the shot is
called `scale`. `lock_shot` mapped only `scale-plate` onto contract.scalePlate, so
following the framework's own scaffold filed the plate under emptyPlates instead,
left contract.scalePlate null, and therefore never satisfied SETTING_CONTRACT_FIELDS.
The entity stayed `unlocked`, assert-story refused the story, and nothing anywhere
explained why. It was diagnosed by hand and patched with a throwaway script.

This is the scaffold and the locker disagreeing about a name. The test pins both
ends: the name the scaffold emits, and where that name lands.
"""
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agenticstory.authoring import scaffold_entity, lock_shot, prompts_skeleton
from agenticstory.model import SETTING_CONTRACT_FIELDS


def _full_contract(ent):
    """Fill every non-plate contract field so only the scale slot is in question."""
    c = ent["contract"]
    c.update({"map": "m", "blocking": "b", "dressing": "d", "scale": "s"})
    return ent


class TestScaleAlias(unittest.TestCase):
    def test_scaffold_emits_the_name_scale(self):
        """If this ever changes, the alias below can be revisited."""
        ent = scaffold_entity("setting", "a-room", "A Room", origin_story="s")
        md = prompts_skeleton(ent)
        self.assertIn("## scale", md)
        self.assertNotIn("## scale-plate", md)

    def test_scale_lands_in_scalePlate_not_emptyPlates(self):
        for kind in ("setting", "visual-metaphor"):
            with self.subTest(kind=kind):
                ent = _full_contract(scaffold_entity(kind, "a-room", "A Room", origin_story="s"))
                lock_shot(ent, "scale", "reference/a-room/scale.png")
                self.assertEqual(ent["contract"]["scalePlate"], "reference/a-room/scale.png")
                self.assertNotIn("reference/a-room/scale.png",
                                 ent["contract"].get("emptyPlates") or [])

    def test_scale_plate_spelling_still_works(self):
        ent = _full_contract(scaffold_entity("setting", "a-room", "A Room", origin_story="s"))
        lock_shot(ent, "scale-plate", "reference/a-room/scale.png")
        self.assertEqual(ent["contract"]["scalePlate"], "reference/a-room/scale.png")

    def test_following_the_scaffold_reaches_locked(self):
        """The whole point: shoot every slot the scaffold names, and the entity locks."""
        ent = _full_contract(scaffold_entity("visual-metaphor", "a-room", "A Room", origin_story="s"))
        for shot in ("turnaround", "blueprint", "empty-c1", "scale"):
            lock_shot(ent, shot, f"reference/a-room/{shot}.png")
        missing = [f for f in SETTING_CONTRACT_FIELDS
                   if ent["contract"].get(f) in (None, "", [])]
        self.assertEqual(missing, [], f"contract still unsatisfied: {missing}")
        self.assertEqual(ent["status"], "locked")


if __name__ == "__main__":
    unittest.main()
