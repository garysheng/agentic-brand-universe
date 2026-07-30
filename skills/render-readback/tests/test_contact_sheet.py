#!/usr/bin/env python3
"""The contact sheet must refuse a partial set rather than quietly shrink.

A short sheet reads as "everything I rendered", which is exactly how a missing spread
goes unnoticed. One spread of gain-everything-lose-nothing was parked mid-batch and its
absence was only caught by counting files by hand (2026-07-30).
"""
import os, subprocess, sys, tempfile, unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "contact_sheet.py"


def _png(p, w=80, h=60, tint=(200, 180, 140)):
    from PIL import Image
    Image.new("RGB", (w, h), tint).save(p)


def _run(args):
    return subprocess.run([sys.executable, str(SCRIPT)] + args, capture_output=True, text=True)


class TestContactSheet(unittest.TestCase):
    def test_builds_a_labelled_sheet(self):
        with tempfile.TemporaryDirectory() as tmp:
            imgs = []
            for i in range(4):
                p = os.path.join(tmp, f"spread-0{i+1}.png"); _png(p); imgs.append(p)
            out = os.path.join(tmp, "sheet.png")
            r = _run(imgs + ["--out", out])
            self.assertEqual(r.returncode, 0, r.stderr)
            from PIL import Image
            self.assertEqual(Image.open(out).size[0], 690 * 2, "default is a 2-up grid")

    def test_refuses_a_partial_sheet_and_names_what_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = os.path.join(tmp, "spread-01.png"); _png(good)
            missing = os.path.join(tmp, "spread-02.png")
            out = os.path.join(tmp, "sheet.png")
            r = _run([good, missing, "--out", out])
            self.assertEqual(r.returncode, 1, "a missing render must fail the sheet")
            self.assertIn("spread-02.png", r.stderr, "it must name what is missing")
            self.assertFalse(os.path.exists(out), "no sheet should be written at all")

    def test_cols_and_width_are_honoured(self):
        with tempfile.TemporaryDirectory() as tmp:
            imgs = []
            for i in range(3):
                p = os.path.join(tmp, f"s{i}.png"); _png(p); imgs.append(p)
            out = os.path.join(tmp, "sheet.png")
            r = _run(imgs + ["--out", out, "--cols", "3", "--width", "100"])
            self.assertEqual(r.returncode, 0, r.stderr)
            from PIL import Image
            self.assertEqual(Image.open(out).size[0], 300)


if __name__ == "__main__":
    unittest.main(verbosity=2)
