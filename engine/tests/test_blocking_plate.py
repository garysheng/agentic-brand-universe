"""SPEC v0.19: contract.blockingPlate, the seating chart as a picture.

Earned on the-creamery-counter (will-there-be-ice-cream, 2026-08-01): a two-hander
whose two people swapped viewer-left and viewer-right across six of twenty-six
spreads, and whose stools rendered in front of a glass display case where neither
person could set a bowl down. `blocking` is prose and `structured.seating` is one
sentence; neither shows the model a geometry it can copy.
"""
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]
                       / "skills/compose-spread/scripts"))
from agenticstory.authoring import scaffold_entity, lock_shot
from agenticstory.model import SETTING_CONTRACT_FIELDS
from assemble_prompt import resolve_setting


def _setting(**contract):
    base = {"emptyPlates": [], "map": "m", "blocking": "b", "dressing": "d", "scale": "s"}
    base.update(contract)
    return {"id": "a-room", "kind": "setting",
            "structured": {"sheets": {"master": "reference/a-room/master.png"}},
            "contract": base}


class TestBlockingPlate(unittest.TestCase):
    def test_setting_scaffolds_the_slot(self):
        ent = scaffold_entity("setting", "a-room", "A Room", origin_story="s")
        self.assertIn("blockingPlate", ent["contract"])
        self.assertIsNone(ent["contract"]["blockingPlate"])

    def test_it_is_advisory_so_no_existing_setting_unlocks(self):
        # If it joined the required contract, every already-locked setting in every
        # universe would silently drop back to unlocked on its next lock-shot.
        self.assertNotIn("blockingPlate", SETTING_CONTRACT_FIELDS)

    def test_lock_shot_routes_it_to_the_contract_not_to_emptyplates(self):
        for shot in ("blocking", "blocking-plate"):
            with self.subTest(shot=shot):
                ent = scaffold_entity("setting", "a-room", "A Room", origin_story="s")
                path = f"reference/a-room/{shot}.png"
                e = lock_shot(ent, shot, path)
                self.assertEqual(e["contract"]["blockingPlate"], path)
                # an emptyPlate is people-free by definition; this one has mannequins
                self.assertNotIn(path, e["contract"].get("emptyPlates") or [])

    def test_compiler_passes_it_on_every_camera(self):
        refs, _ = resolve_setting(
            _setting(blockingPlate="reference/a-room/blocking.png"), "master")
        self.assertIn("reference/a-room/blocking.png", refs,
                      "placement is continuity, so it rides along on every camera")

    def test_absent_slot_changes_nothing(self):
        refs, _ = resolve_setting(_setting(), "master")
        self.assertTrue(all("blocking" not in r for r in refs))


if __name__ == "__main__":
    unittest.main()
