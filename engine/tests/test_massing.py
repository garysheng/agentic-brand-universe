"""Tests for the code-built 3D massing renderer (setting blueprints).

The value of a massing blueprint is that it is DETERMINISTIC and that it actually encodes
the geometry claims a setting contract makes. So the tests check exactly that: same spec
gives same bytes, the projector agrees with hand-computed perspective, and the handedness
a setting contract depends on ("bookshelf wall is C1-LEFT") really does invert when the
camera turns around. That last one is the whole reason the plan-view blueprint was not
good enough.
"""

import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from agenticstory import massing  # noqa: E402

try:
    import PIL  # noqa: F401
    HAVE_PIL = True
except ImportError:
    HAVE_PIL = False


ROOM = {
    "title": "TEST ROOM",
    "sheet": {"width": 600, "height": 420},
    "solids": [
        {"type": "box", "min": [0, 0, 0], "max": [8, 4, 3],
         "color": [200, 195, 185], "faces": ["bottom", "front", "back"]},
        # a marker hard against the y=4 wall, so we can prove which side it lands on
        {"type": "box", "min": [3, 3.8, 0], "max": [4, 4.0, 2.5], "color": [120, 90, 60]},
    ],
    "cameras": [
        {"id": "c1", "caption": "C1", "eye": [0.5, 2, 1.6], "target": [8, 2, 1.4], "fov": 60},
        {"id": "c2", "caption": "C2", "eye": [7.5, 2, 1.6], "target": [0, 2, 1.4], "fov": 60},
    ],
    "notes": [{"text": "a rule", "tone": "rule"}],
}


class TestGeometry(unittest.TestCase):
    def test_box_quads_default_is_six_faces(self):
        self.assertEqual(len(massing.box_quads((0, 0, 0), (1, 1, 1))), 6)

    def test_box_quads_face_subset(self):
        q = massing.box_quads((0, 0, 0), (1, 1, 1), ["bottom", "left"])
        self.assertEqual(len(q), 2)

    def test_box_quads_are_planar_and_four_sided(self):
        for q in massing.box_quads((0, 0, 0), (2, 3, 4)):
            self.assertEqual(len(q), 4)
            for axis in range(3):
                vals = {round(p[axis], 9) for p in q}
                if len(vals) == 1:
                    break
            else:
                self.fail("quad is not axis-planar")

    def test_unknown_solid_type_is_refused(self):
        with self.assertRaises(ValueError):
            massing._solids_to_quads([{"type": "sphere", "min": [0, 0, 0], "max": [1, 1, 1]}])


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestRender(unittest.TestCase):
    def test_projection_puts_center_of_view_at_screen_center(self):
        cam = {"eye": [0, 0, 0], "target": [1, 0, 0], "fov": 60}
        _im, project = massing.render_view([], cam, 400, 300)
        x, y = project((5, 0, 0))
        self.assertAlmostEqual(x, 200, delta=0.5)
        self.assertAlmostEqual(y, 150, delta=0.5)

    def test_point_behind_the_camera_does_not_project(self):
        cam = {"eye": [0, 0, 0], "target": [1, 0, 0], "fov": 60}
        _im, project = massing.render_view([], cam, 400, 300)
        self.assertIsNone(project((-5, 0, 0)))

    def test_handedness_inverts_between_opposing_cameras(self):
        """The claim a setting contract makes ('shelf wall is C1-LEFT') must really flip in C2."""
        marker = (3.5, 3.9, 1.2)
        c1 = {"eye": [0.5, 2, 1.6], "target": [8, 2, 1.4], "fov": 60}
        c2 = {"eye": [7.5, 2, 1.6], "target": [0, 2, 1.4], "fov": 60}
        _i1, p1 = massing.render_view([], c1, 600, 420)
        _i2, p2 = massing.render_view([], c2, 600, 420)
        self.assertLess(p1(marker)[0], 300, "marker should read LEFT of centre in C1")
        self.assertGreater(p2(marker)[0], 300, "marker should read RIGHT of centre in C2")

    def test_render_sheet_is_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = os.path.join(td, "a.png"), os.path.join(td, "b.png")
            massing.render_sheet(ROOM, a)
            massing.render_sheet(ROOM, b)
            self.assertEqual(open(a, "rb").read(), open(b, "rb").read())

    def test_render_sheet_honours_declared_size(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "s.png")
            massing.render_sheet(ROOM, p)
            self.assertEqual(Image.open(p).size, (600, 420))

    def test_sheet_needs_a_camera(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                massing.render_sheet({"title": "x", "solids": []}, os.path.join(td, "s.png"))

    def test_recipe_records_deterministic_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "bp.png")
            massing.render_sheet(ROOM, out)
            rp = massing.write_recipe(out, "spec.json", universe="u", spec_version="0.15",
                                      entity="the-long-room")
            rec = json.load(open(rp))
            self.assertTrue(rec["deterministic"])
            self.assertIsNone(rec["model"])
            self.assertIsNone(rec["prompt"])
            self.assertEqual(rec["entity"], "the-long-room")
            self.assertIn("spec.json", rec["inputs"])


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestCLI(unittest.TestCase):
    def test_massing_verb_writes_sheet_and_recipe(self):
        root = os.path.join(os.path.dirname(__file__), "..")
        with tempfile.TemporaryDirectory() as td:
            spec = os.path.join(td, "room.json")
            out = os.path.join(td, "blueprint.png")
            with open(spec, "w") as fh:
                json.dump(ROOM, fh)
            r = subprocess.run([sys.executable, "-m", "agenticstory.cli", "massing", spec,
                                "--out", out, "--entity", "the-long-room"],
                               cwd=root, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue(os.path.exists(out))
            self.assertTrue(os.path.exists(out + ".recipe.json"))


if __name__ == "__main__":
    unittest.main()
