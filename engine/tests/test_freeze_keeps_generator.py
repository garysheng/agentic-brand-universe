"""lock-shot --recipe must not strip the code-drawn marker off a massing blueprint (#47).

`freeze_recipe` rewrote the sidecar as {goldenDigest, provider, prompt, specVersion, inputs}
and dropped `generator`/`deterministic`, so a locked massing blueprint read as PAINTED and a
blueprint-seeded shoot had no legal first shot (the-academy-hall, 2026-08-21).
"""
import json
import tempfile
import unittest
from pathlib import Path

from agenticstory import massing, seen
from agenticstory.authoring import freeze_recipe, scaffold_entity, lock_shot


class TestFreezeKeepsGenerator(unittest.TestCase):
    def test_massing_marker_survives_the_freeze(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "blueprint.png"
            out.write_bytes(b"png")
            spec = Path(t) / "spec.json"
            spec.write_text("{}")
            rp = massing.write_recipe(str(out), str(spec), universe="u", entity="hall")
            frozen = freeze_recipe(out, json.loads(Path(rp).read_text()))
        self.assertTrue(frozen["generator"].startswith("agenticstory.massing"))
        self.assertIs(frozen["deterministic"], True)
        self.assertEqual(frozen["entity"], "hall")
        self.assertTrue(frozen["goldenDigest"])

    def test_a_painted_recipe_gains_no_marker(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "master.png"
            out.write_bytes(b"png")
            frozen = freeze_recipe(out, {"model": "gpt-image-2", "prompt": "p"})
        self.assertNotIn("generator", frozen)
        self.assertNotIn("deterministic", frozen)

    def test_lock_shot_with_the_massing_recipe_keeps_the_sidecar_code_drawn(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "reference" / "hall").mkdir(parents=True)
            out = root / "reference" / "hall" / "blueprint.png"
            out.write_bytes(b"png")
            rp = massing.write_recipe(str(out), "canon/blueprints/hall.json", entity="hall")
            recipe = json.loads(Path(rp).read_text())
            ent = scaffold_entity("setting", "hall", "Hall")
            # The lock's seen gate is exercised in test_seen; record the documented
            # exception so this test reaches the freeze.
            from agenticstory import display
            seen.record_board(out, question="blueprint", options=["keep"],
                              display=display.pending(display.FRAPP, ""))
            seen.record_tap(out, "waived", why="test: code-drawn geometry, no art to judge")
            lock_shot(ent, "blueprint", "reference/hall/blueprint.png", recipe=recipe,
                      root=str(root))
            side = json.loads((out.parent / "blueprint.png.recipe.json").read_text())
        self.assertTrue(side.get("generator", "").startswith("agenticstory.massing"), side)


if __name__ == "__main__":
    unittest.main()
