#!/usr/bin/env python3
"""Tests for the composer.

These lock in behaviours that were verified by hand once. A behaviour verified by
hand and never tested is a behaviour that quietly regresses, and the failure model
here is the part most likely to rot because it only runs on the unhappy path.

No generation and no API: every test exercises pure planning, resolution, and
feasibility logic.
"""
import importlib.util, json, os, pathlib, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("compose", HERE.parent / "scripts" / "compose.py")
compose = importlib.util.module_from_spec(spec); spec.loader.exec_module(compose)


def universe(tmp, projections):
    root = pathlib.Path(tmp); (root / "projections").mkdir(parents=True)
    for name, p in projections.items():
        (root / "projections" / f"{name}.json").write_text(json.dumps(p))
    return root


BASE = {"id": "base", "surface": {"geometry": {"w": 1500, "h": 900}},
        "slots": [{"id": "text", "type": "deterministic", "emitter": "agenticstory:brand-card"},
                  {"id": "art", "type": "generated", "geometry": {"w": 600, "h": 900}}],
        "generators": [{"for": "art", "capability": "image",
                        "producibleAspects": [1.0, 0.667, 1.5], "tolerance": 0.25}],
        "invariants": {"perSlot": [], "crossSlot": []}}


class TestExtends(unittest.TestCase):
    def test_extends_resolves_and_records_the_chain(self):
        child = {"id": "child", "extends": "base@1.0.0", "surface": {"geometry": {"w": 1200, "h": 1200}}}
        with tempfile.TemporaryDirectory() as t:
            root = universe(t, {"base": BASE, "child": child})
            p = compose.load_projection(str(root), "child@1.0.0")
        self.assertEqual(p["_extends_chain"], ["base"])
        self.assertEqual(p["surface"]["geometry"]["w"], 1200, "child must override parent")
        self.assertEqual(len(p["slots"]), 2, "child must inherit slots it did not redeclare")

    def test_no_extends_gives_empty_chain(self):
        with tempfile.TemporaryDirectory() as t:
            root = universe(t, {"base": BASE})
            p = compose.load_projection(str(root), "base@1.0.0")
        self.assertEqual(p["_extends_chain"], [])


class TestFeasibility(unittest.TestCase):
    """A contract can be internally valid and physically undeliverable."""

    def test_refuses_an_aspect_no_generator_can_produce(self):
        bad = json.loads(json.dumps(BASE))
        bad["slots"][1]["geometry"] = {"w": 400, "h": 1200}      # 0.333
        errs = compose.feasibility(bad, {})
        self.assertTrue(any("0.333" in e for e in errs), errs)

    def test_accepts_a_producible_aspect(self):
        self.assertEqual(compose.feasibility(BASE, {}), [])

    def test_refuses_a_deterministic_slot_with_no_emitter(self):
        bad = json.loads(json.dumps(BASE))
        del bad["slots"][0]["emitter"]
        errs = compose.feasibility(bad, {})
        self.assertTrue(any("no emitter" in e for e in errs), errs)

    def test_composition_can_override_surface_and_stay_feasible(self):
        self.assertEqual(compose.feasibility(BASE, {"surface": {"w": 1500, "h": 900}}), [])


class TestPlan(unittest.TestCase):
    def test_repeat_expands_into_one_unit_per_index(self):
        p = json.loads(json.dumps(BASE))
        p["slots"].append({"id": "spread", "repeat": "$.n", "type": "generated"})
        units = compose.plan(p, {"repeat": {"spread": 4}})
        spreads = [u for u in units if u["slot"] == "spread"]
        self.assertEqual(len(spreads), 4)
        self.assertEqual([u["index"] for u in spreads], [0, 1, 2, 3])

    def test_non_repeated_slots_produce_exactly_one_unit(self):
        units = compose.plan(BASE, {})
        self.assertEqual(len(units), 2)


class TestQuirks(unittest.TestCase):
    """Quirks bind to the RESOLVED provider, not to the pin. Binding them to the pin
    left the deliberately portable projection as the only unguarded one."""

    def test_unpinned_generator_still_inherits_provider_quirks(self):
        qk = compose.quirks_for(BASE, "art", "gpt-image-2")
        self.assertTrue(qk, "an unpinned slot must still inherit its runtime provider's quirks")
        self.assertTrue(all("counter" in q and "id" in q for q in qk))

    def test_unknown_provider_yields_no_quirks_rather_than_crashing(self):
        self.assertEqual(compose.quirks_for(BASE, "art", "no-such-model"), [])


class TestFailureModel(unittest.TestCase):
    def test_a_slot_with_no_scene_is_a_defect_not_an_exception(self):
        """An exception is not a parked slot. One bad field must never take down a run."""
        with tempfile.TemporaryDirectory() as t:
            root = universe(t, {"base": BASE})
            comp = {"universe": str(root), "slots": {"art": {}}, "bind": {"style-pack": "nope"}}
            status, detail, _ = compose.run_slot(
                {"slot": "art", "index": 0, "type": "generated", "emitter": None},
                BASE, comp, t)
        self.assertEqual(status, "DEFECT")
        self.assertIsInstance(detail, str)

    def test_missing_composition_data_is_a_defect(self):
        with tempfile.TemporaryDirectory() as t:
            status, _, _ = compose.run_slot(
                {"slot": "ghost", "index": 0, "type": "deterministic", "emitter": "a:brand-card"},
                BASE, {"universe": t, "slots": {}}, t)
        self.assertEqual(status, "DEFECT")


class TestJudgeIsARole(unittest.TestCase):
    """The judge must not be the maker. The composer therefore does not judge at all:
    it writes a BRIEF stating what a judge must see, and refuses to call the slot a
    pass until an independent verdict comes back."""

    def brief(self, tmp, checklist=("no text in the art",), mode="style"):
        f = compose.judge_request(tmp, "art", 0, "/ref.png", "/out.png",
                                  list(checklist), mode, roll=1)
        return json.loads(pathlib.Path(f).read_text())

    def test_the_brief_carries_the_artifact_reference_and_checklist(self):
        with tempfile.TemporaryDirectory() as t:
            b = self.brief(t)
            self.assertEqual(b["artifact"], "/out.png")
            self.assertEqual(b["reference"], "/ref.png")
            self.assertEqual(b["checklist"], ["no text in the art"])

    def test_the_brief_withholds_the_plan(self):
        """If the brief carried the beats or the compiled prompt, the judge would be
        reading intent instead of pixels, which is the exact failure the rule exists
        for: a maker shown its own reasoning defends it."""
        with tempfile.TemporaryDirectory() as t:
            b = self.brief(t)
            for leak in ("prompt", "beats", "scene", "plan", "intent", "composition"):
                self.assertNotIn(leak, b, f"the brief leaks '{leak}' to the judge")

    def test_mode_distinguishes_identity_from_style(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(self.brief(t, mode="identity")["mode"], "identity")
            self.assertEqual(self.brief(t, mode="style")["mode"], "style")

    def test_absent_verdict_is_not_a_pass(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertIsNone(compose.verdict_for(t, "art", 0))

    def test_unparseable_verdict_fails_closed(self):
        """A gate whose answer you cannot read is not a gate."""
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "verdicts"; d.mkdir()
            (d / "art-0.json").write_text("{not json")
            self.assertIsNone(compose.verdict_for(t, "art", 0))

    def test_a_verdict_of_an_unknown_word_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "verdicts"; d.mkdir()
            (d / "art-0.json").write_text(json.dumps({"verdict": "probably fine"}))
            self.assertIsNone(compose.verdict_for(t, "art", 0))

    def test_a_real_verdict_is_read_back(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "verdicts"; d.mkdir()
            (d / "art-0.json").write_text(json.dumps({"verdict": "PASS", "why": "clean"}))
            self.assertEqual(compose.verdict_for(t, "art", 0)["verdict"], "PASS")

    def test_no_api_key_is_consulted_anywhere(self):
        """The judge role is filled by a subagent in the runtime that is already
        composing. Requiring a key made the cheapest correct judge unreachable and
        parked every slot as unjudgeable."""
        src = pathlib.Path(compose.__file__).read_text()
        self.assertNotIn("ANTHROPIC_API_KEY", src)


class TestSceneContradictions(unittest.TestCase):
    """A scene must not name something the style pack rejects. The compiler appends
    "no <pole>" to the same prompt, so the model receives both instructions at once
    and picks one. Free to check, and it runs before anything is generated."""

    def pack(self, tmp, poles):
        d = pathlib.Path(tmp) / "reference" / "style" / "p"
        d.mkdir(parents=True)
        (d / "pack.json").write_text(json.dumps({
            "id": "p", "anchor": "a.png", "refs": ["a.png"],
            "styleLine": "flat", "rejectedPoles": poles}))
        return "reference/style/p"

    def comp(self, tmp, poles, beats):
        return {"universe": tmp, "bind": {"style-pack": self.pack(tmp, poles)},
                "beats": beats}

    def test_a_scene_naming_a_rejected_pole_is_refused_before_generating(self):
        with tempfile.TemporaryDirectory() as t:
            errs = compose.scene_contradictions(
                {}, self.comp(t, ["perspective", "shading"],
                              ["a flat grid drawn in perspective"]))
            self.assertTrue(errs)
            self.assertIn("perspective", errs[0])

    def test_a_clean_scene_passes(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["perspective"], ["two hands holding a cream block"])), [])

    def test_it_matches_whole_words_only(self):
        """'perspectives' in a sentence about points of view must not trip a pack
        that rejects the rendering technique. False positives are how a check gets
        switched off."""
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["3d"], ["a hand holding a 3dimensional-looking block"])), [])

    def test_multiword_and_slashed_poles_are_skipped_not_guessed(self):
        """'3D/CGI/Pixar' as a literal substring would fire on almost anything. This
        check is deliberately literal and single-word; implication is the gate's job."""
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["3D/CGI/Pixar", "neo-comic action-zine"],
                              ["a pixar style hand"])), [])

    def test_no_style_pack_binding_is_not_an_error_here(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, {"universe": t, "beats": ["anything"]}), [])


class TestRollAccounting(unittest.TestCase):
    """The roll counter belongs to whoever GENERATES. Counting a re-run as a roll made
    a slot that was merely WAITING on a judge burn through its budget and eventually
    get declared "exhausted its rolls" for waiting. A gate that punishes you for
    running it is not a gate."""

    def test_run_slot_always_returns_a_roll(self):
        """Every exit path carries the roll it ended on, so main never has to guess."""
        st, detail, roll = compose.run_slot(
            {"slot": "x", "index": 0, "type": "generated", "emitter": None},
            {"slots": [], "invariants": {"perSlot": [], "crossSlot": []}},
            {"universe": "/nonexistent", "bind": {}}, "/tmp/nope")
        self.assertEqual(st, "DEFECT")
        self.assertIsInstance(roll, int)

    def test_a_slot_never_generated_reports_roll_zero(self):
        _, _, roll = compose.run_slot(
            {"slot": "x", "index": 0, "type": "generated", "emitter": None},
            {"slots": [], "invariants": {"perSlot": [], "crossSlot": []}},
            {"universe": "/nonexistent", "bind": {}}, "/tmp/nope")
        self.assertEqual(roll, 0)

    def test_run_slot_still_never_raises(self):
        st, _, _ = compose.run_slot({"slot": "x", "index": 0, "type": "generated"},
                                    {}, {}, "/tmp/nope")
        self.assertEqual(st, "DEFECT")


class TestExhaustionNeverDiscardsAPass(unittest.TestCase):
    """A slot that has spent its last roll still has an artifact on disk and may have a
    PASSING verdict waiting. Declaring it exhausted before reading that verdict throws
    away a good result and reports a defect that does not exist.

    This actually happened: a plate passed all eight of its items and was reported
    DEFECT because the roll budget was consulted first. It is the same failure as resume
    logic that restores defects, the bookkeeping outranking the result."""

    def setup_slot(self, tmp, verdict, roll):
        work = pathlib.Path(tmp)
        (work / "state").mkdir(parents=True)
        (work / "verdicts").mkdir()
        (work / "state" / "art-0.json").write_text(json.dumps({"roll": roll}))
        (work / "verdicts" / "art-0.json").write_text(json.dumps({"verdict": verdict}))
        (work / "art-0.png").write_bytes(b"\x89PNG")
        return str(work)

    def test_a_pass_at_max_rolls_is_still_a_pass(self):
        with tempfile.TemporaryDirectory() as t:
            work = self.setup_slot(t, "PASS", roll=3)
            self.assertEqual(compose.verdict_for(work, "art", 0)["verdict"], "PASS")
            # the state file says the budget is spent; the verdict must still win
            self.assertEqual(json.loads(
                (pathlib.Path(work) / "state" / "art-0.json").read_text())["roll"], 3)

    def test_a_defect_at_max_rolls_is_exhaustion(self):
        with tempfile.TemporaryDirectory() as t:
            work = self.setup_slot(t, "DEFECT", roll=3)
            self.assertEqual(compose.verdict_for(work, "art", 0)["verdict"], "DEFECT")

    def test_clearing_a_verdict_leaves_no_stale_pass_behind(self):
        """A cleared verdict must read as absent, not as the previous answer."""
        with tempfile.TemporaryDirectory() as t:
            work = self.setup_slot(t, "PASS", roll=1)
            compose.clear_verdict(work, "art", 0)
            self.assertIsNone(compose.verdict_for(work, "art", 0))


class TestStaleArtifactIsNotMistakenForAnUnjudgedOne(unittest.TestCase):
    """An artifact on disk with no verdict is AMBIGUOUS and the roll counter cannot
    disambiguate it. It is either awaiting its first look, or already judged, rejected,
    and its verdict consumed. The prior STATUS is what tells them apart.

    Using the roll count alone silently re-briefed a known-rejected plate instead of
    re-rolling it, so repairing the beat AND raising the roll budget both had no
    effect: the composer reported it as awaiting judgment and never regenerated."""

    def state(self, tmp, status, roll):
        w = pathlib.Path(tmp); (w / "state").mkdir(parents=True)
        (w / "state" / "art-0.json").write_text(json.dumps({"status": status, "roll": roll}))
        (w / "art-0.png").write_bytes(b"\x89PNG")
        return str(w)

    def test_a_slot_previously_needing_judgment_is_still_awaiting_one(self):
        with tempfile.TemporaryDirectory() as t:
            w = self.state(t, "NEEDS-JUDGMENT", 1)
            self.assertEqual(compose.spec_state(w, "art", 0)["status"], "NEEDS-JUDGMENT")

    def test_a_slot_previously_DEFECT_is_stale_and_must_not_be_re_briefed(self):
        with tempfile.TemporaryDirectory() as t:
            w = self.state(t, "DEFECT", 3)
            self.assertEqual(compose.spec_state(w, "art", 0)["status"], "DEFECT")
            self.assertIsNone(compose.verdict_for(w, "art", 0),
                              "a consumed verdict must read as absent, which is exactly "
                              "why status rather than verdict presence has to decide")

    def test_status_survives_a_round_trip_through_state(self):
        with tempfile.TemporaryDirectory() as t:
            w = self.state(t, "DEFECT", 3)
            d = compose.spec_state(w, "art", 0)
            self.assertEqual((d["status"], d["roll"]), ("DEFECT", 3))


class TestVerdictIsBoundToTheArtifactItJudged(unittest.TestCase):
    """A verdict is only ever valid for the bytes it looked at. Without binding, a PASS
    on roll 2 could silently authorise a completely different roll-3 image."""

    def setup(self, tmp, content=b"\x89PNG-one"):
        w = pathlib.Path(tmp)
        (w / "verdicts").mkdir(parents=True); (w / "judge").mkdir()
        art = w / "art-0.png"; art.write_bytes(content)
        (w / "verdicts" / "art-0.json").write_text(json.dumps({"verdict": "PASS"}))
        (w / "judge" / "art-0.json").write_text(json.dumps(
            {"artifactDigest": compose.digest(str(art))}))
        return str(w), str(art)

    def test_a_verdict_matching_its_artifact_is_honoured(self):
        with tempfile.TemporaryDirectory() as t:
            w, art = self.setup(t)
            self.assertEqual(compose.verdict_for(w, "art", 0, art)["verdict"], "PASS")

    def test_a_verdict_whose_artifact_changed_is_STALE_and_reads_as_absent(self):
        with tempfile.TemporaryDirectory() as t:
            w, art = self.setup(t)
            pathlib.Path(art).write_bytes(b"\x89PNG-a-completely-different-image")
            self.assertIsNone(compose.verdict_for(w, "art", 0, art),
                              "a PASS must not carry over to a re-rolled image")

    def test_digest_of_a_missing_file_is_None_rather_than_a_crash(self):
        self.assertIsNone(compose.digest("/nonexistent/nope.png"))

    def test_binding_is_skipped_when_no_artifact_is_supplied(self):
        """Callers that only want to know whether a verdict exists still work."""
        with tempfile.TemporaryDirectory() as t:
            w, _ = self.setup(t)
            self.assertEqual(compose.verdict_for(w, "art", 0)["verdict"], "PASS")


class TestImpliedPolesAreCaughtToo(unittest.TestCase):
    """Some words do not NAME a rejected pole but reliably summon one. On a six-plate
    run, three plates failed for exactly this reason and the literal check caught none
    of them: an 'open book' and an 'open door' are inherently volumetric, and a scene
    saying 'glowing' and 'dark' produced a radial glow and a vignette on a pack that
    requires one flat ground colour."""

    def comp(self, tmp, poles, beats):
        d = pathlib.Path(tmp) / "reference" / "style" / "p"
        d.mkdir(parents=True)
        (d / "pack.json").write_text(json.dumps({
            "id": "p", "anchor": "a.png", "refs": ["a.png"],
            "styleLine": "flat", "rejectedPoles": poles}))
        return {"universe": tmp, "bind": {"style-pack": "reference/style/p"}, "beats": beats}

    def test_open_book_is_caught_by_a_pack_rejecting_perspective(self):
        with tempfile.TemporaryDirectory() as t:
            errs = compose.scene_contradictions(
                {}, self.comp(t, ["perspective"], ["one open book lying on the ground"]))
            self.assertTrue(errs)
            self.assertIn("perspective", errs[0])

    def test_glowing_is_caught_by_a_pack_rejecting_gradients(self):
        with tempfile.TemporaryDirectory() as t:
            errs = compose.scene_contradictions(
                {}, self.comp(t, ["gradients"], ["a small rectangle glowing in the centre"]))
            self.assertTrue(errs)

    def test_a_flat_description_of_the_same_object_passes(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["perspective", "gradients"],
                              ["one closed book lying face-on as a flat rectangle"])), [])

    def test_an_implied_word_only_fires_for_a_pole_the_pack_actually_rejects(self):
        """A pack that permits perspective must not be told off for saying 'open book'.
        A check that fires where the brand does not care is noise."""
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["neon"], ["one open book lying on the ground"])), [])


class TestNegatedPolesAreNotContradictions(unittest.TestCase):
    """A scene that says "no glow" is EXCLUDING the pole, not summoning it. Matching the
    bare word flagged every careful exclusion as a contradiction and refused a whole
    composition at plan time, blocking a real run. The check false-fired on the very
    repairs that were written to satisfy it."""

    def comp(self, tmp, poles, beats):
        d = pathlib.Path(tmp) / "reference" / "style" / "p"
        d.mkdir(parents=True)
        (d / "pack.json").write_text(json.dumps({
            "id": "p", "anchor": "a.png", "refs": ["a.png"],
            "styleLine": "flat", "rejectedPoles": poles}))
        return {"universe": tmp, "bind": {"style-pack": "reference/style/p"}, "beats": beats}

    def test_no_glow_is_not_a_contradiction(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["gradients"], ["a flat shape. No glow, no darkness."])), [])

    def test_with_no_depth_is_not_a_contradiction(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["perspective"], ["a square seen straight on with no depth"])), [])

    def test_never_tilted_is_not_a_contradiction(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["perspective"], ["no object may be turned or tilted"])), [])

    def test_an_UNNEGATED_pole_still_fires(self):
        """The negation guard must not defeat the check it protects."""
        with tempfile.TemporaryDirectory() as t:
            errs = compose.scene_contradictions(
                {}, self.comp(t, ["gradients"], ["a rectangle glowing in the centre"]))
            self.assertTrue(errs)

    def test_a_negator_governing_a_LONG_coordinated_list_still_negates(self):
        """The case that broke a fixed word window: the negator is eight words back and
        plainly governs the whole list. Distance is the wrong signal; scope is."""
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(compose.scene_contradictions(
                {}, self.comp(t, ["perspective"],
                              ["no object may be turned, angled, opened, or tilted"])), [])

    def test_an_article_ends_the_reach_of_an_earlier_negator(self):
        """'a' starts a fresh noun phrase, so the earlier 'no' does not excuse it."""
        with tempfile.TemporaryDirectory() as t:
            errs = compose.scene_contradictions(
                {}, self.comp(t, ["gradients"], ["no text at all, and a big glowing box"]))
            self.assertTrue(errs, "an article must end the negation scope")

    def test_a_negation_far_away_does_not_excuse_a_later_mention(self):
        """'No text anywhere. A glowing rectangle.' must still fire on the glow: the
        negator has to be NEAR the word, not merely somewhere in the sentence."""
        with tempfile.TemporaryDirectory() as t:
            errs = compose.scene_contradictions(
                {}, self.comp(t, ["gradients"],
                              ["no text anywhere in this picture at all, and a big glowing box"]))
            self.assertTrue(errs)


class TestReadbackCatchesTheEmptyFrame(unittest.TestCase):
    """Every invariant in a typical projection is NEGATIVE: no text, no perspective, at
    most N elements, one flat ground. Nothing asserts the artifact means anything, so
    repairing a slot against that gate walks it toward the artifact that satisfies every
    rule most easily: the EMPTY FRAME.

    This is not hypothetical. A plate for "a great-grandfather preaching under
    persecution" passed all eight of its invariants as a blank rectangle. The gate cannot
    catch it, because the judge is blind to the plan, which is exactly what makes it
    honest about style and blind to a missing subject."""

    def test_a_contract_declaring_depicts_its_subject_is_detected(self):
        self.assertTrue(compose.wants_readback(
            {"invariants": {"perSlot": [{"id": "depicts-its-subject", "check": "judged"}],
                            "crossSlot": []}}))

    def test_a_contract_without_it_is_not(self):
        self.assertFalse(compose.wants_readback(
            {"invariants": {"perSlot": [{"id": "no-text", "check": "judged"}], "crossSlot": []}}))

    def test_a_verdict_with_no_depicts_fails_CLOSED_when_readback_is_required(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "verdicts"; d.mkdir()
            (d / "art-0.json").write_text(json.dumps({"verdict": "PASS"}))
            self.assertIsNone(compose.verdict_for(t, "art", 0, require_depicts=True))
            # ...but the same verdict is fine when the contract does not ask for it
            self.assertIsNotNone(compose.verdict_for(t, "art", 0))

    def test_an_empty_depicts_string_also_fails_closed(self):
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "verdicts"; d.mkdir()
            (d / "art-0.json").write_text(json.dumps({"verdict": "PASS", "depicts": "   "}))
            self.assertIsNone(compose.verdict_for(t, "art", 0, require_depicts=True))

    def test_the_readback_pair_withholds_the_image_from_the_comparer(self):
        """Stage 2 must never see the picture, or it starts judging the art instead of
        the match, which is stage 1's job and a different question."""
        with tempfile.TemporaryDirectory() as t:
            d = pathlib.Path(t) / "verdicts"; d.mkdir()
            (d / "art-0.json").write_text(json.dumps(
                {"verdict": "PASS", "depicts": "a blank white rectangle"}))
            f = compose.readback(t, "art", 0, "a great-grandfather preaching")
            pair = json.loads(pathlib.Path(f).read_text())
            self.assertEqual(pair["intended"], "a great-grandfather preaching")
            self.assertEqual(pair["judgeSaw"], "a blank white rectangle")
            self.assertNotIn("artifact", pair)
            self.assertIn("withheld", pair)


class TestGoldensResolveAgainstTheUniverse(unittest.TestCase):
    """A golden is declared relative to the UNIVERSE ROOT. Left verbatim it resolved only
    when the process happened to be run from that directory; from anywhere else the
    identity anchor silently failed to attach and the render produced a plausible image
    of the WRONG PERSON, with every style gate still green because the look was never
    what broke.

    Silent identity loss is the precise failure goldens exist to prevent, so it must not
    depend on a working directory."""

    def test_a_relative_golden_is_joined_to_the_universe_root(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            pk = root / "p"; (pk / "refs").mkdir(parents=True)
            (pk / "refs" / "a.png").write_bytes(b"\x89PNG")
            (pk / "pack.json").write_text(json.dumps({
                "id": "p", "anchor": "refs/a.png", "refs": ["refs/a.png"],
                "styleLine": "s", "rejectedPoles": []}))
            (root / "reference").mkdir()
            (root / "reference" / "m.png").write_bytes(b"\x89PNG")
            pack = compose.load_pack(str(root), "p")
            _, refs, _ = compose.compile_slot(
                {"generators": [], "invariants": {"perSlot": [], "crossSlot": []}},
                {"universe": str(root)}, "spread", "a scene", pack,
                ["reference/m.png"])
            self.assertTrue(any(r.endswith("reference/m.png") for r in refs))
            self.assertTrue(all(os.path.isabs(r) for r in refs),
                            f"every reference must be absolute, got {refs}")

    def test_an_absolute_golden_is_left_alone(self):
        with tempfile.TemporaryDirectory() as t:
            root = pathlib.Path(t)
            pk = root / "p"; (pk / "refs").mkdir(parents=True)
            (pk / "refs" / "a.png").write_bytes(b"\x89PNG")
            (pk / "pack.json").write_text(json.dumps({
                "id": "p", "anchor": "refs/a.png", "refs": ["refs/a.png"],
                "styleLine": "s", "rejectedPoles": []}))
            abs_g = str(root / "abs.png")
            pack = compose.load_pack(str(root), "p")
            _, refs, _ = compose.compile_slot(
                {"generators": [], "invariants": {"perSlot": [], "crossSlot": []}},
                {"universe": str(root)}, "spread", "a scene", pack, [abs_g])
            self.assertIn(abs_g, refs)

    def test_generate_REFUSES_when_a_reference_does_not_resolve(self):
        """A missing golden that is merely skipped yields a plausible picture of the
        wrong person, which passes every check that is not about identity."""
        ok, detail = compose.generate("p", ["/nonexistent/golden.png"], "/tmp/x.png", "1024x1024")
        self.assertFalse(ok)
        self.assertIn("refusing to render", detail)


class TestSurfaceShrinkIsCalledOut(unittest.TestCase):
    """A projection's geometry states what this KIND of deliverable is. A storybook
    declaring 24 spreads says a book of this kind runs about that long. Overriding it is
    allowed, but a large cut is rarely editorial: it is the maker shrinking the job to
    what is cheap to generate.

    Earned three times in one evening: the characterless register chosen to avoid the
    hardest invariant, plates simplified until one was an empty rectangle, and a book cut
    from 24 spreads to 8. Every other safeguard here constrains EXECUTION. Nothing
    constrained SELECTION, and selection is where the drift was."""

    PROJ = {"surface": {"geometry": {"spreads": 24}}}

    def test_a_large_cut_is_called_out(self):
        w = compose.surface_shrink(self.PROJ, {"surface": {"spreads": 8}})
        self.assertTrue(w)
        self.assertIn("24", w[0])
        self.assertIn("33%", w[0])

    def test_the_declared_length_is_silent(self):
        self.assertEqual(compose.surface_shrink(self.PROJ, {"surface": {"spreads": 24}}), [])

    def test_a_modest_trim_is_silent(self):
        """18 of 24 is an editorial choice, not a flinch."""
        self.assertEqual(compose.surface_shrink(self.PROJ, {"surface": {"spreads": 18}}), [])

    def test_a_LONGER_book_is_never_flagged(self):
        self.assertEqual(compose.surface_shrink(self.PROJ, {"surface": {"spreads": 40}}), [])

    def test_it_reads_repeat_when_surface_is_not_overridden(self):
        self.assertTrue(compose.surface_shrink(self.PROJ, {"repeat": {"spreads": 6}}))

    def test_non_numeric_geometry_is_ignored(self):
        self.assertEqual(compose.surface_shrink(
            {"surface": {"geometry": {"aspect": "2:3"}}}, {"surface": {"aspect": "1:1"}}), [])


class TestStagedGoldens(unittest.TestCase):
    """Goldens could only be bound per SLOT, which cannot express a character whose state
    changes partway through a book. A wardrobe marker that ARRIVES at the turn is one of
    the cheapest ways to make a reader feel a change before they read it, and it was
    unrepresentable when every spread had to share one sheet."""

    STAGED = {"goldens": {"spread": {"0-20": ["a.png"], "21-23": ["b.png"]},
                          "cover": ["a.png"]}}

    def test_an_index_before_the_turn_binds_the_first_sheet(self):
        self.assertEqual(compose.goldens_for(self.STAGED, "spread", 0), ["a.png"])
        self.assertEqual(compose.goldens_for(self.STAGED, "spread", 20), ["a.png"])

    def test_an_index_after_the_turn_binds_the_second(self):
        self.assertEqual(compose.goldens_for(self.STAGED, "spread", 21), ["b.png"])
        self.assertEqual(compose.goldens_for(self.STAGED, "spread", 23), ["b.png"])

    def test_ranges_are_inclusive_on_both_ends(self):
        one = {"goldens": {"s": {"5-5": ["x.png"]}}}
        self.assertEqual(compose.goldens_for(one, "s", 5), ["x.png"])
        self.assertEqual(compose.goldens_for(one, "s", 4), [])
        self.assertEqual(compose.goldens_for(one, "s", 6), [])

    def test_a_plain_list_still_applies_to_every_index(self):
        flat = {"goldens": {"spread": ["m.png"]}}
        for i in (0, 7, 99):
            self.assertEqual(compose.goldens_for(flat, "spread", i), ["m.png"])

    def test_default_is_used_when_the_slot_is_not_named(self):
        self.assertEqual(compose.goldens_for({"goldens": {"default": ["d.png"]}}, "spread", 3),
                         ["d.png"])

    def test_an_uncovered_index_binds_NOTHING_rather_than_guessing(self):
        """It then fails loudly at the reference resolver, which is far better than
        silently rendering a character with no identity anchor."""
        gap = {"goldens": {"s": {"0-2": ["a.png"]}}}
        self.assertEqual(compose.goldens_for(gap, "s", 9), [])

    def test_a_single_index_key_works(self):
        self.assertEqual(compose.goldens_for({"goldens": {"s": {"4": ["q.png"]}}}, "s", 4),
                         ["q.png"])


class TestSlotScopedRulesAndPermits(unittest.TestCase):
    """A rule that is right for interior art can be flatly wrong for a cover. Every book
    cover ever printed carries its own title, so a blanket "no text or lettering" turns
    the one slot that MUST have type into a defect.

    Gary, on finding the cover bare: "if the style pack rejects lettering outright, the
    style pack is wrong... we just got to update our code, not listen to rules that we
    need to update." A canon rule is not physics."""

    def pack(self, tmp):
        d = pathlib.Path(tmp) / "p"; (d / "refs").mkdir(parents=True)
        (d / "refs" / "a.png").write_bytes(b"\x89PNG")
        (d / "pack.json").write_text(json.dumps({
            "id": "p", "anchor": "refs/a.png", "refs": ["refs/a.png"],
            "styleLine": "warm", "rejectedPoles": ["neon", "text or lettering"]}))
        return compose.load_pack(tmp, "p")

    PROJ = {"slots": [{"id": "cover", "permits": ["text"]}, {"id": "spread"}],
            "generators": [],
            "invariants": {"perSlot": [
                {"id": "no-text-in-art", "check": "judged", "slots": ["spread"]},
                {"id": "flat", "check": "judged"}], "crossSlot": []}}

    def test_the_cover_prompt_does_not_forbid_text(self):
        with tempfile.TemporaryDirectory() as t:
            prompt, _, _ = compose.compile_slot(
                self.PROJ, {"universe": t}, "cover", "a scene", self.pack(t), [])
            self.assertNotIn("ABSOLUTELY NO text", prompt)
            self.assertNotIn("no text or lettering", prompt)
            self.assertIn("no neon", prompt, "other poles must still be enforced")

    def test_an_interior_spread_still_forbids_text(self):
        with tempfile.TemporaryDirectory() as t:
            prompt, _, _ = compose.compile_slot(
                self.PROJ, {"universe": t}, "spread", "a scene", self.pack(t), [])
            self.assertIn("ABSOLUTELY NO text", prompt)
            self.assertIn("no text or lettering", prompt)

    def test_the_no_text_invariant_is_not_checked_on_the_cover(self):
        with tempfile.TemporaryDirectory() as t:
            _, _, qa = compose.compile_slot(
                self.PROJ, {"universe": t}, "cover", "a scene", self.pack(t), [])
            self.assertNotIn("no-text-in-art", qa)
            self.assertIn("flat", qa, "unscoped invariants still apply everywhere")

    def test_it_IS_checked_on_a_spread(self):
        with tempfile.TemporaryDirectory() as t:
            _, _, qa = compose.compile_slot(
                self.PROJ, {"universe": t}, "spread", "a scene", self.pack(t), [])
            self.assertIn("no-text-in-art", qa)

    def test_an_invariant_naming_no_slots_applies_to_all_of_them(self):
        self.assertTrue(compose.applies_to({"id": "x"}, "anything"))
        self.assertTrue(compose.applies_to({"id": "x", "slots": ["a", "b"]}, "b"))
        self.assertFalse(compose.applies_to({"id": "x", "slots": ["a"]}, "b"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
