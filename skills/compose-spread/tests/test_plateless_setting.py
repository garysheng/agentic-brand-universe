#!/usr/bin/env python3
"""A setting cast with no plate must be refused, not silently rendered from prose.

resolve_plate returns [] for a null plate, so such a spread passes NO setting image and
the model invents the place from scratch, differently every render. It was silent, and
an audit of nation-of-fire found 10 shipped spreads doing exactly this, plus 42 more
selecting a plate absent from the entity's `sheets` map.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build, Refuse


def _universe(tmp):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "a-room").mkdir(parents=True)
    (root / "reference" / "a-room" / "master.png").write_bytes(b"\x89PNG")
    (root / "reference" / "anchor.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "r", "anchor": "reference/anchor.png"}}}))
    (root / "canon" / "entities" / "a-room.json").write_text(json.dumps({
        "id": "a-room", "kind": "setting", "status": "locked",
        "structured": {"sheets": {"master": "reference/a-room/master.png"},
                       "requiredForRender": ["reference/a-room/master.png"]},
        "contract": {"map": "A room.", "blocking": "", "dressing": "", "scale": ""}}))
    return root


def _spec(**over):
    sp = {"id": "spread-01", "setting": "a-room", "scene": "A quiet room.", "cast": []}
    sp.update(over)
    return {"book": "b", "story": "s", "size": "1536x1024",
            "preamble": {"register": "r"}, "spreads": [sp]}


class TestPlatelessSetting(unittest.TestCase):
    def test_refuses_when_no_plate_is_selected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            with self.assertRaises(Refuse) as cm:
                build(root, _spec(), "spread-01")
            msg = str(cm.exception)
            self.assertIn("SETTING CAST WITH NO PLATE", msg)
            self.assertIn("a-room", msg, "the refusal must name the setting")
            self.assertIn("spread-01", msg, "the refusal must name the spread")

    def test_accepts_a_named_plate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec(plate="master"), "spread-01")
            self.assertTrue(any("master.png" in r for r in out["refs"]),
                            "the selected plate must actually be passed as a reference")

    def test_escape_hatch_is_explicit_and_works(self):
        """Opting out must be possible, deliberate, and leave a trace in the spec."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec(allowPlatelessSetting=True), "spread-01")
            self.assertFalse(any("master.png" in r for r in out["refs"]),
                             "opting out means no setting image, which is the point")


if __name__ == "__main__":
    unittest.main(verbosity=2)
