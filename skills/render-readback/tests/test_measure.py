"""measure.py — a measurement is landmarks plus a method, never a bare number.

Three consecutive sessions hand-rolled this ruler and produced three
irreconcilable answers for overlapping plates, because none recorded HOW it
measured. These tests pin the two properties that make the numbers comparable:
the record carries its landmarks, and an impossible result refuses instead of
returning.
"""
import importlib.util
import pathlib
import unittest

from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("measure", HERE.parent / "scripts" / "measure.py")
measure = importlib.util.module_from_spec(spec)
spec.loader.exec_module(measure)


def figure_plate(w=400, h=1200, crown=100, sole=1100):
    """A light backdrop with a dark head blob and dark feet."""
    im = Image.new("RGB", (w, h), (235, 228, 215))
    d = ImageDraw.Draw(im)
    d.rectangle([w // 2 - 30, crown, w // 2 + 30, crown + 120], fill=(20, 18, 16))
    d.rectangle([w // 2 - 60, sole - 40, w // 2 + 60, sole], fill=(30, 22, 18))
    return im


class TestFigure(unittest.TestCase):
    def test_finds_crown_and_sole(self):
        m = measure.measure_figure(figure_plate())
        self.assertAlmostEqual(m["landmarks"]["crown"], 100, delta=8)
        self.assertAlmostEqual(m["landmarks"]["sole"], 1100, delta=8)

    def test_refuses_to_invent_a_ratio_without_a_chin(self):
        """The chin resists automation, so no chin means no number, not a guess."""
        m = measure.measure_figure(figure_plate())
        self.assertIsNone(m["headToBody"])
        self.assertEqual(m["method"]["chin"], "NOT MEASURED")

    def test_records_landmarks_and_method_with_the_ratio(self):
        m = measure.measure_figure(figure_plate(), chin=250)
        self.assertIsNotNone(m["headToBody"])
        self.assertEqual(m["landmarks"]["chin"], 250)
        self.assertEqual(m["method"]["chin"], "operator-supplied")
        self.assertIn("crown", m["method"])
        self.assertGreater(m["sensitivity"], 0)

    def test_a_blank_frame_refuses(self):
        blank = Image.new("RGB", (400, 1200), (235, 228, 215))
        with self.assertRaises(measure.Unmeasurable):
            measure.measure_figure(blank)

    def test_a_chin_above_the_crown_refuses(self):
        with self.assertRaises(measure.Unmeasurable):
            measure.measure_figure(figure_plate(), chin=10)

    def test_a_stray_speck_does_not_become_the_crown(self):
        """Keying on the FIRST qualifying row picked up specks and shrank the head."""
        im = figure_plate()
        ImageDraw.Draw(im).rectangle([195, 30, 215, 33], fill=(10, 10, 10))
        m = measure.measure_figure(im)
        self.assertGreater(m["landmarks"]["crown"], 60)


class TestStar(unittest.TestCase):
    def _star(self, w, bottom):
        im = Image.new("RGB", (300, 300), (245, 245, 245))
        d = ImageDraw.Draw(im)
        cy, cx = 120, 150
        d.polygon([(cx, cy - w // 2), (cx + w // 2, cy), (cx, cy + bottom), (cx - w // 2, cy)],
                  fill=(200, 160, 60))
        return im

    def test_measures_a_star_from_the_centre(self):
        m = measure.measure_star(self._star(60, 45))
        self.assertGreater(m["heightOverWidth"], 0)
        self.assertIn(m["verdict"], ("PASS", "DEFECT"))
        self.assertIn("targets", m)

    def test_an_impossible_ratio_refuses_rather_than_returning(self):
        """Every wrong number this module produced in testing was above 3:1.

        A refusal the caller can act on beats a ratio they might believe.
        """
        with self.assertRaises(measure.Unmeasurable):
            measure.measure_star(self._star(12, 400))

    def test_no_gold_refuses(self):
        with self.assertRaises(measure.Unmeasurable):
            measure.measure_star(Image.new("RGB", (100, 100), (250, 250, 250)))


if __name__ == "__main__":
    unittest.main()
