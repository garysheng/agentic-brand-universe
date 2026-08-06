#!/usr/bin/env python3
"""Lint's two register-neutral behaviours (SPEC v0.37 §12).

1. `REGISTER-UNLOCKED` STAYS AN ERROR and only its wording changed. A null
   `identity.register.anchor` still means every RENDER refuses (compose-spread and the
   cover compiler both require it), so a universe in this state genuinely cannot make a
   spread, a cover or a book. Downgrading it so a bootstrapping universe could go green
   would weaken a check that is telling the truth. What was false was the totalizing
   word "generation": a declared register-neutral matrix may now be shot, so the finding
   names those entities instead of dead-ending the operator.

2. `REGISTER-NEUTRAL-UNTYPED-SLOT` is a new WARNING. A register-neutral plate is passed
   into renders whose medium it does not share, and an untyped slot emits no per-ref
   instruction at all, so it is the loudest unlabelled reference in the request.
"""
import importlib.util, json, pathlib, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lint_rn", HERE.parent / "scripts" / "lint.py")
lint = importlib.util.module_from_spec(spec); spec.loader.exec_module(lint)

RN = {"medium": "hyper-realistic documentary photography",
      "why": "one photoreal master; every register is a conversion of it"}


def engine_spec_version():
    import re
    initf = HERE.parents[2] / "engine" / "agenticstory" / "__init__.py"
    return re.search(r'SPEC_VERSION\s*=\s*"([^"]+)"', initf.read_text()).group(1)


def build(tmp, *, anchor=False, neutral=True, role=None):
    root = pathlib.Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "reference" / "register").mkdir(parents=True)
    (root / "reference" / "register" / "anchor.png").write_bytes(b"\x89PNG")
    (root / "reference" / "russ").mkdir(parents=True)
    (root / "reference" / "russ" / "face-neutral.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "spec": {"version": engine_spec_version()},
        "identity": {"register": {
            "id": "r",
            "anchor": "reference/register/anchor.png" if anchor else None}}}))
    sheet = "reference/russ/face-neutral.png"
    st = {"sheets": {"face-neutral": ({"path": sheet, "role": role} if role else sheet)},
          "requiredForRender": ["face-neutral"],
          "render": {"always": "a man"}}
    if neutral:
        st["registerNeutral"] = RN
    (root / "canon" / "entities" / "russ.json").write_text(json.dumps({
        "id": "russ", "kind": "character", "name": "Russ",
        "authority": {"lockedBy": "gary"}, "structured": st}))
    return root


def run(root):
    lint.E.clear(); lint.W.clear()
    lint.lint(str(root))
    return ({c: m for c, m in lint.E}, {c: m for c, m in lint.W})


class TestRegisterUnlocked(unittest.TestCase):
    def test_it_is_still_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            errs, _ = run(build(t))
        self.assertIn("REGISTER-UNLOCKED", errs,
                      "renders genuinely still refuse; this must not be weakened")

    def test_it_names_the_entities_that_may_be_shot_now(self):
        with tempfile.TemporaryDirectory() as t:
            errs, _ = run(build(t))
        self.assertIn("russ", errs["REGISTER-UNLOCKED"])
        self.assertIn("REGISTER-NEUTRAL", errs["REGISTER-UNLOCKED"])

    def test_with_no_neutral_entity_it_still_teaches_the_route(self):
        with tempfile.TemporaryDirectory() as t:
            errs, _ = run(build(t, neutral=False))
        self.assertIn("structured.registerNeutral", errs["REGISTER-UNLOCKED"])

    def test_a_locked_register_raises_nothing(self):
        with tempfile.TemporaryDirectory() as t:
            errs, _ = run(build(t, anchor=True))
        self.assertNotIn("REGISTER-UNLOCKED", errs)


class TestUntypedSlot(unittest.TestCase):
    def test_an_untyped_slot_on_a_neutral_entity_warns(self):
        with tempfile.TemporaryDirectory() as t:
            errs, warns = run(build(t, anchor=True))
        self.assertIn("REGISTER-NEUTRAL-UNTYPED-SLOT", warns)
        self.assertIn("face-neutral", warns["REGISTER-NEUTRAL-UNTYPED-SLOT"])
        self.assertNotIn("REGISTER-NEUTRAL-UNTYPED-SLOT", errs,
                         "the entity-level line is already in force; this is depth")

    def test_a_typed_slot_does_not_warn(self):
        with tempfile.TemporaryDirectory() as t:
            _, warns = run(build(t, anchor=True, role="identity"))
        self.assertNotIn("REGISTER-NEUTRAL-UNTYPED-SLOT", warns)

    def test_an_ordinary_entity_never_warns(self):
        with tempfile.TemporaryDirectory() as t:
            _, warns = run(build(t, anchor=True, neutral=False))
        self.assertNotIn("REGISTER-NEUTRAL-UNTYPED-SLOT", warns)


if __name__ == "__main__":
    unittest.main()
