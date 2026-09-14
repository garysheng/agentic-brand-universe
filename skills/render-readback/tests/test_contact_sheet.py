#!/usr/bin/env python3
"""The contact sheet must refuse a partial set rather than quietly shrink.

A short sheet reads as "everything I rendered", which is exactly how a missing spread
goes unnoticed. One spread of gain-everything-lose-nothing was parked mid-batch and its
absence was only caught by counting files by hand (2026-07-30).
"""
import os, pathlib, subprocess, sys, tempfile, unittest
from pathlib import Path

from PIL import Image

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


class AspectRatio(unittest.TestCase):
    """The defect that shipped: a sheet mixing orientations stretched every image that did
    not match the FIRST one's shape. None of the tests above caught it, because they all
    used one shape. A contact sheet is the surface a human picks from, so a distorted plate
    means a pick made on an image that is not the image.
    """

    def _sheet(self, sizes, **kw):
        d = pathlib.Path(tempfile.mkdtemp())
        paths = []
        # One solid colour per image, so each can be found in the output by its own colour
        # and measured. Distortion then shows up as a changed aspect of that colour region.
        colours = [(220, 20, 20), (20, 200, 20), (20, 20, 220), (220, 200, 20)]
        for n, (w, h) in enumerate(sizes):
            f = d / f"i{n}.png"
            Image.new("RGB", (w, h), colours[n % len(colours)]).save(f)
            paths.append(str(f))
        out = d / "sheet.png"
        cmd = [sys.executable, str(SCRIPT), *paths, "--out", str(out)]
        for k, v in kw.items():
            cmd += [f"--{k}", str(v)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        return Image.open(out).convert("RGB"), colours

    def _region(self, im, colour):
        px = im.load()
        xs, ys = [], []
        for y in range(im.size[1]):
            for x in range(im.size[0]):
                c = px[x, y]
                if sum(abs(c[i] - colour[i]) for i in range(3)) < 40:
                    xs.append(x); ys.append(y)
        self.assertTrue(xs, f"colour {colour} not found in the sheet at all")
        return (max(xs) - min(xs) + 1), (max(ys) - min(ys) + 1)

    def test_MIXED_ORIENTATIONS_ARE_NOT_DISTORTED(self):
        """A portrait first, then a landscape: the exact shape of the real sheet that was
        caught by eye. 1024x1536 then 1536x1024 is a 2.25x aspect error when stretched."""
        im, cols = self._sheet([(1024, 1536), (1536, 1024)], cols=2)
        for n, (sw, sh) in enumerate([(1024, 1536), (1536, 1024)]):
            w, h = self._region(im, cols[n])
            got, want = w / h, sw / sh
            self.assertAlmostEqual(got, want, delta=0.04,
                                   msg=f"image {n} arrived at aspect {got:.3f}, source is "
                                       f"{want:.3f}: the sheet distorted it")

    def test_landscape_first_then_portrait(self):
        """The same defect in the other order, which is the one a fix keyed on the first
        image's orientation would still get wrong."""
        im, cols = self._sheet([(1536, 1024), (1024, 1536)], cols=2)
        for n, (sw, sh) in enumerate([(1536, 1024), (1024, 1536)]):
            w, h = self._region(im, cols[n])
            self.assertAlmostEqual(w / h, sw / sh, delta=0.04, msg=f"image {n} distorted")

    def test_nothing_is_cropped_either(self):
        """Cropping to fill the cell is the same lie as stretching, told more quietly: the
        full image must be present, so its scaled area must match what the fit predicts."""
        im, cols = self._sheet([(1024, 1536), (1536, 1024)], cols=2, width=400)
        w, h = self._region(im, cols[1])
        # The landscape image fits by WIDTH in a portrait-shaped cell.
        self.assertAlmostEqual(w, 400, delta=2)

    def test_uniform_sheet_still_fills_the_cell(self):
        """The fix must be a no-op when every image shares one shape, which is most sheets.
        A letterbox that shrinks a uniform sheet would have changed every existing one."""
        im, cols = self._sheet([(1024, 1536), (1024, 1536)], cols=2, width=400)
        w, h = self._region(im, cols[0])
        self.assertAlmostEqual(w, 400, delta=2)
        self.assertAlmostEqual(h, 600, delta=2)


class CoverTheWholeBatch(unittest.TestCase):
    """The refusal `shoot-references` already claimed this script had (v0.49).

    Its SKILL.md says the sheet "already refuses a partial one, so a short sheet cannot
    read as 'everything I rendered'". That was true only of a file that did not EXIST.
    Nothing knew what the batch was, so three of twelve renders built a sheet happily and
    read, to the person looking at it, as twelve.
    """

    def batch(self, tmp, n=4):
        return [os.path.join(tmp, f"shot-{i}.png") for i in range(n)]

    def test_a_short_sheet_is_refused_and_names_what_is_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp)
            for s in shots:
                _png(s)
            r = _run(shots[:2] + ["--out", os.path.join(tmp, "sheet.png"), "--cover", tmp])
            self.assertEqual(r.returncode, 1)
            self.assertIn("REFUSING a partial sheet", r.stderr)
            self.assertIn("shot-2.png", r.stderr)
            self.assertIn("shot-3.png", r.stderr)
            self.assertFalse(os.path.exists(os.path.join(tmp, "sheet.png")),
                             "a refused sheet must not be written")

    def test_a_complete_sheet_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp)
            for s in shots:
                _png(s)
            out = os.path.join(tmp, "sheet.png")
            r = _run(shots + ["--out", out, "--cover", tmp])
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(out))

    def test_the_sheet_being_written_into_the_batch_dir_is_not_itself_a_shot(self):
        """Otherwise the first run poisons the second: the sheet becomes a missing shot."""
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp, 2)
            for s in shots:
                _png(s)
            out = os.path.join(tmp, "sheet.png")
            self.assertEqual(_run(shots + ["--out", out, "--cover", tmp]).returncode, 0)
            r = _run(shots + ["--out", out, "--cover", tmp])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_parked_candidate_is_history_not_a_shot(self):
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp, 2)
            for s in shots:
                _png(s)
            _png(os.path.join(tmp, "shot-0-contact-sheet.png"))
            r = _run(shots + ["--out", os.path.join(tmp, "s.png"), "--cover", tmp])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_without_cover_nothing_changes(self):
        """The flag is opt-in: an existing caller building a deliberate subset still works."""
        with tempfile.TemporaryDirectory() as tmp:
            shots = self.batch(tmp)
            for s in shots:
                _png(s)
            r = _run(shots[:2] + ["--out", os.path.join(tmp, "sheet.png")])
            self.assertEqual(r.returncode, 0, r.stderr)

    def test_a_cover_dir_that_is_not_a_dir_is_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            s = os.path.join(tmp, "a.png")
            _png(s)
            r = _run([s, "--out", os.path.join(tmp, "o.png"), "--cover", s])
            self.assertEqual(r.returncode, 1)
            self.assertIn("not a directory", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
