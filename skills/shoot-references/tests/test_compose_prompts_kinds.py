"""compose_prompts writes an OBJECT prompt for a prop or motif, never a person's (gap G7, #8).

A bell or a mark composed from the character template was asked for "Full body, standing,
head to feet" and a "calm neutral expression, mouth closed" against a warm studio field.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compose_prompts.py"


class ObjectKindsGetAnObjectPrompt(unittest.TestCase):
    def compose(self, kind, poses=None):
        with tempfile.TemporaryDirectory() as t:
            u = Path(t)
            (u / "canon" / "entities").mkdir(parents=True)
            (u / "canon" / "entities" / "bell.json").write_text(json.dumps({
                "id": "bell", "kind": kind,
                "structured": {"sheets": {"hero": None, "detail": None},
                               "invariants": ["the crack runs left of the strike line"],
                               "render": {"always": "THE BELL: bronze, cracked, on a yoke.",
                                          "poses": poses or {}}}}))
            r = subprocess.run([sys.executable, str(SCRIPT), str(u), "bell", "--all"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            return (u / "reference" / "bell" / "prompts.md").read_text()

    def test_a_prop_gets_no_body_framing_and_no_expression(self):
        for kind in ("prop", "motif"):
            md = self.compose(kind)
            self.assertNotIn("head to feet", md, kind)
            self.assertNotIn("expression", md, kind)
            self.assertNotIn("warm neutral studio", md, kind)
            self.assertIn("WHAT THIS IS: THE BELL", md, kind)
            self.assertIn("The object alone", md, kind)

    def test_a_props_pose_bake_is_its_plate_line(self):
        md = self.compose("prop", poses={"detail": {"sheets": ["detail"],
                                                    "bake": "Tight on the crack."}})
        self.assertIn("THIS PLATE: Tight on the crack.", md)

    def test_a_character_is_unchanged(self):
        with tempfile.TemporaryDirectory() as t:
            u = Path(t)
            (u / "canon" / "entities").mkdir(parents=True)
            (u / "canon" / "entities" / "jim.json").write_text(json.dumps({
                "id": "jim", "kind": "character",
                "structured": {"sheets": {"master": None}, "invariants": ["x"],
                               "render": {"always": "JIM.", "poses": {}}}}))
            subprocess.run([sys.executable, str(SCRIPT), str(u), "jim", "--all"],
                           capture_output=True, text=True, check=True)
            self.assertIn("head to feet", (u / "reference/jim/prompts.md").read_text())


if __name__ == "__main__":
    unittest.main()
