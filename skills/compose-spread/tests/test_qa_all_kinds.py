#!/usr/bin/env python3
"""Read-back QA is compiled from EVERY in-frame entity, not only characters.

SPEC 4.6 states the contract plainly: "qa = the union of every in-frame entity's
`invariants` + `render.qa`". The compiler did not do that. `qa` was appended only in the
character branch, and every other kind hit a `continue` before reaching it, so a setting,
visual-metaphor, motif or prop could DECLARE invariants, pass `validate` and `lint`, and
still contribute nothing to the checklist. The entity looked guarded and was not, which is
the worst of the three states (guarded, unguarded, looks-guarded).

Earned on the-only-scoreboard (nation-of-fire, 2026-08-02). `the-one-lit-board` is the
spine object of that book and declares twelve invariants covering exactly the things that
drift: no board is ever gold, the marked row is a solid dark dot and never a white fill,
the lit board is never enlarged, never a screen, never a sports scoreboard.
`compose-spread --dry-run` reported "0 qa invariants" on all seven spreads that cast it,
so all twelve were checked by eye and three drifted anyway, twice on the gold rule the
entity states first.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build


BOARD_INVARIANTS = [
    "no-board-is-ever-gold",
    "the-marker-is-a-solid-dark-filled-dot-never-a-white-fill",
    "never-a-screen-no-pixels-no-bezels",
]
PROP_INVARIANTS = ["lamp-is-terracotta-never-glazed"]
MOTIF_INVARIANTS = ["wisp-is-warm-gold-and-never-touches-a-devil"]


def _universe(tmp):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    for d in ("a-board", "a-lamp", "a-wisp", "a-room"):
        (root / "reference" / d).mkdir(parents=True)
        (root / "reference" / d / "master.png").write_bytes(b"\x89PNG")
    (root / "reference" / "anchor.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "r", "anchor": "reference/anchor.png"}}}))

    (root / "canon" / "entities" / "a-board.json").write_text(json.dumps({
        "id": "a-board", "kind": "visual-metaphor", "status": "locked",
        "structured": {"sheets": {"master": "reference/a-board/master.png"},
                       "invariants": BOARD_INVARIANTS},
        "contract": {"map": "A board.", "blocking": "", "dressing": "", "scale": ""}}))

    (root / "canon" / "entities" / "a-room.json").write_text(json.dumps({
        "id": "a-room", "kind": "setting", "status": "locked",
        "structured": {"sheets": {"master": "reference/a-room/master.png"},
                       "invariants": ["room-is-windowless"]},
        "contract": {"map": "A room.", "blocking": "", "dressing": "", "scale": ""}}))

    (root / "canon" / "entities" / "a-lamp.json").write_text(json.dumps({
        "id": "a-lamp", "kind": "prop", "status": "locked",
        "structured": {"sheets": {"master": "reference/a-lamp/master.png"},
                       "requiredForRender": ["reference/a-lamp/master.png"],
                       "invariants": PROP_INVARIANTS},
        "prose": {"rules": "A lamp."}}))

    (root / "canon" / "entities" / "a-wisp.json").write_text(json.dumps({
        "id": "a-wisp", "kind": "motif", "status": "locked",
        "structured": {"sheets": {"master": "reference/a-wisp/master.png"},
                       "requiredForRender": ["reference/a-wisp/master.png"],
                       "invariants": MOTIF_INVARIANTS},
        "prose": {"rules": "A wisp."}}))
    return root


def _spec(cast):
    return {"book": "b", "story": "s", "size": "1536x1024",
            "preamble": {"register": "r"},
            "spreads": [{"id": "spread-01", "scene": "A quiet room.", "cast": cast}]}


class TestQaFromEveryKind(unittest.TestCase):
    def test_visual_metaphor_invariants_reach_the_checklist(self):
        """The regression that earned this file."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "a-board", "plate": "master"}]), "spread-01")
            self.assertTrue(out["qa"], "a visual-metaphor declaring invariants produced an EMPTY checklist")
            for inv in BOARD_INVARIANTS:
                self.assertTrue(any(inv in q for q in out["qa"]),
                                f"invariant {inv!r} never reached qa: {out['qa']}")

    def test_qa_lines_name_the_entity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "a-board", "plate": "master"}]), "spread-01")
            self.assertTrue(all(q.startswith("a-board: ") for q in out["qa"]),
                            f"every qa line must name its entity: {out['qa']}")

    def test_setting_prop_and_motif_all_contribute(self):
        """SPEC 4.6 says EVERY in-frame entity, so no kind is exempt."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([
                {"id": "a-room", "plate": "master"},
                {"id": "a-board", "plate": "master"},
                {"id": "a-lamp", "plate": "master"},
                {"id": "a-wisp", "plate": "master"},
            ]), "spread-01")
            joined = " | ".join(out["qa"])
            for inv in ["room-is-windowless"] + BOARD_INVARIANTS + PROP_INVARIANTS + MOTIF_INVARIANTS:
                self.assertIn(inv, joined, f"{inv!r} missing from qa: {joined}")

    def test_an_entity_with_no_invariants_adds_nothing(self):
        """The fix must stay additive: silence in, silence out."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _universe(tmp)
            (root / "canon" / "entities" / "bare.json").write_text(json.dumps({
                "id": "bare", "kind": "visual-metaphor", "status": "locked",
                "structured": {"sheets": {"master": "reference/a-board/master.png"}},
                "contract": {"map": "Bare.", "blocking": "", "dressing": "", "scale": ""}}))
            out = build(root, _spec([{"id": "bare", "plate": "master"}]), "spread-01")
            self.assertEqual(out["qa"], [], f"an entity with no invariants must add nothing: {out['qa']}")


if __name__ == "__main__":
    unittest.main()
