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


def engine_spec_version():
    """The engine's own SPEC_VERSION, read from source, so a valid fixture pins the
    version the linter will accept without warning."""
    import re
    initf = HERE.parents[2] / "engine" / "agenticstory" / "__init__.py"
    return re.search(r'SPEC_VERSION\s*=\s*"([^"]+)"', initf.read_text()).group(1)


def build(tmp, *, projections=None, pack=True, anchor=True, entity=None):
    """Minimal valid universe, then break exactly what a test asks to break.

    A valid universe pins the current spec version. Tests that care about the pin
    (TestSpecPin) override it; everything else stays clean so an unrelated break is
    the only error a test sees."""
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
        "spec": {"version": engine_spec_version()},
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

    def test_a_fork_INHERITS_its_parents_generator(self):
        """The bug this locks: the linter checked the child's RAW fields, so a fork
        that inherited a generator instead of redeclaring one false-failed with
        SLOT-NO-GENERATOR. The field was absent from the file and present at run
        time, because the composer merges `extends` and the linter did not. The one
        prior fork overrode every field it used, which is why this went unseen until
        a fork that inherits."""
        errs, _ = self.lint_with(projections={
            "base": {"id": "base", "surface": {"geometry": {"w": 2, "h": 3}},
                     "slots": [OK_SLOT], "generators": [OK_GEN], "invariants": OK_INV},
            "fork": {"id": "fork", "extends": "base@1.0.0",
                     "description": "adds nothing but a name"}})
        self.assertNotIn("SLOT-NO-GENERATOR", errs)
        self.assertNotIn("INVARIANT-UNTYPED", errs)
        self.assertEqual(errs, set())

    def test_a_fork_is_still_checked_on_what_it_OVERRIDES(self):
        """Inheritance must not become a way to smuggle a defect past the linter."""
        errs, _ = self.lint_with(projections={
            "base": {"id": "base", "surface": {"geometry": {"w": 2, "h": 3}},
                     "slots": [OK_SLOT], "generators": [OK_GEN], "invariants": OK_INV},
            "fork": {"id": "fork", "extends": "base@1.0.0",
                     "invariants": {"perSlot": [{"id": "i", "check": "vibes"}],
                                    "crossSlot": []}}})
        self.assertIn("INVARIANT-UNTYPED", errs)

    def test_a_fork_that_adds_a_slot_its_parent_cannot_produce_still_errors(self):
        errs, _ = self.lint_with(projections={
            "base": {"id": "base", "surface": {"geometry": {"w": 2, "h": 3}},
                     "slots": [OK_SLOT], "generators": [OK_GEN], "invariants": OK_INV},
            "fork": {"id": "fork", "extends": "base@1.0.0",
                     "slots": [OK_SLOT, {"id": "orphan", "type": "generated",
                                         "geometry": {"w": 2, "h": 3}}]}})
        self.assertIn("SLOT-NO-GENERATOR", errs)

    def test_an_extends_cycle_is_reported_not_hung_on(self):
        """Two projections extending each other used to recurse forever. A linter
        that hangs is a linter nobody runs."""
        errs, _ = self.lint_with(projections={
            "a": {"id": "a", "extends": "b@1.0.0", "slots": [OK_SLOT],
                  "generators": [OK_GEN], "invariants": OK_INV},
            "b": {"id": "b", "extends": "a@1.0.0", "slots": [OK_SLOT],
                  "generators": [OK_GEN], "invariants": OK_INV}})
        self.assertIn("EXTENDS-UNRESOLVED", errs)

    def test_warns_when_an_invariant_collides_with_a_pinned_providers_quirk(self):
        """A contract can be internally coherent and, in practice, undeliverable.
        Feasibility caught that for geometry. This catches it for behaviour: a rule
        the pinned provider is registered as breaking. Earned after six artifacts
        failed the same item twice each, prompt counter included."""
        with tempfile.TemporaryDirectory() as t:
            root = build(t, projections={"p": {
                "id": "p", "surface": {"geometry": {"w": 2, "h": 3}},
                "slots": [OK_SLOT],
                "generators": [{**OK_GEN, "pin": "fakeprov"}],
                "invariants": {"perSlot": [
                    {"id": "hands have four fingers plus a thumb", "check": "judged"}],
                    "crossSlot": []}}})
            lint.E.clear(); lint.W.clear()
            real = lint.jload
            reg = {"providers": {"fakeprov": {"quirks": [
                {"id": "stylized-hands-lose-a-digit", "counter": "c", "check": "judged"}]}}}
            lint.jload = lambda f: reg if str(f).endswith("providers.json") else real(f)
            try:
                lint.lint(str(root))
            finally:
                lint.jload = real
            self.assertIn("INVARIANT-VS-QUIRK", {c for c, _ in lint.W})

    def test_it_is_a_warning_not_an_error(self):
        """A brand is allowed to demand something hard. A known quirk is a re-roll
        cost, not an impossibility. What it must not be is a surprise found after
        paying for generation."""
        with tempfile.TemporaryDirectory() as t:
            root = build(t, projections={"p": {
                "id": "p", "surface": {"geometry": {"w": 2, "h": 3}},
                "slots": [OK_SLOT], "generators": [{**OK_GEN, "pin": "fakeprov"}],
                "invariants": {"perSlot": [
                    {"id": "hands have four fingers plus a thumb", "check": "judged"}],
                    "crossSlot": []}}})
            lint.E.clear(); lint.W.clear()
            real = lint.jload
            reg = {"providers": {"fakeprov": {"quirks": [
                {"id": "stylized-hands-lose-a-digit", "counter": "c", "check": "judged"}]}}}
            lint.jload = lambda f: reg if str(f).endswith("providers.json") else real(f)
            try:
                lint.lint(str(root))
            finally:
                lint.jload = real
            self.assertNotIn("INVARIANT-VS-QUIRK", {c for c, _ in lint.E})

    def test_an_unpinned_generator_raises_no_collision_warning(self):
        """Quirks bind to the RESOLVED provider at run time, but a projection with no
        pin has no provider to check against statically. Guessing one would be noise."""
        errs, warns = self.lint_with(projections={"p": {
            "id": "p", "surface": {"geometry": {"w": 2, "h": 3}},
            "slots": [OK_SLOT], "generators": [OK_GEN],
            "invariants": {"perSlot": [
                {"id": "hands have four fingers plus a thumb", "check": "judged"}],
                "crossSlot": []}}})
        self.assertNotIn("INVARIANT-VS-QUIRK", warns)

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


class TestGoldenProvenance(unittest.TestCase):
    """A golden is Gary's approved answer of record. An approval that recorded only a
    path could not say what it was approved AGAINST, so the taste corpus was
    un-auditable. These checks make the `<golden>.recipe.json` sidecar load-bearing."""

    def universe_with_golden(self, tmp, *, recipe=None, input_bytes=b"anchor-v1"):
        """A universe with one character whose 'master' golden exists, optionally with a
        provenance sidecar recording one input at `input_bytes`."""
        root = build(tmp, projections={"p": {"id": "p", "slots": [OK_SLOT],
                                             "generators": [OK_GEN], "invariants": OK_INV}})
        (root / "reference" / "hero").mkdir(parents=True)
        (root / "reference" / "hero" / "master.png").write_bytes(b"golden")
        (root / "reference" / "hero" / "anchor.png").write_bytes(input_bytes)
        (root / "canon" / "entities" / "hero.json").write_text(json.dumps({
            "id": "hero", "kind": "character",
            "structured": {"sheets": {"master": "reference/hero/master.png"},
                           "requiredForRender": ["master"]}}))
        if recipe is not None:
            (root / "reference" / "hero" / "master.png.recipe.json").write_text(
                json.dumps(recipe))
        return root

    def test_a_golden_with_no_sidecar_warns(self):
        with tempfile.TemporaryDirectory() as t:
            _, warns = run(self.universe_with_golden(t, recipe=None))
        self.assertIn("GOLDEN-NO-RECIPE", warns)

    def test_a_golden_whose_input_is_unchanged_is_clean(self):
        import hashlib
        with tempfile.TemporaryDirectory() as t:
            h = hashlib.sha256(b"anchor-v1").hexdigest()[:16]
            recipe = {"inputs": [{"path": "reference/hero/anchor.png", "digest": h}]}
            _, warns = run(self.universe_with_golden(t, recipe=recipe))
        self.assertNotIn("GOLDEN-NO-RECIPE", warns)
        self.assertNotIn("GOLDEN-STALE", warns)

    def test_a_golden_whose_input_bytes_changed_is_stale(self):
        """The free half of the divergence loop: an approval made against inputs that
        have since changed, caught statically over the whole corpus."""
        with tempfile.TemporaryDirectory() as t:
            # sidecar records a digest that will NOT match anchor.png's real bytes
            recipe = {"inputs": [{"path": "reference/hero/anchor.png",
                                  "digest": "0000000000000000"}]}
            _, warns = run(self.universe_with_golden(t, recipe=recipe))
        self.assertIn("GOLDEN-STALE", warns)

    def test_a_golden_whose_input_vanished_is_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            recipe = {"inputs": [{"path": "reference/hero/deleted.png",
                                  "digest": "abcdef0123456789"}]}
            _, warns = run(self.universe_with_golden(t, recipe=recipe))
        self.assertIn("GOLDEN-INPUT-GONE", warns)

    def test_a_null_input_digest_is_not_treated_as_drift(self):
        """A recipe may record an input that was unresolved at approval (null digest).
        That is a fact about the approval, not a mismatch to re-flag every run."""
        with tempfile.TemporaryDirectory() as t:
            recipe = {"inputs": [{"path": "reference/hero/anchor.png", "digest": None}]}
            _, warns = run(self.universe_with_golden(t, recipe=recipe))
        self.assertNotIn("GOLDEN-STALE", warns)


class TestSpecPin(unittest.TestCase):
    """A universe.json that pins no spec, or pins a version the engine no longer
    implements, conforms to nothing anyone can check. On 2026-07-24 three surfaces gave
    three answers and every one was internally consistent, which is why nobody caught
    it. Consistency is not truth; this makes the pin verifiable."""

    def universe_with(self, tmp, spec):
        """A minimal valid universe whose spec block is set to `spec`, or removed
        entirely when `spec` is None."""
        root = build(tmp, projections={"p": {"id": "p", "slots": [OK_SLOT],
                                             "generators": [OK_GEN], "invariants": OK_INV}})
        uf = root / "universe.json"
        u = json.loads(uf.read_text())
        if spec is None:
            u.pop("spec", None)
        else:
            u["spec"] = spec
        uf.write_text(json.dumps(u))
        return root

    def test_no_pin_is_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            errs, _ = run(self.universe_with(t, None))
        self.assertIn("NO-SPEC-PIN", errs)

    def test_a_pin_behind_the_engine_warns(self):
        with tempfile.TemporaryDirectory() as t:
            _, warns = run(self.universe_with(t, {"version": "0.4.1"}))
        self.assertIn("SPEC-PIN-BEHIND", warns)

    def test_the_engine_version_does_not_warn(self):
        with tempfile.TemporaryDirectory() as t:
            _, warns = run(self.universe_with(t, {"version": engine_spec_version()}))
        self.assertNotIn("SPEC-PIN-BEHIND", warns)


class TestCraftMembership(unittest.TestCase):
    """A story's declared spine/genre must be a registered craft-canon record, so 'where are
    this universe's story types?' is answerable by data and a typo/prose value fails loudly.
    The check is a WARNING (a universe mid-normalization still validates)."""

    def _uni(self, tmp, *, craft, story):
        root = build(tmp)  # a minimal valid universe
        cdir = root / "canon" / "craft"; cdir.mkdir(parents=True, exist_ok=True)
        for c in craft:
            (cdir / f"{c['id']}.json").write_text(json.dumps({**c, "rules": "r"}))
        sdir = root / "stories"; sdir.mkdir(exist_ok=True)
        (sdir / f"{story['id']}.json").write_text(json.dumps(story))
        return root

    def test_registered_spine_and_genre_are_clean(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._uni(t,
                craft=[{"id": "obedient-servant", "kind": "spine"},
                       {"id": "expectant-biography", "kind": "genre"}],
                story={"id": "s", "spine": "obedient-servant", "genre": "expectant-biography"})
            _, warns = run(root)
        self.assertNotIn("STORY-SPINE-UNREGISTERED", warns)
        self.assertNotIn("STORY-GENRE-UNREGISTERED", warns)

    def test_unregistered_spine_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._uni(t,
                craft=[{"id": "obedient-servant", "kind": "spine"}],
                story={"id": "s", "spine": "thesis-testimony"})  # a typo/compound, unregistered
            _, warns = run(root)
        self.assertIn("STORY-SPINE-UNREGISTERED", warns)

    def test_unregistered_genre_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._uni(t,
                craft=[{"id": "obedient-servant", "kind": "spine"},
                       {"id": "expectant-biography", "kind": "genre"}],
                story={"id": "s", "spine": "obedient-servant",
                       "genre": "testimony (Jerry-voiced, prose not a key)"})
            _, warns = run(root)
        self.assertIn("STORY-GENRE-UNREGISTERED", warns)

    def test_null_genre_is_exempt(self):
        # genre is optional: a story may declare none. Only a NON-NULL unregistered value warns.
        with tempfile.TemporaryDirectory() as t:
            root = self._uni(t,
                craft=[{"id": "obedient-servant", "kind": "spine"}],
                story={"id": "s", "spine": "obedient-servant", "genre": None})
            _, warns = run(root)
        self.assertNotIn("STORY-GENRE-UNREGISTERED", warns)


class TestGoldenRecipeInputs(unittest.TestCase):
    """A golden recipe's `inputs` may be bare path strings (older lock-shot) or {path,digest}
    dicts. A bare string once crashed the whole linter; it must be skipped, not fatal."""

    def test_string_inputs_do_not_crash_the_linter(self):
        with tempfile.TemporaryDirectory() as t:
            root = build(t)
            ent = root / "canon" / "entities" / "c.json"
            (root / "reference").mkdir(exist_ok=True)
            (root / "reference" / "hero.png").write_bytes(b"\x89PNG")
            (root / "reference" / "hero.png.recipe.json").write_text(
                json.dumps({"inputs": ["reference/some-bare-string.png"]}))  # bare string, no digest
            ent.write_text(json.dumps({
                "id": "c", "kind": "character",
                "structured": {"sheets": {"hero": "reference/hero.png"},
                               "requiredForRender": ["hero"]}}))
            errs, _ = run(root)  # must not raise
        self.assertNotIn("PARSE", errs)


class TestSettingScale(unittest.TestCase):
    """SPEC v0.9: a setting must be able to prove its own SIZE.

    emptyPlates are people-free so a reference never bakes a face into a room. The
    unpriced cost is that a figure-free interior has no unit of comparison, so the
    model picks a size and every render inherits the guess. These checks make the
    gap visible before it is expensive. WARNINGS, never errors: a setting with no
    scale plate still locks and still renders.
    """

    def _setting(self, tmp, **contract):
        con = {"map": "m", "blocking": "b", "dressing": "d"}
        con.update(contract)
        return build(tmp, entity={"id": "hall", "kind": "setting", "contract": con})

    def test_warns_when_no_scale_plate(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(t))
            self.assertIn("SETTING-NO-SCALE-PLATE", w)

    def test_warns_when_no_scale_descriptor(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(t))
            self.assertIn("SETTING-NO-SCALE-DESCRIPTOR", w)

    def test_clean_when_both_present(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setting(t, scalePlate="reference/hall/scale.png",
                                 scale="a circular hall about 80 feet across")
            (root / "reference" / "hall").mkdir(parents=True, exist_ok=True)
            (root / "reference" / "hall" / "scale.png").write_bytes(b"\x89PNG")
            _, w = run(root)
            self.assertNotIn("SETTING-NO-SCALE-PLATE", w)
            self.assertNotIn("SETTING-NO-SCALE-DESCRIPTOR", w)

    def test_warns_when_scale_plate_declared_but_missing_on_disk(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._setting(t, scalePlate="reference/hall/nope.png", scale="big")
            _, w = run(root)
            self.assertIn("SETTING-NO-SCALE-PLATE", w)

    def test_is_never_an_error(self):
        """A universe mid-normalization must still compose."""
        with tempfile.TemporaryDirectory() as t:
            e, _ = run(self._setting(t))
            self.assertNotIn("SETTING-NO-SCALE-PLATE", e)
            self.assertNotIn("SETTING-NO-SCALE-DESCRIPTOR", e)

    def test_only_applies_to_settings(self):
        """A character has no contract; it must not be nagged about scale."""
        with tempfile.TemporaryDirectory() as t:
            root = build(t, entity={"id": "c", "kind": "character",
                                    "structured": {"sheets": {}, "requiredForRender": []}})
            _, w = run(root)
            self.assertNotIn("SETTING-NO-SCALE-PLATE", w)




class TestCastability(unittest.TestCase):
    """An entity can be locked, art-approved, pass validate AND pass assert-story and
    still be impossible to put in a picture, because the render compiler reads
    structured.render while every gate reads sheets and files. It surfaced as a hard
    KeyError at cast time, after the story was written. Hit at least three times in
    nation-of-fire; these tests make it static and free."""

    def lint_with(self, **kw):
        with tempfile.TemporaryDirectory() as t:
            return run(build(t, **kw))

    def test_catches_a_character_with_no_render_block(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/gabr.png"}}})
        self.assertIn("CAST-UNRENDERABLE", e)

    def test_catches_a_character_with_always_but_no_poses(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/gabr.png"},
                           "render": {"always": "a description"}}})
        self.assertIn("CAST-NO-POSES", e)

    def test_catches_a_pose_written_as_a_bare_string(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/gabr.png"},
                           "render": {"always": "a", "poses": {"p": "just prose"}}}})
        self.assertIn("CAST-POSE-SHAPE", e)

    def test_catches_a_pose_naming_a_sheet_key_that_does_not_exist(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/gabr.png"},
                           "render": {"always": "a",
                                      "poses": {"p": {"sheets": ["suitNoTie"], "bake": "b"}}}}})
        self.assertIn("CAST-POSE-SHEET-MISSING", e)

    def test_a_castable_character_passes(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/gabr.png"},
                           "render": {"always": "a",
                                      "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        for code in ("CAST-UNRENDERABLE", "CAST-NO-POSES", "CAST-POSE-SHAPE",
                     "CAST-POSE-SHEET-MISSING"):
            self.assertNotIn(code, e)

    def test_an_entity_with_an_empty_sheets_dict_is_not_flagged(self):
        """`{}` means the same thing as no sheets key: no art yet, so no poses are owed.
        Checking only for None flagged a doctrine-only group that has no art and wants none."""
        e, _ = self.lint_with(entity={"id": "e", "kind": "group",
                                      "structured": {"sheets": {}, "requiredForRender": []}})
        self.assertNotIn("CAST-UNRENDERABLE", e)

    def test_an_unscaffolded_entity_is_not_flagged(self):
        """Before the art step an entity has no sheets at all; flagging it would fire on
        every freshly scaffolded character and train people to ignore the linter."""
        e, _ = self.lint_with(entity={"id": "e", "kind": "character", "structured": {}})
        self.assertNotIn("CAST-UNRENDERABLE", e)


if __name__ == "__main__":
    unittest.main(verbosity=2)
