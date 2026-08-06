#!/usr/bin/env python3
"""The CONSUMPTION half of a register-neutral matrix (SPEC v0.37 §12).

`shoot-references` makes an identity master with no register in it. That guarantee is
worthless on its own: the plate is then passed into renders whose medium it deliberately
does not share, and a reference image outranks a word, so its medium arrives with its
likeness unless something says otherwise. A photoreal master of a real person, cast into
a halftone-pop poster, drags photography into the poster.

The per-slot `role` vocabulary (v0.23) says "ignore its medium" for a TYPED slot and
nothing at all for an untyped one, and "these plates belong to no register" is only true
of the SET. So the compiler emits ONE entity-level line for a declared register-neutral
cast entry, and roles keep saying what each individual plate contributes.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from assemble_prompt import build, register_neutral_line  # noqa: E402

MEDIUM = "hyper-realistic documentary photography"
RN = {"medium": MEDIUM, "why": "one photoreal master; registers are conversions of it"}


def _universe(tmp, neutral=True, role=None):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "anchor").mkdir(parents=True)
    (root / "reference" / "anchor" / "hero.png").write_bytes(b"\x89PNG")
    (root / "reference" / "russ").mkdir(parents=True)
    (root / "reference" / "russ" / "face-neutral.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "halftone pop poster",
                                  "anchor": "reference/anchor/hero.png",
                                  "rejectedPoles": ["photoreal"]}}}))
    sheet = "reference/russ/face-neutral.png"
    st = {"sheets": {"face-neutral": ({"path": sheet, "role": role} if role else sheet)},
          "requiredForRender": ["face-neutral"],
          "invariants": ["left-neck-chevron-tattoo"],
          "render": {"always": ""}}
    if neutral:
        st["registerNeutral"] = RN
    (root / "canon" / "entities" / "russ.json").write_text(json.dumps({
        "id": "russ", "kind": "character", "structured": st}))
    return root


def _spec():
    return {"book": "b", "story": "s", "size": "1536x1024", "preamble": {},
            "spreads": [{"id": "spread-01", "scene": "A man on a porch at golden hour.",
                         "cast": [{"id": "russ"}]}]}


class TestUnit(unittest.TestCase):
    def test_an_entity_without_the_field_emits_nothing(self):
        self.assertIsNone(register_neutral_line({"structured": {}}, "russ"))

    def test_the_line_names_the_entity_and_the_medium(self):
        line = register_neutral_line({"id": "russ", "structured": {"registerNeutral": RN}},
                                     "russ")
        self.assertIn("REGISTER-NEUTRAL MASTER", line)
        self.assertIn(MEDIUM, line)
        self.assertIn("russ", line)


class TestInAssembledPrompt(unittest.TestCase):
    def test_a_declared_master_gets_the_drop_the_medium_instruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = build(_universe(tmp), _spec(), "spread-01")
            self.assertIn("REGISTER-NEUTRAL MASTER", out["prompt"])
            self.assertIn(MEDIUM, out["prompt"])
            self.assertIn("render russ fully in this image's declared style",
                          out["prompt"])

    def test_an_undeclared_entity_renders_byte_identically(self):
        """Backward compatibility as a test: the field is opt-in, so no existing
        universe's prompt moves by a character."""
        with tempfile.TemporaryDirectory() as tmp:
            before = build(_universe(tmp, neutral=False), _spec(), "spread-01")["prompt"]
        with tempfile.TemporaryDirectory() as tmp:
            after = build(_universe(tmp, neutral=True), _spec(), "spread-01")["prompt"]
        self.assertNotIn("REGISTER-NEUTRAL MASTER", before)
        self.assertIn("REGISTER-NEUTRAL MASTER", after)
        # The ONLY difference is the one added sentence, joined with the surrounding
        # blocks by a single space.
        line = register_neutral_line({"id": "russ", "structured": {"registerNeutral": RN}},
                                     "russ")
        self.assertEqual(before, after.replace(" " + line, ""))

    def test_it_composes_with_a_per_slot_role_rather_than_replacing_it(self):
        """Both halves reach the model: the role says what ONE plate contributes, the
        entity line says the whole set carries no register."""
        with tempfile.TemporaryDirectory() as tmp:
            out = build(_universe(tmp, role="identity"), _spec(), "spread-01")
            self.assertIn("REFERENCE ROLES, obey exactly:", out["prompt"])
            self.assertIn("REGISTER-NEUTRAL MASTER", out["prompt"])

    def test_a_malformed_declaration_refuses_the_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            p = root / "canon" / "entities" / "russ.json"
            e = json.loads(p.read_text())
            e["structured"]["registerNeutral"] = {"medium": MEDIUM}
            p.write_text(json.dumps(e))
            with self.assertRaises(Exception) as c:
                build(root, _spec(), "spread-01")
            self.assertIn("`why`", str(c.exception))


if __name__ == "__main__":
    unittest.main()
