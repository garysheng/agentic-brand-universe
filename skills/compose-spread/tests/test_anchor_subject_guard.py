#!/usr/bin/env python3
"""`identity.register.anchorSubject` must be negated on every spread, not just on shoots.

The generic ANCHOR_STYLE_GUARD ("take NO subject from the anchor") loses to a concrete
picture, which is why `anchorSubject` exists: it NAMES what the anchor depicts so it can
be banned specifically. Two sibling compilers already read it (chain_matrix.py since
v0.29, compile_cover.py after an oil lamp was painted onto a finished cover). The spread
compiler, which handles every interior of every book, was the last one that did not.

The cost was silent and paid per book. On Why We Are the Luckiest Generation (2026-08-04)
all 27 spreads hand-wrote "No ancient oil lamp, no clay oil jar or flask, no terracotta
oil vessel, no tabletop pottery still life" into their own negatives, and the Nation of
Fire cartridge asserted outright that "the compiler injects the negation" -- true of a
retired universe-local fork, false of this one, and nothing checked it.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build, anchor_subject_guard  # noqa: E402

SUBJECT = "an ancient oil lamp, a clay oil jar or flask, terracotta vessels"


def _universe(tmp, subject=SUBJECT):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "anchor").mkdir(parents=True)
    (root / "reference" / "anchor" / "hero.png").write_bytes(b"\x89PNG")
    (root / "reference" / "anchor" / "other.png").write_bytes(b"\x89PNG")
    reg = {"name": "soft painterly", "anchor": "reference/anchor/hero.png",
           "rejectedPoles": ["photoreal"]}
    if subject is not None:
        reg["anchorSubject"] = subject
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".", "identity": {"register": reg}}))
    return root


def _spec(spread):
    return {"book": "b", "story": "s", "size": "1536x1024", "preamble": {},
            "spreads": [spread]}


class TestAnchorSubjectGuardUnit(unittest.TestCase):
    def test_empty_subject_emits_nothing(self):
        self.assertEqual(anchor_subject_guard(None), "")
        self.assertEqual(anchor_subject_guard(""), "")

    def test_it_names_the_subject_and_keeps_the_carve_out(self):
        g = anchor_subject_guard(SUBJECT)
        self.assertIn(SUBJECT, g)
        self.assertIn("does not ask for them by name", g,
                      "a book legitimately set in the anchor's own period must still be "
                      "able to ask for that subject explicitly")


class TestAnchorSubjectInAssembledPrompt(unittest.TestCase):
    def test_declared_subject_is_negated_on_a_plain_spread(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            out = build(root, _spec({"id": "spread-01", "scene": "A dark hillside at night."}),
                        "spread-01")
            self.assertIn(SUBJECT, out["prompt"])

    def test_a_universe_with_no_anchor_subject_is_unchanged(self):
        """Advisory field: absent it, behaviour is exactly as before."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp, subject=None)
            out = build(root, _spec({"id": "spread-01", "scene": "A dark hillside."}),
                        "spread-01")
            self.assertNotIn("NONE OF THE FOLLOWING", out["prompt"])

    def test_anchor_ref_override_suppresses_the_guard(self):
        """An override replaces the first image, so anchorSubject no longer describes it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            spec = _spec({"id": "spread-01", "scene": "A dark hillside.",
                          "anchorRef": "reference/anchor/other.png"})
            out = build(root, spec, "spread-01")
            self.assertNotIn(SUBJECT, out["prompt"])
            self.assertEqual(Path(out["refs"][0]).name, "other.png")


if __name__ == "__main__":
    unittest.main()
