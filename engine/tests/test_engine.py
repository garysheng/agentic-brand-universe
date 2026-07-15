"""
Agentic Story engine v0 — tests. Stdlib unittest (no deps).

Runs against a SELF-CONTAINED synthetic fixture (tests/fixtures/example) so the
engine has no dependency on any content repo. The fixture mirrors the real
shape: renderable characters/motifs with on-disk assets, a gated real-person, a
crossover relation, and one UNLOCKED setting that must block a story.

(To validate the real Nation of Fire canon, point the CLI at
 nation-of-fire/universe — the engine is universe-agnostic by design.)
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

from agenticstory import CanonStore, refs, scaffold, SPEC_VERSION  # noqa: E402
from agenticstory.model import Entity  # noqa: E402

UNIVERSE = Path(__file__).resolve().parent / "fixtures" / "example"


class TestCanon(unittest.TestCase):
    def setUp(self):
        self.store = CanonStore(UNIVERSE)

    def test_canon_validates_clean(self):
        problems = self.store.validate_canon()
        self.assertEqual(problems, [], f"canon should be structurally clean, got: {problems}")

    def test_expected_entities_loaded(self):
        for eid in ("hero", "sage", "guide", "the-hall"):
            self.assertIn(eid, self.store.entities)

    def test_crossovers_query(self):
        rels = self.store.crossovers("hero")
        others = {r.to if r.from_ == "hero" else r.from_ for r in rels}
        self.assertIn("sage", others)

    def test_real_person_gated(self):
        self.assertEqual(self.store.entity("sage").real_person["approval"]["state"], "gated")

    def test_setting_is_unlocked(self):
        self.assertFalse(self.store.entity("the-hall").is_locked_setting())


class TestLoadBearing(unittest.TestCase):
    def setUp(self):
        self.store = CanonStore(UNIVERSE)

    def test_featured_entity_art_resolves_on_disk(self):
        for cid in ("hero", "sage", "guide"):
            resolved, missing = refs.resolve_entity_assets(self.store, cid)
            self.assertEqual(missing, [], f"{cid} art should resolve on disk, missing: {missing}")
            self.assertTrue(resolved)

    def test_assert_story_only_blocks_on_unlocked_setting(self):
        problems = refs.assert_story(self.store, "first-trial")
        self.assertTrue(problems, "expected the unlocked hall to block the story")
        self.assertTrue(all("hall" in p for p in problems),
                        f"only the unlocked setting should block; got: {problems}")

    def test_assert_spread_without_setting_passes(self):
        problems = refs.assert_spread(self.store, ["hero", "sage"], None)
        self.assertEqual(problems, [], f"spread should pass, got: {problems}")

    def test_assert_spread_unlocked_setting_blocks(self):
        problems = refs.assert_spread(self.store, ["hero"], "the-hall")
        self.assertTrue(any("hall" in p for p in problems))


class TestValidationCatchesBreakage(unittest.TestCase):
    def test_missing_required_sheet_is_caught(self):
        good = CanonStore(UNIVERSE).entity("hero")
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


class TestScaffold(unittest.TestCase):
    """`init` must produce a universe that loads and validates GREEN out of the box,
    carries spec provenance, and (with --example) self-demonstrates the load-bearing
    gate: structurally valid, but assert-story refuses until real assets exist."""

    def test_empty_scaffold_validates_green(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "myverse"
            written = scaffold.scaffold_universe(target, name="myverse")
            self.assertTrue(written)
            store = CanonStore(target)
            self.assertEqual(store.validate_canon(), [], "empty scaffold must validate clean")

    def test_manifest_carries_spec_provenance(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "myverse"
            scaffold.scaffold_universe(target, name="myverse")
            man = json.loads((target / "universe.json").read_text())
            self.assertEqual(man["name"], "myverse")
            self.assertEqual(man["spec"]["version"], SPEC_VERSION)
            self.assertIn("agenticstory.wiki", man["spec"]["wiki"])
            self.assertIn(f"v{SPEC_VERSION}", man["spec"]["conformsTo"])

    def test_gate_wrapper_written_and_executable(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "myverse"
            scaffold.scaffold_universe(target, name="myverse")
            gate = target / "canon" / "scripts" / "assert.sh"
            self.assertTrue(gate.exists())
            self.assertTrue(gate.stat().st_mode & 0o111, "assert.sh must be executable")

    def test_example_scaffold_validates_green(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "exverse"
            scaffold.scaffold_universe(target, name="exverse", example=True)
            store = CanonStore(target)
            self.assertEqual(store.validate_canon(), [], "example scaffold must validate clean")
            for eid in ("protagonist", "the-crossroads"):
                self.assertIn(eid, store.entities)
            self.assertIn("the-first-step", store.stories)

    def test_example_gate_refuses_until_assets_exist(self):
        # The example character's sheets are placeholder paths not on disk, so the
        # load-bearing gate must refuse the story — that refusal is the feature.
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "exverse"
            scaffold.scaffold_universe(target, name="exverse", example=True)
            store = CanonStore(target)
            problems = refs.assert_story(store, "the-first-step")
            self.assertTrue(problems, "gate should refuse: example assets are placeholders")
            self.assertTrue(any("protagonist" in p for p in problems), problems)

    def test_refuses_overwrite_without_force(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "myverse"
            scaffold.scaffold_universe(target, name="myverse")
            with self.assertRaises(FileExistsError):
                scaffold.scaffold_universe(target, name="myverse")
            # force overwrites cleanly
            written = scaffold.scaffold_universe(target, name="myverse2", force=True)
            self.assertTrue(written)
            self.assertEqual(json.loads((target / "universe.json").read_text())["name"], "myverse2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
