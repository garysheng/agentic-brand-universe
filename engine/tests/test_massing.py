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
from pathlib import Path

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


@unittest.skipUnless(HAVE_PIL, "Pillow not installed")
class TestNearPlaneClipping(unittest.TestCase):
    """A ground plane extending behind the eye must still render.

    The renderer used to DROP any face with a vertex at or behind the near plane.
    A floor, lawn or tabletop is normally one big quad that extends under and
    behind the camera, so it vanished entirely and the sheet came back as empty
    background. Silent, and it pushes authors into chopping the ground into
    strips that all sit in front of the eye.
    """

    def _spec(self, pts):
        return {
            "title": "CLIP TEST",
            "sheet": {"width": 320, "height": 240},
            "solids": [{"type": "quad", "pts": pts, "color": [40, 200, 40]}],
            "cameras": [{"id": "c1", "caption": "c1", "eye": [0, 0, 2],
                         "target": [0, -10, 0], "fov": 60}],
        }

    def _render(self, spec):
        import PIL.Image
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "s.png"
            massing.render_sheet(spec, str(out))
            return PIL.Image.open(out).convert("RGB").copy()

    def _has_green(self, im):
        return any(g > r + 30 and g > b + 30 for r, g, b in im.getdata())

    def test_ground_spanning_the_eye_is_not_dropped(self):
        """The regression: near corners BEHIND the camera at y=0."""
        im = self._render(self._spec([[-8, -20, 0], [8, -20, 0], [8, 4, 0], [-8, 4, 0]]))
        self.assertTrue(self._has_green(im), "ground plane vanished entirely")

    def test_fully_forward_polygon_still_renders(self):
        im = self._render(self._spec([[-8, -20, 0], [8, -20, 0], [8, -2, 0], [-8, -2, 0]]))
        self.assertTrue(self._has_green(im))

    def test_fully_behind_polygon_is_dropped(self):
        im = self._render(self._spec([[-8, 6, 0], [8, 6, 0], [8, 20, 0], [-8, 20, 0]]))
        self.assertFalse(self._has_green(im), "geometry behind the eye must not draw")

    def test_clip_returns_forward_polygon_unchanged(self):
        cam = [(0, 0, -5), (1, 0, -5), (1, 1, -5)]
        self.assertEqual(massing._clip_near(cam), cam)

    def test_clip_drops_fully_behind_polygon(self):
        cam = [(0, 0, 1), (1, 0, 2), (1, 1, 3)]
        self.assertLess(len(massing._clip_near(cam)), 3)


class TestAuthoring(unittest.TestCase):
    """Authoring helpers + the scaffolder (2026-07-31).

    The renderer took a FINISHED spec and nothing helped anyone write one, so
    every setting that needed a blueprint grew the same throwaway file beside it,
    redefining `quad`, `box`, and a `room` that is a floor plus three walls. Four
    rooms in one run before this was promoted.
    """

    def test_room_leaves_the_near_wall_open(self):
        """Every camera stands against the near wall looking in. Drawing that wall
        would put an opaque quad between the camera and the whole room."""
        solids = massing.room(4, 5, 2.5)
        self.assertEqual(len(solids), 4)          # floor + far + left + right
        ys = [min(p[1] for p in s["pts"]) for s in solids]
        # no solid is a full plane at y=0 spanning the room's width and height
        near = [s for s in solids
                if all(p[1] == 0 for p in s["pts"]) and any(p[2] > 0 for p in s["pts"])]
        self.assertEqual(near, [], "the near wall must not be drawn")
        self.assertEqual(min(ys), 0)

    def test_room_uses_the_declared_dimensions(self):
        solids = massing.room(4, 5, 2.5)
        xs = [p[0] for s in solids for p in s["pts"]]
        zs = [p[2] for s in solids for p in s["pts"]]
        self.assertEqual((max(xs), max(zs)), (4, 2.5))

    def test_room_renders_without_further_editing(self):
        spec = {"title": "T", "solids": massing.room(3, 3, 2.4),
                "cameras": [{"id": "c1", "eye": [1.5, 0.3, 1.5], "target": [1.5, 3, 1.2]}]}
        with tempfile.TemporaryDirectory() as t:
            out = massing.render_sheet(spec, os.path.join(t, "b.png"))
            self.assertTrue(os.path.exists(out))

    def test_box_and_quad_emit_renderable_solids(self):
        solids = massing.room(3, 3, 2.4) + [
            massing.box([0.9, 1.5, 0], [1.9, 3.4, 0.62], massing.DARK),
            massing.quad([[0.02, 2.2, 0.9], [0.02, 3.2, 0.9],
                          [0.02, 3.2, 2.0], [0.02, 2.2, 2.0]], massing.GLASS)]
        quads = massing._solids_to_quads(solids)
        self.assertGreater(len(quads), len(solids))   # the box expands to faces

    def test_scaffold_emits_two_OPPOSED_cameras_by_default(self):
        """Handedness is a property of the CAMERA, so one camera cannot state it."""
        spec = massing.scaffold_room("the long room", 4, 6, 2.6)
        self.assertEqual(len(spec["cameras"]), 2)
        a, b = spec["cameras"]
        self.assertLess(a["eye"][1], b["eye"][1])
        self.assertGreater(a["target"][1], b["target"][1])

    def test_scaffold_leaves_the_furniture_to_the_author(self):
        """What a room CONTAINS is authorship. A scaffolder that guessed it would
        be guessing the story."""
        spec = massing.scaffold_room("t", 4, 6, 2.6)
        self.assertEqual(len(spec["solids"]), 4)
        self.assertTrue(any("TODO(author)" in n["text"] for n in spec["notes"]))

    def test_scaffold_records_the_size_in_the_subtitle(self):
        spec = massing.scaffold_room("t", 4, 6, 2.6)
        self.assertIn("4 x 6 x 2.6", spec["subtitle"])

    def test_scaffold_output_renders(self):
        spec = massing.scaffold_room("t", 4, 6, 2.6)
        with tempfile.TemporaryDirectory() as t:
            self.assertTrue(os.path.exists(massing.render_sheet(spec, os.path.join(t, "b.png"))))

    def test_cli_scaffold_then_render(self):
        eng = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as t:
            js, png = os.path.join(t, "s.json"), os.path.join(t, "s.png")
            r = subprocess.run([sys.executable, "-m", "agenticstory.cli", "massing-scaffold",
                                "Sickroom", "--size", "3.6x3.6x2.4", "--out", js],
                               cwd=eng, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            r = subprocess.run([sys.executable, "-m", "agenticstory.cli", "massing", js,
                                "--out", png, "--no-recipe"],
                               cwd=eng, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.exists(png))

    def test_cli_scaffold_refuses_to_clobber_an_authored_spec(self):
        """Overwriting would lose the furniture, the only part a human wrote."""
        eng = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as t:
            js = os.path.join(t, "s.json")
            open(js, "w").write("{}")
            r = subprocess.run([sys.executable, "-m", "agenticstory.cli", "massing-scaffold",
                                "T", "--size", "3x3x2.4", "--out", js],
                               cwd=eng, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("--force", r.stdout + r.stderr)

    def test_cli_scaffold_rejects_a_bad_size(self):
        eng = str(Path(__file__).resolve().parents[1])
        with tempfile.TemporaryDirectory() as t:
            r = subprocess.run([sys.executable, "-m", "agenticstory.cli", "massing-scaffold",
                                "T", "--size", "big", "--out", os.path.join(t, "s.json")],
                               cwd=eng, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("WxDxH", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
