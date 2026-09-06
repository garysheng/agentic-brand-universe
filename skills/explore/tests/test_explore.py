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


if __name__ == "__main__":
    unittest.main()
