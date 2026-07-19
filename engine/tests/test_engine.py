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


class TestLockLevel(unittest.TestCase):
    def test_lock_level_reports_matrix_completeness(self):
        import tempfile, json, os
        from pathlib import Path
        from agenticstory import CanonStore
        from agenticstory.refs import lock_level
        d = Path(tempfile.mkdtemp())
        (d / "canon" / "entities").mkdir(parents=True)
        (d / "stories").mkdir()
        (d / "canon" / "relations").mkdir()
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        art = d / "art"; art.mkdir()
        def png(name):
            p = art / name; p.write_bytes(b"x"); return f"art/{name}"
        # a character with the FULL matrix on disk -> locked
        full = {
            "id": "hero", "kind": "character",
            "structured": {
                "sheets": {k: png(f"{k}.png") for k in
                           ["face-neutral","face-3q","expressions","forward-fullbody",
                            "profile-left","profile-right","back","signature-pose"]},
                "requiredForRender": ["forward-fullbody","face-neutral"],
            },
        }
        # a character with only required on disk (legacy-style keys) -> partial
        partial = {
            "id": "sidekick", "kind": "character",
            "structured": {"sheets": {"man": png("man.png"), "face": png("face.png")},
                           "requiredForRender": ["man","face"]},
        }
        # a character with no sheets -> stub
        stub = {"id": "ghost", "kind": "character", "structured": {"sheets": {}, "requiredForRender": []}}
        for e in (full, partial, stub):
            (d / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))
        store = CanonStore(d)
        self.assertEqual(lock_level(store, "hero"), "locked")
        self.assertEqual(lock_level(store, "sidekick"), "partial")
        self.assertEqual(lock_level(store, "ghost"), "stub")
        self.assertEqual(lock_level(store, "nonexistent"), "stub")

    def test_lock_level_never_raises_on_malformed_canon(self):
        """lock_level must never raise, even on malformed sheets or contract fields."""
        import tempfile, json
        from pathlib import Path
        from agenticstory import CanonStore
        from agenticstory.refs import lock_level
        d = Path(tempfile.mkdtemp())
        (d / "canon" / "entities").mkdir(parents=True)
        (d / "stories").mkdir()
        (d / "canon" / "relations").mkdir()
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        art = d / "art"; art.mkdir()
        def png(name):
            p = art / name; p.write_bytes(b"x"); return f"art/{name}"

        # Character with sheets as a list instead of dict (malformed)
        malformed_sheets_list = {
            "id": "bad-sheets-list", "kind": "character",
            "structured": {
                "sheets": ["face.png", "body.png"],  # WRONG: should be dict
                "requiredForRender": []
            }
        }

        # Character with sheets as an empty list (malformed)
        malformed_sheets_empty = {
            "id": "bad-sheets-empty", "kind": "character",
            "structured": {
                "sheets": [],  # WRONG: should be dict
                "requiredForRender": []
            }
        }

        # Setting with contract having non-string field value (malformed)
        malformed_setting = {
            "id": "bad-setting", "kind": "setting",
            "status": "locked",
            "contract": {
                "turnaround": 123,  # WRONG: should be string path
                "blueprint": "path/to/blueprint.png",
                "emptyPlates": [png("empty1.png")],
                "map": "A hall",
                "blocking": "Characters stand here",
                "dressing": "Props scattered"
            }
        }

        for e in (malformed_sheets_list, malformed_sheets_empty, malformed_setting):
            (d / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))

        store = CanonStore(d)

        # All should return a valid level string, never raise
        result1 = lock_level(store, "bad-sheets-list")
        self.assertIn(result1, ("stub", "partial", "locked"),
                      f"malformed sheets list should return valid level, got {result1}")

        result2 = lock_level(store, "bad-sheets-empty")
        self.assertIn(result2, ("stub", "partial", "locked"),
                      f"malformed sheets empty should return valid level, got {result2}")

        result3 = lock_level(store, "bad-setting")
        self.assertIn(result3, ("stub", "partial", "locked"),
                      f"malformed setting contract should return valid level, got {result3}")


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

    def test_scaffold_emits_register_and_reference_dir(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "demo-universe"
            scaffold.scaffold_universe(target, name="demo")
            man = json.loads((target / "universe.json").read_text())
            reg = man["identity"]["register"]
            self.assertEqual(reg["name"], "detailed comic book")
            self.assertIsNone(reg["anchor"])            # not locked yet
            self.assertIn("photoreal", reg["rejectedPoles"])
            self.assertTrue((target / "reference" / "register" / ".gitkeep").exists())

    def test_scaffold_entity_validates_and_reports_stub(self):
        import json
        from agenticstory import CanonStore, scaffold_entity
        from agenticstory.model import Entity
        from agenticstory.refs import lock_level
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        (d / "canon" / "entities").mkdir(parents=True)
        (d / "canon" / "relations").mkdir()
        (d / "stories").mkdir()
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        # character (fictional): 8 matrix slots, requiredForRender empty, validates, lock_level stub
        ch = scaffold_entity("character", "hero", "Hero")
        self.assertEqual(set(ch["structured"]["sheets"].keys()),
                         {"face-neutral","face-3q","expressions","forward-fullbody",
                          "profile-left","profile-right","back","signature-pose"})
        self.assertEqual(ch["structured"]["requiredForRender"], [])
        self.assertNotIn("realPerson", ch)
        self.assertEqual(Entity.from_dict(ch).validate(), [])
        # real person: photo stack required -> realPerson gated
        rp = scaffold_entity("character", "vip", "Vip", photo_stack=["reference/vip/photos/01.jpg"])
        self.assertEqual(rp["realPerson"]["approval"]["state"], "gated")
        self.assertEqual(rp["realPerson"]["photoStack"], ["reference/vip/photos/01.jpg"])
        self.assertEqual(Entity.from_dict(rp).validate(), [])
        # setting: unlocked contract, validates
        st = scaffold_entity("setting", "the-hall", "The Hall")
        self.assertEqual(st["status"], "unlocked")
        self.assertIn("contract", st)
        self.assertEqual(Entity.from_dict(st).validate(), [])
        # prop: hero+detail slots
        pr = scaffold_entity("prop", "the-key", "The Key")
        self.assertEqual(set(pr["structured"]["sheets"].keys()), {"hero","detail"})
        self.assertEqual(Entity.from_dict(pr).validate(), [])
        # write them and confirm lock_level stub + store validates
        for e in (ch, rp, st, pr):
            (d / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))
        store = CanonStore(d)
        self.assertEqual(store.validate_canon(), [])
        self.assertEqual(lock_level(store, "hero"), "stub")
        self.assertEqual(lock_level(store, "the-hall"), "stub")


class TestCraftCanon(unittest.TestCase):
    def test_craft_canon_loads_and_validates(self):
        import json, tempfile
        from pathlib import Path
        from agenticstory import CanonStore
        from agenticstory.model import CraftCanon
        d = Path(tempfile.mkdtemp())
        (d / "canon" / "entities").mkdir(parents=True)
        (d / "canon" / "relations").mkdir(); (d / "stories").mkdir()
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        # no craft dir yet -> still validates
        store = CanonStore(d)
        self.assertEqual(store.validate_canon(), [])
        self.assertEqual(store.craft, {})
        # add a craft dir with a good and a bad record
        (d / "canon" / "craft").mkdir()
        (d / "canon" / "craft" / "obedient-servant.json").write_text(json.dumps(
            {"id": "obedient-servant", "kind": "spine", "name": "Obedient Servant",
             "summary": "the servant obeys and God acts", "rules": "...", "origin": "test"}))
        (d / "canon" / "craft" / "bad.json").write_text(json.dumps(
            {"id": "bad", "kind": "not-a-kind", "name": "Bad"}))
        store = CanonStore(d)
        self.assertIn("obedient-servant", store.craft)
        self.assertIsInstance(store.craft["obedient-servant"], CraftCanon)
        problems = store.validate_canon()
        self.assertTrue(any("bad" in p and "kind" in p for p in problems))
        # a valid-only store validates clean
        (d / "canon" / "craft" / "bad.json").unlink()
        self.assertEqual(CanonStore(d).validate_canon(), [])


class TestLockShot(unittest.TestCase):
    def test_lock_shot_promotes_required_and_keeps_validate_green(self):
        import json, tempfile
        from pathlib import Path
        from agenticstory import CanonStore, scaffold_entity, lock_shot
        from agenticstory.model import Entity
        from agenticstory.refs import lock_level
        d = Path(tempfile.mkdtemp())
        (d / "canon" / "entities").mkdir(parents=True)
        (d / "canon" / "relations").mkdir(); (d / "stories").mkdir()
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        art = d / "art"; art.mkdir()
        def png(name):
            p = art / name; p.write_bytes(b"x"); return f"art/{name}"
        ch = scaffold_entity("character", "hero", "Hero")
        # lock ONE required shot -> requiredForRender gains just that key, validate green, still partial
        lock_shot(ch, "forward-fullbody", png("ff.png"))
        self.assertEqual(ch["structured"]["requiredForRender"], ["forward-fullbody"])
        # lock the other required -> both required present
        lock_shot(ch, "face-neutral", png("fn.png"))
        self.assertEqual(set(ch["structured"]["requiredForRender"]), {"forward-fullbody", "face-neutral"})
        self.assertEqual(Entity.from_dict(ch).validate(), [])
        (d / "canon" / "entities" / "hero.json").write_text(json.dumps(ch))
        store = CanonStore(d)
        self.assertEqual(lock_level(store, "hero"), "partial")   # required locked, matrix not complete
        # lock the rest of the matrix -> locked
        for shot in ["face-3q", "expressions", "profile-left", "profile-right", "back", "signature-pose"]:
            lock_shot(ch, shot, png(f"{shot}.png"))
        (d / "canon" / "entities" / "hero.json").write_text(json.dumps(ch))
        store = CanonStore(d)
        self.assertEqual(lock_level(store, "hero"), "locked")
        self.assertEqual(Entity.from_dict(ch).validate(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
