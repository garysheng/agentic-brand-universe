"""ONE photo-stack rule for the whole framework (SPEC v0.21).

The defect (2026-08-01, christofuturism `gary`): `realPerson.photoStack` may name a
DIRECTORY, which SPEC §12 calls the idiomatic whole-stack form, and the render-time
assembler expanded it correctly while `shoot-references` refused it outright
("is a DIRECTORY, not an image") and never read `realPerson.photoLimit` at all. So the
idiomatic stack could be rendered FROM and not shot FROM, and a declared ceiling was
honored at render time and ignored at shoot time.

The parity test at the bottom is the point: the assembler is deliberately
dependency-free (it imports nothing from the engine), so the rule lives in two places by
design. Two implementations that must agree and nothing checking that they do is exactly
how they drifted, so this checks it.
"""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

from agenticstory.refs import expand_ref, photo_stack

REPO = Path(__file__).resolve().parents[2]


def load_assembler():
    p = REPO / "skills" / "compose-spread" / "scripts" / "assemble_prompt.py"
    spec = importlib.util.spec_from_file_location("_assemble_prompt_for_parity", p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = Path(self.tmp.name) / "uni"
        (self.u / "reference" / "gary" / "photos").mkdir(parents=True)
        self.photos = []
        for n in ("c.png", "a.jpg", "b.webp"):
            p = self.u / "reference" / "gary" / "photos" / n
            p.write_bytes(b"\x89PNG")
            self.photos.append(p)
        (self.u / "reference" / "gary" / "photos" / "notes.txt").write_text("not an image")

    def tearDown(self):
        self.tmp.cleanup()

    def ent(self, stack, limit=None):
        rp = {"photoStack": stack}
        if limit is not None:
            rp["photoLimit"] = limit
        return {"id": "gary", "realPerson": rp}


class ExpandRef(Base):
    def test_a_directory_expands_to_its_images_sorted(self):
        got = expand_ref(self.u, "reference/gary/photos")
        self.assertEqual([Path(p).name for p in got], ["a.jpg", "b.webp", "c.png"])

    def test_non_images_are_not_expanded(self):
        got = expand_ref(self.u, "reference/gary/photos")
        self.assertNotIn("notes.txt", [Path(p).name for p in got])

    def test_a_file_resolves_to_itself(self):
        got = expand_ref(self.u, "reference/gary/photos/a.jpg")
        self.assertEqual(len(got), 1)

    def test_a_missing_path_raises_rather_than_resolving_to_nothing(self):
        with self.assertRaises(FileNotFoundError):
            expand_ref(self.u, "reference/gary/nope")

    def test_an_empty_directory_raises(self):
        (self.u / "reference" / "empty").mkdir()
        with self.assertRaises(FileNotFoundError):
            expand_ref(self.u, "reference/empty")


class PhotoStack(Base):
    def test_directory_form_is_expanded(self):
        got = photo_stack(self.ent(["reference/gary/photos"]), self.u)
        self.assertEqual(len(got), 3)

    def test_limit_applies_AFTER_expansion(self):
        got = photo_stack(self.ent(["reference/gary/photos"], limit=2), self.u)
        self.assertEqual([Path(p).name for p in got], ["a.jpg", "b.webp"])

    def test_no_limit_passes_them_all(self):
        self.assertEqual(len(photo_stack(self.ent(["reference/gary/photos"]), self.u)), 3)

    def test_a_string_stack_is_one_path_not_a_character_sequence(self):
        got = photo_stack(self.ent("reference/gary/photos"), self.u)
        self.assertEqual(len(got), 3)

    def test_mixed_file_and_directory_entries_dedupe(self):
        got = photo_stack(self.ent(["reference/gary/photos/a.jpg",
                                    "reference/gary/photos"]), self.u)
        self.assertEqual(len(got), 3)
        self.assertTrue(got[0].endswith("a.jpg"))

    def test_no_realperson_block_is_no_photos(self):
        self.assertEqual(photo_stack({"id": "x"}, self.u), [])


class ParityWithTheAssembler(Base):
    """The engine rule and compose-spread's copy must return the SAME list."""

    def setUp(self):
        super().setUp()
        self.mod = load_assembler()

    def check(self, ent):
        self.assertEqual(photo_stack(ent, self.u), self.mod._photo_refs(ent, self.u))

    def test_directory_stack(self):
        self.check(self.ent(["reference/gary/photos"]))

    def test_capped_directory_stack(self):
        self.check(self.ent(["reference/gary/photos"], limit=2))

    def test_file_stack(self):
        self.check(self.ent(["reference/gary/photos/a.jpg",
                             "reference/gary/photos/c.png"]))

    def test_empty(self):
        self.check({"id": "x"})


if __name__ == "__main__":
    unittest.main()
