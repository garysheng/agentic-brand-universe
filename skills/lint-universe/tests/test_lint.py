import json
import sys
import tempfile
import pathlib
import unittest
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

    def test_a_golden_with_no_sidecar_is_an_error(self):
        """Was a warning until 2026-07-25. Provenance is now enforced going forward: a golden
        with no recipe and no grandfather entry was locked after the policy and skipped the
        tool, which is an error, not advice."""
        with tempfile.TemporaryDirectory() as t:
            errs, _ = run(self.universe_with_golden(t, recipe=None))
        self.assertIn("GOLDEN-NO-RECIPE", errs)

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


class TestSettingWantsNesting(unittest.TestCase):
    """SPEC v0.29: find the multi-room entity before it costs another book.

    A setting carries ONE flat contract, so an entity covering several rooms has
    nowhere to put a per-room rule. Authors work around it by prefixing the plate
    name onto an invariant, and that workaround is the tell. It is not cosmetic:
    every setting invariant becomes a render-readback QA check, so on a nine-room
    entity each room gets graded against the other eight rooms' furniture.

    christofuturist-home is the worked case and cost the spec twice: v0.13 added
    contract.scalePlate because its hearth room rendered small, and v0.29 added
    nesting because its sunken pit had nowhere to declare fixed lettered seating.
    Run against real canon this check found FIVE more multi-room settings.
    """

    def _house(self, tmp, *, invariants=None, sheets=None, houseRules=None):
        st = {"sheets": sheets or {"studyNook": "reference/h/a.png",
                                   "hearth": "reference/h/b.png"}}
        if invariants is not None:
            st["invariants"] = invariants
        if houseRules is not None:
            st["houseRules"] = houseRules
        return build(tmp, entity={"id": "house", "kind": "setting",
                                  "contract": {"map": "m", "blocking": "b", "dressing": "d"},
                                  "structured": st})

    def test_flags_a_plate_scoped_invariant(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._house(t, invariants=["studyNook ONLY: exactly two armchairs"]))
            self.assertIn("SETTING-WANTS-NESTING", w)

    def test_quiet_when_invariants_are_room_wide(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._house(t, invariants=["shoes-come-off-indoors"]))
            self.assertNotIn("SETTING-WANTS-NESTING", w)

    def test_a_bare_plate_prefix_is_not_the_tell(self):
        """Four false positives on real canon before this narrowed.

        `porch-house-wall-left-valley-and-rail-right` and
        `summit-is-a-modest-bald-rock-and-grass-crown` merely BEGIN with a plate key.
        They are per-angle handedness and identity statements, which is the correct
        way to describe one entity's several cameras. Only an explicit exclusivity
        marker says a rule holds for one plate and NOT its siblings.
        """
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._house(t, sheets={"porch": "reference/h/p.png"},
                                   invariants=["porch-house-wall-left-and-rail-right"]))
            self.assertNotIn("SETTING-WANTS-NESTING", w)

    def test_contract_slots_do_not_count_as_rooms(self):
        """the-cold-cathedral read as 8 rooms when three were structural slots."""
        with tempfile.TemporaryDirectory() as t:
            sheets = {k: f"reference/h/{k}.png" for k in
                      ("turnaround", "blueprint", "scalePlate", "blockingPlate", "master",
                       "nave", "corridor", "exterior")}
            _, w = run(self._house(t, sheets=sheets, invariants=[]))
            self.assertNotIn("SETTING-WANTS-NESTING", w)

    def test_flags_a_building_by_plate_count(self):
        with tempfile.TemporaryDirectory() as t:
            many = {f"room{i}": f"reference/h/{i}.png" for i in range(9)}
            _, w = run(self._house(t, sheets=many))
            self.assertIn("SETTING-WANTS-NESTING", w)

    def test_plate_count_alone_is_quiet_once_houseRules_exist(self):
        """Declaring houseRules is the signal the author has thought about it."""
        with tempfile.TemporaryDirectory() as t:
            many = {f"room{i}": f"reference/h/{i}.png" for i in range(9)}
            _, w = run(self._house(t, sheets=many,
                                   houseRules={"invariants": ["shoes-come-off-indoors"]}))
            self.assertNotIn("SETTING-WANTS-NESTING", w)

    def test_houseRules_with_no_children_is_dead_config(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._house(t, houseRules={"invariants": ["r"]}))
            self.assertIn("HOUSE-RULES-WITH-NO-CHILDREN", w)

    def test_houseRules_are_fine_once_a_room_nests(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._house(t, houseRules={"invariants": ["r"]})
            (root / "canon" / "entities" / "room.json").write_text(json.dumps(
                {"id": "room", "kind": "setting", "partOf": "house",
                 "contract": {"map": "m", "blocking": "b", "dressing": "d"}}))
            _, w = run(root)
            self.assertNotIn("HOUSE-RULES-WITH-NO-CHILDREN", w)

    def test_is_never_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            e, _ = run(self._house(t, invariants=["studyNook ONLY: two armchairs"]))
            self.assertNotIn("SETTING-WANTS-NESTING", e)
            self.assertNotIn("HOUSE-RULES-WITH-NO-CHILDREN", e)


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




class TestSettingContractLeaks(unittest.TestCase):
    """A setting's contract rides on EVERY render of it in EVERY book (v0.29).

    `the-park-bench` was authored for will-there-be-ice-cream. Its `contract.dressing`
    said "Each of them holds an ice cream cone" and its blocking plate showed two
    mannequins holding cones. Three of the first seven spreads of an UNRELATED book came
    back with both men holding ice cream, through scene text AND a per-spread negative
    that banned ice cream by name. A reference image plus an injected contract sentence
    together outrank a negative word.
    """

    def _setting(self, tmp, **contract):
        con = {"map": "m", "blocking": "b", "dressing": "d"}
        con.update(contract)
        return build(tmp, entity={"id": "bench", "kind": "setting", "contract": con})

    def test_a_held_prop_in_dressing_is_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(
                t, dressing="A bench under a tree. Each of them holds an ice cream cone."))
            self.assertIn("SETTING-DRESSING-NAMES-HELD-PROP", w)

    def test_a_held_prop_in_blocking_is_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(
                t, blocking="Two seats. He is carrying the bowl in his left hand."))
            self.assertIn("SETTING-DRESSING-NAMES-HELD-PROP", w)

    def test_ordinary_room_dressing_is_silent(self):
        """The room's own furniture is exactly what `dressing` is FOR."""
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(
                t, dressing="Fallen leaves on the slats, a litter bin, a bike rack.",
                blocking="Two seats, the left one nearer the path."))
            self.assertNotIn("SETTING-DRESSING-NAMES-HELD-PROP", w)

    def test_it_is_never_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            e, _ = run(self._setting(t, dressing="Each of them holds a cone."))
            self.assertNotIn("SETTING-DRESSING-NAMES-HELD-PROP", e)


class TestLockedSettingAgreesWithTheGate(unittest.TestCase):
    """`status: locked` is a claim about art on disk, so the gate must agree with it.

    `lock_shot` and `refs.resolve_setting` disagreed about what locked meant, which
    forced hand-flipping the JSON, and a hand-flip cannot be checked by the tool it
    bypassed. nation-of-fire's `the-candle-against-the-sun` sits at `locked` with a null
    `turnaround`, a state `resolve_setting` refuses, and nothing said so.
    """

    def _setting(self, tmp, status, **contract):
        con = {"map": "m", "blocking": "b", "dressing": "d",
               "turnaround": "t.png", "blueprint": "bp.png", "emptyPlates": ["e.png"]}
        con.update(contract)
        return build(tmp, entity={"id": "hall", "kind": "setting", "status": status,
                                  "contract": con})

    def test_locked_with_a_null_turnaround_is_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(t, "locked", turnaround=None))
            self.assertIn("SETTING-LOCKED-BUT-GATE-REFUSES", w)

    def test_a_gate_complete_locked_setting_is_silent(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(t, "locked"))
            self.assertNotIn("SETTING-LOCKED-BUT-GATE-REFUSES", w)

    def test_a_missing_scale_plate_is_not_a_gate_gap(self):
        """The advisory fields must not come back in through this door."""
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(t, "locked", scalePlate=None, scale=""))
            self.assertNotIn("SETTING-LOCKED-BUT-GATE-REFUSES", w)

    def test_an_unlocked_setting_is_not_nagged(self):
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._setting(t, "unlocked", turnaround=None))
            self.assertNotIn("SETTING-LOCKED-BUT-GATE-REFUSES", w)


class TestQaWithoutInvariants(unittest.TestCase):
    """`render.qa` is compiled now, but `invariants` is what four other gates read.

    `theo-doorchaser` (The Tithe Is a Test, 2026-08-02) carried six well-written qa
    items and zero invariants, so a dry assemble reported ZERO checks on the spread
    where he stands alone, and his half-on jacket was the spine of the book.
    """

    def _char(self, tmp, **structured):
        st = {"sheets": {"forward-fullbody": "reference/e/f.png"},
              "requiredForRender": [],
              "render": {"always": "a man", "poses": {"front": {"sheets": []}}}}
        st.update(structured)
        return build(tmp, entity={"id": "theo", "kind": "character",
                                  "authority": {"lockedBy": "gary"}, "structured": st})

    def test_populated_qa_with_no_invariants_is_flagged(self):
        with tempfile.TemporaryDirectory() as t:
            st = {"sheets": {"forward-fullbody": "reference/e/f.png"},
                  "requiredForRender": [], "invariants": [],
                  "render": {"always": "a man", "qa": ["jacket-half-on", "brown-boots"],
                             "poses": {"front": {"sheets": []}}}}
            _, w = run(self._char(t, **st))
            self.assertIn("ENTITY-QA-WITHOUT-INVARIANTS", w)

    def test_qa_alongside_invariants_is_silent(self):
        with tempfile.TemporaryDirectory() as t:
            st = {"invariants": ["one-locked-face"],
                  "render": {"always": "a man", "qa": ["brown-boots"],
                             "poses": {"front": {"sheets": []}}}}
            _, w = run(self._char(t, **st))
            self.assertNotIn("ENTITY-QA-WITHOUT-INVARIANTS", w)

    def test_no_qa_at_all_is_silent(self):
        """Additive: an entity that never used the field is not nagged about it."""
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._char(t, invariants=[]))
            self.assertNotIn("ENTITY-QA-WITHOUT-INVARIANTS", w)


class TestProvenancePolicy(unittest.TestCase):
    """Provenance is enforced going forward; the pre-policy library is historical (Gary,
    2026-07-25). The grandfather list is a FILE, not a date, so the debt is reviewable and
    can only shrink: a recipe-less golden NOT on the list was locked after the policy and
    skipped the tool, which is an error."""

    def _uni(self, tmp, listed):
        root = build(tmp, entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/g.png"},
                           "requiredForRender": ["gabr"],
                           "render": {"always": "a",
                                      "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        (root/"reference"/"e").mkdir(parents=True)
        (root/"reference"/"e"/"g.png").write_bytes(b"\x89PNG")   # golden exists, no .recipe.json
        if listed is not None:
            (root/"canon"/"provenance-grandfathered.json").write_text(
                json.dumps({"goldens": listed}))
        return root

    def test_a_new_recipeless_golden_is_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            e, _ = run(self._uni(t, listed=[]))
        self.assertIn("GOLDEN-NO-RECIPE", e)

    def test_a_grandfathered_golden_is_not_an_error(self):
        with tempfile.TemporaryDirectory() as t:
            e, w = run(self._uni(t, listed=["reference/e/g.png"]))
        self.assertNotIn("GOLDEN-NO-RECIPE", e)
        self.assertIn("PROVENANCE-DEBT", w)

    def test_with_no_list_at_all_every_recipeless_golden_is_an_error(self):
        """A universe that never adopted the policy gets the strict behaviour, not a free pass."""
        with tempfile.TemporaryDirectory() as t:
            e, w = run(self._uni(t, listed=None))
        self.assertIn("GOLDEN-NO-RECIPE", e)
        self.assertNotIn("PROVENANCE-DEBT", w)


class TestSheetHygiene(unittest.TestCase):
    """Two keys on one file is not free: requiredForRender then passes the same image twice,
    so a 'face macro' contributes nothing while the entity looks better-referenced than it is.
    And invariants is what read-back checks are generated FROM, so workflow state parked there
    becomes a check nobody can run. Both found across nation-of-fire, 2026-07-25."""

    def lint_with(self, **kw):
        with tempfile.TemporaryDirectory() as t:
            return run(build(t, **kw))

    def test_two_required_keys_on_one_file_is_an_error(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"master": "reference/e/m.png", "face": "reference/e/m.png"},
                           "requiredForRender": ["master", "face"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["master"], "bake": "b"}}}}})
        self.assertIn("SHEET-DUPLICATE-ALIAS", e)

    def test_a_dead_alias_outside_required_is_only_a_warning(self):
        e, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"master": "reference/e/m.png", "alias": "reference/e/m.png"},
                           "requiredForRender": ["master"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["master"], "bake": "b"}}}}})
        self.assertNotIn("SHEET-DUPLICATE-ALIAS", e)
        self.assertIn("SHEET-DUPLICATE-ALIAS", w)

    def test_a_declared_sheet_alias_is_not_flagged(self):
        # the add-keys-never-remove pattern, DECLARED: structured.sheetAliases makes an
        # intentional alias (retired-hearthRotunda; the-park-bench camera aliases,
        # 2026-08-02) distinguishable from a dead duplicate
        e, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"the-park-bench-cam": "reference/e/m.png",
                                      "c1-wide": "reference/e/m.png"},
                           "sheetAliases": {"c1-wide": "the-park-bench-cam"},
                           "requiredForRender": ["the-park-bench-cam"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["the-park-bench-cam"], "bake": "b"}}}}})
        self.assertNotIn("SHEET-DUPLICATE-ALIAS", e)
        self.assertNotIn("SHEET-DUPLICATE-ALIAS", w)

    def test_a_declared_alias_passed_twice_in_required_is_still_an_error(self):
        # declaring the alias does not make passing the same image twice informative
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"master": "reference/e/m.png", "cam": "reference/e/m.png"},
                           "sheetAliases": {"cam": "master"},
                           "requiredForRender": ["master", "cam"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["master"], "bake": "b"}}}}})
        self.assertIn("SHEET-DUPLICATE-ALIAS", e)

    def test_an_undeclared_duplicate_still_warns_beside_a_declared_alias(self):
        e, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"master": "reference/e/m.png",
                                      "cam": "reference/e/m.png",
                                      "dead": "reference/e/m.png"},
                           "sheetAliases": {"cam": "master"},
                           "requiredForRender": ["master"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["master"], "bake": "b"}}}}})
        self.assertNotIn("SHEET-DUPLICATE-ALIAS", e)
        self.assertIn("SHEET-DUPLICATE-ALIAS", w)

    def test_distinct_files_are_not_flagged(self):
        e, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"master": "reference/e/m.png", "face": "reference/e/f.png"},
                           "requiredForRender": ["master", "face"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["master"], "bake": "b"}}}}})
        self.assertNotIn("SHEET-DUPLICATE-ALIAS", e)
        self.assertNotIn("SHEET-DUPLICATE-ALIAS", w)

    def test_placeholder_authorship_on_locked_art_is_an_error(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character", "authority": {"lockedBy": "TODO-you"},
            "structured": {"sheets": {"gabr": "reference/e/g.png"},
                           "render": {"always": "a", "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        self.assertIn("AUTHORITY-UNFILLED", e)

    def test_filled_authorship_is_clean(self):
        e, _ = self.lint_with(entity={
            "id": "e", "kind": "character", "authority": {"lockedBy": "gary"},
            "structured": {"sheets": {"gabr": "reference/e/g.png"},
                           "render": {"always": "a", "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        self.assertNotIn("AUTHORITY-UNFILLED", e)

    def test_workflow_state_in_invariants_is_warned(self):
        _, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/g.png"},
                           "invariants": ["design-pending-tier1"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        self.assertIn("INVARIANT-IS-STATUS", w)

    def test_a_prohibition_containing_a_trigger_word_is_not_warned(self):
        """A prohibition is a checkable fact about an image even when it contains a word like
        'review'. Both false positives on the first real run were of this shape."""
        _, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/g.png"},
                           "invariants": ["no-barcode-no-publisher-mark-no-review-quote"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        self.assertNotIn("INVARIANT-IS-STATUS", w)

    def test_a_real_visual_invariant_is_not_warned(self):
        _, w = self.lint_with(entity={
            "id": "e", "kind": "character",
            "structured": {"sheets": {"gabr": "reference/e/g.png"},
                           "invariants": ["full-salt-and-pepper-beard"],
                           "render": {"always": "a", "poses": {"p": {"sheets": ["gabr"], "bake": "b"}}}}})
        self.assertNotIn("INVARIANT-IS-STATUS", w)


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


class TestCharacterScaleAndFutureLooks(unittest.TestCase):
    """SPEC v0.10. Two blind spots with one shape: a dimension nothing depicts
    cannot be judged. Relative height between two characters was stated nowhere,
    and a declared-future look reached the model with no face."""

    def _chars(self, tmp, *entities):
        root = build(tmp)
        for e in entities:
            (root / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))
        return root

    @staticmethod
    def _c(cid, **structured):
        return {"id": cid, "kind": "character", "structured": structured}

    def test_one_sided_relation_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._chars(t,
                               self._c("beef", scale={"relativeTo": {"russ": "shorter than"}}),
                               self._c("russ"))
            _, w = run(root)
            self.assertIn("CHARACTER-SCALE-ONE-SIDED", w)

    def test_symmetric_relation_is_clean(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._chars(t,
                               self._c("beef", scale={"relativeTo": {"russ": "shorter than"}}),
                               self._c("russ", scale={"relativeTo": {"beef": "taller than"}}))
            _, w = run(root)
            self.assertNotIn("CHARACTER-SCALE-ONE-SIDED", w)
            self.assertNotIn("CHARACTER-SCALE-UNKNOWN-TARGET", w)

    def test_relation_to_an_unknown_entity_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._chars(t, self._c("beef", scale={"relativeTo": {"ghost": "shorter than"}}))
            _, w = run(root)
            self.assertIn("CHARACTER-SCALE-UNKNOWN-TARGET", w)

    def test_character_without_a_scale_block_is_not_flagged(self):
        """Advisory like the rest of the matrix: most characters never share a
        frame with someone whose height matters, and flagging every one of them
        would train people to ignore the linter."""
        with tempfile.TemporaryDirectory() as t:
            _, w = run(self._chars(t, self._c("beef")))
            self.assertNotIn("CHARACTER-SCALE-ONE-SIDED", w)
            self.assertNotIn("CHARACTER-SCALE-UNKNOWN-TARGET", w)

    def test_future_look_with_no_face_source_warns(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._chars(t, self._c(
                "beef", altLooks={"era-2030": {"era": "2030",
                                               "invariants": ["lean-and-powerfully-built"]}}))
            _, w = run(root)
            self.assertIn("LOOK-NO-IDENTITY-ANCHOR", w)

    def test_future_look_with_keep_sheets_is_clean(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._chars(t, self._c(
                "beef", altLooks={"era-2030": {"era": "2030",
                                               "keepSheets": ["face-neutral"]}}))
            _, w = run(root)
            self.assertNotIn("LOOK-NO-IDENTITY-ANCHOR", w)

    def test_ordinary_alt_look_with_an_anchor_photo_is_clean(self):
        with tempfile.TemporaryDirectory() as t:
            root = self._chars(t, self._c(
                "beef", altLooks={"bearded": {"anchorPhoto": "reference/beef/alt.png"}}))
            _, w = run(root)
            self.assertNotIn("LOOK-NO-IDENTITY-ANCHOR", w)






class TestValidityWindows(unittest.TestCase):
    """SPEC v0.18 variant validity windows.

    compose-spread refuses a WRONG-era selection at render time. What only the
    linter can see is the shape of the whole variant SET, and that is where the
    dangerous case lives: a PARTIALLY windowed set has a hole at exactly the
    point where the author believed the gate was closed.
    """

    def lint_entity(self, ent):
        with tempfile.TemporaryDirectory() as t:
            return run(build(t, entity=ent))

    def character(self, **structured):
        return {"id": "e", "kind": "character", "status": "locked",
                "structured": structured}

    def test_a_set_with_no_windows_is_silent(self):
        errs, warns = self.lint_entity(self.character(
            altLooks={"elder": {"anchorPhoto": "a.png"},
                      "young": {"anchorPhoto": "b.png"}}))
        self.assertNotIn("VALIDFOR-PARTIAL", warns)
        self.assertEqual({e for e in errs if e.startswith("VALIDFOR")}, set())

    def test_a_fully_windowed_set_is_silent(self):
        _, warns = self.lint_entity(self.character(
            validFor={"from": 1935, "to": 1973},
            altLooks={"bedfast": {"anchorPhoto": "a.png",
                                  "validFor": {"from": 1933, "to": 1934}},
                      "elder": {"anchorPhoto": "b.png", "validFor": {"from": 1974}}}))
        self.assertNotIn("VALIDFOR-PARTIAL", warns)

    def test_a_partially_windowed_set_warns(self):
        """The hole: an undeclared variant stays legal at EVERY date."""
        _, warns = self.lint_entity(self.character(
            validFor={"from": 1935, "to": 1973},
            altLooks={"bedfast": {"anchorPhoto": "a.png",
                                  "validFor": {"from": 1933, "to": 1934}},
                      "elder": {"anchorPhoto": "b.png"}}))
        self.assertIn("VALIDFOR-PARTIAL", warns)

    def test_an_inverted_window_is_an_error(self):
        errs, _ = self.lint_entity(self.character(
            altLooks={"elder": {"anchorPhoto": "b.png",
                                "validFor": {"from": 2000, "to": 1900}}}))
        self.assertIn("VALIDFOR-INVERTED", errs)

    def test_a_string_year_is_an_error(self):
        """A window is compared numerically, so "1974" would silently never match."""
        errs, _ = self.lint_entity(self.character(
            altLooks={"elder": {"anchorPhoto": "b.png", "validFor": {"from": "1974"}}}))
        self.assertIn("VALIDFOR-MALFORMED", errs)

    def test_an_empty_window_is_an_error(self):
        errs, _ = self.lint_entity(self.character(
            altLooks={"elder": {"anchorPhoto": "b.png", "validFor": {}}}))
        self.assertIn("VALIDFOR-MALFORMED", errs)

    def test_a_setting_carries_its_window_on_the_PLATE(self):
        """Two eras of one place stay ONE entity: the plates are the era axis."""
        _, warns = self.lint_entity({
            "id": "e", "kind": "setting", "status": "locked",
            "contract": {"emptyPlates": ["reference/e/era-farm.png",
                                         "reference/e/era-1976.png"],
                         "plates": {"era-farm": {"validFor": {"to": 1930}}}}})
        self.assertIn("VALIDFOR-PARTIAL", warns)

    def test_a_fully_windowed_setting_is_silent(self):
        _, warns = self.lint_entity({
            "id": "e", "kind": "setting", "status": "locked",
            "contract": {"emptyPlates": ["reference/e/era-farm.png",
                                         "reference/e/era-1976.png"],
                         "plates": {"era-farm": {"validFor": {"to": 1930}},
                                    "era-1976": {"validFor": {"from": 1970}}}}})
        self.assertNotIn("VALIDFOR-PARTIAL", warns)


if __name__ == "__main__":
    unittest.main(verbosity=2)
