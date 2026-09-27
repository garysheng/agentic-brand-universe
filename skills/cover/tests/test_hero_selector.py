"""A non-character hero's plate is SELECTED, never silently defaulted (gaps G15/G33, #20 #35).

`--hero-pose` on a visual-metaphor was accepted and ignored, and the hero fell to its FIRST
empty plate even when canon's `requiredForRender` named another. Now: refuse the pose with
the right spelling, honour `id:plate` on every non-character kind, and default to canon.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_cover_scripts import COMPILE, build_universe, png  # noqa: E402


def add_engine(root: Path):
    for s in ("roar", "master", "idle"):
        png(root / "reference" / "engine" / f"{s}.png")
    (root / "canon" / "entities" / "pace-engine.json").write_text(json.dumps({
        "id": "pace-engine", "kind": "visual-metaphor", "status": "locked",
        "structured": {"sheets": {"roar": "reference/engine/roar.png",
                                  "master": "reference/engine/master.png",
                                  "idle": "reference/engine/idle.png"},
                       "requiredForRender": ["master"]},
        # emptyPlates lists `roar` FIRST: the exact shape the-pace-engine had.
        "contract": {"emptyPlates": ["reference/engine/roar.png",
                                     "reference/engine/idle.png"],
                     "turnaround": "reference/engine/master.png"},
    }))


def compile_(root: Path, *extra):
    return subprocess.run([sys.executable, str(COMPILE), str(root), "tale",
                           "--title", "T", *extra], capture_output=True, text=True)


class TestNonCharacterHero(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.u = build_universe(Path(self.t.name))
        add_engine(self.u)

    def tearDown(self):
        self.t.cleanup()

    def refs(self, *extra):
        r = compile_(self.u, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["refs"]

    def test_hero_pose_on_a_visual_metaphor_is_refused_with_the_right_spelling(self):
        r = compile_(self.u, "--hero", "pace-engine", "--hero-pose", "master")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--hero pace-engine:<plate>", r.stderr)
        self.assertIn("master", r.stderr)

    def test_default_plate_is_canons_required_sheet_not_the_first_empty_plate(self):
        refs = self.refs("--hero", "pace-engine")
        self.assertTrue(any(r.endswith("engine/master.png") for r in refs), refs)
        self.assertFalse(any(r.endswith("engine/roar.png") for r in refs), refs)

    def test_explicit_plate_selection_still_wins(self):
        refs = self.refs("--hero", "pace-engine:idle")
        self.assertTrue(any(r.endswith("engine/idle.png") for r in refs), refs)
        self.assertFalse(any(r.endswith("engine/master.png") for r in refs), refs)

    def test_motif_plate_selector_is_honoured(self):
        png(self.u / "reference" / "sigil" / "lit.png")
        ent = json.loads((self.u / "canon/entities/sigil.json").read_text())
        ent["structured"]["sheets"]["lit"] = "reference/sigil/lit.png"
        (self.u / "canon/entities/sigil.json").write_text(json.dumps(ent))
        refs = self.refs("--with", "sigil:lit")
        self.assertTrue(any(r.endswith("sigil/lit.png") for r in refs), refs)

    def test_motif_unknown_plate_refuses(self):
        r = compile_(self.u, "--with", "sigil:nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no plate 'nope'", r.stderr)

    def test_character_hero_pose_still_works(self):
        refs = self.refs("--hero", "hero", "--hero-pose", "back")
        self.assertTrue(any(r.endswith("hero/back.png") for r in refs), refs)


if __name__ == "__main__":
    unittest.main()
