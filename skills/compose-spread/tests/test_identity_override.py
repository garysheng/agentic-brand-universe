#!/usr/bin/env python3
"""A cast entry's `bake` must not silently replace a locked character's identity.

entity_block() lets `bake` REPLACE the derived block. That is right for a multi-state
prop and catastrophic for a character: the canon block is where ONE LOCKED FACE, the
wardrobe rules and the modesty anatomy live. Earned 2026-07-30, when all 17 spreads of
gain-everything-lose-nothing carried a typed Selah paragraph that replaced her canon
block (aging her a decade past canon), and it shipped before anyone noticed.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build, Refuse

IDENTITY_INV = ["one-locked-face", "double-eyelid-crease"]


def _universe(tmp, invariants=IDENTITY_INV):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "her").mkdir(parents=True)
    for f in ("face.png", "anchor.png"):
        (root / "reference" / "her" / f).write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "r", "anchor": "reference/her/anchor.png"}}}))
    (root / "canon" / "entities" / "her.json").write_text(json.dumps({
        "id": "her", "kind": "character", "status": "locked",
        "structured": {"sheets": {"face": "reference/her/face.png"},
                       "requiredForRender": ["face"],
                       "invariants": invariants,
                       "render": {"always": "HER, exactly as her canon face sheet."}}}))
    return root


def _spec(cast):
    return {"book": "b", "story": "s", "size": "1536x1024",
            "preamble": {"register": "r"},
            "spreads": [{"id": "spread-01", "cast": cast, "scene": "A room."}]}


class TestIdentityOverride(unittest.TestCase):
    def test_refuses_a_bake_over_a_locked_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            with self.assertRaises(Refuse) as cm:
                build(root, _spec([{"id": "her", "bake": "A woman in her forties."}]), "spread-01")
            msg = str(cm.exception)
            self.assertIn("BAKE WOULD REPLACE A LOCKED IDENTITY", msg)
            self.assertIn("her", msg)
            self.assertIn("one-locked-face", msg, "the refusal must name which invariant is at risk")

    def test_canon_block_reaches_the_prompt_when_no_bake_is_set(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "her"}]), "spread-01")
            self.assertIn("exactly as her canon face sheet", out["prompt"],
                          "canon must describe the character when the spec does not")

    def test_override_is_possible_but_must_be_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "her", "bake": "A deliberate override.",
                                      "allowIdentityOverride": True}]), "spread-01")
            self.assertIn("A deliberate override.", out["prompt"])

    def test_a_character_without_identity_invariants_is_unaffected(self):
        """Extras and bit-part characters keep the cheap path."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp, invariants=["wears-a-hat"])
            out = build(root, _spec([{"id": "her", "bake": "A passer-by."}]), "spread-01")
            self.assertIn("A passer-by.", out["prompt"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
