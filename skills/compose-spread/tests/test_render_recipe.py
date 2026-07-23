"""
compose-spread render_spread.py — provenance-recipe tests. Stdlib unittest,
reusing the synthetic universe from test_assemble_prompt.

Why this exists: AGENTS.md makes provenance non-negotiable ("every generated
asset MUST carry its provenance recipe, saved right alongside it"), but
render_spread.py used to write a bare PNG and nothing else. A folder of bare
PNGs cannot be reproduced, verified, or blessed into a golden. These tests fail
against that older behavior.

The model call is stubbed: `write_recipe` is pure software over the assembled
job, so it is tested directly rather than by burning image-model credits.

Run:  python3 -m unittest discover -s tests -v   (from the compose-spread skill dir)
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))

from test_assemble_prompt import build_universe, write_spec, png  # noqa: E402
from assemble_prompt import build, load  # noqa: E402
from render_spread import write_recipe, _sha16  # noqa: E402


class TestRenderRecipe(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)
        self.spec_path = write_spec(self.root, [{"id": "clean"}])
        self.spec = load(self.spec_path)
        self.job = build(self.root, self.spec, "s1")
        self.out = self.root / "spreads" / "spread-01.png"
        png(self.out)

    def tearDown(self):
        self.tmp.cleanup()

    def recipe(self):
        p = write_recipe(self.out, self.root, self.spec, "s1", self.job, "high")
        return p, json.loads(p.read_text())

    def test_recipe_is_written_beside_the_asset(self):
        p, _ = self.recipe()
        self.assertEqual(p.parent, self.out.parent)
        self.assertEqual(p.name, "spread-01.png.recipe.json")

    def test_recipe_pins_the_exact_prompt_and_model(self):
        _, r = self.recipe()
        self.assertEqual(r["prompt"], self.job["prompt"])
        self.assertEqual(r["model"], "gpt-image-2")
        self.assertEqual(r["size"], self.job["size"])
        self.assertEqual(r["quality"], "high")

    def test_every_ref_is_recorded_by_path_and_hash(self):
        _, r = self.recipe()
        self.assertEqual([x["path"] for x in r["refs"]], self.job["refs"])
        for entry in r["refs"]:
            self.assertEqual(entry["sha256_16"], _sha16(entry["path"]))

    def test_asset_hash_pins_the_bytes_it_describes(self):
        _, r = self.recipe()
        self.assertEqual(r["assetSha256_16"], _sha16(self.out))
        # a regenerated (different) asset must not still match the old recipe
        png(self.out, size=(16, 16))
        self.assertNotEqual(r["assetSha256_16"], _sha16(self.out))

    def test_recipe_carries_the_descriptor_and_qa_checklist(self):
        _, r = self.recipe()
        self.assertEqual(r["descriptor"], self.spec["spreads"][0])
        self.assertEqual(r["qa"], self.job["qa"])
        self.assertEqual(r["spread"], "s1")


if __name__ == "__main__":
    unittest.main()
