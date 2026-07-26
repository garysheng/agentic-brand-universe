#!/usr/bin/env python3
"""Tests for the Universe Doctor grader. Builds tiny fixture universes on disk and
asserts the scorecard reflects what is actually present."""
import json, importlib.util, tempfile, unittest
from pathlib import Path

_spec = importlib.util.spec_from_file_location(
    "grade", str(Path(__file__).resolve().parent.parent / "scripts" / "grade.py"))
grade = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(grade)


def _write(d, rel, obj):
    p = Path(d) / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj) if not isinstance(obj, str) else obj)
    return p


class TestGrader(unittest.TestCase):
    def _bare_universe(self, d):
        _write(d, "universe.json", {"name": "t", "assetRoot": ".",
                                    "identity": {"register": {"name": "r"}}})

    def test_empty_universe_grades_low_with_actionable_issues(self):
        d = tempfile.mkdtemp()
        self._bare_universe(d)
        _, scores, total, issues = grade.grade_universe(d)
        self.assertLess(total, 70)                       # a bare universe is not an A
        self.assertEqual(scores["stories"], 0)           # no stories
        self.assertEqual(scores["entities"], 0)          # no renderable entities
        self.assertEqual(scores["craft_canon"], 0)       # no encoded invariants
        whats = " ".join(w for _, _, w, _ in issues)
        self.assertIn("no stories", whats)
        self.assertIn("no renderable entities", whats)
        # the punch-list is sorted highest-impact first
        self.assertEqual(issues, sorted(issues, key=lambda x: -x[0]))

    def test_setting_without_scaleplate_loses_size_points(self):
        d = tempfile.mkdtemp()
        self._bare_universe(d)
        # a setting whose contract has NO scalePlate + NO scale descriptor
        _write(d, "canon/entities/hall.json", {
            "id": "hall", "kind": "setting", "status": "unlocked",
            "contract": {"turnaround": None, "emptyPlates": [], "blueprint": None,
                         "scalePlate": None, "map": "m", "blocking": "b",
                         "dressing": "dr", "scale": ""}})
        _, scores, _, issues = grade.grade_universe(d)
        self.assertLess(scores["setting_size"], 10)
        self.assertTrue(any("prove its size" in w for _, _, w, _ in issues))

    def test_scaleplate_present_earns_size_points(self):
        d = tempfile.mkdtemp()
        self._bare_universe(d)
        _write(d, "reference/hall/scale-plate.png", "x")  # the plate must actually resolve
        _write(d, "canon/entities/hall.json", {
            "id": "hall", "kind": "setting", "status": "unlocked",
            "contract": {"turnaround": None, "emptyPlates": [], "blueprint": None,
                         "scalePlate": "reference/hall/scale-plate.png",
                         "map": "m", "blocking": "b", "dressing": "dr",
                         "scale": "a hall ~80ft across"}})
        _, scores, _, _ = grade.grade_universe(d)
        self.assertEqual(scores["setting_size"], 10)

    def test_provenance_counts_only_recipe_backed_images(self):
        d = tempfile.mkdtemp()
        self._bare_universe(d)
        _write(d, "reference/x/a.png", "x")                       # no recipe
        _write(d, "reference/x/b.png", "x")
        _write(d, "reference/x/b.png.recipe.json", {"provider": "p"})  # has recipe
        _, scores, _, _ = grade.grade_universe(d)
        self.assertEqual(scores["provenance"], 5)                 # 1 of 2 -> half of 10

    def test_pack_and_lookbook_refs_are_excluded_from_provenance(self):
        # a ref copied into a style pack / lookbook is provenanced at the manifest level,
        # so it must NOT be counted as an un-provenanced primary render.
        d = tempfile.mkdtemp()
        self._bare_universe(d)
        _write(d, "reference/style/mypack/refs/a.png", "x")          # pack ref, no recipe
        _write(d, "reference/lookbook/mylook/refs/b.png", "x")       # lookbook ref, no recipe
        _write(d, "reference/hero/shot.png", "x")                    # primary render, no recipe
        _write(d, "reference/hero/shot.png.recipe.json", {"p": 1})   # ...but it HAS a recipe
        _, scores, _, issues = grade.grade_universe(d)
        self.assertEqual(scores["provenance"], 10)                   # the 2 pack refs don't count against it
        self.assertFalse(any(d_ == "provenance" for _, d_, _, _ in issues))

    def test_letter_thresholds(self):
        self.assertEqual(grade.letter(90), "A")
        self.assertEqual(grade.letter(69), "D")
        self.assertEqual(grade.letter(59), "F")


if __name__ == "__main__":
    unittest.main()
