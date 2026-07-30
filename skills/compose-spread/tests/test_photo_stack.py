"""
compose-spread — realPerson photoStack expansion + capping.

Regression tests for the bug found 2026-07-29 building `she-had-everything-but-peace`:
`photoStack` may name a DIRECTORY (the documented convention), and the old code applied
its `[:2]` cap to the RAW list. A one-entry directory stack therefore sailed past the cap
and passed EVERY photograph in the folder. Nation of Fire's `victory` shipped six refs
that way -- two of them multi-person family-band photos -- on every spread that cast her,
and nothing warned.

The fix: expand FIRST, cap AFTER, and default to UNCAPPED (more bare-face angles make a
stronger identity lock, which is why a real-person entity carries photographs at all).
An entity that needs a ceiling sets `realPerson.photoLimit`.

Run:  python3 -m unittest discover -s tests -v   (from the compose-spread skill dir)
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_spec = importlib.util.spec_from_file_location("ap", SCRIPTS / "assemble_prompt.py")
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)


def png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (200, 180, 140)).save(path)


class PhotoStackTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        for i in range(1, 7):
            png(self.root / "reference" / "p" / "photos" / f"{i:02d}.png")
        png(self.root / "reference" / "p" / "master.png")

    def tearDown(self):
        self.tmp.cleanup()

    def ent(self, stack, limit="unset"):
        rp = {"photoStack": stack}
        if limit != "unset":
            rp["photoLimit"] = limit
        return {
            "id": "p", "kind": "character",
            "structured": {"sheets": {"master": "reference/p/master.png"},
                           "requiredForRender": ["master"], "invariants": ["x"]},
            "realPerson": rp,
        }

    def test_directory_stack_expands_to_every_photo_uncapped(self):
        """THE BUG. A directory stack used to be capped at 2 by slicing the raw list
        (which had ONE element), so the cap did nothing. It must now expand fully."""
        refs, _ = ap.resolve_character(self.ent(["reference/p/photos"]), None, self.root)
        photos = [r for r in refs if "photos" in r]
        self.assertEqual(len(photos), 6, "a directory stack must expand to all 6 photos")

    def test_more_than_two_named_files_all_reach_the_model(self):
        """Gary, 2026-07-29: allow more than two real photos."""
        stack = [f"reference/p/photos/{i:02d}.png" for i in range(1, 6)]
        refs, _ = ap.resolve_character(self.ent(stack), None, self.root)
        self.assertEqual(len([r for r in refs if "photos" in r]), 5)

    def test_photo_limit_caps_AFTER_expansion(self):
        """The cap is meaningful again: it applies to expanded FILES, not stack entries."""
        refs, _ = ap.resolve_character(self.ent(["reference/p/photos"], limit=2), None, self.root)
        self.assertEqual(len([r for r in refs if "photos" in r]), 2)

    def test_photo_limit_zero_passes_none(self):
        refs, _ = ap.resolve_character(self.ent(["reference/p/photos"], limit=0), None, self.root)
        self.assertEqual([r for r in refs if "photos" in r], [])

    def test_string_stack_is_one_path_not_characters(self):
        """A string photoStack is a documented authoring mistake; treat it as one path
        instead of iterating it character by character."""
        refs = ap._photo_refs(self.ent("reference/p/photos/01.png"), self.root)
        self.assertEqual(len(refs), 1)
        self.assertTrue(refs[0].endswith("01.png"))

    def test_required_sheet_still_comes_first(self):
        refs, _ = ap.resolve_character(self.ent(["reference/p/photos"]), None, self.root)
        self.assertTrue(refs[0].endswith("master.png"))

    def test_no_photo_stack_is_fine(self):
        e = self.ent([]) ; e["realPerson"] = {}
        refs, _ = ap.resolve_character(e, None, self.root)
        self.assertEqual(refs, ["reference/p/master.png"])

    def test_no_duplicate_refs(self):
        stack = ["reference/p/photos", "reference/p/photos/01.png"]
        refs = ap._photo_refs(self.ent(stack), self.root)
        self.assertEqual(len(refs), len(set(refs)))
        self.assertEqual(len(refs), 6)

    def test_works_without_uroot_backwards_compatible(self):
        """Older callers pass no uroot; entries stay unexpanded rather than crashing."""
        refs = ap._photo_refs(self.ent(["reference/p/photos/01.png"]), None)
        self.assertEqual(refs, ["reference/p/photos/01.png"])


if __name__ == "__main__":
    unittest.main()
