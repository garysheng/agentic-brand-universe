"""Engine fixes from the v0.54 gap sweep: #5 G4, #7 G6, #22 G17, #52, #53."""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agenticstory.authoring import lock_shot, scaffold_entity  # noqa: E402
from agenticstory.model import Generator, setting_contract_gaps  # noqa: E402
from agenticstory.store import CanonStore  # noqa: E402

LINT = pathlib.Path(__file__).resolve().parents[2] / "skills" / "lint-universe" / "scripts" / "lint.py"


def _vm(**contract):
    ent = scaffold_entity("visual-metaphor", "a-spring", "A Spring", origin_story="s")
    ent["contract"].update({"map": "m", "blocking": "b", "dressing": "d", "scale": "s"})
    ent["contract"].update(contract)
    return ent


class TestAnchorShot(unittest.TestCase):
    """G4: the anchor is DECLARED, not spelled `master`."""

    def test_scaffold_declares_master_as_the_anchor(self):
        self.assertEqual(_vm()["contract"]["anchorShot"], "master")

    def test_a_designed_anchor_name_reaches_turnaround(self):
        ent = _vm(anchorShot="sealed")
        lock_shot(ent, "sealed", "reference/a-spring/sealed.png")
        self.assertEqual(ent["contract"]["turnaround"], "reference/a-spring/sealed.png")
        self.assertNotIn("reference/a-spring/sealed.png", ent["contract"]["emptyPlates"])

    def test_master_is_then_just_a_state(self):
        ent = _vm(anchorShot="sealed")
        lock_shot(ent, "master", "reference/a-spring/master.png")
        self.assertIsNone(ent["contract"]["turnaround"])

    def test_default_is_still_master_without_the_field(self):
        ent = _vm()
        ent["contract"].pop("anchorShot")
        lock_shot(ent, "master", "reference/a-spring/master.png")
        self.assertEqual(ent["contract"]["turnaround"], "reference/a-spring/master.png")


class TestBlueprintWaived(unittest.TestCase):
    """G6: an organic visual-metaphor may waive the blueprint with a written reason."""

    FULL = {"turnaround": "t.png", "emptyPlates": ["a.png"], "map": "m", "blocking": "b",
            "dressing": "d"}

    def test_waiver_clears_the_gate_for_a_visual_metaphor(self):
        c = dict(self.FULL, blueprint=None, blueprintWaived="organic aerial city, no massing")
        self.assertEqual(setting_contract_gaps(c, "visual-metaphor"), [])

    def test_a_blank_waiver_waives_nothing(self):
        c = dict(self.FULL, blueprint=None, blueprintWaived="  ")
        self.assertTrue(any("blueprint" in g for g in setting_contract_gaps(c, "visual-metaphor")))

    def test_a_setting_keeps_the_hard_gate_and_says_why(self):
        c = dict(self.FULL, blueprint=None, blueprintWaived="it is round")
        gaps = setting_contract_gaps(c, "setting")
        self.assertTrue(any("only applies to a visual-metaphor" in g for g in gaps), gaps)

    def test_lock_shot_promotes_a_waived_metaphor(self):
        ent = _vm(blueprintWaived="organic, no fixed geometry")
        lock_shot(ent, "master", "reference/a-spring/master.png")
        lock_shot(ent, "lit", "reference/a-spring/lit.png")
        self.assertEqual(ent["status"], "locked")


class TestCharacterScaffoldRenderBlock(unittest.TestCase):
    """G17: a fresh character is born with a visible render block and lint does not ERROR
    until a story casts it."""

    def _universe(self, root: pathlib.Path, cast: bool):
        (root / "canon" / "entities").mkdir(parents=True)
        (root / "stories").mkdir()
        (root / "universe.json").write_text(json.dumps({"name": "u", "assetRoot": "."}))
        ent = scaffold_entity("character", "josh", "Josh")
        self.assertEqual(ent["structured"]["render"], {"always": "", "poses": {}})
        (root / "canon" / "entities" / "josh.json").write_text(json.dumps(ent))
        (root / "stories" / "s.json").write_text(json.dumps(
            {"id": "s", "features": ["josh"] if cast else []}))

    def _lint(self, root):
        return subprocess.run([sys.executable, str(LINT), str(root)],
                              capture_output=True, text=True)

    def _line(self, out):
        return next((l for l in out.splitlines() if "CAST-UNRENDERABLE" in l), "")

    def test_uncast_fresh_character_is_a_warning(self):
        with tempfile.TemporaryDirectory() as t:
            self._universe(pathlib.Path(t), cast=False)
            r = self._lint(pathlib.Path(t))
            line = self._line(r.stdout + r.stderr)
            self.assertTrue(line, r.stdout)
            self.assertNotIn("ERROR", line.upper().split("CAST-UNRENDERABLE")[0])

    def test_cast_unrenderable_character_is_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            self._universe(pathlib.Path(t), cast=True)
            r = self._lint(pathlib.Path(t))
            line = self._line(r.stdout + r.stderr)
            self.assertIn("ERROR", line.upper().split("CAST-UNRENDERABLE")[0], line)


class TestGenerators(unittest.TestCase):
    """#52 transform generators; #53 a generator folder with no manifest."""

    def _gen(self, **kw):
        d = {"id": "negative-finish", "kind": "generator", "entrypoint": "generate.py",
             "determinism": "pure", "params": {"strength": 0.5}}
        d.update(kw)
        return Generator.from_dict(d)

    def test_a_transform_needs_no_outputs(self):
        self.assertEqual(self._gen(shape="transform", inputs=["x.png"]).validate(), [])

    def test_a_drawing_generator_still_needs_outputs(self):
        self.assertTrue(any("declares no outputs" in p for p in self._gen().validate()))

    def test_an_unknown_shape_is_refused(self):
        self.assertTrue(any("shape must be" in p for p in self._gen(shape="warp").validate()))

    def _store(self, root: pathlib.Path) -> CanonStore:
        (root / "canon" / "entities").mkdir(parents=True)
        (root / "universe.json").write_text(json.dumps({"name": "u", "assetRoot": "."}))
        return root

    def test_a_folder_with_a_script_and_no_manifest_is_reported(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._store(pathlib.Path(t))
            g = root / "generators" / "workspace-avatar"
            g.mkdir(parents=True)
            (g / "generate.py").write_text("print(1)\n")
            problems = CanonStore(root)._validate_generators()
            self.assertTrue(any("workspace-avatar" in p and "generator.json" in p
                                for p in problems), problems)

    def test_a_transforms_missing_input_is_reported(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._store(pathlib.Path(t))
            g = root / "generators" / "negative-finish"
            g.mkdir(parents=True)
            (g / "generate.py").write_text("print(1)\n")
            (g / "generator.json").write_text(json.dumps({
                "id": "negative-finish", "kind": "generator", "entrypoint": "generate.py",
                "determinism": "pure", "shape": "transform", "inputs": ["stock/film.png"]}))
            problems = CanonStore(root)._validate_generators()
            self.assertTrue(any("stock/film.png" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
