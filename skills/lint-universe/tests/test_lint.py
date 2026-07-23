#!/usr/bin/env python3
"""Tests for the brand universe linter.

Every test builds a universe that is BROKEN IN ONE SPECIFIC WAY and asserts the
linter catches that exact error code. A linter that misses a defect is worse than
no linter, because it converts an unchecked repo into a falsely confident one.

Each case corresponds to a failure that actually shipped.
"""
import importlib.util, json, pathlib, shutil, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lint", HERE.parent / "scripts" / "lint.py")
lint = importlib.util.module_from_spec(spec); spec.loader.exec_module(lint)


def build(tmp, *, projections=None, pack=True, anchor=True, entity=None):
    """Minimal valid universe, then break exactly what a test asks to break."""
    root = pathlib.Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "projections").mkdir()
    pk = root / "reference" / "style" / "p"
    (pk / "refs").mkdir(parents=True)
    for n in ("a", "b", "c"):
        (pk / "refs" / f"{n}.png").write_bytes(b"\x89PNG")
    if pack:
        (pk / "pack.json").write_text(json.dumps({
            "id": "p", "anchor": "refs/a.png",
            "refs": ["refs/a.png", "refs/b.png", "refs/c.png"],
            "styleLine": "a style", "gate": ["a rule"]}))
    (root / "reference" / "register").mkdir(parents=True, exist_ok=True)
    (root / "reference" / "register" / "anchor.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "identity": {"register": {"id": "r",
                                  "anchor": "reference/register/anchor.png" if anchor else None}}}))
    if entity:
        (root / "canon" / "entities" / "e.json").write_text(json.dumps(entity))
    for name, p in (projections or {}).items():
        (root / "projections" / f"{name}.json").write_text(json.dumps(p))
    return root


def run(root):
    lint.E.clear(); lint.W.clear()
    lint.lint(str(root))
    return {c for c, _ in lint.E}, {c for c, _ in lint.W}


OK_SLOT = {"id": "s", "type": "generated", "geometry": {"w": 2, "h": 3}}
OK_GEN = {"for": "s", "capability": "image", "producibleAspects": [0.667], "tolerance": 0.25}
OK_INV = {"perSlot": [{"id": "i", "check": "computed"}], "crossSlot": []}


class TestLinter(unittest.TestCase):
    def lint_with(self, **kw):
        with tempfile.TemporaryDirectory() as t:
            return run(build(t, **kw))

    def test_clean_universe_has_no_errors(self):
        errs, _ = self.lint_with(projections={"good": {
            "id": "good", "slots": [OK_SLOT], "generators": [OK_GEN], "invariants": OK_INV}})
        self.assertEqual(errs, set(), f"a valid universe must not error, got {errs}")

    def test_catches_deterministic_slot_with_no_emitter(self):
        """Finding 1: a deterministic slot naming no producer is unspecified."""
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "slots": [{"id": "s", "type": "deterministic"}],
            "generators": [], "invariants": OK_INV}})
        self.assertIn("SLOT-NO-EMITTER", errs)

    def test_catches_unknown_emitter(self):
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "slots": [{"id": "s", "type": "deterministic", "emitter": "x:nope"}],
            "generators": [], "invariants": OK_INV}})
        self.assertIn("EMITTER-UNKNOWN", errs)

    def test_catches_infeasible_surface(self):
        """Finding 2: the 0.333 class. Coherent contract, no model can make it."""
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "slots": [{"id": "s", "type": "generated", "geometry": {"w": 1, "h": 3}}],
            "generators": [{"for": "s", "capability": "image",
                            "producibleAspects": [1.0, 0.667, 1.5], "tolerance": 0.25}],
            "invariants": OK_INV}})
        self.assertIn("SURFACE-INFEASIBLE", errs)

    def test_feasible_surface_does_not_error(self):
        """Guards the inverse: the check must not fire on a deliverable surface."""
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "slots": [OK_SLOT], "generators": [OK_GEN], "invariants": OK_INV}})
        self.assertNotIn("SURFACE-INFEASIBLE", errs)

    def test_catches_generated_slot_with_no_generator(self):
        """The bug the linter found on its own first run, silently parking every cover."""
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "slots": [OK_SLOT], "generators": [], "invariants": OK_INV}})
        self.assertIn("SLOT-NO-GENERATOR", errs)

    def test_does_not_demand_an_aspect_from_a_text_or_audio_slot(self):
        """Aspect is a visual property. Warning on prose or audio is a false
        positive, and false positives train people to ignore the linter."""
        _, warns = self.lint_with(projections={"p": {
            "id": "p",
            "slots": [{"id": "chapter", "type": "generated"},
                      {"id": "narration", "type": "generated"}],
            "generators": [{"for": "chapter", "capability": "text"},
                           {"for": "narration", "capability": "audio"}],
            "invariants": OK_INV}})
        self.assertNotIn("NO-PRODUCIBLE-ASPECTS", warns)

    def test_still_warns_when_an_IMAGE_slot_lacks_aspects(self):
        _, warns = self.lint_with(projections={"p": {
            "id": "p", "slots": [{"id": "art", "type": "generated"}],
            "generators": [{"for": "art", "capability": "image"}],
            "invariants": OK_INV}})
        self.assertIn("NO-PRODUCIBLE-ASPECTS", warns)

    def test_catches_untyped_invariant(self):
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "slots": [OK_SLOT], "generators": [OK_GEN],
            "invariants": {"perSlot": [{"id": "i", "check": "vibes"}], "crossSlot": []}}})
        self.assertIn("INVARIANT-UNTYPED", errs)

    def test_catches_unresolved_extends(self):
        errs, _ = self.lint_with(projections={"p": {
            "id": "p", "extends": "ghost@1.0.0", "slots": [OK_SLOT],
            "generators": [OK_GEN], "invariants": OK_INV}})
        self.assertIn("EXTENDS-UNRESOLVED", errs)

    def test_catches_null_register_anchor(self):
        """A null anchor means the style is not locked; generation should refuse."""
        errs, _ = self.lint_with(anchor=False, projections={"p": {
            "id": "p", "slots": [OK_SLOT], "generators": [OK_GEN], "invariants": OK_INV}})
        self.assertIn("REGISTER-UNLOCKED", errs)

    def test_catches_missing_golden(self):
        """A required sheet that does not resolve is a crash waiting for render time."""
        errs, _ = self.lint_with(
            entity={"id": "e", "kind": "character",
                    "structured": {"requiredForRender": ["master"],
                                   "sheets": {"master": "reference/e/gone.png"}}},
            projections={"p": {"id": "p", "slots": [OK_SLOT],
                               "generators": [OK_GEN], "invariants": OK_INV}})
        self.assertIn("GOLDEN-MISSING", errs)

    def test_warns_on_thin_pack_but_does_not_error(self):
        with tempfile.TemporaryDirectory() as t:
            root = build(t, projections={"p": {"id": "p", "slots": [OK_SLOT],
                                               "generators": [OK_GEN], "invariants": OK_INV}})
            pk = root / "reference" / "style" / "p" / "pack.json"
            d = json.loads(pk.read_text()); d["refs"] = ["refs/a.png"]; pk.write_text(json.dumps(d))
            errs, warns = run(root)
        self.assertIn("PACK-THIN", warns)
        self.assertEqual(errs, set(), "a thin pack is a warning, never an error")

    def test_catches_pack_with_no_gate(self):
        """A pack without a gate is a mood board."""
        with tempfile.TemporaryDirectory() as t:
            root = build(t, projections={"p": {"id": "p", "slots": [OK_SLOT],
                                               "generators": [OK_GEN], "invariants": OK_INV}})
            pk = root / "reference" / "style" / "p" / "pack.json"
            d = json.loads(pk.read_text()); del d["gate"]; pk.write_text(json.dumps(d))
            errs, _ = run(root)
        self.assertIn("PACK-NO-GATE", errs)

    def test_exit_code_is_2_on_error_1_on_warn_0_on_clean(self):
        with tempfile.TemporaryDirectory() as t:
            root = build(t, projections={"p": {"id": "p", "slots": [OK_SLOT],
                                               "generators": [OK_GEN], "invariants": OK_INV}})
            sys.argv = ["lint", str(root)]
            self.assertIn(lint.main(), (0, 1), "clean or warn-only must not exit 2")


if __name__ == "__main__":
    unittest.main(verbosity=2)
