"""`measure extent`: how far a feature RUNS, how continuous it is, how many.

Earned on proof-of-vibes' `pov-fine-screen-halftone` (2026-08-20, docs/GAPS.md
G38). The pack's prismatic-fringe assertion failed its own round-trip TWICE on
two different ref sets, both calls made by eye and in prose, and the two calls
were not comparable to each other because no method was recorded. Dot pitch and
sky colour had both been promoted to rulers earlier the same day; the fringe was
the one gate left being judged by looking at it.

`test_the_predicate_refuses_a_ground_it_cannot_separate_from` is the test that
matters most, and it is the one the design pass actually hit. THREE predicates
were tried against the real plates before this one, and all three failed by
scoring the SHEET rather than the feature on it: distance off the canonical
paper-to-ink axis put 12-16% of a saturated plate's pixels "off axis" and ranked
the most-fringed plate LOWEST; fitting that axis per plate did not help, because
halftone dot edges are partial coverage and do not travel it in sRGB; and doing
it again in linear light, where coverage IS linear, still failed because these
sheets are not one ink (the blue itself drifts in hue across the frame). Warm-side
CIELAB works because it asks a different question, and the refusal exists so that
the next predicate which cannot separate its ground says so instead of returning
a confident number, which is this module's founding rule.
"""
import importlib.util
import pathlib
import unittest

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("measure", HERE.parent / "scripts" / "measure.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

W, H = 1536, 1024
PAPER = (236, 233, 229)
INK = (94, 150, 197)      # a cool blue: negative b*, so a warm feature separates
GOLD = (196, 150, 70)     # +b*, the accent ink a misregistration fringe shows as


def sheet(*, warm_boxes=(), ground=INK) -> "Image.Image":
    """A cool-inked sheet carrying zero or more warm rectangles.

    `warm_boxes` are (x0, y0, x1, y1) in PIXELS, so a test states the extent it
    expects to get back rather than deriving it from the same code under test.
    """
    a = np.zeros((H, W, 3))
    a[:, :] = PAPER
    a[int(H * .2):, :] = ground          # the cool ground, lower four fifths
    for x0, y0, x1, y1 in warm_boxes:
        a[y0:y1, x0:x1] = GOLD
    return Image.fromarray(a.clip(0, 255).astype("uint8"))


class TestExtent(unittest.TestCase):
    def test_it_recovers_a_known_run_length(self):
        # A horizontal bar 300px long on a 1536px frame: 0.195 of frame width.
        img = sheet(warm_boxes=[(400, 500, 700, 520)])
        m = M.measure_extent(img, "warm-chroma", blur=0)
        self.assertEqual(m["regions"], 1)
        self.assertAlmostEqual(m["longestRunFracW"], 300 / W, delta=0.02)

    def test_it_counts_separate_regions(self):
        img = sheet(warm_boxes=[(200, 300, 320, 320), (900, 700, 1020, 720)])
        m = M.measure_extent(img, "warm-chroma", blur=0)
        self.assertEqual(m["regions"], 2)

    def test_a_diagonal_run_is_measured_along_its_own_axis(self):
        # A fringe tracing a cloud edge is diagonal. Measured by bbox width it is
        # understated; by bbox diagonal, overstated. The principal axis is right.
        a = np.zeros((H, W, 3))
        a[:, :] = INK
        for i in range(300):
            a[400 + i, 500 + i:500 + i + 12] = GOLD
        m = M.measure_extent(Image.fromarray(a.astype("uint8")), "warm-chroma", blur=0)
        # 300px of run at 45 degrees is 300*sqrt(2) along its own axis.
        self.assertAlmostEqual(m["longestRunFracW"], 300 * np.sqrt(2) / W, delta=0.03)

    def test_occupancy_separates_a_solid_line_from_a_broken_one(self):
        """Length was never the only way a fringe fails, so it is not the only number."""
        solid = M.measure_extent(sheet(warm_boxes=[(400, 500, 900, 520)]),
                                 "warm-chroma", blur=0)
        dotted = M.measure_extent(
            sheet(warm_boxes=[(x, 500, x + 10, 520) for x in range(400, 900, 50)]),
            "warm-chroma", blur=0, bridge=60)
        self.assertGreater(solid["longestRunOccupancy"], 0.95)
        self.assertLess(dotted["longestRunOccupancy"], 0.6)

    def test_bridging_merges_stretches_the_eye_reads_as_one_line(self):
        """The real X1 case: one fringe arriving as four separated dotty stretches."""
        boxes = [(500, y, 512, y + 60) for y in range(200, 500, 80)]
        unbridged = M.measure_extent(sheet(warm_boxes=boxes), "warm-chroma", blur=0)
        bridged = M.measure_extent(sheet(warm_boxes=boxes), "warm-chroma", blur=0,
                                   bridge=30)
        self.assertEqual(unbridged["regions"], 4)
        self.assertEqual(bridged["regions"], 1)
        self.assertGreater(bridged["longestRunFracW"], unbridged["longestRunFracW"] * 3)

    def test_bridging_does_not_inflate_area(self):
        """Bridging may merge regions; it must never claim ink that is not there."""
        boxes = [(500, y, 512, y + 60) for y in range(200, 500, 80)]
        bridged = M.measure_extent(sheet(warm_boxes=boxes), "warm-chroma", blur=0,
                                   bridge=30)
        self.assertAlmostEqual(bridged["detail"][0]["areaPx"], 4 * 12 * 60, delta=200)

    def test_no_feature_is_a_measurement_not_a_refusal(self):
        """A plate with no fringe has no extent, and that is an ANSWER.

        The pack's own C2 is this case: a fine screen with no prismatic treatment
        at all. Refusing on it would make the control unmeasurable.
        """
        m = M.measure_extent(sheet(), "warm-chroma", blur=0)
        self.assertEqual(m["regions"], 0)
        self.assertNotIn("longestRunFracW", m)

    # ------------------------------------------------------------- refusals

    def test_the_predicate_refuses_a_ground_it_cannot_separate_from(self):
        """A warm sheet has nothing for a warm feature to be a departure FROM."""
        warm_ground = Image.fromarray(
            (np.ones((H, W, 3)) * np.array([225, 200, 150])).astype("uint8"))
        with self.assertRaises(M.Unmeasurable) as e:
            M.measure_extent(warm_ground, "warm-chroma", blur=0)
        self.assertIn("no cool ground", str(e.exception))

    def test_it_refuses_when_the_mask_describes_the_sheet(self):
        """Over the ceiling it is not a feature, it is the ground. Say so."""
        img = sheet(warm_boxes=[(0, 0, W, int(H * .5))])
        with self.assertRaises(M.Unmeasurable) as e:
            M.measure_extent(img, "warm-chroma", blur=0)
        self.assertIn("of the frame", str(e.exception))

    def test_it_refuses_a_clipped_extent_unless_told_it_is_a_lower_bound(self):
        img = sheet(warm_boxes=[(0, 500, 600, 520)])       # runs off the left edge
        with self.assertRaises(M.Unmeasurable) as e:
            M.measure_extent(img, "warm-chroma", blur=0)
        self.assertIn("LOWER BOUND", str(e.exception))
        m = M.measure_extent(img, "warm-chroma", blur=0, allow_clipped=True)
        self.assertTrue(m["extentIsLowerBound"])

    def test_an_unnamed_predicate_is_refused_rather_than_guessed(self):
        with self.assertRaises(M.Unmeasurable):
            M.measure_extent(sheet(), "whatever-looks-bright", blur=0)

    def test_the_method_is_recorded_so_two_runs_are_comparable(self):
        """The founding rule of this module: a number alone is not a measurement."""
        m = M.measure_extent(sheet(warm_boxes=[(400, 500, 700, 520)]),
                             "warm-chroma", blur=0, bridge=12)
        self.assertEqual(m["feature"], "warm-chroma")
        self.assertEqual(m["method"]["bridgePx"], 12)
        self.assertEqual(m["method"]["blurPx"], 0)
        self.assertIn("minChroma", m["method"])
        self.assertIn("principal axis", m["method"]["extent"])


class TestRecord(unittest.TestCase):
    def test_extent_does_not_clobber_a_sibling_measurement(self):
        """A cloud plate legitimately carries a pitch, a colour AND a fringe."""
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = pathlib.Path(d) / "plate.png"
            sheet(warm_boxes=[(400, 500, 700, 520)]).save(p)
            M.write_record(p, {"kind": "periodic", "dotsAcrossWidth": 192})
            M.write_record(p, M.measure_extent(Image.open(p), "warm-chroma", blur=0))
            doc = json.loads(M.record_path(p).read_text())
            self.assertEqual(doc["periodic"]["dotsAcrossWidth"], 192)
            self.assertEqual(doc["extent"]["feature"], "warm-chroma")


if __name__ == "__main__":
    unittest.main()
