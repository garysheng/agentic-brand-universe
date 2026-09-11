"""SPEC 4.7 `requiredEntities`: a Style Pack that names a locked canon entity refuses a
render that does not bind it via --entity.

Earned 2026-09-10: afrochristofuturism's pack.json said in prose that the North Star Cross
must come from the canon entity, four album-cover candidates rendered without it, and the
operator caught the drifted proportions by eye. A note is not a gate.
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GENERATE = REPO / "skills" / "on-brand-image" / "scripts" / "generate.py"


def _load():
    spec = importlib.util.spec_from_file_location("obi_generate", GENERATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


PACK = {"id": "afrochristofuturism", "requiredEntities": ["north-star-cross"]}
PLAIN = {"id": "receipt-flatlay"}
BOUND = "/u/christofuturism-universe:north-star-cross"


class RequiredEntityProblemTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_refuses_when_required_entity_is_not_bound(self):
        msg = self.mod.required_entity_problem(PACK, [], [])
        self.assertIsNotNone(msg)
        self.assertIn("north-star-cross", msg)
        self.assertIn("--waive-entity", msg)

    def test_passes_when_bound_with_or_without_a_look(self):
        self.assertIsNone(self.mod.required_entity_problem(PACK, [BOUND], []))
        self.assertIsNone(self.mod.required_entity_problem(PACK, [BOUND + "@brass"], []))

    def test_another_entity_does_not_satisfy(self):
        self.assertIsNotNone(self.mod.required_entity_problem(PACK, ["/u/x:some-chair"], []))

    def test_waiver_lifts_it_for_one_render(self):
        self.assertIsNone(self.mod.required_entity_problem(PACK, [], ["north-star-cross"]))

    def test_waiver_of_an_unrequired_entity_is_refused(self):
        msg = self.mod.required_entity_problem(PACK, [], ["some-chair"])
        self.assertIsNotNone(msg)
        self.assertIn("some-chair", msg)

    def test_pack_without_the_field_is_untouched(self):
        self.assertIsNone(self.mod.required_entity_problem(PLAIN, [], []))
        self.assertIsNone(self.mod.required_entity_problem({"id": "p", "requiredEntities": []}, [], []))


class RequiredEntityCliTest(unittest.TestCase):
    """The refusal fires at pack load, before any provider is reached or any file written."""

    def test_generate_refuses_before_rendering(self):
        with tempfile.TemporaryDirectory() as td:
            pack_dir = Path(td) / "pack"
            pack_dir.mkdir()
            (pack_dir / "pack.json").write_text(json.dumps({**PACK, "styleLine": "x", "textPolicy": "none"}))
            out = Path(td) / "out.png"
            r = subprocess.run(
                [sys.executable, str(GENERATE), "--out", str(out), "--prompt", "a cross",
                 "--style-pack", str(pack_dir), "--no-open"],
                capture_output=True, text=True, env={**os.environ, "OPENAI_API_KEY": "", "GEMINI_API_KEY": ""},
            )
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("north-star-cross", r.stderr + r.stdout)
            self.assertFalse(out.exists())


if __name__ == "__main__":
    unittest.main()
