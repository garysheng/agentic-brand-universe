#!/usr/bin/env python3
"""
Tests for the explanatory-plate emitter.

This emitter is deterministic, which is exactly why it is worth unit testing: every
rule it enforces is a `computed` invariant, so a test can assert the same thing the
gate asserts, for free, with no model in the loop.

Each test below corresponds to a defect that actually shipped or that the gate was
written to stop. Where that is true the test says so, because a test whose reason is
forgotten is the first one someone deletes.
"""
import contextlib, io, json, os, re, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPTS = os.path.join(os.path.dirname(HERE), "scripts")
sys.path.insert(0, SCRIPTS)
import plate  # noqa: E402


def quiet_gate(*a, **kw):
    """Several tests trigger the gate ON PURPOSE. Its diagnostics are correct output,
    but printed into the shared test runner they land after the summary line and hide
    whether the suite passed. Swallow them here; the return value is what is asserted."""
    with contextlib.redirect_stdout(io.StringIO()):
        return plate.gate(*a, **kw)


def quiet_gate_headers(*a, **kw):
    with contextlib.redirect_stdout(io.StringIO()):
        return plate.gate_headers(*a, **kw)


def spec_rows(**over):
    s = {
        "title": "A test plate", "primitive": "rows", "width": 900, "colWidth": 150,
        "reachFor": "WHO DOES WHAT", "columns": ["ONE", "TWO"],
        "rows": [{"name": "First", "sub": "a subtitle", "who": ["YOU", "ant"]}],
        "out": "/dev/null",
    }
    s.update(over)
    return s


def spec_stack(**over):
    s = {
        "title": "A stack", "primitive": "stack", "width": 900,
        "eyebrow": "READ IT BOTTOM UP",
        "layers": [{"name": "COMPOSER", "sub": "the agent", "tag": "AGENTIC", "accent": True},
                   {"name": "CANON", "sub": "typed entities"}],
        "out": "/dev/null",
    }
    s.update(over)
    return s


class TestPalette(unittest.TestCase):
    """The plate may only use tokens. An off-palette colour is the single most
    common way a 'small tweak' leaves the brand."""

    def test_every_emitted_colour_is_a_token(self):
        for dark in (True, False):
            svg, H = plate.build(spec_rows(), dark)
            used = {c.lower() for c in re.findall(r"#[0-9a-fA-F]{6}", svg)}
            allowed = {v.lower() for v in plate.T.values()}
            self.assertTrue(used, "plate emitted no colours at all, gate would be vacuous")
            self.assertEqual(used - allowed, set(), f"off-palette colour in dark={dark}")

    def test_gate_rejects_an_off_palette_colour(self):
        svg, H = plate.build(spec_rows(), True)
        poisoned = svg.replace(plate.T["clay"], "#ff00ff")
        self.assertFalse(quiet_gate(poisoned, H, "test"))

    def test_gate_accepts_clean_output(self):
        svg, H = plate.build(spec_rows(), True)
        self.assertTrue(plate.gate(svg, H, "test"))


class TestGeometry(unittest.TestCase):
    def test_nothing_is_drawn_below_the_declared_height(self):
        """Content past the viewBox is silently clipped: it looks like a plate that
        just does not mention the last row."""
        for maker in (spec_rows, spec_stack):
            for dark in (True, False):
                svg, H = plate.build(maker(), dark)
                ys = [float(m) for m in re.findall(r'\by="(-?[\d.]+)"', svg)]
                self.assertTrue(ys)
                self.assertLessEqual(max(ys), H, f"{maker.__name__} clips at dark={dark}")

    def test_gate_rejects_clipped_content(self):
        svg, H = plate.build(spec_rows(), True)
        clipped = svg.replace("</svg>", f'<text y="{H + 40}">below</text></svg>')
        self.assertFalse(quiet_gate(clipped, H, "test"))

    def test_height_grows_with_row_count(self):
        one = plate.build(spec_rows(), True)[1]
        many = plate.build(spec_rows(rows=[
            {"name": f"R{i}", "sub": "s", "who": ["YOU", "ant"]} for i in range(5)]), True)[1]
        self.assertGreater(many, one)


class TestHeaderFit(unittest.TestCase):
    """Two column headers wider than their columns overlap and read as one garbled
    word. It looks fine in the JSON and is obvious the moment it renders."""

    def test_header_that_fits_passes(self):
        self.assertTrue(plate.gate_headers(spec_rows(columns=["ONE", "TWO"])))

    def test_header_wider_than_its_column_fails(self):
        self.assertFalse(quiet_gate_headers(
            spec_rows(colWidth=60, columns=["A VERY LONG COLUMN HEADER INDEED"])))

    def test_wrapped_header_is_measured_per_line_not_whole(self):
        """'A|B' renders as two lines, so it must be measured per line. Measuring the
        raw string would false-fail every wrapped header."""
        self.assertTrue(plate.gate_headers(spec_rows(colWidth=150, columns=["SHORT|LINES"])))

    def test_header_fit_only_applies_to_rows(self):
        self.assertTrue(plate.gate_headers(spec_stack()))


class TestStructure(unittest.TestCase):
    def test_gate_requires_a_title(self):
        svg, H = plate.build(spec_rows(), True)
        self.assertFalse(quiet_gate(re.sub(r"<title>.*?</title>", "", svg), H, "t"))

    def test_gate_requires_role_img(self):
        svg, H = plate.build(spec_rows(), True)
        self.assertFalse(quiet_gate(svg.replace('role="img"', ""), H, "t"))

    def test_title_is_the_accessible_name(self):
        svg, _ = plate.build(spec_rows(title="Why it is Managed Agents"), True)
        self.assertIn("<title>Why it is Managed Agents</title>", svg)


class TestEscaping(unittest.TestCase):
    """Spec text is authored by hand and by agents. An unescaped ampersand makes the
    SVG unparseable, which presents as an image that silently does not load."""

    def test_ampersand_is_escaped(self):
        svg, _ = plate.build(spec_rows(title="Canon & Goldens"), True)
        self.assertIn("Canon &amp; Goldens", svg)
        self.assertNotIn("Canon & Goldens", svg)

    def test_angle_brackets_cannot_inject_markup(self):
        svg, _ = plate.build(spec_rows(title="<script>x</script>"), True)
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)


class TestAnthropicMark(unittest.TestCase):
    """The mark is lifted verbatim from anthropic.com's nav. It was previously drawn
    by hand and the A-to-bar gap and the bar length were both wrong. Locking the path
    data means a future 'cleanup' cannot silently redraw it."""

    def test_path_data_is_the_authentic_geometry(self):
        self.assertTrue(plate._MARK_A.startswith("M9.49897 0L0 24H5.31125"))
        self.assertTrue(plate._MARK_BAR.startswith("M24.5475 0H19.3384"))
        self.assertEqual((plate.MARK_W, plate.MARK_H), (35.0, 24.0))

    def test_mark_is_centred_on_the_requested_point(self):
        g = plate.anthropic_mark(cx=100, cy=50, h=24, cls="k")
        x, y = (float(v) for v in re.search(r"translate\(([-\d.]+),([-\d.]+)\)", g).groups())
        s = float(re.search(r"scale\(([\d.]+)\)", g).group(1))
        self.assertAlmostEqual(x + plate.MARK_W * s / 2, 100, places=1)
        self.assertAlmostEqual(y + 24 / 2, 50, places=1)

    def test_mark_scales_by_cap_height(self):
        self.assertAlmostEqual(
            float(re.search(r"scale\(([\d.]+)\)", plate.anthropic_mark(0, 0, 48, "k")).group(1)),
            48 / plate.MARK_H, places=3)


class TestDualEmit(unittest.TestCase):
    """One source emits the theme-aware plate AND a light-locked copy. That used to be
    a hand-maintained @media strip, which is what let a dark plate ship onto a cream
    deck slide."""

    def test_dark_and_light_differ(self):
        self.assertNotEqual(plate.build(spec_rows(), True)[0], plate.build(spec_rows(), False)[0])

    def test_light_locked_copy_carries_no_dark_scheme_rule(self):
        light = plate.build(spec_rows(), False)[0]
        self.assertNotIn("prefers-color-scheme", light)

    def test_theme_aware_copy_does_respond_to_scheme(self):
        self.assertIn("prefers-color-scheme", plate.build(spec_rows(), True)[0])

    def test_geometry_is_identical_across_the_two(self):
        """Only colour may differ. If the light copy laid out differently, the deck
        and the wiki would disagree about the same diagram."""
        self.assertEqual(plate.build(spec_rows(), True)[1], plate.build(spec_rows(), False)[1])


class TestDeterminism(unittest.TestCase):
    def test_same_spec_gives_byte_identical_output(self):
        a = plate.build(spec_stack(), True)[0]
        b = plate.build(spec_stack(), True)[0]
        self.assertEqual(a, b)


class TestPrimitives(unittest.TestCase):
    def test_every_registered_primitive_renders(self):
        specs = {
            "rows": spec_rows(),
            "stack": spec_stack(),
            "dotgrid": {"title": "d", "primitive": "dotgrid", "width": 900,
                        "eyebrow": "A CORPUS", "headline": "Six of many",
                        "total": 24, "on": 6,
                        "legend": [{"on": True, "n": "6", "text": "done"}],
                        "out": "/dev/null"},
            "split": {"title": "s", "primitive": "split", "width": 900,
                      "panels": [{"eyebrow": "L", "headline": "Left", "items": ["a"],
                                  "accent": True, "foot": "f"},
                                 {"eyebrow": "R", "headline": "Right", "items": ["b"]}],
                      "out": "/dev/null"},
        }
        self.assertEqual(set(specs), set(plate.PRIMITIVES),
                         "a primitive was added or removed without updating this test")
        for name, s in specs.items():
            with self.subTest(primitive=name):
                svg, H = plate.build(s, True)
                self.assertTrue(svg.startswith("<svg"), name)
                self.assertTrue(svg.rstrip().endswith("</svg>"), name)
                self.assertTrue(plate.gate(svg, H, name), name)


class TestCli(unittest.TestCase):
    def test_writes_both_files_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as d:
            dark, light = os.path.join(d, "a.svg"), os.path.join(d, "a.light.svg")
            p = os.path.join(d, "spec.json")
            with open(p, "w") as f:
                json.dump(spec_rows(out=dark, outLightLocked=light), f)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "plate.py"), p],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue(os.path.exists(dark) and os.path.exists(light))

    def test_a_failing_header_gate_exits_nonzero_and_writes_nothing(self):
        """A gate that fails but still writes the file is not a gate."""
        with tempfile.TemporaryDirectory() as d:
            out = os.path.join(d, "a.svg")
            p = os.path.join(d, "spec.json")
            with open(p, "w") as f:
                json.dump(spec_rows(out=out, colWidth=40,
                                    columns=["AN EXTREMELY LONG HEADER"]), f)
            r = subprocess.run([sys.executable, os.path.join(SCRIPTS, "plate.py"), p],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 1)
            self.assertFalse(os.path.exists(out))


if __name__ == "__main__":
    unittest.main(verbosity=1)
