"""The candidate rule: what an approval board may put in front of an operator (v0.52).

Earned 2026-09-24, when the entity shot board read `witney/superseded-unlit-2026-09-24/` as a
look folder and Gary was shown retired and rejected plates beside the live ones. The rule is
one module, and the page-side copy the frapps load is held to it here by running both.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agenticstory.candidates import is_candidate, why_not_candidate

ROOT = Path(__file__).resolve().parents[2]
MJS = ROOT / "skills" / "shoot-references" / "frapps" / "candidates.mjs"

CASES = {
    "witney/back.png": True,
    "witney/casual/back.png": True,
    "works/heroes/absorbed-rigor.png": True,
    "works/heroes/a-harness.r1.png": False,
    "works/heroes/a-harness.R12.webp": False,
    "witney/rejected/back.png": False,
    "witney/casual/rejected/back.png": False,
    "witney/superseded-unlit-2026-09-24/back.png": False,
    "the-gym/superseded/plate.jpg": False,
    "book/candidates/pre-reroll-20260901/spread-01.png": False,
    "book/pre-reroll-20260901/spread-01.png": False,
    "witney/photos/source.jpg": False,
    "works/heroes/heroes.json": False,
    "works/heroes/rolled-over.png": True,   # "r" inside a word is not a roll suffix
    "works/heroes/a.r1x.png": True,
}


class CandidateRuleTest(unittest.TestCase):
    def test_each_case(self):
        for rel, want in CASES.items():
            with self.subTest(rel=rel):
                self.assertEqual(is_candidate(Path("/u") / rel, "/u"), want,
                                 why_not_candidate(Path("/u") / rel, "/u"))

    def test_the_root_bounds_the_folder_check(self):
        # A universe that happens to live under a folder called `candidates` is not refused.
        self.assertTrue(is_candidate("/x/candidates/u/witney/back.png", "/x/candidates/u"))
        self.assertFalse(is_candidate("/x/candidates/u/witney/back.png"))

    def test_the_refusal_names_the_folder(self):
        why = why_not_candidate("/u/witney/superseded-unlit/back.png", "/u")
        self.assertIn("superseded-unlit/", why)

    @unittest.skipUnless(shutil.which("node"), "node not installed")
    def test_the_page_side_copy_agrees_on_every_case(self):
        script = (f"import {{ isCandidate }} from {json.dumps(MJS.as_uri())};\n"
                  f"const cases = {json.dumps(list(CASES))};\n"
                  "console.log(JSON.stringify(cases.map((c) => isCandidate('/u/' + c, '/u'))));")
        with tempfile.NamedTemporaryFile("w", suffix=".mjs", delete=False) as f:
            f.write(script)
        out = subprocess.run(["node", f.name], capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(out), list(CASES.values()))


if __name__ == "__main__":
    unittest.main()
