"""A pose on a non-character selects nothing, so the compiler refuses it.

`pose` is a character selector. Every other kind chooses its variant with `plate`,
and no branch for those kinds reads pose, so a cast entry writing
`{"id": "a-visual-metaphor", "pose": "dark"}` was accepted in silence and resolved
to the entity's DEFAULT plate. A multi-state object then rendered the same state on
every spread while the render-spec looked correct.

Nine spreads of a real book shipped that way on 2026-08-03, every one showing a
wall of lights the story needed dark. Canon that reads as a rule and steers nothing
is this repo's most-repeated defect; the fix is always the same, which is to make
the mistake refuse.
"""
import importlib.util
import json
import pathlib
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("ap", HERE / "scripts" / "assemble_prompt.py")
ap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ap)


class PoseOnNonCharacter(unittest.TestCase):
    def universe(self, kind):
        root = pathlib.Path(tempfile.mkdtemp())
        (root / "canon" / "entities").mkdir(parents=True)
        (root / "reference" / "thing").mkdir(parents=True)
        for n in ("a", "b"):
            (root / "reference" / "thing" / f"{n}.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (root / "reference" / "style").mkdir(parents=True)
        (root / "reference" / "style" / "anchor.png").write_bytes(b"\x89PNG\r\n\x1a\n")
        (root / "universe.json").write_text(json.dumps(
            {"id": "u", "identity": {"register": {"name": "r",
                                                  "anchor": "reference/style/anchor.png",
                                                  "rejectedPoles": []}}}))
        (root / "canon" / "entities" / "thing.json").write_text(json.dumps({
            "id": "thing", "kind": kind, "status": "locked",
            "contract": {"turnaround": "reference/thing/a.png", "emptyPlates": [],
                         "map": "m", "blocking": "b", "dressing": "d", "scale": "s"},
            "structured": {"invariants": [],
                           "sheets": {"a": "reference/thing/a.png",
                                      "b": "reference/thing/b.png"}},
        }))
        return root

    def spec_with(self, selector, value):
        return {"book": "bk", "story": "st", "size": "1536x1024", "preamble": {},
                "spreads": [{"id": "spread-01", "scene": "a scene",
                             "cast": [{"id": "thing", selector: value}]}]}

    def test_pose_on_a_visual_metaphor_refuses(self):
        root = self.universe("visual-metaphor")
        with self.assertRaises(ap.Refuse) as e:
            ap.build(root, self.spec_with("pose", "b"), "spread-01")
        self.assertIn("'plate', not 'pose'", str(e.exception))

    def test_the_refusal_names_the_available_plates(self):
        """A refusal that does not say what to write instead is a wall, not a gate."""
        root = self.universe("visual-metaphor")
        with self.assertRaises(ap.Refuse) as e:
            ap.build(root, self.spec_with("pose", "b"), "spread-01")
        self.assertIn("'a', 'b'", str(e.exception))

    def test_plate_on_the_same_entity_is_accepted(self):
        root = self.universe("visual-metaphor")
        out = ap.build(root, self.spec_with("plate", "b"), "spread-01")
        self.assertTrue(any(r.endswith("b.png") for r in out["refs"]))

    def test_a_motif_refuses_too(self):
        """The rule is about every non-character kind, not one of them."""
        root = self.universe("motif")
        with self.assertRaises(ap.Refuse):
            ap.build(root, self.spec_with("pose", "b"), "spread-01")


if __name__ == "__main__":
    unittest.main()
