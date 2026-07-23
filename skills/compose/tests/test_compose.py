#!/usr/bin/env python3
"""Tests for the composer.

These lock in behaviours that were verified by hand once. A behaviour verified by
hand and never tested is a behaviour that quietly regresses, and the failure model
here is the part most likely to rot because it only runs on the unhappy path.

No generation and no API: every test exercises pure planning, resolution, and
feasibility logic.
"""
import importlib.util, json, pathlib, sys, tempfile, unittest

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
            status, detail = compose.run_slot(
                {"slot": "art", "index": 0, "type": "generated", "emitter": None},
                BASE, comp, t)
        self.assertEqual(status, "DEFECT")
        self.assertIsInstance(detail, str)

    def test_missing_composition_data_is_a_defect(self):
        with tempfile.TemporaryDirectory() as t:
            status, _ = compose.run_slot(
                {"slot": "ghost", "index": 0, "type": "deterministic", "emitter": "a:brand-card"},
                BASE, {"universe": t, "slots": {}}, t)
        self.assertEqual(status, "DEFECT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
