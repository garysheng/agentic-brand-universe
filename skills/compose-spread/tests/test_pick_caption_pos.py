#!/usr/bin/env python3
"""pick_caption_pos.py — the caption anchor is MEASURED off the art, not defaulted.

Earned 2026-08-08 (Gary, reading the-introducer): "the caption location needs to
be determined by the agent moving forward, seeing too many examples like this."
Until this, `pos` was hand-guessed per spread and anything unset fell to the
reader's "bottom" default, so plates landed on faces.

The two rules that matter and are easy to regress:
  * the caption page for a full-spread book is the RIGHT HALF of the image, so
    busy paint on the LEFT half must not move the anchor;
  * a bottom/center choice must survive the short-viewport FLIP to top, because
    that flip is invisible on a laptop and is how a measured-calm caption still
    ends up across a face.
"""
import os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from pick_caption_pos import BANDS, FLIP, caption_page_box, pick  # noqa: E402

try:
    from PIL import Image, ImageDraw
    HAVE_PIL = True
except ImportError:  # pragma: no cover
    HAVE_PIL = False


def art(tmp, busy_boxes, size=(1536, 1024), name="s.png"):
    """Flat mid-grey art with high-frequency noise painted into busy_boxes
    (fractions of the WHOLE image)."""
    im = Image.new("L", size, 150)
    d = ImageDraw.Draw(im)
    W, H = size
    for x0, y0, x1, y1 in busy_boxes:
        for i, y in enumerate(range(int(y0 * H), int(y1 * H), 3)):
            d.line([(x0 * W, y), (x1 * W, y)], fill=0 if i % 2 else 255, width=2)
    p = Path(tmp) / name
    im.save(p)
    return p


@unittest.skipUnless(HAVE_PIL, "Pillow required")
class TestPick(unittest.TestCase):
    def test_a_calm_bottom_stays_bottom(self):
        with tempfile.TemporaryDirectory() as t:
            # busy across the MIDDLE only; bottom and top bands both calm
            p = art(t, [(0.0, 0.35, 1.0, 0.62)])
            self.assertEqual(pick(p)["pos"], "bottom")

    def test_busy_bottom_moves_the_caption_up(self):
        with tempfile.TemporaryDirectory() as t:
            p = art(t, [(0.0, 0.62, 1.0, 1.0)])
            self.assertIn(pick(p)["pos"], {"top", "top-left", "top-right", "center"})

    def test_only_the_right_half_counts_for_a_full_spread(self):
        """Busy paint on the LEFT half is on the other page; it must not move the
        anchor. This is the rule a naive whole-image scorer gets wrong."""
        with tempfile.TemporaryDirectory() as t:
            p = art(t, [(0.0, 0.62, 0.48, 1.0)])   # busy bottom-LEFT half only
            self.assertEqual(pick(p, layout="full-spread")["pos"], "bottom")

    def test_art_and_text_layout_scores_the_whole_image(self):
        with tempfile.TemporaryDirectory() as t:
            p = art(t, [(0.0, 0.62, 1.0, 1.0)])
            with Image.open(p) as im:
                self.assertEqual(caption_page_box(im, "art-and-text"), (0, 0, *im.size))
            self.assertNotEqual(pick(p, layout="art-and-text")["pos"], "bottom")

    def test_a_busy_flip_partner_pushes_off_bottom(self):
        """Bottom is calm, but the TOP it would flip to on a short viewport is
        painted solid. A corner anchor (which never flips) must win."""
        with tempfile.TemporaryDirectory() as t:
            p = art(t, [(0.5, 0.02, 1.0, 0.34)])   # busy top of the RIGHT page
            r = pick(p)
            self.assertNotIn(r["pos"], {"bottom", "center"},
                             "a bottom pick would flip onto the busy top band")

    def test_crowded_is_reported_not_hidden(self):
        with tempfile.TemporaryDirectory() as t:
            p = art(t, [(0.0, 0.0, 1.0, 1.0)])     # every band busy
            self.assertTrue(pick(p)["crowded"])

    def test_every_band_is_a_legal_reader_pos(self):
        legal = {"bottom", "top", "center", "bottom-right", "bottom-left",
                 "top-right", "top-left"}
        self.assertEqual({b[0] for b in BANDS}, legal)
        self.assertTrue(set(FLIP) <= legal and set(FLIP.values()) <= legal)


if __name__ == "__main__":
    unittest.main()
