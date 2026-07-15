"""
Agentic Story engine v0 — tests. Stdlib unittest (no deps).

These run against the REAL Nation of Fire reference universe, so they prove the
engine executes on real canon + real art on disk:
  - the canon validates clean
  - crossovers resolve as graph queries
  - assert_story on Not Every Fire Is Holy: every featured entity's art RESOLVES
    on disk, and the ONLY remaining problems are the arena setting being unlocked
    (the load-bearing gate correctly refuses it)
  - a deliberately broken entity is caught
"""
import copy
import sys
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

from agenticstory import CanonStore, refs  # noqa: E402
from agenticstory.model import Entity  # noqa: E402

UNIVERSE = ENGINE_DIR.parent / "universes" / "nation-of-fire"


class TestCanon(unittest.TestCase):
    def setUp(self):
        self.store = CanonStore(UNIVERSE)

    def test_canon_validates_clean(self):
        problems = self.store.validate_canon()
        self.assertEqual(problems, [], f"canon should be structurally clean, got: {problems}")

    def test_expected_entities_loaded(self):
        for eid in ("jerry-man", "brenda-gentry", "wisp", "the-fear-thing",
                    "anjali-sambalu", "wally-boone", "the-arena"):
            self.assertIn(eid, self.store.entities)

    def test_crossovers_query(self):
        rels = self.store.crossovers("jerry-man")
        others = {r.to if r.from_ == "jerry-man" else r.from_ for r in rels}
        self.assertIn("brenda-gentry", others)

    def test_real_person_gated(self):
        brenda = self.store.entity("brenda-gentry")
        self.assertEqual(brenda.real_person["approval"]["state"], "gated")

    def test_arena_is_unlocked(self):
        self.assertFalse(self.store.entity("the-arena").is_locked_setting())


class TestLoadBearing(unittest.TestCase):
    def setUp(self):
        self.store = CanonStore(UNIVERSE)

    def test_featured_character_art_resolves_on_disk(self):
        # every featured renderable entity's required sheets must be REAL files
        for cid in ("jerry-man", "brenda-gentry", "anjali-sambalu", "wally-boone", "wisp", "the-fear-thing"):
            resolved, missing = refs.resolve_entity_assets(self.store, cid)
            self.assertEqual(missing, [], f"{cid} art should resolve on disk, missing: {missing}")
            self.assertTrue(resolved, f"{cid} should resolve at least one sheet")

    def test_assert_story_only_blocks_on_arena(self):
        problems = refs.assert_story(self.store, "not-every-fire-is-holy")
        # There MUST be problems (the arena is not locked yet)...
        self.assertTrue(problems, "expected the unlocked arena to block the story")
        # ...and every problem must be about the arena — no character/art/provenance gaps.
        self.assertTrue(all("arena" in p for p in problems),
                        f"only the arena should block; got: {problems}")

    def test_assert_spread_endorsement_passes(self):
        # spread 4 (Anjali + Boone, no arena) is fully renderable
        problems = refs.assert_spread(self.store, ["anjali-sambalu", "wally-boone"], None)
        self.assertEqual(problems, [], f"endorsement spread should pass, got: {problems}")

    def test_assert_spread_arena_blocks(self):
        problems = refs.assert_spread(self.store, ["anjali-sambalu"], "the-arena")
        self.assertTrue(any("arena" in p for p in problems))


class TestValidationCatchesBreakage(unittest.TestCase):
    def test_missing_required_sheet_is_caught(self):
        good = CanonStore(UNIVERSE).entity("jerry-man")
        broken = copy.deepcopy(good.raw)
        broken["structured"]["sheets"].pop("face")  # required but now absent
        problems = Entity.from_dict(broken).validate()
        self.assertTrue(any("face" in p for p in problems), f"should flag missing face, got {problems}")

    def test_realperson_without_photostack_is_caught(self):
        broken = {"id": "x", "kind": "character",
                  "structured": {"sheets": {"g": "p"}, "requiredForRender": ["g"]},
                  "realPerson": {"approval": {"state": "gated"}}}
        problems = Entity.from_dict(broken).validate()
        self.assertTrue(any("photoStack" in p for p in problems))


if __name__ == "__main__":
    unittest.main(verbosity=2)
