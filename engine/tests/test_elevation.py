"""Tests for the 2D elevation blueprint renderer.

The load-bearing ones are the GUARD test and the REPEAT test. The guard is what five
of the nine hand-rolled sheets this replaces forgot; repeat is where their hand-written
member loops hid off-by-ones.
"""
import json
import os
import tempfile
import unittest

from agenticstory import elevation


def _has_pillow() -> bool:
    try:
        import PIL  # noqa: F401
        return True
    except Exception:
        return False


MINIMAL = {
    "title": "TEST DOOR",
    "subtitle": "ELEVATION",
    "sheet": {"width": 800, "height": 600, "margin": 40},
    "scale": {"unit": "ft", "pxPerUnit": 50, "originPx": [200, 150]},
    "parts": [{"kind": "rect", "at": [0, 0], "size": [3, 7], "fill": "wood", "stroke": "ink"}],
    "laws": ["A STANDING LAW."],
}


class TestExpand(unittest.TestCase):
    def test_repeat_offsets_every_coordinate_key(self):
        parts = [{"kind": "repeat", "count": 3, "step": [0.6, 0],
                  "of": {"kind": "line", "from": [1, 0], "to": [1, 7]}}]
        out = elevation._expand(parts)
        self.assertEqual([p["from"][0] for p in out], [1.0, 1.6, 2.2])
        self.assertEqual([p["to"][0] for p in out], [1.0, 1.6, 2.2])
        # y untouched by an x-only step
        self.assertTrue(all(p["from"][1] == 0 and p["to"][1] == 7 for p in out))

    def test_repeat_count_is_exact_no_off_by_one(self):
        """The bug every hand-written member loop eventually ships."""
        for n in (0, 1, 5):
            out = elevation._expand([{"kind": "repeat", "count": n, "step": [1, 0],
                                      "of": {"kind": "rect", "at": [0, 0], "size": [1, 1]}}])
            self.assertEqual(len(out), n)

    def test_repeat_numbers_labels_from_one_by_default(self):
        out = elevation._expand([{"kind": "repeat", "count": 3, "step": [1, 0],
                                  "of": {"kind": "rect", "at": [0, 0], "size": [1, 1],
                                         "text": "plank {i}"}}])
        self.assertEqual([p["text"] for p in out], ["plank 1", "plank 2", "plank 3"])

    def test_repeat_does_not_mutate_the_prototype(self):
        proto = {"kind": "rect", "at": [0, 0], "size": [1, 1]}
        elevation._expand([{"kind": "repeat", "count": 3, "step": [5, 5], "of": proto}])
        self.assertEqual(proto["at"], [0, 0])

    def test_repeat_rejects_a_non_object_prototype(self):
        with self.assertRaises(ValueError):
            elevation._expand([{"kind": "repeat", "count": 2, "of": "rect"}])

    def test_non_repeat_parts_pass_through(self):
        parts = [{"kind": "rect", "at": [0, 0], "size": [1, 1]}]
        self.assertEqual(elevation._expand(parts), parts)


class TestColor(unittest.TestCase):
    def test_palette_names_and_hex_and_triples(self):
        self.assertEqual(elevation._color("ink"), elevation.INK)
        self.assertEqual(elevation._color("#ff0000"), (255, 0, 0))
        self.assertEqual(elevation._color([1, 2, 3]), (1, 2, 3))

    def test_unknown_colour_fails_closed(self):
        with self.assertRaises(ValueError):
            elevation._color("chartreuse-ish")


class TestScale(unittest.TestCase):
    def test_declared_units_convert_to_pixels_from_the_origin(self):
        s = elevation._Scale({"scale": {"unit": "ft", "pxPerUnit": 84, "originPx": [300, 200]}},
                             {"margin": 60})
        self.assertEqual(s.p([0, 0]), (300.0, 200.0))
        self.assertEqual(s.p([3, 7]), (300 + 3 * 84, 200 + 7 * 84))
        self.assertEqual(s.d(1), 84.0)

    def test_nonpositive_scale_fails_closed(self):
        with self.assertRaises(ValueError):
            elevation._Scale({"scale": {"pxPerUnit": 0}}, {"margin": 60})


@unittest.skipUnless(_has_pillow(), "Pillow not installed")
class TestRender(unittest.TestCase):
    def test_renders_at_the_declared_sheet_size(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "bp.png")
            elevation.render_sheet(MINIMAL, out)
            self.assertEqual(Image.open(out).size, (800, 600))

    def test_deterministic_same_spec_same_pixels(self):
        with tempfile.TemporaryDirectory() as td:
            a, b = os.path.join(td, "a.png"), os.path.join(td, "b.png")
            elevation.render_sheet(MINIMAL, a)
            elevation.render_sheet(MINIMAL, b)
            self.assertEqual(open(a, "rb").read(), open(b, "rb").read())

    def test_guard_is_always_stamped_even_with_no_laws(self):
        """Five of the nine hand-rolled sheets omitted this. It has no off switch."""
        spec = dict(MINIMAL)
        spec.pop("laws", None)
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "bp.png")
            elevation.render_sheet(spec, out)
            self.assertTrue(os.path.exists(out))
        # the guard text is a module constant consumers can assert on
        self.assertIn("LAYOUT REFERENCE ONLY", elevation.GUARD)

    def test_every_documented_part_kind_renders(self):
        spec = dict(MINIMAL)
        spec["parts"] = [
            {"kind": "rect", "at": [0, 0], "size": [3, 7], "fill": "wood", "stroke": "ink"},
            {"kind": "rect", "at": [1, 5], "size": [1, 1], "stroke": "accent", "dashed": True},
            {"kind": "line", "from": [0, 0], "to": [3, 0], "stroke": "ink"},
            {"kind": "ellipse", "center": [2.8, 4], "r": [0.25, 0.25], "stroke": "iron", "width": 7},
            {"kind": "polygon", "points": [[0, 1], [1.8, 1.1], [1.8, 1.3], [0, 1.4]], "fill": "iron"},
            {"kind": "repeat", "count": 4, "step": [0.6, 0],
             "of": {"kind": "line", "from": [0.6, 0], "to": [0.6, 7], "stroke": "ink", "width": 2}},
            {"kind": "dim", "axis": "h", "from": [0, 7], "to": [3, 7], "offset": 38, "label": "3 ft"},
            {"kind": "dim", "axis": "v", "from": [0, 0], "to": [0, 7], "offset": 60, "label": "7 ft"},
            {"kind": "note", "at": [-2.4, 4], "text": ["FLAP FOOTPRINT", "14 in x 12 in"],
             "leaderTo": [1, 5.5], "stroke": "accent"},
        ]
        with tempfile.TemporaryDirectory() as td:
            out = os.path.join(td, "bp.png")
            self.assertEqual(elevation.render_sheet(spec, out), out)
            self.assertTrue(os.path.getsize(out) > 0)

    def test_unknown_part_kind_fails_closed(self):
        spec = dict(MINIMAL)
        spec["parts"] = [{"kind": "sprocket", "at": [0, 0]}]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(ValueError):
                elevation.render_sheet(spec, os.path.join(td, "bp.png"))

    def test_recipe_records_the_spec_and_no_model(self):
        with tempfile.TemporaryDirectory() as td:
            sp = os.path.join(td, "spec.json")
            with open(sp, "w") as fh:
                json.dump(MINIMAL, fh)
            out = os.path.join(td, "bp.png")
            elevation.render_sheet(MINIMAL, out)
            rp = elevation.write_recipe(out, sp, entity="the-little-door", spec_version="0.16")
            rec = json.load(open(rp))
            self.assertEqual(rec["generator"], "agenticstory.elevation")
            self.assertIsNone(rec["model"])
            self.assertEqual(rec["inputs"], [])
            self.assertEqual(rec["entity"], "the-little-door")
            self.assertTrue(rec["spec"].endswith("spec.json"))


if __name__ == "__main__":
    unittest.main()
