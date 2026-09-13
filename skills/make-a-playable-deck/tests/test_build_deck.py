#!/usr/bin/env python3
"""Does the deck builder refuse what it should, and is its output actually self-contained?"""
import json, pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
BUILD = HERE.parent / "scripts" / "build_deck.py"
PAL = {"tokens": {"ink": {"hex": "#1E1B19"}, "cream": {"hex": "#F0ECE5"},
                  "live": {"hex": "#007AFF"}}}


def run(deck, extra=(), palette=None, files=None):
    d = pathlib.Path(tempfile.mkdtemp())
    (d / "deck.json").write_text(json.dumps(deck))
    for name, body in (files or {}).items():
        (d / name).write_text(body)
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
            {"kind": "list", "items": ["one", "two"]},
            {"kind": "handoff", "heading": "H", "paste": "do the thing"}]}
        r, p = run(deck)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        self.assertEqual(t.count('<section class="s"'), 10)
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

    def test_ink_may_be_stated_EXPLICITLY_and_is_still_a_no_op(self):
        """Refusing an explicit `ink` was the first behaviour and it was wrong. Being explicit
        about a slide's ground is good practice, especially on a slide that sits between two
        cream ones, and an author who writes the default out loud should not be refused."""
        r, p = run({"slides": [{"kind": "statement", "heading": "H", "ground": "ink"}]})
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        t = p.read_text()
        self.assertIn('<section class="s"', t)
        self.assertNotIn("ground-ink", t)

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



def kinds():
    """The builder's own kind table, read rather than restated."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("bd", BUILD)
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


class KindCoverage(unittest.TestCase):
    def test_EVERY_DECLARED_KIND_IS_EXERCISED_BY_test_every_kind_renders(self):
        """A kind added to the table and to no test renders once, by hand, and never again.

        This is the gate rather than a convention, because the failure is silent: the suite
        stays green, and the first person to find out is the reader looking at a slide that
        rendered wrong.
        """
        declared = set(kinds().KINDS)
        src = pathlib.Path(__file__).read_text()
        body = src.split("def test_every_kind_renders")[1].split("def test_deterministic")[0]
        used = {k for k in declared if f'"kind": "{k}"' in body}
        self.assertEqual(declared, used,
                         f"kinds with no sample slide: {sorted(declared - used)}")


class Handoff(unittest.TestCase):
    """The copy-pasteable block: a prompt the reader is meant to take away with them."""

    D = {"title": "T", "slides": [{"kind": "handoff", "id": "go", "heading": "Run it",
                                   "paste": "line one\nline two", "label": "Copy the prompt",
                                   "footnote": "and *send* it back"}]}

    def test_paste_is_required(self):
        r, _ = run({"slides": [{"kind": "handoff", "heading": "H"}]})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("paste", r.stdout + r.stderr)

    def test_the_block_and_its_button_are_wired_to_each_other(self):
        r, p = run(self.D)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        self.assertIn('<pre id="paste-1">', t)
        self.assertIn('data-for="paste-1"', t)
        self.assertIn("Copy the prompt", t)

    def test_THE_PASTE_IS_ESCAPED(self):
        """A prompt is the one slide kind most likely to contain angle brackets and quotes,
        and it is rendered inside an element rather than as an attribute."""
        r, p = run({"slides": [{"kind": "handoff",
                                "paste": '<script>alert("x")</script> & <b>'}]})
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        self.assertNotIn("<script>alert", t)
        self.assertIn("&lt;script&gt;", t)

    def test_a_horizontal_drag_inside_the_block_does_not_change_slide(self):
        """Selecting text with a thumb is exactly the gesture that means "next slide"."""
        js = (BUILD.parent / "shell" / "deck.js").read_text()
        guard = js.split("stage.addEventListener('touchstart'")[1].split("}, { passive")[0]
        self.assertIn(".closest('.paste')", guard)
        self.assertIn("tracking = false", guard)

    def test_the_paste_block_never_needs_a_horizontal_scroll(self):
        css = (BUILD.parent / "shell" / "deck.css").read_text()
        block = css.split(".paste pre{")[1].split("}")[0]
        self.assertIn("white-space:pre-wrap", block)
        self.assertIn("word-break:break-word", block)
        self.assertIn("touch-action:pan-y", block)

    def test_copy_has_a_fallback_for_a_page_with_no_clipboard_api(self):
        """navigator.clipboard is absent on any page not served over https, which is exactly
        where a local build gets checked. A button that silently does nothing is worse than
        no button."""
        js = (BUILD.parent / "shell" / "deck.js").read_text()
        self.assertIn("navigator.clipboard", js)
        self.assertIn("selectNodeContents", js)


REV = {
    "title": "Brand", "summary": "S",
    "review": {"baseUrl": "https://example.com/", "repo": "org/uni",
               "clone": "git clone git@github.com:org/uni.git",
               "author": "A", "reviewer": "R",
               "protocol": ["name the slide"],
               "canon": [{"path": "canon/entities/m.json", "what": "the mark"}]},
    "slides": [
        {"kind": "image", "id": "one", "image": "a.webp", "caption": "cap", "ground": "cream",
         "source": {"path": "reference/m/hero.png", "depicts": "the blessed cut",
                    "governs": ["canon/entities/m.json"], "status": "blessed"}},
        {"kind": "statement", "heading": "no images here"},
        {"kind": "pair", "images": [
            {"image": "b.webp", "source": {"path": "reference/m/r/x.png", "depicts": "rejected",
                                           "status": "rejected"}},
            {"image": "c.webp", "source": {"path": "reference/m/y.png", "depicts": "kept"}}]}]}


class Review(unittest.TestCase):
    """llms.txt: the deck as something an agent can read, with every asset traceable."""

    def out(self, deck=None, **kw):
        r, p = run(deck or REV, **kw)
        return r, p.parent / "llms.txt"

    def test_no_review_block_means_no_file_and_the_build_SAYS_so(self):
        r, p = run(MIN)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse((p.parent / "llms.txt").exists())
        self.assertIn("no review file", r.stdout)

    def test_every_image_is_listed_with_BOTH_a_url_and_a_repo_path(self):
        """The two halves are for two different readers: an agent holding only the link
        fetches the url, and an agent holding the repo opens the plate and its recipe."""
        r, f = self.out()
        self.assertEqual(r.returncode, 0, r.stderr)
        t = f.read_text()
        for name in ("a.webp", "b.webp", "c.webp"):
            self.assertIn(f"https://example.com/{name}", t)
        for path in ("reference/m/hero.png", "reference/m/r/x.png", "reference/m/y.png"):
            self.assertIn(path, t)

    def test_the_trailing_slash_on_baseurl_does_not_double(self):
        r, f = self.out()
        self.assertNotIn("//a.webp", f.read_text())

    def test_it_carries_what_each_image_depicts_and_what_governs_it(self):
        t = self.out()[1].read_text()
        self.assertIn("depicts: the blessed cut", t)
        self.assertIn("governs: canon/entities/m.json", t)
        self.assertIn("[blessed]", t)
        self.assertIn("[rejected]", t)

    def test_a_text_only_slide_says_it_has_no_images(self):
        """Silence would read to an agent as an image it failed to parse."""
        self.assertIn("images: none", self.out()[1].read_text())

    def test_the_ground_is_recorded_because_a_mark_is_judged_against_it(self):
        t = self.out()[1].read_text()
        self.assertIn("ground: cream", t)
        self.assertIn("ground: ink", t)          # the default, stated

    def test_every_slide_gets_a_deep_link(self):
        t = self.out()[1].read_text()
        self.assertIn("https://example.com/#one", t)

    def test_AN_UNTRACEABLE_IMAGE_REFUSES_THE_BUILD(self):
        """A review file with holes is worse than none: the one image with no source is the
        one the reviewer's agent quietly guesses about, and a guess reads like a fact."""
        d = json.loads(json.dumps(REV))
        del d["slides"][0]["source"]
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        out = r.stdout + r.stderr
        self.assertIn("a.webp", out)
        self.assertIn("Untraceable", out)

    def test_a_source_missing_depicts_is_just_as_untraceable_as_a_missing_path(self):
        d = json.loads(json.dumps(REV))
        d["slides"][0]["source"] = {"path": "reference/m/hero.png"}
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Untraceable", r.stdout + r.stderr)

    def test_review_needs_a_baseurl_because_the_urls_are_absolute(self):
        d = json.loads(json.dumps(REV)); del d["review"]["baseUrl"]
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("baseUrl", r.stdout + r.stderr)

    def test_an_unknown_review_key_is_refused_by_name(self):
        d = json.loads(json.dumps(REV)); d["review"]["reveiwer"] = "typo"
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reveiwer", r.stdout + r.stderr)

    def test_an_unknown_source_key_is_refused_by_name(self):
        d = json.loads(json.dumps(REV)); d["slides"][0]["source"]["depicst"] = "typo"
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("depicst", r.stdout + r.stderr)

    def test_an_unknown_key_inside_an_image_object_is_refused_by_name(self):
        """Nothing validated the entries of `images` before, so a typo there was the one
        silent hole left in a validator built to refuse exactly this."""
        d = json.loads(json.dumps(REV))
        d["slides"][2]["images"][0]["captoin"] = "typo"
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("captoin", r.stdout + r.stderr)

    def test_an_invented_status_is_refused(self):
        d = json.loads(json.dumps(REV)); d["slides"][0]["source"]["status"] = "quite-good"
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("quite-good", r.stdout + r.stderr)

    def test_the_boomerang_is_copied_beside_the_deck_and_linked(self):
        d = json.loads(json.dumps(REV)); d["review"]["boomerang"] = "BOOMERANG.md"
        r, f = self.out(d, files={"BOOMERANG.md": "# prompt\n"})
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((f.parent / "BOOMERANG.md").read_text(), "# prompt\n")
        self.assertIn("https://example.com/BOOMERANG.md", f.read_text())

    def test_A_MISSING_BOOMERANG_REFUSES_RATHER_THAN_SHIPPING_A_DEAD_LINK(self):
        """The deck links it from the one slide whose whole job is to be pasted."""
        d = json.loads(json.dumps(REV)); d["review"]["boomerang"] = "BOOMERANG.md"
        r, _ = run(d)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("BOOMERANG.md", r.stdout + r.stderr)

    def test_it_points_the_reader_at_the_recipe_files(self):
        """The provenance beside each plate is the answer to "why does it look like this",
        and an agent that does not know it exists will never open it."""
        self.assertIn("recipe.json", self.out()[1].read_text())

    def test_deterministic(self):
        a = self.out()[1].read_text()
        b = self.out()[1].read_text()
        self.assertEqual(a, b)


class ReviewPaths(unittest.TestCase):
    """--repo-root: every path the review file promises actually resolves."""

    def build(self, deck, make):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "deck.json").write_text(json.dumps(deck))
        repo = d / "repo"
        for rel in make:
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text("x")
        repo.mkdir(parents=True, exist_ok=True)
        r = subprocess.run([sys.executable, str(BUILD), str(d / "deck.json"),
                            "--out", str(d / "out"), "--repo-root", str(repo)],
                           capture_output=True, text=True)
        return r

    REAL = ["reference/m/hero.png", "reference/m/r/x.png", "reference/m/y.png",
            "canon/entities/m.json"]

    def test_all_paths_present_builds_and_says_how_many_it_checked(self):
        r = self.build(REV, self.REAL)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("path(s) verified", r.stdout)

    def test_A_DEAD_SOURCE_PATH_REFUSES_AND_NAMES_IT(self):
        """A path that does not resolve is worse than no path: the agent goes looking, finds
        nothing, and has to decide whether the deck is lying."""
        r = self.build(REV, [p for p in self.REAL if p != "reference/m/y.png"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("reference/m/y.png", r.stdout + r.stderr)

    def test_a_dead_governs_path_refuses_too(self):
        r = self.build(REV, [p for p in self.REAL if p != "canon/entities/m.json"])
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("canon/entities/m.json", r.stdout + r.stderr)

    def test_the_gate_is_OPT_IN_so_a_deck_with_no_repo_on_hand_still_builds(self):
        r, f = run(REV)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("verified", r.stdout)


class Recipes(unittest.TestCase):
    """Whether a plate carries provenance is CHECKED per image, never promised in general."""

    def build(self, make, with_root=True):
        d = pathlib.Path(tempfile.mkdtemp())
        (d / "deck.json").write_text(json.dumps(REV))
        repo = d / "repo"; repo.mkdir(parents=True, exist_ok=True)
        for rel in make:
            (repo / rel).parent.mkdir(parents=True, exist_ok=True)
            (repo / rel).write_text("x")
        cmd = [sys.executable, str(BUILD), str(d / "deck.json"), "--out", str(d / "out")]
        if with_root:
            cmd += ["--repo-root", str(repo)]
        r = subprocess.run(cmd, capture_output=True, text=True)
        return r, d / "out" / "llms.txt"

    PLATES = ["reference/m/hero.png", "reference/m/r/x.png", "reference/m/y.png",
              "canon/entities/m.json"]

    def test_a_plate_WITH_a_recipe_gets_its_path(self):
        r, f = self.build(self.PLATES + ["reference/m/hero.png.recipe.json"])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("recipe: reference/m/hero.png.recipe.json", f.read_text())

    def test_A_PLATE_WITHOUT_ONE_SAYS_SO_RATHER_THAN_SENDING_THE_AGENT_LOOKING(self):
        """Found for real: 2 of 13 plates in the first deck through this had no recipe, while
        the file promised in general that every plate did. An agent that goes looking for a
        file that is not there spends the reviewer's attention on the tooling."""
        r, f = self.build(self.PLATES)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = f.read_text()
        self.assertIn("recipe: NONE on disk", t)
        self.assertIn("Do not go looking", t)

    def test_with_no_repo_it_does_not_claim_to_know_either_way(self):
        r, f = self.build([], with_root=False)
        self.assertEqual(r.returncode, 0, r.stderr)
        t = f.read_text()
        self.assertIn("could not check", t)
        self.assertNotIn("recipe:", t)


class DeepLinks(unittest.TestCase):
    """A hash is either a position or an id, and the id is the one anything durable points at."""

    def js(self):
        return (BUILD.parent / "shell" / "deck.js").read_text()

    def test_an_id_hash_resolves_by_matching_a_section_id(self):
        self.assertIn("S[k].id === h", self.js())

    def test_A_DIGIT_INSIDE_AN_ID_IS_NOT_TREATED_AS_A_POSITION(self):
        """The old resolver stripped non-digits, so `#why-2` opened slide TWO: a different
        slide, with nothing reporting a problem. Only a digits-ONLY hash is a position."""
        js = self.js()
        self.assertNotIn("replace(/[^0-9]/g, '')", js)
        self.assertIn("/^[0-9]+$/.test(h)", js)

    def test_the_builder_writes_the_id_the_resolver_looks_for(self):
        r, p = run({"title": "T", "slides": [
            {"kind": "statement", "id": "why-2", "heading": "H"},
            {"kind": "statement", "id": "handoff", "heading": "H"}]})
        self.assertEqual(r.returncode, 0, r.stderr)
        t = p.read_text()
        self.assertIn('id="why-2"', t)
        self.assertIn('id="handoff"', t)

    def test_the_review_file_promises_id_links_so_they_have_to_WORK(self):
        """The two halves are written in different files and only break together."""
        r, p = run(REV)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("#one", (p.parent / "llms.txt").read_text())
        self.assertIn('id="one"', p.read_text())


class Links(unittest.TestCase):
    """`[text](https://…)` renders, and nothing else that looks like a link does."""

    def one(self, text):
        r, p = run({"slides": [{"kind": "statement", "heading": "H", "body": text}]})
        self.assertEqual(r.returncode, 0, r.stderr)
        return p.read_text()

    def test_an_https_link_renders(self):
        t = self.one("see [the standard](https://appliedai.wiki/x) for this")
        self.assertIn('<a href="https://appliedai.wiki/x" target="_blank" '
                      'rel="noopener">the standard</a>', t)

    def test_A_JAVASCRIPT_URL_IS_NOT_A_LINK(self):
        """https-only is the security boundary, not a style preference: this would otherwise
        become a live script handler on a page that escapes everything else it is given."""
        t = self.one("[x](javascript:alert(1))")
        self.assertNotIn("<a href", t)
        self.assertNotIn("javascript:alert(1)\"", t)

    def test_http_and_relative_urls_are_left_as_text(self):
        for bad in ("[x](http://example.com)", "[x](/local/path)", "[x](data:text/html,y)"):
            self.assertNotIn("<a href", self.one(bad), bad)

    def test_the_link_text_is_still_escaped(self):
        t = self.one('[<b>hi</b>](https://e.com/a)')
        self.assertIn("&lt;b&gt;hi&lt;/b&gt;", t)
        self.assertNotIn("<b>hi</b>", t)

    def test_a_quote_in_the_url_cannot_break_out_of_the_attribute(self):
        t = self.one('[x](https://e.com/a"onload="alert(1))')
        self.assertNotIn('"onload="', t)

    def test_plain_brackets_are_left_alone(self):
        t = self.one("array[0] and (a note)")
        self.assertNotIn("<a href", t)
        self.assertIn("array[0]", t)


class PasteLayout(unittest.TestCase):
    def test_THE_BUTTON_IS_NOT_INSIDE_THE_SCROLLING_BLOCK(self):
        """Absolutely positioned over the <pre> it covered whichever line was scrolled into
        view, and looked deliberate while doing it. Bottom padding does not help: the padding
        scrolls with the content, so the gap is almost never where the button is."""
        r, p = run({"slides": [{"kind": "handoff", "paste": "x"}]})
        t = p.read_text()
        pre_end = t.index("</pre>")
        self.assertLess(pre_end, t.index('class="copy"'),
                        "the button is rendered inside the <pre>")
        self.assertIn('<div class="pastebar">', t)

    def test_the_bar_does_not_scroll_away_with_the_content(self):
        css = (BUILD.parent / "shell" / "deck.css").read_text()
        bar = css.split(".pastebar{")[1].split("}")[0]
        self.assertIn("flex:none", bar)
        self.assertNotIn("position:absolute", bar)

    def test_the_bar_follows_a_cream_ground(self):
        css = (BUILD.parent / "shell" / "deck.css").read_text()
        self.assertIn("section.s.ground-cream .pastebar{", css)


if __name__ == "__main__":
    unittest.main(verbosity=1)
