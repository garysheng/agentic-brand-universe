#!/usr/bin/env python3
"""ABU's deck skill wraps Freedom's builder: does it find it, forward everything, and add the
universe's palette exactly when it should?

The builder's own suite moved to Freedom with the builder on 2026-09-23. These tests stand a FAKE
Freedom builder in its place that records the argv it was handed, so they need no Freedom
install and test only what this wrapper decides.
"""
import json, os, pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
WRAP = HERE.parent / "scripts" / "build_deck.py"
FAKE = 'import json, sys; open(sys.argv[0] + ".argv", "w").write(json.dumps(sys.argv[1:]))\n'
DECK = {"title": "T", "slides": [{"kind": "statement", "heading": "H"}]}


class Wrapper(unittest.TestCase):
    def setUp(self):
        self.d = pathlib.Path(tempfile.mkdtemp())
        self.fake = self.d / "freedom" / "build_deck.py"
        self.fake.parent.mkdir()
        self.fake.write_text(FAKE)

    def universe(self, root):
        (root / "canon" / "craft").mkdir(parents=True)
        (root / "canon" / "craft" / "palette.json").write_text("{}")
        return root / "canon" / "craft" / "palette.json"

    def deck(self, where, **extra):
        where.mkdir(parents=True, exist_ok=True)
        f = where / "deck.json"
        f.write_text(json.dumps({**DECK, **extra}))
        return f

    def run_(self, *args, env=None):
        e = {**os.environ, "FREEDOM_DECK_BUILDER": str(self.fake), **(env or {})}
        r = subprocess.run([sys.executable, str(WRAP), *map(str, args)],
                           capture_output=True, text=True, env=e)
        got = self.fake.with_name(self.fake.name + ".argv")
        return r, (json.loads(got.read_text()) if got.exists() else None)

    def test_forwards_every_argument_to_freedoms_builder(self):
        f = self.deck(self.d / "loose")
        r, argv = self.run_(f, "--out", self.d / "o", "--assets", self.d / "a")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(argv, [str(f), "--out", str(self.d / "o"), "--assets", str(self.d / "a")])

    def test_a_deck_inside_a_universe_gets_its_palette_with_no_flag(self):
        pal = self.universe(self.d / "uni")
        f = self.deck(self.d / "uni" / "works" / "a-deck")
        _, argv = self.run_(f, "--out", self.d / "o")
        self.assertEqual(argv[-2], "--palette")
        self.assertEqual(pathlib.Path(argv[-1]).resolve(), pal.resolve())

    def test_the_decks_own_universe_declaration_wins_over_where_it_sits(self):
        self.universe(self.d / "sits-in")
        declared = self.universe(self.d / "declared")
        f = self.deck(self.d / "sits-in" / "works" / "x", universe="../../../declared")
        _, argv = self.run_(f, "--out", self.d / "o")
        self.assertEqual(pathlib.Path(argv[-1]).resolve(), declared.resolve())

    def test_a_declared_universe_that_does_not_resolve_is_refused(self):
        f = self.deck(self.d / "loose", universe="nowhere")
        r, argv = self.run_(f, "--out", self.d / "o")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("declares universe 'nowhere'", r.stderr)
        self.assertIsNone(argv, "the builder must not run on a brand that does not resolve")

    def test_repo_root_supplies_the_palette_for_a_deck_outside_it(self):
        pal = self.universe(self.d / "uni")
        f = self.deck(self.d / "loose")
        _, argv = self.run_(f, "--out", self.d / "o", "--repo-root", self.d / "uni")
        self.assertEqual(argv[-2:], ["--palette", str(pal)])

    def test_an_explicit_palette_is_left_alone(self):
        self.universe(self.d / "uni")
        f = self.deck(self.d / "uni" / "works" / "a")
        _, argv = self.run_(f, "--out", self.d / "o", "--palette", "mine.json")
        self.assertEqual(argv.count("--palette"), 1)
        self.assertEqual(argv[argv.index("--palette") + 1], "mine.json")

    def test_no_universe_anywhere_adds_nothing(self):
        f = self.deck(self.d / "loose")
        _, argv = self.run_(f, "--out", self.d / "o")
        self.assertNotIn("--palette", argv)

    def test_no_freedom_is_refused_by_name(self):
        f = self.deck(self.d / "loose")
        r, _ = self.run_(f, "--out", self.d / "o",
                         env={"FREEDOM_DECK_BUILDER": str(self.d / "absent.py"),
                              "FREEDOM_PLUGIN": str(self.d / "none"), "HOME": str(self.d)})
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("Freedom's deck builder was not found", r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=1)
