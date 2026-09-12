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


if __name__ == "__main__":
    unittest.main(verbosity=1)
