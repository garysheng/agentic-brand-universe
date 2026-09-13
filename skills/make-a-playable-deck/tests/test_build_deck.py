#!/usr/bin/env python3
"""Does the deck builder refuse what it should, and is its output actually self-contained?"""
import json, pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE.parent / "scripts" / "build_deck.py"
PAL = {"tokens": {"ink": {"hex": "#1E1B19"}, "cream": {"hex": "#F0ECE5"},
                  "live": {"hex": "#007AFF"}}}


def run(deck, extra=(), palette=None):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "deck.json").write_text(json.dumps(deck))
    cmd = [sys.executable, str(BUILD), str(d / "deck.json"), "--out", str(d / "out")]
    if palette is not None:
        (d / "pal.json").write_text(json.dumps(palette))
        cmd += ["--palette", str(d / "pal.json")]
    cmd += list(extra)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r, d / "out" / "index.html"


MIN = {"title": "T", "slides": [{"kind": "statement", "heading": "H", "body": "B"}]}


class Refusals(unittest.TestCase):
    def test_no_slides(self):
        r, _ = run({"title": "T", "slides": []})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no slides", r.stdout + r.stderr)

    def test_unknown_kind_names_the_known_ones(self):
        r, _ = run({"slides": [{"kind": "carousel"}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("known kinds are", r.stdout + r.stderr)

    def test_UNKNOWN_KEY_IS_REFUSED_BY_NAME(self):
        """The defect a deck cannot show you: a mistyped key means the content is simply
        absent on one slide and the deck still looks finished."""
        r, _ = run({"slides": [{"kind": "statement", "heading": "H", "bodyy": "typo"}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("bodyy", r.stdout + r.stderr)

    def test_missing_required_payload(self):
        for kind, need in (("pair", "images"), ("quote", "quote"),
                           ("chat", "turns"), ("list", "items")):
            r, _ = run({"slides": [{"kind": kind, "heading": "H"}]})
            self.assertNotEqual(r.returncode, 0, kind)
            self.assertIn(need, r.stdout + r.stderr, kind)

    def test_table_needs_columns(self):
        r, _ = run({"slides": [{"kind": "table", "rows": [["a", "b"]]}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("columns", r.stdout + r.stderr)


class Output(unittest.TestCase):
    def test_self_contained_single_file(self):
        r, p = run(MIN)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        # No external stylesheet or script: a deck read on a phone with bad signal, or saved
        # to disk and reopened, must not depend on a second request.
        self.assertNotIn("<link rel=\"stylesheet\"", t)
        self.assertNotIn("<script src=", t)
        self.assertIn("function fitSlide", t)
        self.assertIn("section class=\"s\"", t)

    def test_palette_is_read_not_typed(self):
        r, p = run(MIN, palette=PAL)
        t = p.read_text()
        self.assertIn("--live:#007AFF", t)
        self.assertIn("palette pal.json", t)

    def test_absent_palette_is_SAID_not_silently_defaulted(self):
        """A deck not carrying a universe's tokens must say so in its own provenance, or a
        reader cannot tell a themed deck from an unthemed one."""
        r, p = run(MIN)
        self.assertIn("no palette passed", p.read_text())

    def test_missing_token_is_named(self):
        r, p = run(MIN, palette={"tokens": {"ink": {"hex": "#111111"}}})
        t = p.read_text()
        self.assertIn("MISSING cream, live", t)

    def test_noindex_because_a_deck_is_sent_not_published(self):
        r, p = run(MIN)
        self.assertIn('name="robots" content="noindex,nofollow"', p.read_text())

    def test_dvh_not_vh(self):
        """On iOS Safari vh is taller than the visible viewport, so a vh deck hides its own
        footer on the device most likely to open a link from a text message.

        ASSERT THE DECLARATION, NOT THE STRING. The first version of this test checked for
        "100dvh" anywhere in the output and passed on the CSS COMMENT that explains the
        choice, so it survived a mutation changing the real declaration to 100vh. A check
        that matches its own documentation is a check that never ran.
        """
        r, p = run(MIN)
        t = p.read_text()
        self.assertIn("height:100dvh", t)
        self.assertNotIn("height:100vh", t)

    def test_content_is_escaped(self):
        r, p = run({"slides": [{"kind": "statement",
                                "heading": "<script>alert(1)</script>", "body": "x"}]})
        t = p.read_text()
        self.assertNotIn("<script>alert(1)", t)
        self.assertIn("&lt;script&gt;", t)

    def test_bold_and_italic_survive_escaping(self):
        r, p = run({"slides": [{"kind": "statement", "heading": "H",
                                "body": "a **hard** and *soft* word"}]})
        t = p.read_text()
        self.assertIn("<strong>hard</strong>", t)
        self.assertIn("<em>soft</em>", t)

    def test_unbalanced_marks_are_left_alone(self):
        r, p = run({"slides": [{"kind": "statement", "heading": "H", "body": "2 ** 3 is 8"}]})
        self.assertNotIn("<strong>", p.read_text())

    def test_assets_are_copied_so_the_folder_travels(self):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "a").mkdir(); (d / "a" / "x.png").write_bytes(b"\x89PNG\r\n")
        r, p = run({"slides": [{"kind": "image", "image": "x.png", "caption": "c"}]},
                   extra=["--assets", str(d / "a")])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue((p.parent / "x.png").exists())

    def test_every_kind_renders(self):
        deck = {"title": "T", "slides": [
            {"kind": "cover", "heading": "H", "lede": "L"},
            {"kind": "statement", "heading": "H", "body": ["a", "b"]},
            {"kind": "image", "image": "i.png", "caption": "c"},
            {"kind": "pair", "images": [{"image": "a.png"}, {"image": "b.png"}]},
            {"kind": "split", "heading": "H", "body": "b", "image": "i.png"},
            {"kind": "quote", "quote": "q", "who": "w"},
            {"kind": "chat", "turns": [{"from": "me", "text": "hi"},
                                       {"from": "them", "text": "yo"}]},
            {"kind": "table", "columns": ["a", "b"], "rows": [["x", "1"], ["y", "2"]],
             "pick": "y"},
            {"kind": "list", "items": ["one", "two"]}]}
        r, p = run(deck)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        self.assertEqual(t.count('<section class="s"'), 9)
        self.assertIn('class="b me"', t)
        self.assertIn('<tr class="pick">', t)

    def test_deterministic(self):
        """Same slides, same bytes. A deck that changes on every build cannot be reviewed."""
        r1, p1 = run(MIN, palette=PAL)
        r2, p2 = run(MIN, palette=PAL)
        self.assertEqual(p1.read_text(), p2.read_text())


class Glow(unittest.TestCase):
    """The Freedom Glow chrome: opt-in, derived, and NOT neon.

    The derivation went wrong once in exactly the way worth a regression test. The live token
    is fully saturated, so rotating its hue at that saturation produced #FF14C8 and #FFF314:
    rainbow confetti, which is the failure the brand's own canon warns against. The fix was to
    drop saturation so a hue reads as light rather than paint, and a ceiling here is what stops
    a future edit walking it back up.
    """

    def test_off_by_default_so_no_universe_inherits_a_rainbow(self):
        r, p = run(MIN, palette=PAL)
        t = p.read_text()
        self.assertNotIn("@keyframes corebreathe", t)
        self.assertIn("chrome: flat accent", t)

    def test_on_when_declared(self):
        r, p = run(dict(MIN, glow=True), palette=PAL)
        t = p.read_text()
        for k in ("corebreathe", "wander1", "wander2", "wander3", "breathe"):
            self.assertIn("@keyframes " + k, t, k)
        self.assertIn("the Freedom Glow, derived from live", t)

    def test_DERIVED_STOPS_ARE_LIGHT_NOT_NEON(self):
        """The regression. Saturation is what separates light from paint here."""
        sys.path.insert(0, str(BUILD.parent))
        from build_deck import spectrum_from
        import colorsys
        for hexv in spectrum_from("#007AFF"):
            r, g, b = (int(hexv[1:][i:i + 2], 16) / 255 for i in (0, 2, 4))
            _, s, v = colorsys.rgb_to_hsv(r, g, b)
            self.assertLessEqual(s, 0.62, f"{hexv} is saturated {s:.2f}: that is paint")
            self.assertGreaterEqual(v, 0.85, f"{hexv} is dark at {v:.2f}: light is bright")

    def test_spectrum_starts_at_cyan_not_violet(self):
        """The material law names the order: cyan, green, gold, warm pink, violet. Walking
        the hue circle the other way put violet first and read as a UI theme rather than as
        a separation."""
        sys.path.insert(0, str(BUILD.parent))
        from build_deck import spectrum_from
        import colorsys
        second = spectrum_from("#007AFF")[1]
        r, g, b = (int(second[1:][i:i + 2], 16) / 255 for i in (0, 2, 4))
        h, _, _ = colorsys.rgb_to_hsv(r, g, b)
        self.assertTrue(0.40 <= h <= 0.55, f"the second stop is hue {h:.2f}, not a cyan")

    def test_the_glow_surface_gets_ONE_class_attribute(self):
        """The bug this replaced a test for. Emitting class="fill" class="glowbar" is valid
        HTML that parses, logs nothing, and inspects fine, and the browser silently keeps the
        first and drops the second, so the pools were painted onto an element with no
        positioning context. A duplicate attribute has to be asserted against directly
        because nothing else complains."""
        r, p = run(dict(MIN, glow=True), palette=PAL)
        t = p.read_text()
        fill = [l for l in t.splitlines() if 'class="fill' in l][0]
        self.assertEqual(fill.count("class="), 1, f"two class attributes: {fill.strip()}")
        self.assertIn('class="fill glowbar"', fill)
        self.assertIn("<i></i><i></i><i></i><i></i>", fill)

    def test_pools_are_NOT_screen_blended(self):
        """screen ADDS light, so a pale hue over a saturated blue goes white and the colour
        disappears. That is what 'where are the rainbow colors' was looking at."""
        r, p = run(dict(MIN, glow=True), palette=PAL)
        self.assertNotIn("mix-blend-mode:screen", p.read_text())

    def test_pool_hues_are_actually_chromatic(self):
        """The pools use a higher saturation than the calm set, because a small drifting
        shape needs more chroma to read than a large calm surface does."""
        sys.path.insert(0, str(BUILD.parent))
        from build_deck import spectrum_from
        import colorsys
        for hexv in spectrum_from("#007AFF", sat=0.88):
            r_, g_, b_ = (int(hexv[1:][i:i + 2], 16) / 255 for i in (0, 2, 4))
            _, s, _ = colorsys.rgb_to_hsv(r_, g_, b_)
            self.assertGreaterEqual(s, 0.7, f"{hexv} at {s:.2f} will not read as colour")

    def test_the_traces_take_different_paths(self):
        """One shared keyframe at three speeds is a procession, which the eye reassembles
        into exactly the ordered sweep this design exists to avoid."""
        r, p = run(dict(MIN, glow=True), palette=PAL)
        t = p.read_text()
        import re
        bodies = [m.group(1) for n in ("wander1", "wander2", "wander3")
                  if (m := re.search(r"@keyframes " + n + r"\{(.*?)\}\n", t, re.S))]
        self.assertEqual(len(bodies), 3)
        self.assertEqual(len(set(bodies)), 3, "two traces share a path")

    def test_THE_STRUCTURE_IS_VERTICAL_NOT_A_LEFT_TO_RIGHT_RAMP(self):
        """The regression that matters most. Two earlier attempts put an ordered spectrum
        along the bar's LENGTH, which reads as a flag however the hues are tuned. The mark's
        colour runs through its THICKNESS, edge to core, so the chrome does too."""
        r, p = run(dict(MIN, glow=True), palette=PAL)
        t = p.read_text()
        # The RULE, not its first line: .glowbar{...} wraps across lines, and reading only
        # line one tested the selector rather than the gradient.
        s = t.index(".glowbar{")
        base = t[s:t.index("}", s)]
        self.assertIn("to bottom", base, "the base gradient must run through the thickness")
        self.assertNotIn("90deg", base)
        self.assertNotIn("to right", base)

    def test_the_core_is_lighter_than_the_edge(self):
        """Edge-to-core is the measured direction: deep at the stroke's edge, luminous in the
        middle. Inverting it would read as a tube rather than as light inside."""
        sys.path.insert(0, str(BUILD.parent))
        from build_deck import spectrum_depth
        import colorsys
        d = spectrum_depth("#007AFF")
        def sat(h):
            r_, g_, b_ = (int(h[1:][i:i + 2], 16) / 255 for i in (0, 2, 4))
            return colorsys.rgb_to_hsv(r_, g_, b_)[1]
        self.assertGreater(sat(d[0]), sat(d[-1]), "the core must be less saturated than the edge")

    def test_derived_depth_tracks_the_MEASURED_bands(self):
        """The mark's own light cut measures #066BFA at the edge and #4CC7FB at the core.
        The derivation must land near those or the chrome is a second blue free to disagree
        with the artwork."""
        sys.path.insert(0, str(BUILD.parent))
        from build_deck import spectrum_depth
        d = spectrum_depth("#007AFF")
        def dist(a, b):
            return max(abs(int(a[1:][i:i+2], 16) - int(b[1:][i:i+2], 16)) for i in (0, 2, 4))
        self.assertLessEqual(dist(d[0], "#066BFA"), 30, f"edge {d[0]} is far from measured")
        self.assertLessEqual(dist(d[-1], "#4CC7FB"), 30, f"core {d[-1]} is far from measured")

    def test_reduced_motion_keeps_the_colour_and_drops_the_motion(self):
        """Removing the gradient as well would take the brand out of the chrome for a reader
        who asked only not to be moved at."""
        r, p = run(dict(MIN, glow=True), palette=PAL)
        t = p.read_text()
        i = t.find("@media(prefers-reduced-motion:reduce){\n  .glowbar::before")
        self.assertGreater(i, 0, "no reduced-motion override for the glow")
        block = t[i:i + 480]
        self.assertIn("animation:none", block)
        self.assertIn("opacity:.8", block)      # the core sits at full, still coloured
        self.assertNotIn("display:none", block)


class TouchBehaviour(unittest.TestCase):
    def test_double_tap_zoom_is_disabled_on_the_chrome(self):
        """A reader taps the next arrow quickly twice and mobile Safari reads that as
        double-tap-to-zoom, so the deck lurches to 2x on the one gesture it is navigated by.
        touch-action:manipulation on the footer is the fix, and it must cover the whole
        footer rather than only the buttons, because the gaps between them are just as
        tappable and just as fast."""
        r, p = run(MIN)
        t = p.read_text()
        self.assertIn("touch-action:manipulation", t)
        i = t.index("touch-action:manipulation")
        rule = t[t.rindex("\n", 0, i) + 1:i]
        for sel in ("footer", ".nav button"):
            self.assertIn(sel, rule, f"{sel} is not covered: {rule}")

    def test_the_scrub_keeps_touch_action_none(self):
        """The scrub is DRAGGED, so it needs none rather than manipulation: manipulation
        still allows panning, which would let a drag scroll the page instead of seeking."""
        r, p = run(MIN)
        self.assertIn("touch-action:none", p.read_text())


class Grounds(unittest.TestCase):
    """A mark must always be shown on a background it was drawn for. A light-ground mark on a
    dark slide arrives as a bright white panel floating mid-deck."""

    def test_a_slide_can_carry_its_own_ground(self):
        r, p = run({"slides": [{"kind": "image", "image": "m.png", "ground": "cream"}]})
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        self.assertIn('class="s ground-cream"', t)
        self.assertIn("section.s.ground-cream{background:var(--cream)", t)

    def test_ink_is_the_default_and_adds_no_class(self):
        r, p = run(MIN)
        self.assertIn('<section class="s"', p.read_text())

    def test_AN_UNSTYLED_GROUND_IS_REFUSED(self):
        """The failure this prevents is silent: an unknown ground emits a class the shell has
        no rule for, so the slide stays dark and looks like the author forgot to set it."""
        r, _ = run({"slides": [{"kind": "statement", "heading": "H", "ground": "sepia"}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("sepia", r.stdout + r.stderr)
        self.assertIn("dead class", r.stdout + r.stderr)

    def test_the_cream_ground_restyles_everything_that_would_vanish(self):
        """Flipping only the background leaves cream text on cream. Each of these is a thing
        that disappears or goes illegible if the ground flips without it."""
        r, p = run({"slides": [{"kind": "table", "columns": ["a", "b"],
                                "rows": [["x", "1"]], "ground": "cream"}]})
        t = p.read_text()
        for sel in ("section.s.ground-cream .lede", "section.s.ground-cream figcaption",
                    "section.s.ground-cream th", "section.s.ground-cream .chat .b.them",
                    "section.s.ground-cream figure img"):
            self.assertIn(sel, t, f"{sel} is not restyled for the cream ground")
    def test_the_fixed_chrome_follows_the_ground(self):
        """The footer and counter live OUTSIDE the section and cannot inherit from it, so a
        cream slide otherwise gets a dark bar across its bottom that reads as a separate layer.
        go() sets the class on <body>, which is the only element above both."""
        r, p = run({"slides": [{"kind": "image", "image": "m.png", "ground": "cream"}]})
        t = p.read_text()
        self.assertIn("classList.toggle('on-cream'", t)
        for sel in ("body.on-cream footer", "body.on-cream #no",
                    "body.on-cream .nav button", "body.on-cream #scrub .track"):
            self.assertIn(sel, t, f"{sel} does not follow the ground")


if __name__ == "__main__":
    unittest.main(verbosity=1)
