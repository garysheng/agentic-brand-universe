#!/usr/bin/env python3
"""A pose's extra sheets must survive TYPED slots ({"path", "role"}, legal since v0.23).

The pose-sheet line passed the RAW slot value into refs, so a typed slot reached
resolve_ref as a dict and crashed the whole build with a TypeError. Found on
the-introducer (2026-08-08): david-kobrosky's register-neutral matrix types every
slot with role "identity" (as lint-universe itself advises), and the first spread
selecting his signature pose could not assemble. Same failure class as the v0.37
linter crash: the slot form the spec recommends must never be the form that breaks
a code path.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build  # noqa: E402


def _universe(tmp):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "anchor").mkdir(parents=True)
    (root / "reference" / "hero").mkdir(parents=True)
    (root / "reference" / "anchor" / "swatch.png").write_bytes(b"\x89PNG")
    for s in ("face-neutral", "forward-fullbody", "signature-pose"):
        (root / "reference" / "hero" / f"{s}.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "soft painterly",
                                  "anchor": "reference/anchor/swatch.png",
                                  "rejectedPoles": []}}}))
    # every slot TYPED, exactly as lint-universe advises for register-neutral entities
    (root / "canon" / "entities" / "hero.json").write_text(json.dumps({
        "id": "hero", "kind": "character",
        "structured": {
            "sheets": {
                "face-neutral": {"path": "reference/hero/face-neutral.png", "role": "identity"},
                "forward-fullbody": {"path": "reference/hero/forward-fullbody.png", "role": "identity"},
                "signature-pose": {"path": "reference/hero/signature-pose.png", "role": "identity"},
            },
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["tall"],
            "render": {
                "always": "HERO, a tall person.",
                "poses": {
                    "front": {"sheets": ["forward-fullbody", "face-neutral"]},
                    "signature": {"sheets": ["signature-pose", "face-neutral"]},
                },
            },
        },
        "prose": {}}))
    return root


def _spec(spread):
    return {"book": "b", "story": "s", "size": "1536x1024", "preamble": {},
            "spreads": [spread]}


class TestTypedPoseSheets(unittest.TestCase):
    def test_typed_slots_survive_a_pose_selection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec({
                "id": "spread-01",
                "cast": [{"id": "hero", "pose": "signature"}],
                "scene": "HERO stands alone on a hill."}), "spread-01")
            for r in out["refs"]:
                self.assertIsInstance(r, str)
            self.assertTrue(any(r.endswith("signature-pose.png") for r in out["refs"]),
                            "the pose's extra sheet must actually be passed")

    def test_bare_string_slots_still_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            ent = json.loads((root / "canon" / "entities" / "hero.json").read_text())
            sheets = ent["structured"]["sheets"]
            ent["structured"]["sheets"] = {k: v["path"] for k, v in sheets.items()}
            (root / "canon" / "entities" / "hero.json").write_text(json.dumps(ent))
            out = build(root, _spec({
                "id": "spread-01",
                "cast": [{"id": "hero", "pose": "signature"}],
                "scene": "HERO stands alone on a hill."}), "spread-01")
            self.assertTrue(any(r.endswith("signature-pose.png") for r in out["refs"]))


if __name__ == "__main__":
    unittest.main()
