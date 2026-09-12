"""explore forwards a canon entity to the adapter on every roll.

Until 2026-09-06 an explore of a canon character (six gym outfits for the same woman) had no way to
carry her locked identity plates, so every caller hand-picked plates and passed them as --ref, each
one differently. The fix is a passthrough: --entity, --entity-required-only and --no-wardrobe go to
generate.py, which already resolves sheets, alt-looks and invariants from canon. These tests run the
script in --dry-run, which spends nothing and prints the exact commands it would run.
"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "explore.py"


def dry_run(extra):
    with tempfile.TemporaryDirectory() as td:
        d = pathlib.Path(td)
        (d / "subject.txt").write_text("SUBJECT.\n")
        (d / "variants.txt").write_text("a-one: first\nb-two: second\n")
        cmd = [sys.executable, str(SCRIPT), "--subject-file", str(d / "subject.txt"),
               "--variants", str(d / "variants.txt"), "--out-dir", str(d / "out"), "--dry-run"] + extra
        return subprocess.run(cmd, capture_output=True, text=True)


class ExploreEntityPassthrough(unittest.TestCase):
    def test_entity_reaches_every_roll(self):
        r = dry_run(["--entity", "/u:the-relieved-woman", "--entity", "/u:the-terrace"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        lines = [l for l in r.stdout.splitlines() if l.strip().startswith(("a-one:", "b-two:"))]
        self.assertEqual(len(lines), 2)
        for l in lines:
            self.assertIn("--entity /u:the-relieved-woman", l)
            self.assertIn("--entity /u:the-terrace", l)

    def test_look_suffix_survives(self):
        r = dry_run(["--entity", "/u:the-relieved-woman@gym"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--entity /u:the-relieved-woman@gym", r.stdout)

    def test_adapter_flags_forward(self):
        r = dry_run(["--entity", "/u:x", "--entity-required-only", "--no-wardrobe"])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("--entity-required-only", r.stdout)
        self.assertIn("--no-wardrobe", r.stdout)

    def test_without_entity_nothing_is_added(self):
        r = dry_run([])
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertNotIn("--entity", r.stdout)
        self.assertNotIn("--no-wardrobe", r.stdout)



class ContactSheetIsEmittedForEveryFanOut(unittest.TestCase):
    """A fan-out must hand back a labelled contact sheet, not a pile of files.

    Earned 2026-09-12. Gary, after a dozen rounds of being shown variants one at a time:
    "Moving forward show me contact sheets when there are multiple images to review so I have
    images ids". A fan-out exists to be chosen between, and choosing means seeing the variants
    together with their ids attached. Sent individually, the operator holds the differences in
    their head and has no way to name a pick except by describing the picture.

    It is emitted by the script rather than by the caller because a step that depends on an agent
    remembering happens most of the time, and the comparison IS the point of the verb.
    """

    SRC = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "explore.py"

    def test_it_calls_the_framework_contact_sheet_verb(self):
        src = self.SRC.read_text()
        self.assertIn("contact_sheet.py", src,
                      "explore.py must build its sheet with render-readback's contact_sheet verb "
                      "rather than hand-rolling a montage")

    def test_the_cells_are_labelled_so_a_pick_is_one_word(self):
        src = self.SRC.read_text()
        self.assertIn('"--label"', src,
                      "the sheet must be labelled; unlabelled cells give the operator no id to "
                      "name a pick with, which is the whole reason this exists")

    def test_a_single_roll_gets_no_sheet(self):
        """One image is not a comparison, and a one-cell sheet is noise."""
        src = self.SRC.read_text()
        self.assertIn("len(made) > 1", src,
                      "a sheet should only be built when there is more than one roll to compare")

    def test_a_failed_sheet_never_fails_the_run(self):
        """The rolls are the deliverable and they cost money. A montage is a convenience."""
        src = self.SRC.read_text()
        self.assertIn("the rolls are unaffected", src,
                      "a contact-sheet failure must be reported and must not abort or fail the "
                      "run, because the renders already exist and are not reproducible")

    def test_it_only_sheets_rolls_that_actually_landed(self):
        src = self.SRC.read_text()
        self.assertIn('(out / f"{vid}.png").exists()', src,
                      "a failed variant has no png; sheeting it would crash the sheet builder")

if __name__ == "__main__":
    unittest.main()
