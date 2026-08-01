"""book-doctor book_doctor.py — tests. Stdlib unittest, no network, no API keys.

Every test builds a SYNTHETIC book in a tempdir: a render-spec, some rendered
files at chosen sizes, and recipe sidecars. Each case then breaks exactly one
thing, so a failure names its own cause.

The load-bearing test is `test_landscape_closing_plate_is_a_problem`: it
reproduces the real defect that earned this tool. A book shipped with its
closing plate rendered at landscape interior aspect, when the reader composes
the closing plate as a single-page BACK COVER at 3:4 and therefore crops it.
Every pre-render gate passed, because at gate time there is no output to
measure.

`test_self_referencing_spread_is_a_problem` covers the other check a delivery
probe structurally cannot do: recipes are build artifacts and never ship, so
"was this spread generated from another spread" is only answerable locally.

Run:  python3 tests/test_book_doctor.py     (from the book-doctor skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "book_doctor.py"

LANDSCAPE = (1536, 1024)   # interior aspect 1.5
PORTRAIT = (1152, 1536)    # endcap aspect 0.75


def img(path: Path, size):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 180, 140)).save(path)


def recipe(asset: Path, inputs=None):
    asset.with_suffix(asset.suffix + ".recipe.json").write_text(
        json.dumps({"model": "test", "prompt": "x", "input_images": inputs or []})
    )


def build(tmp: Path, n_spreads=3, plate_size=PORTRAIT, cover_size=PORTRAIT,
          with_recipes=True, plate=True, plate_inputs=None):
    """A synthetic book that is healthy unless a caller breaks one thing."""
    book = tmp / "a-book"
    spec = {
        "book": "a-book",
        "size": "1536x1024",
        "spreads": [{"id": f"spread-{i:02d}", "scene": "s"} for i in range(1, n_spreads + 1)],
    }
    (book).mkdir(parents=True, exist_ok=True)
    (book / "render-spec.json").write_text(json.dumps(spec))

    cover = book / "cover" / "spread-00-cover.webp"
    img(cover, cover_size)
    if with_recipes:
        recipe(cover)

    for i in range(1, n_spreads + 1):
        p = book / "spreads" / f"spread-{i:02d}.png"
        img(p, LANDSCAPE)
        if with_recipes:
            recipe(p)

    if plate:
        pl = book / "spreads" / f"spread-{n_spreads + 1:02d}.png"
        img(pl, plate_size)
        if with_recipes:
            recipe(pl, plate_inputs)
    return book


def build_composer(tmp: Path, n_spreads=3, plate_size=PORTRAIT, cover_size=PORTRAIT,
                   cast=None):
    """A book in the COMPOSER dialect, which is what `compose-spec` actually emits.

    Two things differ from `build()` above and BOTH of them hid a real bug for the
    whole life of this tool:

      1. The endcaps are DECLARED IN `spreads`, with the ids `cover` and
         `closing-plate`. The old fixture left them out of the spec entirely, so
         the interior loop never saw them and never mis-graded them.
      2. Cast is `cast: [{"id": ...}]`, which is what `compose_spec.py` writes and
         `assemble_prompt.py` reads. The old fixture used `characters`/`extras`,
         a dialect nothing in the chain emits.

    Reproduces the-power-of-obeying-book (69 spreads, shipped 2026-07-31), which a
    correct book graded as three FAILs.
    """
    book = tmp / "composed-book"
    spreads = [{"id": "cover", "scene": "s"}]
    for i in range(1, n_spreads + 1):
        sp = {"id": f"spread-{i:02d}", "scene": "s"}
        if cast and i == 1:
            sp["cast"] = cast
        spreads.append(sp)
    spreads.append({"id": "closing-plate", "scene": "s"})
    book.mkdir(parents=True, exist_ok=True)
    (book / "render-spec.json").write_text(
        json.dumps({"book": "composed-book", "size": "1536x1024", "spreads": spreads}))

    img(book / "spreads" / "cover.png", cover_size)
    recipe(book / "spreads" / "cover.png")
    img(book / "spreads" / "closing-plate.png", plate_size)
    recipe(book / "spreads" / "closing-plate.png")
    for i in range(1, n_spreads + 1):
        p = book / "spreads" / f"spread-{i:02d}.png"
        img(p, LANDSCAPE)
        recipe(p)
    return book


def run(book: Path, *extra):
    r = subprocess.run([sys.executable, str(SCRIPT), str(book), *extra],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class TestBookDoctor(unittest.TestCase):
    def test_healthy_book_passes(self):
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t))
            code, out = run(book)
            self.assertEqual(code, 0, out)
            self.assertIn("healthy", out)

    def test_landscape_closing_plate_is_a_problem(self):
        """THE defect this tool exists for: the closing plate is an endcap, not
        an interior, so a landscape plate gets cropped by the reader."""
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t), plate_size=LANDSCAPE)
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("closing plate", out)
            self.assertIn("0.75", out)

    def test_missing_spread_is_a_problem(self):
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t))
            (book / "spreads" / "spread-02.png").unlink()
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("spread-02", out)

    def test_missing_closing_plate_is_a_problem(self):
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t), plate=False)
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("closing plate", out)

    def test_cropped_cover_is_a_problem(self):
        """A 2:3 cover (gpt-image-2's only portrait size) shears its title."""
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t), cover_size=(1024, 1536))
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("front cover", out)

    def test_missing_provenance_is_a_problem(self):
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t), with_recipes=False)
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("provenance", out)

    def test_self_referencing_spread_is_a_problem(self):
        """A spread built from another spread render lets a defect survive into
        its own fix. Only checkable locally: recipes never ship."""
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t), plate_inputs=["/x/spreads/spread-01.png"])
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("self-reference", out)

    def test_unreadable_book_exits_two(self):
        with tempfile.TemporaryDirectory() as t:
            code, out = run(Path(t) / "nope")
            self.assertEqual(code, 2, out)

    def test_unlocked_cast_entity_is_a_problem(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            book = build(tmp)
            spec = json.loads((book / "render-spec.json").read_text())
            spec["spreads"][0]["characters"] = [{"entity": "someone", "pose": "front"}]
            (book / "render-spec.json").write_text(json.dumps(spec))
            ents = tmp / "u" / "canon" / "entities"
            ents.mkdir(parents=True)
            (ents / "someone.json").write_text(json.dumps({"id": "someone", "status": "unlocked"}))
            code, out = run(book, "--universe", str(tmp / "u"))
            self.assertEqual(code, 1, out)
            self.assertIn("someone", out)

    def test_uncast_entity_not_in_canon_is_a_problem(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            book = build(tmp)
            spec = json.loads((book / "render-spec.json").read_text())
            spec["spreads"][0]["setting"] = {"entity": "ghost-room"}
            (book / "render-spec.json").write_text(json.dumps(spec))
            (tmp / "u" / "canon" / "entities").mkdir(parents=True)
            code, out = run(book, "--universe", str(tmp / "u"))
            self.assertEqual(code, 1, out)
            self.assertIn("ghost-room", out)

    # ── the composer dialect: endcaps DECLARED in `spreads` ──────────────────
    #
    # Earned 2026-07-31 by the-power-of-obeying-book, a 69-spread book that was
    # CORRECT and that this tool failed on all three of its endcap checks. As
    # written the doctor failed every book whose spec declares its endcaps, which
    # is every book compose-spec has ever produced, and a doctor that always fails
    # trains its operator to ignore it.

    def test_declared_endcaps_are_not_graded_as_interiors(self):
        """The bug: an endcap declared in `spreads` was graded TWICE, once
        correctly as an endcap and then again at interior aspect, and the second
        grade can never pass. `aspect 0.75 (want 1.5)` on a portrait cover."""
        with tempfile.TemporaryDirectory() as t:
            book = build_composer(Path(t))
            code, out = run(book)
            self.assertEqual(code, 0, out)
            self.assertIn("healthy", out)

    def test_declared_endcaps_do_not_invent_a_plate_number(self):
        """`max(int(id.rsplit('-')[-1]))` raised ValueError on the id `cover`, and
        the fallback `last = len(declared)` counted the endcaps in, so a 69-spread
        book was told its closing plate was `missing spread-72`."""
        with tempfile.TemporaryDirectory() as t:
            book = build_composer(Path(t), n_spreads=3)
            code, out = run(book)
            self.assertNotIn("spread-05", out)
            self.assertNotIn("spread-06", out)
            self.assertEqual(code, 0, out)

    def test_composer_dialect_still_catches_a_landscape_closing_plate(self):
        """The fix must not buy a green light by loosening the real check."""
        with tempfile.TemporaryDirectory() as t:
            book = build_composer(Path(t), plate_size=LANDSCAPE)
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("closing plate", out)

    def test_composer_dialect_still_catches_a_landscape_cover(self):
        with tempfile.TemporaryDirectory() as t:
            book = build_composer(Path(t), cover_size=LANDSCAPE)
            code, out = run(book)
            self.assertEqual(code, 1, out)
            self.assertIn("front cover", out)

    def test_cast_dialect_is_actually_checked(self):
        """Check 6 read `characters`/`extras`, a dialect nothing emits, so the
        cast-registered-and-locked check was a silent no-op on every real book."""
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            book = build_composer(tmp, cast=[{"id": "someone"}])
            ents = tmp / "u" / "canon" / "entities"
            ents.mkdir(parents=True)
            (ents / "someone.json").write_text(
                json.dumps({"id": "someone", "status": "unlocked"}))
            code, out = run(book, "--universe", str(tmp / "u"))
            self.assertEqual(code, 1, out)
            self.assertIn("someone", out)

    def test_cast_dialect_catches_an_unregistered_entity(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            book = build_composer(tmp, cast=["ghost"])
            (tmp / "u" / "canon" / "entities").mkdir(parents=True)
            code, out = run(book, "--universe", str(tmp / "u"))
            self.assertEqual(code, 1, out)
            self.assertIn("ghost", out)

    def test_cast_dialect_passes_on_a_locked_entity(self):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            book = build_composer(tmp, cast=[{"id": "someone"}])
            ents = tmp / "u" / "canon" / "entities"
            ents.mkdir(parents=True)
            (ents / "someone.json").write_text(
                json.dumps({"id": "someone", "status": "locked"}))
            code, out = run(book, "--universe", str(tmp / "u"))
            self.assertEqual(code, 0, out)

    def test_json_output_is_machine_readable(self):
        with tempfile.TemporaryDirectory() as t:
            book = build(Path(t))
            code, out = run(book, "--json")
            self.assertEqual(code, 0, out)
            self.assertTrue(json.loads(out)["healthy"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
