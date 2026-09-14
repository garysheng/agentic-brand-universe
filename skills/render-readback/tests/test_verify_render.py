"""verify_render — the readback that used to be two pasted one-liners.

Every check here corresponds to a silent failure that reached a human's eyes: a bypassed
binding (four times), a pure-black frame (twice), and a "binding test" whose scene text
named the garment, which proves nothing at all.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE.parent / "scripts" / "verify_render.py"
_spec = importlib.util.spec_from_file_location("verify_render", _SCRIPT)
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)


def png(path: Path, *, black=False):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), (0, 0, 0) if black else (200, 180, 160)).save(path)
    return str(path)


def recipe(path: Path, *, entities=None, prompt=None, guards=None, gate=None):
    if prompt is None:
        prompt = ("A scene. These are LOCKED canonical traits: a gold visor."
                  if entities else "A scene with nobody in it.")
    body = {"prompt": prompt}
    if entities is not None:
        body["entities"] = entities
    if guards is not None:
        body["guards"] = guards
        body["guardGate"] = gate if gate is not None else [
            f"{g.upper()}: look at it. If it is wrong: DEFECT." for g in guards]
    Path(str(path) + ".recipe.json").write_text(json.dumps(body))


def ent(eid, look=None, sheets=2, photos=0):
    return {"id": eid, "look": look,
            "sheets": {f"s{i}": f"{i}.png" for i in range(sheets)},
            "photoStackDeclared": [], "photoStackPassed": ["p.png"] * photos}


class VerifyRender(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="abu-vr-"))
        self.addCleanup(shutil.rmtree, self.d, True)

    def run_it(self, *args):
        """Returns (exit_code, stderr_text)."""
        import io
        from contextlib import redirect_stderr, redirect_stdout
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            code = vr.main(list(args))
        return code, err.getvalue()

    def good(self, name="a.png", **kw):
        p = Path(png(self.d / name))
        recipe(p, entities=[ent("selah", "wedding-dress")], **kw)
        return str(p)

    # --- the happy path must actually pass, or the gate gets disabled ------
    def test_a_correct_render_passes(self):
        code, _ = self.run_it(self.good())
        self.assertEqual(code, 0)

    def test_several_files_at_once(self):
        code, _ = self.run_it(self.good("a.png"), self.good("b.png"))
        self.assertEqual(code, 0)

    # --- recipe --------------------------------------------------------
    def test_a_missing_recipe_fails_and_names_the_cause(self):
        p = png(self.d / "orphan.png")
        code, err = self.run_it(p)
        self.assertEqual(code, 1)
        self.assertIn("NO RECIPE", err)
        self.assertIn("Never call a provider directly", err)

    def test_a_missing_file_fails(self):
        code, err = self.run_it(str(self.d / "nope.png"))
        self.assertEqual(code, 1)
        self.assertIn("NOT ON DISK", err)

    # --- invariants ----------------------------------------------------
    def test_entities_without_the_invariant_block_fail(self):
        """The signature of a hand-assembled prompt: it looks fine and is off-canon."""
        p = Path(png(self.d / "a.png"))
        recipe(p, entities=[ent("selah")], prompt="A scene, hand written, no canon.")
        code, err = self.run_it(str(p))
        self.assertEqual(code, 1)
        self.assertIn("invariant block is MISSING", err)

    def test_no_entities_means_the_invariant_check_does_not_apply(self):
        """A render with no people in it is not required to carry an entity block."""
        p = Path(png(self.d / "a.png"))
        recipe(p, entities=[], prompt="An empty room.")
        self.assertEqual(self.run_it(str(p))[0], 0)

    # --- binding -------------------------------------------------------
    def test_expecting_a_look_that_is_bound_passes(self):
        code, _ = self.run_it(self.good(), "--expect", "selah@wedding-dress")
        self.assertEqual(code, 0)

    def test_a_BARE_entity_does_not_satisfy_an_expected_LOOK(self):
        """THE FOUR-TIME BUG. `--entity selah` where `selah@wedding-dress` was meant is
        silent, and produced a fitted trumpet where an A-line was blessed. Matching on the
        id alone would let exactly that through."""
        p = Path(png(self.d / "a.png"))
        recipe(p, entities=[ent("selah", None)])
        code, err = self.run_it(str(p), "--expect", "selah@wedding-dress")
        self.assertEqual(code, 1)
        self.assertIn("expected entity 'selah@wedding-dress'", err)

    def test_the_wrong_look_fails(self):
        code, err = self.run_it(self.good(), "--expect", "selah@usa-flag-dress")
        self.assertEqual(code, 1)
        self.assertIn("usa-flag-dress", err)

    def test_a_missing_second_entity_fails(self):
        code, err = self.run_it(self.good(), "--expect", "selah@wedding-dress",
                                "--expect", "gary@wedding-suit")
        self.assertEqual(code, 1)
        self.assertIn("gary@wedding-suit", err)

    # --- dead frame ----------------------------------------------------
    def test_a_pure_black_render_fails(self):
        p = Path(png(self.d / "dead.png", black=True))
        recipe(p, entities=[ent("selah")])
        code, err = self.run_it(str(p))
        self.assertEqual(code, 1)
        self.assertIn("DEAD FRAME", err)

    def test_a_dead_frame_is_caught_even_with_no_recipe(self):
        """It is a fact about the image and does not depend on provenance."""
        code, err = self.run_it(png(self.d / "dead.png", black=True))
        self.assertEqual(code, 1)
        self.assertIn("DEAD FRAME", err)
        self.assertIn("NO RECIPE", err)

    # --- the binding test ----------------------------------------------
    def test_a_scene_naming_a_garment_fails(self):
        code, err = self.run_it(self.good(), "--scene",
                                "She stands on the steps in an ivory lace gown, laughing.")
        self.assertEqual(code, 1)
        self.assertIn("cannot prove the look is BOUND", err)
        for w in ("gown", "lace"):
            self.assertIn(w, err)

    def test_a_clean_scene_passes(self):
        code, _ = self.run_it(self.good(), "--scene",
                              "She stands at the top of a sunlit stone staircase, laughing.")
        self.assertEqual(code, 0)

    def test_forbid_overrides_the_default_vocabulary(self):
        """Only the caller knows this look's hero words, so the list must be replaceable."""
        code, err = self.run_it(self.good(), "--scene", "A quiet room with a cummerbund.",
                                "--forbid", "cummerbund,capelet")
        self.assertEqual(code, 1)
        self.assertIn("cummerbund", err)

    def test_the_scene_check_is_case_insensitive(self):
        code, err = self.run_it(self.good(), "--scene", "She wears a GOWN.")
        self.assertEqual(code, 1)
        self.assertIn("gown", err)

    def test_the_scene_is_reported_once_not_once_per_file(self):
        """A batch shares one scene; reporting it N times buries the other problems."""
        code, err = self.run_it(self.good("a.png"), self.good("b.png"),
                                "--scene", "in a lace gown")
        self.assertEqual(code, 1)
        self.assertEqual(err.count("cannot prove the look is BOUND"), 1)


class GuardGateIsJudged(unittest.TestCase):
    """An unjudged gate and a passed gate used to look identical (v0.49).

    v0.47 put the read-back assertion in the recipe so a reader would be TOLD to look at
    the thing that shipped wrong on the appliedai hero. Nothing then checked that anyone
    looked, which is the same defect one level up: a prompt guard is an instruction and
    loses some of the time, and so is "evaluate every guardGate entry".
    """

    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="abu-vrg-"))
        self.addCleanup(shutil.rmtree, self.d, True)

    def run_it(self, *args):
        import io
        from contextlib import redirect_stderr, redirect_stdout
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            code = vr.main(list(args))
        return code, err.getvalue(), out.getvalue()

    def guarded(self, name="a.png", guards=("device-anatomy",)):
        p = Path(png(self.d / name))
        recipe(p, entities=[ent("selah")], guards=list(guards),
               prompt="A scene. These are LOCKED canonical traits: a gold visor.")
        return str(p)

    def test_a_fired_guard_with_no_verdict_FAILS(self):
        code, err, _ = self.run_it(self.guarded())
        self.assertEqual(code, 1)
        self.assertIn("device-anatomy", err)
        self.assertIn("no recorded verdict", err)

    def test_the_failure_prints_the_ASSERTION_so_the_reader_knows_where_to_look(self):
        """The appliedai hero's exact miss: nothing told the reader to look."""
        code, err, _ = self.run_it(self.guarded())
        self.assertIn("DEVICE-ANATOMY:", err)
        self.assertIn("--guard device-anatomy=pass", err)

    def test_a_render_that_tripped_no_guard_is_unaffected(self):
        p = Path(png(self.d / "clean.png"))
        recipe(p, entities=[ent("selah")])
        code, _, _ = self.run_it(str(p))
        self.assertEqual(code, 0)

    def test_recording_a_pass_lets_it_through(self):
        p = self.guarded()
        self.assertEqual(self.run_it(p, "--guard", "device-anatomy=pass")[0], 0)
        self.assertEqual(self.run_it(p)[0], 0, "the verdict must persist beside the image")

    def test_a_recorded_DEFECT_is_a_failure_not_a_note(self):
        p = self.guarded()
        code, err, _ = self.run_it(p, "--guard", 'device-anatomy=defect:"screen toward camera"')
        self.assertEqual(code, 1)
        self.assertIn("FROM SCRATCH", err)

    def test_a_waiver_needs_a_written_reason(self):
        p = self.guarded()
        code, err, _ = self.run_it(p, "--guard", "device-anatomy=waived")
        self.assertEqual(code, 2)
        self.assertIn("no reason", err)
        code, _, _ = self.run_it(p, "--guard", "device-anatomy=waived:the page is illegible by design")
        self.assertEqual(code, 0)

    def test_a_defect_needs_a_written_reason_too(self):
        code, err, _ = self.run_it(self.guarded(), "--guard", "device-anatomy=defect")
        self.assertEqual(code, 2)
        self.assertIn("no reason", err)

    def test_an_unknown_verdict_is_refused(self):
        code, err, _ = self.run_it(self.guarded(), "--guard", "device-anatomy=probably")
        self.assertEqual(code, 2)
        self.assertIn("unknown verdict", err)

    def test_a_verdict_for_a_guard_that_never_fired_is_refused(self):
        """A typo must not read as a judgement, leaving the real guard unjudged."""
        code, err, _ = self.run_it(self.guarded(), "--guard", "device-antomy=pass")
        self.assertEqual(code, 2)
        self.assertIn("no guard named", err)

    def test_judging_one_guard_does_not_erase_another(self):
        p = self.guarded(guards=("device-anatomy", "no-ui-chrome"))
        self.run_it(p, "--guard", "device-anatomy=pass")
        code, err, _ = self.run_it(p, "--guard", "no-ui-chrome=pass")
        self.assertEqual(code, 0, err)

    def test_every_fired_guard_needs_its_own_verdict(self):
        p = self.guarded(guards=("device-anatomy", "no-ui-chrome"))
        code, err, _ = self.run_it(p, "--guard", "device-anatomy=pass")
        self.assertEqual(code, 1)
        self.assertIn("no-ui-chrome", err)
        self.assertNotIn("guard 'device-anatomy' FIRED", err)

    def test_a_verdict_may_not_be_spread_across_a_batch(self):
        a, b = self.guarded("a.png"), self.guarded("b.png")
        code, err, _ = self.run_it(a, b, "--guard", "device-anatomy=pass")
        self.assertEqual(code, 2)
        self.assertIn("ONE image", err)

    def test_a_pre_v047_recipe_still_demands_verdicts(self):
        """`guards` with no `guardGate`: the NAMES are the checkable half."""
        p = Path(png(self.d / "old.png"))
        recipe(p, entities=[ent("selah")], guards=["device-anatomy"], gate=[])
        code, err, _ = self.run_it(str(p))
        self.assertEqual(code, 1)
        self.assertIn("predates v0.47", err)
        self.assertIn("READBACK_GATE", err)


class OneSidecarTwoWriters(unittest.TestCase):
    """The guard verdicts and the seen record share one file, so they share one filename.

    v0.50 added `agenticstory.seen`, which writes the operator's tap into the SAME
    `<image>.readback.json` this script writes guard verdicts into. Two spellings of that
    name would each keep passing their own tests while writing to different files, and the
    symptom would be a lock refusing art the operator had just approved.
    """

    def test_the_two_writers_agree_on_the_filename(self):
        sys.path.insert(0, str(_HERE.parents[2] / "engine"))
        from agenticstory import seen
        self.assertEqual(vr.readback_path("/tmp/a/b.png"), str(seen.sidecar_path("/tmp/a/b.png")))

    def test_a_seen_record_survives_a_guard_verdict_being_written(self):
        sys.path.insert(0, str(_HERE.parents[2] / "engine"))
        from agenticstory import seen
        with tempfile.TemporaryDirectory() as d:
            p = png(Path(d) / "x.png")
            seen.record_board(p, question="q", options=["keep"])
            seen.record_tap(p, "keep")
            vr.record_verdicts(p, {"device-anatomy": {"verdict": "pass"}})
            doc = json.loads(open(vr.readback_path(p)).read())
            self.assertEqual(doc["seen"]["verdict"], "keep")
            self.assertEqual(doc["guardVerdicts"]["device-anatomy"]["verdict"], "pass")


if __name__ == "__main__":
    unittest.main()
