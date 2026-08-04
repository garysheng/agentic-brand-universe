#!/usr/bin/env python3
"""render_cover.py publishes the PLATFORM-FACING cover, with provenance, itself.

THE MANUAL STEP THESE TESTS RETIRE. `render_cover.py --out .../cover-raw.png` wrote
`cover-raw.png` + its recipe and stopped; the staging layer wants `cover.png`, so every
book run ended with a hand `cp`, and `book_doctor` then FAILED with

    [FAIL] provenance cover.png    no recipe.json beside the asset

until the sidecar was hand-copied too. Named on An Amazing Sex Life (nation-of-fire,
2026-08-04). The last test here is the one that matters: a book whose cover went
through render_cover's publish step and NOTHING ELSE is healthy, with no `cp` anywhere.

Stdlib + Pillow, no network, no API keys: the publish step is a byte copy and a JSON
write, so it is fully testable without generating a cover.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from importlib import util
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
DOCTOR = SCRIPTS.parent.parent / "book-doctor" / "scripts" / "book_doctor.py"


def _load(name):
    spec = util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    mod = util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


rc = _load("render_cover")


def _raw_cover(d: Path, size=(1152, 1536)) -> Path:
    """A conformed `cover-raw.png` beside the recipe the chain leaves there."""
    raw = d / "cover-raw.png"
    raw.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (180, 140, 90)).save(raw)
    raw.with_name(raw.name + ".recipe.json").write_text(json.dumps({
        "asset": str(raw), "model": "gpt-image-2", "prompt": "a cover",
        "universe": "nation-of-fire", "story": "an-amazing-sex-life", "spec": "v0.32",
        "input_images": [],
    }, indent=2))
    return raw


class TestPlatformPath(unittest.TestCase):
    def test_raw_maps_to_the_platform_name(self):
        self.assertEqual(rc.platform_path(Path("/b/spreads/cover-raw.png")),
                         Path("/b/spreads/cover.png"))

    def test_a_non_raw_out_publishes_nothing(self):
        """--out cover.png must behave exactly as it always has: no surprise file."""
        self.assertIsNone(rc.platform_path(Path("/b/spreads/cover.png")))
        self.assertIsNone(rc.platform_path(Path("/b/spreads/hero-raw-ish.png")))


class TestPublish(unittest.TestCase):
    def test_copy_is_byte_identical_and_carries_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = _raw_cover(Path(tmp))
            dst = rc.publish_platform_copy(raw)
            self.assertEqual(dst.name, "cover.png")
            self.assertEqual(dst.read_bytes(), raw.read_bytes())
            rec = json.loads((dst.with_name(dst.name + ".recipe.json")).read_text())

        # The sidecar must describe THIS file. The hand-copied one on An Amazing Sex
        # Life says `asset: .../cover-raw.png` while sitting beside cover.png, which is
        # a provenance record that names the wrong asset.
        self.assertEqual(rec["asset"], str(dst))
        self.assertEqual(rec["mode"], "derive")
        self.assertIsNone(rec["prompt"])
        self.assertIn("none", rec["model"])
        self.assertEqual(rec["derivedFrom"]["path"], str(raw))
        self.assertTrue(rec["derivedFrom"]["recipe"].endswith("cover-raw.png.recipe.json"))
        # Byte-identical, so the hashes MUST agree; that is what makes the record honest.
        self.assertEqual(rec["sha256_16"], rec["derivedFrom"]["sha256_16"])
        # The chain back to the canon that made the art is unbroken.
        for k in ("universe", "story", "spec"):
            self.assertIn(k, rec, f"{k} was not carried forward from the raw recipe")

    def test_publish_is_idempotent_and_does_not_break_a_book_that_has_both(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw = _raw_cover(Path(tmp))
            first = rc.publish_platform_copy(raw)
            stale = first.read_bytes()
            Image.new("RGB", (1152, 1536), (10, 10, 10)).save(raw)  # a re-rolled cover
            second = rc.publish_platform_copy(raw)
            self.assertEqual(first, second)
            self.assertEqual(second.read_bytes(), raw.read_bytes())
            self.assertNotEqual(second.read_bytes(), stale)


class TestBookDoctorIsHealthyWithNoManualCopy(unittest.TestCase):
    """THE REGRESSION. Build a book whose cover was published by render_cover's own
    step, run the real book_doctor, and require a healthy verdict with no `cp`."""

    def _book(self, tmp: Path, publish: bool) -> Path:
        book = tmp / "a-book"
        (book / "spreads").mkdir(parents=True)
        (book / "render-spec.json").write_text(json.dumps({
            "book": "a-book", "size": "1536x1024",
            "spreads": [{"id": "cover", "scene": "c"},
                        {"id": "spread-01", "scene": "s"},
                        {"id": "spread-02", "scene": "s"},
                        {"id": "closing-plate", "scene": "p"}]}))
        for sid in ("spread-01", "spread-02"):
            p = book / "spreads" / f"{sid}.png"
            Image.new("RGB", (1536, 1024), (200, 180, 140)).save(p)
            p.with_name(p.name + ".recipe.json").write_text(
                json.dumps({"model": "gpt-image-2", "prompt": "x", "input_images": []}))
        plate = book / "spreads" / "closing-plate.png"
        Image.new("RGB", (1152, 1536), (120, 120, 120)).save(plate)
        plate.with_name(plate.name + ".recipe.json").write_text(
            json.dumps({"model": "gpt-image-2", "prompt": "x", "input_images": []}))
        raw = _raw_cover(book / "spreads")
        if publish:
            rc.publish_platform_copy(raw)
        return book

    def _run(self, book: Path):
        return subprocess.run([sys.executable, str(DOCTOR), str(book), "--json"],
                              capture_output=True, text=True)

    def test_healthy_after_render_cover_alone(self):
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book(Path(tmp), publish=True)
            r = self._run(book)
            res = json.loads(r.stdout)
        self.assertTrue(res["healthy"], res["problems"])
        self.assertEqual(r.returncode, 0)

    def test_without_the_publish_step_the_doctor_fails_exactly_as_it_did(self):
        """Proves the test bites: this is the FAIL line the manual `cp` existed to dodge."""
        with tempfile.TemporaryDirectory() as tmp:
            book = self._book(Path(tmp), publish=False)
            res = json.loads(self._run(book).stdout)
        self.assertFalse(res["healthy"])
        self.assertTrue(any("cover" in p["role"] for p in res["problems"]),
                        res["problems"])


if __name__ == "__main__":
    unittest.main()
