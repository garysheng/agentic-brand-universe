"""`measure periodic` / `measure patch`: the two rulers a MEDIUM needs.

Earned on proof-of-vibes' cloud exploration (2026-08-20). Three rounds asked a
halftone plate for a COARSE screen and got a fine one every time, and nobody could
tell, because "coarse" is a word. Round 3 hand-rolled an autocorrelation dot-pitch
ruler and a patch-mean colour ruler over nine plates and threw both away; round 4
needed the identical method hours later. Same story as `measure figure`, replayed
on the medium instead of on the figure.

The test that matters here is `test_a_louder_harmonic_does_not_win`. On a rotated
screen the second harmonic is routinely LOUDER than the fundamental, so the
obvious implementation (take the strongest peak) reports 2p and halves the dot
count. It did, on real plates, before this bit.
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
PATCH = (0.08, 0.18, 0.42, 0.42)


def screen(dots: int, ramp: bool = True) -> "Image.Image":
    """A 45-degree halftone of a known pitch, under a strong tonal ramp.

    The ramp is the point: it is far larger than the dot signal, and an
    autocorrelation run against it reports the size of the PICTURE.
    """
    y, x = np.mgrid[0:H, 0:W]
    p = W / dots
    u, v = (x + y) / np.sqrt(2), (x - y) / np.sqrt(2)
    grid = (np.cos(2 * np.pi * u / (p * np.sqrt(2)))
            * np.cos(2 * np.pi * v / (p * np.sqrt(2))) > 0.1).astype(float)
    tone = (0.25 + 0.6 * (1 - y / H)) if ramp else 0.5
    a = 255 * (1 - grid * tone)
    return Image.fromarray(np.dstack([a * .56, a * .67, a * .80]).clip(0, 255).astype("uint8"))


def flat(rgb=(143, 170, 204)) -> "Image.Image":
    return Image.fromarray((np.ones((H, W, 3)) * np.array(rgb)).astype("uint8"))


class TestPeriodic(unittest.TestCase):
    def test_it_recovers_a_known_pitch_through_a_tonal_ramp(self):
        for dots in (96, 192, 384):
            with self.subTest(dots=dots):
                m = M.measure_periodic(screen(dots), PATCH)
                self.assertEqual(m["dotsAcrossWidth"], dots)

    def test_a_louder_harmonic_does_not_win(self):
        # The whole reason this is not `max(maxima)`. Build a ladder whose second
        # harmonic is twice as loud as the fundamental and assert the SMALL lag wins.
        r = np.zeros(400)
        r[0] = 1.0
        for lag, v in ((6, 0.30), (12, 0.75), (18, 0.40)):
            r[lag - 1], r[lag], r[lag + 1] = v - .1, v, v - .1
        lag, peak, ladder = M._fundamental(r, 1200)
        self.assertEqual(lag, 6, "took a harmonic for the fundamental; the dot "
                                "count comes back at half the truth")
        self.assertEqual([e["lagPx"] for e in ladder], [6, 12, 18],
                         "the ladder is the evidence that reconciles two "
                         "measurements disagreeing by an integer factor")

    def test_one_rung_is_not_a_ladder_so_it_is_taken_as_is(self):
        # The harmonic requirement exists to stop the WRONG rung being picked.
        # A single peak offers no wrong rung, and refusing it lost C3-poster-dots,
        # the one plate in its set whose dots are visible from across the room.
        r = np.zeros(400)
        r[0] = 1.0
        r[33], r[34], r[35] = .4, .5, .4
        lag, _, _ = M._fundamental(r, 1200)
        self.assertEqual(lag, 34)

    def test_the_harmonic_window_is_proportional_not_plus_or_minus_one(self):
        # A real 7.2px pitch shows up at lags 8 and 14, two apart from 2x8. A
        # +-1 window refused six of eighteen plates whose screens were legible.
        r = np.zeros(400)
        r[0] = 1.0
        for lag, v in ((8, .35), (14, .55), (21, .30)):
            r[lag - 1], r[lag], r[lag + 1] = v - .1, v, v - .1
        lag, _, _ = M._fundamental(r, 1200)
        self.assertEqual(lag, 8)

    def test_a_ladder_with_no_harmonic_anywhere_refuses(self):
        r = np.zeros(400)
        r[0] = 1.0
        for lag, v in ((7, .3), (11, .4), (18, .35), (28, .3)):
            r[lag - 1], r[lag], r[lag + 1] = v - .1, v, v - .1
        with self.assertRaises(M.Unmeasurable):
            M._fundamental(r, 1200)

    def test_it_refuses_a_flat_patch_rather_than_inventing_a_pitch(self):
        with self.assertRaises(M.Unmeasurable):
            M.measure_periodic(flat(), PATCH)

    def test_it_refuses_a_patch_too_small_to_hold_cycles(self):
        with self.assertRaises(M.Unmeasurable):
            M.measure_periodic(screen(192), (0.0, 0.0, 0.01, 0.01))

    def test_the_patch_is_required_and_is_recorded(self):
        m = M.measure_periodic(screen(192), PATCH)
        self.assertEqual(m["patch"]["fractional"], list(PATCH))
        self.assertIn("detrend", m["method"])

    def test_a_patch_is_fractions_not_pixels(self):
        for bad in ("0,0,1536,1024", "0.5,0.1,0.2,0.9", "0.1,0.2,0.3"):
            with self.subTest(bad=bad), self.assertRaises(M.Unmeasurable):
                M.parse_patch(bad)


class TestPatch(unittest.TestCase):
    def test_mean_and_distance(self):
        m = M.measure_patch(flat((143, 170, 204)), PATCH, "#8FAACC")
        self.assertEqual(m["mean"]["hex"], "#8FAACC")
        self.assertEqual(m["dHex"], 0)

    def test_distance_is_max_per_channel_not_euclidean(self):
        # One channel 60 out, the others exact. A mean or Euclidean distance
        # dilutes that to something forgiving; the failure is in the one channel.
        m = M.measure_patch(flat((143, 170, 144)), PATCH, "#8FAACC")
        self.assertEqual(m["dHex"], 60)

    def test_no_target_means_no_distance_rather_than_a_zero(self):
        m = M.measure_patch(flat(), PATCH)
        self.assertNotIn("dHex", m)


class TestRecord(unittest.TestCase):
    def test_a_second_measurement_does_not_delete_the_first(self):
        # One plate legitimately carries both a pitch and a colour. The first
        # shape of this file was flat, so measuring the second CLOBBERED the first.
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            img = pathlib.Path(d) / "plate.png"
            screen(192).save(img)
            M.write_record(img, M.measure_periodic(Image.open(img), PATCH))
            M.write_record(img, M.measure_patch(Image.open(img), PATCH, "#8FAACC"))
            import json
            doc = json.loads(M.record_path(img).read_text())
            self.assertEqual(sorted(doc), ["patch", "periodic"])

    def test_a_legacy_flat_record_is_folded_in_rather_than_dropped(self):
        import json, tempfile
        with tempfile.TemporaryDirectory() as d:
            img = pathlib.Path(d) / "plate.png"
            screen(192).save(img)
            M.record_path(img).write_text(json.dumps({"kind": "figure", "headToBody": 7.2}))
            M.write_record(img, M.measure_patch(Image.open(img), PATCH))
            doc = json.loads(M.record_path(img).read_text())
            self.assertEqual(doc["figure"]["headToBody"], 7.2)
            self.assertIn("patch", doc)


if __name__ == "__main__":
    unittest.main()
