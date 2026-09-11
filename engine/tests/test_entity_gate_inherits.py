"""SPEC 3.5 (v0.46): binding an entity puts its invariants on the render's readback gate.

The prompt half always inherited (invariants were baked in as positives). The judgment half
did not: the checklist a piece was read back against was the pack's gate alone. Earned
2026-09-10 by four covers whose North Star Cross drifted while the printed checklist said
nothing about proportions.
"""
import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
GENERATE = REPO / "skills" / "on-brand-image" / "scripts" / "generate.py"
FIXTURE = REPO / "engine" / "tests" / "fixtures" / "example"


def _load():
    spec = importlib.util.spec_from_file_location("obi_generate", GENERATE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class EntityGateTest(unittest.TestCase):
    def setUp(self):
        self.mod = _load()

    def test_entity_gate_is_per_entity_and_skips_entities_without_invariants(self):
        meta = [
            {"id": "north-star-cross", "look": None, "invariants": ["four points", "bottom point 1.48x"]},
            {"id": "some-chair", "look": "oak", "invariants": []},
            {"id": "hero", "look": None},
        ]
        gate = self.mod.entity_gate(meta)
        self.assertEqual(gate, [{"id": "north-star-cross", "look": None,
                                 "invariants": ["four points", "bottom point 1.48x"]}])

    def test_resolve_entities_carries_each_entitys_invariants(self):
        with tempfile.TemporaryDirectory() as td:
            uni = Path(td) / "u"
            shutil.copytree(FIXTURE, uni)
            hero = uni / "canon" / "entities" / "hero.json"
            d = json.loads(hero.read_text())
            d.setdefault("structured", {})["invariants"] = ["two gold incisors", "a scar over the left eye"]
            hero.write_text(json.dumps(d))
            refs, invariants, rules, meta = self.mod.resolve_entities([f"{uni}:hero"])
            self.assertIn("two gold incisors", invariants)
            self.assertEqual(meta[0]["id"], "hero")
            self.assertEqual(meta[0]["invariants"], ["two gold incisors", "a scar over the left eye"])
            gate = self.mod.entity_gate(meta)
            self.assertEqual(gate[0]["id"], "hero")
            self.assertEqual(len(gate[0]["invariants"]), 2)


if __name__ == "__main__":
    unittest.main()
