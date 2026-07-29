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
        # The example story must still be REFUSED by the load-bearing gate — that
        # refusal is the feature. It now refuses on the deliberately-unlocked
        # setting rather than on a dangling character sheet path: since validate
        # enforces principle 3 (a declared asset exists under assetRoot), shipping
        # a placeholder path in the scaffold would mean `init` produces a universe
        # that fails its own validator. Refusing via the setting contract keeps a
        # fresh scaffold green AND still demonstrates the gate.
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "exverse"
            scaffold.scaffold_universe(target, name="exverse", example=True)
            store = CanonStore(target)
            problems = refs.assert_story(store, "the-first-step")
            self.assertTrue(problems, "gate should refuse: example assets are placeholders")
            self.assertTrue(any("the-crossroads" in p for p in problems), problems)

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
        (d / "reference" / "vip" / "photos").mkdir(parents=True, exist_ok=True)
        (d / "reference" / "vip" / "photos" / "01.jpg").write_bytes(b"\xff\xd8")
        rp = scaffold_entity("character", "vip", "Vip", photo_stack=["reference/vip/photos/01.jpg"])
        self.assertEqual(rp["realPerson"]["approval"]["state"], "gated")
        self.assertEqual(rp["realPerson"]["photoStack"], ["reference/vip/photos/01.jpg"])
        self.assertEqual(Entity.from_dict(rp).validate(), [])
        # setting: unlocked contract, validates
        st = scaffold_entity("setting", "the-hall", "The Hall")
        self.assertEqual(st["status"], "unlocked")
        self.assertIn("contract", st)
        self.assertEqual(Entity.from_dict(st).validate(), [])
        # SPEC v0.9: a setting's contract MUST carry the size fields (scalePlate file + scale
        # descriptor), not just the plates — an empty plate cannot prove its own size. Guards
        # against the scaffolder drifting behind the spec (it did: add-entity emitted a setting
        # with no scalePlate/scale for months while scaffold.py already had them).
        from agenticstory.model import SETTING_CONTRACT_FIELDS
        self.assertEqual(
            set(st["contract"].keys()),
            {"turnaround", "emptyPlates", "blueprint", "scalePlate",
             "map", "blocking", "dressing", "scale"},
        )
        self.assertIn("scalePlate", SETTING_CONTRACT_FIELDS)
        self.assertIn("scale", SETTING_CONTRACT_FIELDS)
        # visual-metaphor shares the setting contract path, so it must carry the same size fields
        vm = scaffold_entity("visual-metaphor", "the-yoke", "The Yoke")
        self.assertIn("scalePlate", vm["contract"])
        self.assertIn("scale", vm["contract"])
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

    def test_locking_without_a_recipe_writes_no_sidecar_and_stays_valid(self):
        """A golden with no provenance is still a golden. It is only un-auditable, which
        is the linter's concern, not the lock's."""
        import json, tempfile
        from pathlib import Path
        from agenticstory import scaffold_entity, lock_shot
        from agenticstory.authoring import recipe_sidecar_path
        d = Path(tempfile.mkdtemp()); (d / "art").mkdir()
        (d / "art" / "ff.png").write_bytes(b"golden-bytes")
        ch = scaffold_entity("character", "hero", "Hero")
        lock_shot(ch, "forward-fullbody", "art/ff.png", root=str(d))
        self.assertFalse(recipe_sidecar_path(d / "art" / "ff.png").exists())

    def test_locking_with_a_recipe_freezes_provenance_at_approval(self):
        """The whole divergence loop rests on this: approval captures what was blessed
        and what it was blessed against, by exact bytes."""
        import json, tempfile
        from pathlib import Path
        from agenticstory import scaffold_entity, lock_shot
        from agenticstory.authoring import recipe_sidecar_path
        d = Path(tempfile.mkdtemp())
        (d / "art").mkdir(); (d / "refs").mkdir()
        (d / "art" / "ff.png").write_bytes(b"the-approved-golden")
        (d / "refs" / "anchor.png").write_bytes(b"the-anchor-input")
        ch = scaffold_entity("character", "hero", "Hero")
        recipe = {"provider": "gpt-image-2", "prompt": "a hero, front, full body",
                  "specVersion": "0.6",
                  "refs": [{"path": "refs/anchor.png", "digest": "STALE-WILL-BE-RESTAMPED"}]}
        lock_shot(ch, "forward-fullbody", "art/ff.png", recipe=recipe, root=str(d))
        side = recipe_sidecar_path(d / "art" / "ff.png")
        self.assertTrue(side.exists())
        frozen = json.loads(side.read_text())
        self.assertEqual(frozen["provider"], "gpt-image-2")
        self.assertEqual(frozen["prompt"], "a hero, front, full body")
        # the golden's OWN bytes are recorded: this is what the human blessed
        import hashlib
        want = hashlib.sha256(b"the-approved-golden").hexdigest()[:16]
        self.assertEqual(frozen["goldenDigest"], want)
        # input digests are re-stamped from real bytes NOW, never trusted from the recipe
        anchor_now = hashlib.sha256(b"the-anchor-input").hexdigest()[:16]
        self.assertEqual(frozen["inputs"][0]["digest"], anchor_now)
        self.assertNotEqual(frozen["inputs"][0]["digest"], "STALE-WILL-BE-RESTAMPED")

    def test_an_unresolvable_input_is_recorded_with_a_null_digest(self):
        """Dropping it would make a missing input look like an input never wanted."""
        import json, tempfile
        from pathlib import Path
        from agenticstory import scaffold_entity, lock_shot
        from agenticstory.authoring import recipe_sidecar_path
        d = Path(tempfile.mkdtemp()); (d / "art").mkdir()
        (d / "art" / "ff.png").write_bytes(b"g")
        ch = scaffold_entity("character", "hero", "Hero")
        lock_shot(ch, "forward-fullbody", "art/ff.png",
                  recipe={"refs": [{"path": "refs/gone.png"}]}, root=str(d))
        frozen = json.loads(recipe_sidecar_path(d / "art" / "ff.png").read_text())
        self.assertIsNone(frozen["inputs"][0]["digest"])




class TestAssetExistence(unittest.TestCase):
    """Principle 3: a declared asset resolves to a real file, or validate says so.

    Regression: a universe once validated GREEN while eight declared paths pointed
    at nothing (a lock step that joined four shot names into one key, slots on
    `status: locked` entities whose art was never generated, and paths into
    directories a consolidation sweep had deleted).
    """

    def _universe(self):
        import json, tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp())
        (d / "canon" / "entities").mkdir(parents=True)
        (d / "canon" / "relations").mkdir(); (d / "stories").mkdir()
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        return d

    def _write(self, d, ent):
        import json
        (d / "canon" / "entities" / f"{ent['id']}.json").write_text(json.dumps(ent))

    def test_stub_with_null_sheets_still_validates_clean(self):
        from agenticstory import CanonStore
        from agenticstory.authoring import scaffold_entity
        d = self._universe()
        self._write(d, scaffold_entity("character", "hero", "Hero"))
        self.assertEqual(CanonStore(d).validate_canon(), [],
                         "an unlocked stub declares no paths and must stay clean")

    def test_declared_sheet_with_no_file_is_a_problem(self):
        from agenticstory import CanonStore
        d = self._universe()
        self._write(d, {"id": "ghost", "kind": "character",
                        "structured": {"sheets": {"master": "reference/ghost/master.png"},
                                       "requiredForRender": [], "invariants": []}})
        problems = CanonStore(d).validate_canon()
        self.assertTrue(any("ghost" in p and "NOT ON DISK" in p for p in problems), problems)

    def test_present_file_validates_clean(self):
        from agenticstory import CanonStore
        d = self._universe()
        (d / "reference" / "ghost").mkdir(parents=True)
        (d / "reference" / "ghost" / "master.png").write_bytes(b"\x89PNG")
        self._write(d, {"id": "ghost", "kind": "character",
                        "structured": {"sheets": {"master": "reference/ghost/master.png"},
                                       "requiredForRender": ["master"], "invariants": []}})
        self.assertEqual(CanonStore(d).validate_canon(), [])

    def test_path_outside_the_universe_fails_self_containment(self):
        from agenticstory import CanonStore
        d = self._universe()
        sib = d.parent / "some-book" / "reference"
        sib.mkdir(parents=True, exist_ok=True)
        (sib / "photo.jpg").write_bytes(b"\xff\xd8")
        self._write(d, {"id": "real", "kind": "character",
                        "structured": {"sheets": {"master": "reference/real/m.png"},
                                       "requiredForRender": [], "invariants": []},
                        "realPerson": {"photoStack": ["../some-book/reference/photo.jpg"],
                                       "approval": {"state": "approved"}}})
        problems = CanonStore(d).validate_canon()
        self.assertTrue(any("photoStack" in p for p in problems),
                        f"a ref resolving only outside the universe breaks the clone test: {problems}")

    def test_contract_empty_plates_are_checked(self):
        from agenticstory import CanonStore
        d = self._universe()
        self._write(d, {"id": "hall", "kind": "setting", "status": "locked",
                        "structured": {"invariants": []},
                        "contract": {"turnaround": None, "emptyPlates": ["reference/hall/a.png"],
                                     "blueprint": None, "map": "", "blocking": "", "dressing": ""}})
        problems = CanonStore(d).validate_canon()
        self.assertTrue(any("emptyPlates" in p and "NOT ON DISK" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main(verbosity=2)


# --- SPEC v0.13 §4.11: deterministic generators -----------------------------

class GeneratorTests(unittest.TestCase):
    """A generator's manifest is its contract; these are the ways it can lie."""

    def _g(self, **over):
        base = {"id": "grid", "kind": "generator", "entrypoint": "generate.py",
                "determinism": "pure", "outputs": [{"path": "out/grid.png"}]}
        base.update(over)
        from agenticstory.model import Generator
        return Generator.from_dict(base)

    def test_pure_generator_is_valid(self):
        self.assertEqual(self._g().validate(), [])

    def test_seeded_requires_a_seed_in_the_manifest(self):
        # a seed buried in the code is not reproducible by anyone reading the manifest
        problems = self._g(determinism="seeded").validate()
        self.assertTrue(any("requires a 'seed'" in p for p in problems), problems)
        self.assertEqual(self._g(determinism="seeded", seed=7).validate(), [])

    def test_determinism_must_be_declared_and_known(self):
        problems = self._g(determinism="whenever").validate()
        self.assertTrue(any("determinism must be one of" in p for p in problems), problems)

    def test_generator_must_declare_outputs(self):
        problems = self._g(outputs=[]).validate()
        self.assertTrue(any("declares no outputs" in p for p in problems), problems)

    def test_install_source_must_be_a_declared_output(self):
        problems = self._g(install={"out/nope.png": ["public/nope.png"]}).validate()
        self.assertTrue(any("not a declared output" in p for p in problems), problems)

    def test_kind_must_be_generator(self):
        problems = self._g(kind="entity").validate()
        self.assertTrue(any("kind must be 'generator'" in p for p in problems), problems)


class FormTests(unittest.TestCase):
    """SPEC §4.8 — a form is a portable contract for a KIND of work."""

    def _p(self, **over):
        base = {"id": "scrolling-diorama", "version": "1.0.0",
                "surface": {"medium": "parallax-scene"},
                "requires": [{"kind": "style-pack", "min": 1}],
                "slots": [{"id": "plane", "repeat": "$.planes", "type": "generated"}],
                "emits": ["layers/*.webp"]}
        base.update(over)
        from agenticstory.model import Form
        return Form.from_dict(base)

    def test_a_well_formed_form_is_valid(self):
        self.assertEqual(self._p().validate(), [])

    def test_requires_may_not_name_an_id(self):
        # the kind->id indirection is the ONLY reason a projection can ship to a
        # brand it has never seen; naming an id welds it to one universe
        problems = self._p(requires=[{"kind": "style-pack", "id": "warm-oil", "min": 1}]).validate()
        self.assertTrue(any("requires KINDS" in p for p in problems), problems)

    def test_form_is_versioned(self):
        problems = self._p(version="").validate()
        self.assertTrue(any("no 'version'" in p for p in problems), problems)

    def test_invariant_check_must_be_judged_or_computed(self):
        problems = self._p(invariants={"perSlot": [{"id": "x", "check": "vibes"}]}).validate()
        self.assertTrue(any("judged' or 'computed" in p for p in problems), problems)


class ComputedInvariantTests(unittest.TestCase):
    """The rule evaluator. A generic engine cannot run a check it knows only by name,
    so a computed invariant carries a `rule` evaluated as data."""

    def _eval(self, rule, rows):
        return CanonStore._eval_rule(rule, rows)

    PLANES = [{"z": 0, "speed": 0.28, "alpha": False},
              {"z": 1, "speed": 0.52, "alpha": True},
              {"z": 2, "speed": 0.82, "alpha": True}]

    MONOTONIC = {"op": "monotonic", "over": "plane", "by": "z", "field": "speed",
                 "direction": "increasing", "strict": True}

    def test_depth_order_holds_on_a_correct_scene(self):
        self.assertEqual(self._eval(self.MONOTONIC, self.PLANES), "")

    def test_depth_order_catches_an_inverted_scene(self):
        bad = copy.deepcopy(self.PLANES)
        bad[2]["speed"] = 0.10          # nearest plane now the slowest: depth inverts
        self.assertIn("must rise with z", self._eval(self.MONOTONIC, bad))

    def test_depth_order_rejects_a_tie_when_strict(self):
        tied = copy.deepcopy(self.PLANES)
        tied[1]["speed"] = 0.28         # two planes at one depth is not depth
        self.assertNotEqual(self._eval(self.MONOTONIC, tied), "")

    def test_rows_are_ordered_by_z_not_by_declaration_order(self):
        # a correct scene declared back-to-front must still pass
        self.assertEqual(self._eval(self.MONOTONIC, list(reversed(self.PLANES))), "")

    def test_count_catches_a_second_opaque_plane(self):
        rule = {"op": "count", "over": "plane", "where": {"alpha": False}, "max": 1}
        self.assertEqual(self._eval(rule, self.PLANES), "")
        two = copy.deepcopy(self.PLANES)
        two[1]["alpha"] = False
        self.assertIn("max is 1", self._eval(rule, two))

    def test_extreme_catches_an_opaque_plane_that_is_not_backmost(self):
        rule = {"op": "extreme", "over": "plane", "where": {"alpha": False}, "by": "z", "at": "min"}
        self.assertEqual(self._eval(rule, self.PLANES), "")
        wall = copy.deepcopy(self.PLANES)
        wall[0]["alpha"], wall[2]["alpha"] = True, False   # opaque plane in FRONT
        self.assertIn("must sit at min", self._eval(rule, wall))

    def test_an_unknown_op_is_reported_rather_than_passing_silently(self):
        self.assertIn("unknown rule op", self._eval({"op": "wat", "over": "plane"}, self.PLANES))


class WorkTests(unittest.TestCase):
    """SPEC §4.9 — canon given form, checked against the form it claims."""

    PROJ = {"id": "scrolling-diorama", "version": "1.0.0",
            "surface": {"medium": "parallax-scene"},
            "requires": [{"kind": "style-pack", "min": 1}],
            "slots": [{"id": "plane", "type": "generated"}],
            "emits": ["layers/*.webp"],
            "invariants": {"crossSlot": [
                {"id": "depth-order", "check": "computed",
                 "rule": {"op": "monotonic", "over": "plane", "by": "z",
                          "field": "speed", "direction": "increasing", "strict": True}}]}}

    COMP = {"id": "terrace", "form": "scrolling-diorama@1.0.0",
            "bind": {"style-pack": "warm-gold"},
            "slots": {"plane": [{"z": 0, "speed": 0.3}, {"z": 1, "speed": 0.8}]}}

    def _store(self, proj=None, comp=None):
        d = Path(tempfile.mkdtemp())
        (d / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
        (d / "canon" / "entities").mkdir(parents=True)
        p = d / "forms" / "scrolling-diorama"
        p.mkdir(parents=True)
        (p / "form.json").write_text(json.dumps(proj or self.PROJ))
        c = d / "works" / "terrace"
        c.mkdir(parents=True)
        (c / "work.json").write_text(json.dumps(comp or self.COMP))
        return CanonStore(d)

    def test_a_valid_work_produces_no_problems(self):
        self.assertEqual(self._store().validate_canon(), [])

    def test_unresolvable_form_is_a_problem(self):
        c = dict(self.COMP, form="storybook@9.9.9")
        self.assertTrue(any("not found" in p for p in self._store(comp=c).validate_canon()))

    def test_unpinned_form_reference_is_a_problem(self):
        c = dict(self.COMP, form="scrolling-diorama")
        self.assertTrue(any("unpinned" in p for p in self._store(comp=c).validate_canon()))

    def test_filling_a_slot_the_form_does_not_declare(self):
        c = dict(self.COMP, slots={"spread": [{"z": 0, "speed": 0.3}]})
        self.assertTrue(any("does not declare" in p for p in self._store(comp=c).validate_canon()))

    def test_an_unbound_required_kind_is_caught(self):
        c = dict(self.COMP, bind={})
        problems = self._store(comp=c).validate_canon()
        self.assertTrue(any("requires >=1 of kind 'style-pack'" in p for p in problems), problems)

    def test_a_work_that_violates_a_computed_invariant_is_caught(self):
        c = dict(self.COMP, slots={"plane": [{"z": 0, "speed": 0.9}, {"z": 1, "speed": 0.2}]})
        problems = self._store(comp=c).validate_canon()
        self.assertTrue(any("invariant 'depth-order' fails" in p for p in problems), problems)

    def test_a_pre_0_14_work_using_the_old_projection_key_still_loads(self):
        """A universe written before the Form/Work rename keyed this `projection`. Reading
        only `form` would present those works as formless — a rename silently breaking the
        thing it renamed, which is the failure mode renames are famous for."""
        old = {k: v for k, v in self.COMP.items() if k != "form"}
        old["projection"] = "scrolling-diorama@1.0.0"
        self.assertEqual(self._store(comp=old).validate_canon(), [])

    def test_a_computed_invariant_with_no_rule_is_reported_not_silently_passed(self):
        proj = copy.deepcopy(self.PROJ)
        proj["invariants"]["crossSlot"][0].pop("rule")
        problems = self._store(proj=proj).validate_canon()
        self.assertTrue(any("carries no 'rule'" in p for p in problems), problems)


class TestAltLookResolution(unittest.TestCase):
    """SPEC v0.10 declared altLooks; nothing read them until 2026-07-28.

    Selecting a look used to mean a human typing the right filename into --ref.
    That is a memory test, not a gate, and it was failed live: a `spirit` look was
    rendered with only its own body plate and none of its kept face sheets, and the
    face drifted toward the base model's bias on every batch.
    """

    def _ent(self):
        return Entity(id="jesus", kind="character", raw={
            "id": "jesus", "kind": "character",
            "structured": {
                "sheets": {
                    "face-neutral": "ref/mono-face.webp",
                    "face-neutral-color": "ref/color-face.png",
                    "face-3q": "ref/mono-3q.webp",
                    "forward-fullbody": "ref/body.webp",
                    "back": "ref/back.webp",
                },
                "requiredForRenderOnLock": ["face-neutral-color", "forward-fullbody", "face-neutral"],
                "requiredForRender": ["face-neutral-color", "forward-fullbody", "face-neutral"],
                "invariants": ["brown-skin", "curly-hair"],
                "altLooks": {
                    "spirit": {
                        "sheets": {"forward-fullbody": "ref/spirit-body.png"},
                        "supersedes": ["brown-skin"],
                        "invariants": ["made-of-light"],
                        "keepSheets": ["face-neutral-color", "face-neutral"],
                    },
                    "bare": {"sheets": {"forward-fullbody": "ref/bare.png"}},
                },
            },
        })

    def test_default_look_is_the_required_set(self):
        got = self._ent().look_sheets(None)
        self.assertEqual(set(got), {"face-neutral-color", "forward-fullbody", "face-neutral"})

    def test_alt_look_overlays_its_own_sheet(self):
        got = self._ent().look_sheets("spirit")
        self.assertEqual(got["forward-fullbody"], "ref/spirit-body.png")

    def test_alt_look_keeps_the_face_sheets_it_names(self):
        # The regression that cost seven batches: without keepSheets honoured, the
        # renderer gets a body made of light and no face, and invents a new person.
        got = self._ent().look_sheets("spirit")
        self.assertEqual(got["face-neutral-color"], "ref/color-face.png")
        self.assertEqual(got["face-neutral"], "ref/mono-face.webp")

    def test_alt_look_drops_identity_sheets_it_does_not_keep(self):
        ent = self._ent()
        ent.raw["structured"]["requiredForRender"].append("face-3q")
        ent.raw["structured"]["requiredForRenderOnLock"].append("face-3q")
        self.assertNotIn("face-3q", ent.look_sheets("spirit"))

    def test_look_with_no_keepsheets_loses_every_identity_sheet(self):
        self.assertEqual(set(self._ent().look_sheets("bare")), {"forward-fullbody"})

    def test_supersedes_retires_only_the_named_base_invariant(self):
        got = self._ent().look_invariants("spirit")
        self.assertNotIn("brown-skin", got)
        self.assertIn("curly-hair", got)
        self.assertIn("made-of-light", got)

    def test_base_invariants_survive_for_the_default_look(self):
        self.assertIn("brown-skin", self._ent().look_invariants(None))

    def test_unknown_look_raises_and_names_the_known_ones(self):
        with self.assertRaises(ValueError) as cm:
            self._ent().look_sheets("ghost")
        self.assertIn("spirit", str(cm.exception))



# ---------------------------------------------------------------- lifecycle / archive
from agenticstory import refs as refs_mod


class TestLifecycle(unittest.TestCase):
    """Archiving is EDITORIAL STANDING, orthogonal to reference-completeness."""

    def _e(self, **kw):
        from agenticstory.model import Entity
        d = {"id": "x", "kind": "motif"}
        d.update(kw)
        return Entity.from_dict(d)

    def test_defaults_to_active(self):
        e = self._e()
        self.assertEqual(e.lifecycle, "active")
        self.assertFalse(e.is_archived)

    def test_archived_reports_itself_with_a_replacement(self):
        e = self._e(
            id="jerrys-porch", kind="setting", lifecycle="archived",
            archived={"on": "2026-07-29", "reason": "overused",
                      "supersededBy": "the-creek-path"},
        )
        self.assertTrue(e.is_archived)
        self.assertEqual(e.superseded_by, "the-creek-path")
        n = e.archive_note()
        for frag in ("ARCHIVED", "2026-07-29", "the-creek-path"):
            self.assertIn(frag, n)

    def test_archive_without_a_reason_is_a_validation_problem(self):
        """An archive nobody can audit is worse than no archive."""
        e = self._e(lifecycle="archived", archived={"on": "2026-07-29"})
        self.assertTrue(any("archived" in p and "reason" in p for p in e.validate()))

    def test_unknown_lifecycle_is_rejected(self):
        e = self._e(lifecycle="retired")
        self.assertTrue(any("lifecycle" in p for p in e.validate()))

    def test_active_entity_needs_no_archived_block(self):
        self.assertEqual([p for p in self._e().validate() if "archived" in p], [])

    def test_archived_casts_survives_mixed_id_shapes(self):
        """Real canon is not uniformly typed: beats hold ids OR {"id": ...} objects.

        The first version of this assumed strings and raised on the first mixed story,
        which is exactly the shape the nation-of-fire canon already had.
        """
        import tempfile, json as _json
        from pathlib import Path as _P
        from agenticstory.store import CanonStore
        with tempfile.TemporaryDirectory() as td:
            root = _P(td)
            (root / "canon" / "entities").mkdir(parents=True)
            (root / "stories").mkdir()
            (root / "universe.json").write_text(_json.dumps({"identity": {}}))
            (root / "canon" / "entities" / "porch.json").write_text(_json.dumps({
                "id": "porch", "kind": "setting", "status": "locked", "contract": {},
                "lifecycle": "archived",
                "archived": {"on": "2026-07-29", "reason": "overused"},
            }))
            (root / "stories" / "s.json").write_text(_json.dumps({
                "id": "s", "status": "full", "spine": "thesis", "refrain": "r",
                "logline": "l", "features": ["porch", {"id": "porch"}],
                "beats": [{"n": 1, "text": "t", "provenance": "p",
                           "location": {"id": "porch"},
                           "characters": ["porch", {"id": "porch"}]}],
            }))
            store = CanonStore(root)
            notes = refs_mod.archived_casts(store, "s")
        self.assertEqual(len(notes), 1)
        self.assertIn("porch", notes[0])

    def test_archiving_never_breaks_an_already_shipped_story(self):
        """THE load-bearing property.

        assert_story must stay ignorant of lifecycle. A book that already shipped keeps
        rendering and its provenance stays honest; the refusal lives at the point of NEW
        casting instead. If someone ever teaches the pre-render gate about archiving,
        this test fails and tells them why.
        """
        import inspect
        from agenticstory import refs
        src = inspect.getsource(refs.assert_story)
        self.assertNotIn("lifecycle", src)
        self.assertNotIn("archived", src)
