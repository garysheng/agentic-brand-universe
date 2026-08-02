#!/usr/bin/env python3
"""Three v0.29 fixes, all earned on one book run (The Tithe Is a Test, 2026-08-02).

1. `structured.render.qa` STEERED NOTHING AND CHECKED NOTHING. SPEC 4.6 has said since
   v0.4 that "qa = the union of every in-frame entity's `invariants` + `render.qa`", and
   no compiler ever read the second half. `theo-doorchaser` carried a well-written
   six-item `render.qa` and an EMPTY `structured.invariants`, so a dry assemble reported
   thirteen QA invariants on a two-hander (all thirteen the other man's) and ZERO on the
   spread where he stands alone.

2. A POSE COULD NOT SUPERSEDE A BASE INVARIANT; ONLY AN altLook COULD. An altLook is the
   wrong tool when the FACE must not change, because it auto-drops the base face sheets.
   The only way left to say "in this one pose the jacket is worn half-on" was to hand-word
   the base invariant as "...except in pose X", a rule enforced by an author remembering
   to phrase it.

3. `contract.blockingPlate` RODE ALONG ON EVERY RENDER OF A SETTING. `the-park-bench` was
   authored for a book about ice cream; its blocking plate shows two figures holding
   cones. Three of the first seven spreads of an unrelated book came back with both men
   holding ice cream, through scene text AND a per-spread negative that banned ice cream
   by name. A reference image outranks a negative word.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build


def _universe(tmp, theo=None, bench=None):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    for d in ("theo", "a-bench"):
        (root / "reference" / d).mkdir(parents=True)
    for f in ("theo/fullbody.png", "theo/face.png", "theo/jacket.png",
              "a-bench/wide.png", "a-bench/blocking.png"):
        (root / "reference" / f).write_bytes(b"\x89PNG")
    (root / "reference" / "anchor.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "r", "anchor": "reference/anchor.png"}}}))

    (root / "canon" / "entities" / "theo.json").write_text(json.dumps(theo or {
        "id": "theo", "kind": "character", "status": "locked",
        "structured": {
            "sheets": {"forward-fullbody": "reference/theo/fullbody.png",
                       "face-neutral": "reference/theo/face.png",
                       "jacket-back": "reference/theo/jacket.png"},
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["jacket-worn-fully-on-both-sleeves"],
            "negatives": ["a jacket hanging off one shoulder"],
            "render": {"always": "A young man named Theo.",
                       "qa": ["scuffed-brown-boots", "no-hat-ever"],
                       "poses": {
                           "front": {"sheets": []},
                           "half-on-jacket": {
                               "bake": "His jacket is worn half-on.",
                               "supersedes": ["jacket-worn-fully-on-both-sleeves",
                                              "a jacket hanging off one shoulder"],
                               "invariants": ["jacket-half-on-left-sleeve-off-the-shoulder"],
                               "negatives": ["both arms in both sleeves"],
                           }}}},
        "prose": {"rules": ""}}))

    (root / "canon" / "entities" / "a-bench.json").write_text(json.dumps(bench or {
        "id": "a-bench", "kind": "setting", "status": "locked",
        "structured": {"sheets": {"wide": "reference/a-bench/wide.png"}},
        "contract": {"turnaround": None, "blueprint": None,
                     "emptyPlates": ["reference/a-bench/wide.png"],
                     "blockingPlate": "reference/a-bench/blocking.png",
                     "map": "A park bench under a tree.", "blocking": "Two seats.",
                     "dressing": "Fallen leaves.", "scale": "Bench seats two."}}))
    return root


def _spec(cast, scene="Theo sits."):
    return {"book": "b", "story": "s", "size": "1536x1024",
            "preamble": {"register": "r"},
            "spreads": [{"id": "spread-01", "scene": scene, "cast": cast}]}


class TestRenderQaReachesTheChecklist(unittest.TestCase):
    """SPEC 4.6's stated union, finally implemented."""

    def test_render_qa_items_are_compiled(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "theo"}]), "spread-01")
            self.assertIn("theo: scuffed-brown-boots", out["qa"])
            self.assertIn("theo: no-hat-ever", out["qa"])

    def test_a_populated_render_qa_with_empty_invariants_is_not_a_zero(self):
        """theo-doorchaser's exact shape: six qa items, no invariants at all."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            ent = json.loads((root / "canon" / "entities" / "theo.json").read_text())
            ent["structured"]["invariants"] = []
            (root / "canon" / "entities" / "theo.json").write_text(json.dumps(ent))
            out = build(root, _spec([{"id": "theo"}]), "spread-01")
            self.assertEqual(len(out["qa"]), 2,
                             f"a populated render.qa must not compile to zero: {out['qa']}")

    def test_render_qa_is_compiled_for_non_characters_too(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            ent = json.loads((root / "canon" / "entities" / "a-bench.json").read_text())
            ent["structured"]["render"] = {"qa": ["slats-are-weathered-grey"]}
            (root / "canon" / "entities" / "a-bench.json").write_text(json.dumps(ent))
            out = build(root, _spec([{"id": "a-bench", "plate": "wide"}], "A quiet bench."), "spread-01")
            self.assertIn("a-bench: slats-are-weathered-grey", out["qa"])

    def test_the_checklist_does_not_ask_twice(self):
        """An entity may state one rule in both fields; the checklist says it once."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            ent = json.loads((root / "canon" / "entities" / "theo.json").read_text())
            ent["structured"]["render"]["qa"] = ["jacket-worn-fully-on-both-sleeves"]
            (root / "canon" / "entities" / "theo.json").write_text(json.dumps(ent))
            out = build(root, _spec([{"id": "theo"}]), "spread-01")
            self.assertEqual(out["qa"].count("theo: jacket-worn-fully-on-both-sleeves"), 1)


class TestPoseSupersedes(unittest.TestCase):
    """A pose may retire a base invariant and its matching negative."""

    def test_without_the_pose_the_base_invariant_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "theo"}]), "spread-01")
            self.assertIn("theo: jacket-worn-fully-on-both-sleeves", out["qa"])
            self.assertIn("a jacket hanging off one shoulder", out["prompt"])

    def test_the_pose_retires_the_invariant_it_inverts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "theo", "pose": "half-on-jacket"}]), "spread-01")
            self.assertNotIn("theo: jacket-worn-fully-on-both-sleeves", out["qa"],
                             "the pose inverts this rule; the checklist must not still ask for it")
            self.assertIn("theo: jacket-half-on-left-sleeve-off-the-shoulder", out["qa"])

    def test_the_prompt_block_agrees_with_the_checklist(self):
        """The whole point of `supersedes`: prompt, checklist and negatives by construction."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "theo", "pose": "half-on-jacket"}]), "spread-01")
            self.assertNotIn("jacket worn fully on both sleeves", out["prompt"])
            self.assertIn("jacket half on left sleeve off the shoulder", out["prompt"])

    def test_the_pose_retires_the_negative_that_would_fight_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "theo", "pose": "half-on-jacket"}]), "spread-01")
            self.assertNotIn("a jacket hanging off one shoulder", out["prompt"],
                             "an entity negative that contradicts the selected pose must not "
                             "reach the model; a negative outranks a scene sentence")
            self.assertIn("both arms in both sleeves", out["prompt"])

    def test_an_ordinary_pose_changes_nothing(self):
        """Additive: a pose with no supersedes compiles exactly as before."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            plain = build(root, _spec([{"id": "theo", "pose": "front"}]), "spread-01")
            self.assertIn("theo: jacket-worn-fully-on-both-sleeves", plain["qa"])
            self.assertIn("a jacket hanging off one shoulder", plain["prompt"])


class TestBlockingPlateScoping(unittest.TestCase):
    """One book's props must not leak into every book that reuses the setting."""

    def _refs(self, out):
        return [Path(p).name for p in out["refs"]]

    def test_the_blocking_plate_rides_along_by_default(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "a-bench", "plate": "wide"}], "A quiet bench."), "spread-01")
            self.assertIn("blocking.png", self._refs(out))

    def test_a_spread_can_scope_it_out(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec([{"id": "a-bench", "plate": "wide",
                                      "blockingPlate": False}], "A quiet bench."), "spread-01")
            self.assertNotIn("blocking.png", self._refs(out))
            self.assertIn("wide.png", self._refs(out),
                          "scoping out the blocking plate must not drop the camera plate")

    def test_a_plate_can_scope_it_out_for_every_spread_that_selects_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            ent = json.loads((root / "canon" / "entities" / "a-bench.json").read_text())
            ent["contract"]["plates"] = {"wide": {"includeBlockingPlate": False}}
            (root / "canon" / "entities" / "a-bench.json").write_text(json.dumps(ent))
            out = build(root, _spec([{"id": "a-bench", "plate": "wide"}], "A quiet bench."), "spread-01")
            self.assertNotIn("blocking.png", self._refs(out))


if __name__ == "__main__":
    unittest.main()
