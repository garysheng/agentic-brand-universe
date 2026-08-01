#!/usr/bin/env python3
"""insert_spread.py: the mid-book insert, and specifically its ordering trap.

The expensive bug this guards is NOT the arithmetic. It is that renaming rendered
art ASCENDING silently overwrites: spread-05 -> spread-06 lands on a spread-06 that
has not moved yet, you end up with the right file count and the wrong pages, and
nothing errors. test_insert_does_not_clobber_art is the one that matters.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "insert_spread.py"


def build(root: Path, n=5):
    (root / "u" / "stories").mkdir(parents=True)
    (root / "b" / "spreads").mkdir(parents=True)
    beats = [{"n": i, "text": f"beat {i} text", "location": None,
              "characters": [], "provenance": ""} for i in range(1, n + 1)]
    (root / "u" / "stories" / "s.json").write_text(json.dumps({
        "id": "s", "title": "S", "beats": beats,
        "aimDiscipline": ["something about beat 4 that will go stale"],
    }))
    (root / "b" / "render-spec.json").write_text(json.dumps({
        "book": "b", "story": "s",
        "spreads": [{"id": f"spread-{i:02d}", "scene": f"scene {i}",
                     "_caption": f"beat {i} text"} for i in range(1, n + 1)]
        + [{"id": "plate-closing", "scene": "closing"}],
    }))
    for i in range(1, n + 1):
        # content is the ORIGINAL page number, so a clobber is detectable
        (root / "b" / "spreads" / f"spread-{i:02d}.png").write_text(f"PAGE{i}")
        (root / "b" / "spreads" / f"spread-{i:02d}.png.recipe.json").write_text(f'{{"page":{i}}}')
    (root / "b" / "spreads" / "cover.png").write_text("COVER")
    (root / "b" / "spreads" / "closing-plate.png").write_text("CLOSING")
    return root


def run(root, *extra):
    return subprocess.run(
        [sys.executable, str(SCRIPT), str(root / "u"), "s", "--book", str(root / "b"), *extra],
        capture_output=True, text=True)


class InsertSpread(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.r = build(Path(self.tmp.name))

    def story(self):
        return json.loads((self.r / "u" / "stories" / "s.json").read_text())

    def spec(self):
        return json.loads((self.r / "b" / "render-spec.json").read_text())

    def test_dry_run_writes_nothing(self):
        before = (self.r / "u" / "stories" / "s.json").read_text()
        p = run(self.r, "--at", "3", "--text", "new")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertIn("DRY RUN", p.stdout)
        self.assertEqual(before, (self.r / "u" / "stories" / "s.json").read_text())

    def test_insert_does_not_clobber_art(self):
        """THE test. Ascending renames overwrite; this must move descending."""
        p = run(self.r, "--at", "3", "--text", "new beat", "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        sd = self.r / "b" / "spreads"
        # every original page still exists exactly once, shifted by one
        self.assertEqual((sd / "spread-01.png").read_text(), "PAGE1")
        self.assertEqual((sd / "spread-02.png").read_text(), "PAGE2")
        self.assertEqual((sd / "spread-04.png").read_text(), "PAGE3")
        self.assertEqual((sd / "spread-05.png").read_text(), "PAGE4")
        self.assertEqual((sd / "spread-06.png").read_text(), "PAGE5")
        # the hole is real: nothing was rendered into it
        self.assertFalse((sd / "spread-03.png").exists())
        # no page was lost
        pages = sorted(f.read_text() for f in sd.glob("spread-*.png"))
        self.assertEqual(pages, ["PAGE1", "PAGE2", "PAGE3", "PAGE4", "PAGE5"])

    def test_recipes_shift_with_their_art(self):
        run(self.r, "--at", "2", "--text", "n", "--apply")
        sd = self.r / "b" / "spreads"
        self.assertEqual(json.loads((sd / "spread-03.png.recipe.json").read_text())["page"], 2)

    def test_endcaps_never_shift(self):
        run(self.r, "--at", "1", "--text", "n", "--apply")
        sd = self.r / "b" / "spreads"
        self.assertEqual((sd / "cover.png").read_text(), "COVER")
        self.assertEqual((sd / "closing-plate.png").read_text(), "CLOSING")

    def test_beats_renumber_contiguously(self):
        run(self.r, "--at", "3", "--text", "new beat", "--apply")
        beats = self.story()["beats"]
        self.assertEqual([b["n"] for b in beats], [1, 2, 3, 4, 5, 6])
        self.assertEqual(beats[2]["text"], "new beat")

    def test_spec_ids_stay_contiguous_and_closing_plate_survives(self):
        run(self.r, "--at", "3", "--text", "new beat", "--apply")
        ids = [s["id"] for s in self.spec()["spreads"]]
        self.assertEqual(ids, ["spread-01", "spread-02", "spread-03", "spread-04",
                               "spread-05", "spread-06", "plate-closing"])

    def test_new_spread_has_empty_scene_so_the_compiler_refuses_it(self):
        run(self.r, "--at", "3", "--text", "new beat", "--apply")
        new = [s for s in self.spec()["spreads"] if s["id"] == "spread-03"][0]
        self.assertEqual(new["scene"], "")
        self.assertEqual(new["_caption"], "new beat")

    def test_caption_matches_the_beat_it_was_created_from(self):
        run(self.r, "--at", "2", "--text", "verbatim caption", "--apply")
        self.assertEqual(self.story()["beats"][1]["text"], "verbatim caption")
        new = [s for s in self.spec()["spreads"] if s["id"] == "spread-02"][0]
        self.assertEqual(new["_caption"], "verbatim caption")

    def test_remove_deletes_its_art_and_closes_the_gap(self):
        p = run(self.r, "--at", "3", "--remove", "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        sd = self.r / "b" / "spreads"
        pages = sorted(f.read_text() for f in sd.glob("spread-*.png"))
        self.assertEqual(pages, ["PAGE1", "PAGE2", "PAGE4", "PAGE5"])
        self.assertEqual([b["n"] for b in self.story()["beats"]], [1, 2, 3, 4])

    def test_reports_beat_citations_it_cannot_fix(self):
        p = run(self.r, "--at", "3", "--text", "n")
        self.assertIn("CITATIONS INVALIDATED", p.stdout)
        self.assertIn("aimDiscipline[0]", p.stdout)

    def test_refuses_when_story_and_spec_are_already_out_of_sync(self):
        spec = self.spec()
        spec["spreads"] = spec["spreads"][:-2]
        (self.r / "b" / "render-spec.json").write_text(json.dumps(spec))
        p = run(self.r, "--at", "2", "--text", "n", "--apply")
        self.assertEqual(p.returncode, 1)
        self.assertIn("already out of sync", p.stderr + p.stdout)

    def test_refuses_out_of_range(self):
        p = run(self.r, "--at", "99", "--text", "n", "--apply")
        self.assertEqual(p.returncode, 1)
        self.assertIn("outside", p.stderr + p.stdout)

    def test_refuses_insert_with_no_text(self):
        p = run(self.r, "--at", "2", "--apply")
        self.assertEqual(p.returncode, 1)
        self.assertIn("needs --text", p.stderr + p.stdout)

    def test_insert_at_the_end_appends(self):
        p = run(self.r, "--at", "6", "--text", "last", "--apply")
        self.assertEqual(p.returncode, 0, p.stderr)
        self.assertEqual(self.story()["beats"][-1]["text"], "last")
        ids = [s["id"] for s in self.spec()["spreads"] if s["id"].startswith("spread-")]
        self.assertEqual(ids[-1], "spread-06")


if __name__ == "__main__":
    unittest.main()
