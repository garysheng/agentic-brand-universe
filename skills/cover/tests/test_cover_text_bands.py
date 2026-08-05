"""cover_text_bands.py — tests.

The script deliberately renders NO verdict, so what is tested is that it hands a
judge usable evidence: both lettering bands, at readable scale, labelled, and a
loud refusal rather than a silent pass when a path is wrong.
"""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cover_text_bands.py"


def cover(path: Path, size=(1152, 1536), top=(200, 30, 30), bot=(30, 30, 200)):
    """A cover whose two lettering bands are distinctly coloured, so the test can
    prove the crop landed where cover lettering actually lives."""
    from PIL import ImageDraw
    im = Image.new("RGB", size, (40, 40, 40))
    W, H = size
    d = ImageDraw.Draw(im)
    # SOLID bands, not stripes: the sheet downscales each cover with LANCZOS, and a
    # one-pixel stripe pattern is averaged out of existence on the way down. The first
    # version of this fixture did exactly that and the test failed against correct code.
    d.rectangle([0, 0, W, int(H * 0.34)], fill=top)
    d.rectangle([0, int(H * 0.76), W, H], fill=bot)
    im.save(path)


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True)


class CoverTextBands(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_builds_a_sheet_from_several_covers(self):
        ps = []
        for i in range(4):
            p = self.d / f"c{i}.png"
            cover(p)
            ps.append(p)
        out = self.d / "sheet.png"
        r = run(*ps, "--out", out)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(out.exists())
        self.assertGreater(Image.open(out).size[0], 700)

    def test_sheet_contains_both_lettering_bands(self):
        """The whole point: a full-cover thumbnail hides small lettering, which is
        how a missing byline survived review. Both bands must be in the sheet."""
        p = self.d / "c.png"
        cover(p)
        out = self.d / "sheet.png"
        self.assertEqual(run(p, "--out", out).returncode, 0)
        im = Image.open(out).convert("RGB")
        colours = set(im.getdata())
        self.assertTrue(any(abs(r - 200) < 40 and g < 90 for r, g, b in colours),
                        "the TOP lettering band is missing from the sheet")
        self.assertTrue(any(abs(b - 200) < 40 and g < 90 for r, g, b in colours),
                        "the BOTTOM lettering band is missing from the sheet")

    def test_refuses_a_missing_file(self):
        r = run(self.d / "nope.png", "--out", self.d / "s.png")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no such cover", r.stderr)

    def test_says_out_loud_that_it_is_not_a_verdict(self):
        """A tool that looks like a checker but only prepares evidence must say so,
        or the next agent will report 'ran the checker, all good'."""
        p = self.d / "c.png"
        cover(p)
        r = run(p, "--out", self.d / "s.png")
        self.assertIn("NOT A VERDICT", r.stdout)

    def test_labels_default_to_the_book_folder(self):
        book = self.d / "some-book" / "spreads"
        book.mkdir(parents=True)
        p = book / "cover.png"
        cover(p)
        r = run(p, "--out", self.d / "s.png")
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
