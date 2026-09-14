"""Universe discovery, progress memory, and next-move selection."""
import json
import os
import pathlib
import tempfile
import unittest
from pathlib import Path

from agenticstory import workspace


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.old_home = os.environ.get("ABU_HOME")
        os.environ["ABU_HOME"] = str(self.root / "abuhome")

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("ABU_HOME", None)
        if self.old_home is not None:
            os.environ["ABU_HOME"] = self.old_home

    def make_universe(self, name="u"):
        u = self.root / name
        (u / "canon").mkdir(parents=True)
        (u / "universe.json").write_text(json.dumps({"name": name}))
        return u


class TestDiscovery(Base):
    def test_is_universe_requires_the_marker(self):
        u = self.make_universe()
        self.assertTrue(workspace.is_universe(u))
        self.assertFalse(workspace.is_universe(self.root))

    def test_find_upward_from_deep_inside(self):
        """You are usually standing in stories/ or a book folder when you ask."""
        u = self.make_universe()
        deep = u / "stories" / "a-book" / "spreads"
        deep.mkdir(parents=True)
        self.assertEqual(workspace.find_upward(deep), u.resolve())

    def test_find_upward_returns_none_outside(self):
        self.assertIsNone(workspace.find_upward(self.root))


class TestRegistry(Base):
    def test_register_is_idempotent(self):
        u = self.make_universe()
        workspace.register(u)
        workspace.register(u)
        self.assertEqual(workspace.registered(), [u.resolve()])

    def test_register_refuses_a_non_universe(self):
        with self.assertRaises(ValueError):
            workspace.register(self.root)

    def test_registered_drops_deleted_universes(self):
        """A stale entry must not become a crash later."""
        u = self.make_universe()
        workspace.register(u)
        (u / "universe.json").unlink()
        self.assertEqual(workspace.registered(), [])

    def test_forget(self):
        u = self.make_universe()
        workspace.register(u)
        workspace.forget(u)
        self.assertEqual(workspace.registered(), [])

    def test_corrupt_registry_does_not_crash(self):
        workspace.registry_path().parent.mkdir(parents=True, exist_ok=True)
        workspace.registry_path().write_text("{not json")
        self.assertEqual(workspace.registered(), [])


class TestResolve(Base):
    def test_explicit_wins(self):
        a, b = self.make_universe("a"), self.make_universe("b")
        workspace.register(b)
        self.assertEqual(workspace.resolve(str(a)), [a.resolve()])

    def test_cwd_beats_registry(self):
        a, b = self.make_universe("a"), self.make_universe("b")
        workspace.register(b)
        self.assertEqual(workspace.resolve(start=a), [a.resolve()])

    def test_falls_back_to_registry(self):
        b = self.make_universe("b")
        workspace.register(b)
        self.assertEqual(workspace.resolve(start=self.root), [b.resolve()])

    def test_empty_is_not_an_error(self):
        """No universes is an onboarding moment, not a failure."""
        self.assertEqual(workspace.resolve(start=self.root), [])


class TestProgress(Base):
    def test_first_reading_has_no_delta(self):
        u = self.make_universe()
        r = workspace.record(u, 71, "C", on="2026-07-01")
        self.assertIsNone(r["previous"])
        self.assertIsNone(r["delta"])

    def test_second_reading_reports_the_move(self):
        u = self.make_universe()
        workspace.record(u, 71, "C", on="2026-07-01")
        r = workspace.record(u, 78, "B-", on="2026-07-30")
        self.assertEqual(r["delta"], 7)
        self.assertEqual(r["previous"]["on"], "2026-07-01")

    def test_regression_is_reported_as_negative(self):
        u = self.make_universe()
        workspace.record(u, 78, "B-", on="2026-07-01")
        self.assertEqual(workspace.record(u, 71, "C", on="2026-07-02")["delta"], -7)

    def test_universes_are_tracked_separately(self):
        a, b = self.make_universe("a"), self.make_universe("b")
        workspace.record(a, 50, "F", on="2026-07-01")
        workspace.record(b, 90, "A-", on="2026-07-01")
        self.assertEqual(workspace.last_seen(a)["score"], 50)
        self.assertEqual(workspace.last_seen(b)["score"], 90)


class TestPlan(unittest.TestCase):
    ISSUES = [
        {"impact": 9, "dimension": "provenance", "what": "835/1108 images have no recipe",
         "fix": "on-brand-image"},
        {"impact": 1, "dimension": "entities", "what": "x unlocked", "fix": "shoot-references"},
        {"impact": 1, "dimension": "entities", "what": "y unlocked", "fix": "shoot-references"},
        {"impact": 1, "dimension": "entities", "what": "z unlocked", "fix": "shoot-references"},
        {"impact": 3, "dimension": "identity", "what": "no mark", "fix": "edit universe.json"},
    ]

    def test_headline_is_highest_impact(self):
        self.assertEqual(workspace.plan(self.ISSUES)["headline"]["fix"], "on-brand-image")

    def test_small_is_lowest_impact_not_smallest_group(self):
        """The regression this guards: the grader AGGREGATES, so the 835-image
        provenance job arrives as ONE issue record. Selecting `small` by group size
        picked that as the easy win, which is backwards."""
        p = workspace.plan(self.ISSUES)
        self.assertEqual(p["small"]["fix"], "shoot-references")
        self.assertEqual(p["small"]["impact"], 1)

    def test_small_is_never_the_headline(self):
        one = [{"impact": 9, "dimension": "d", "what": "w", "fix": "f"}]
        p = workspace.plan(one)
        self.assertEqual(p["headline"]["fix"], "f")
        self.assertIsNone(p["small"])

    def test_identical_fixes_are_grouped_and_counted(self):
        g = [x for x in workspace.plan(self.ISSUES)["groups"] if x["fix"] == "shoot-references"]
        self.assertEqual(len(g), 1)
        self.assertEqual(g[0]["count"], 3)

    def test_examples_are_capped(self):
        many = [{"impact": 1, "dimension": "d", "what": f"item {i}", "fix": "f"}
                for i in range(20)]
        self.assertLessEqual(len(workspace.plan(many)["groups"][0]["examples"]), 3)

    def test_total_is_reported_so_the_summary_is_honest(self):
        self.assertEqual(workspace.plan(self.ISSUES)["total_issues"], 5)

    def test_no_issues_is_a_clean_bill(self):
        p = workspace.plan([])
        self.assertIsNone(p["headline"])
        self.assertIsNone(p["small"])
        self.assertEqual(p["total_issues"], 0)



class TestErgonomics(Base):
    def test_standing_in_a_universe_registers_it(self):
        """Without this, `abu` from anywhere else reports 'you have none' about a
        universe you were standing in five minutes ago."""
        u = self.make_universe()
        self.assertEqual(workspace.registered(), [])
        workspace.resolve(start=u)
        self.assertEqual(workspace.registered(), [u.resolve()])

    def test_explicit_path_also_leaves_registry_usable(self):
        a = self.make_universe("a")
        self.assertEqual(workspace.resolve(str(a)), [a.resolve()])

    def test_history_accumulates_across_days(self):
        u = self.make_universe()
        for score, grade, day in ((71, "C", "2026-07-01"), (79, "C", "2026-07-02"),
                                  (80, "B", "2026-07-03")):
            workspace.record(u, score, grade, on=day)
        hist = workspace.last_seen(u)["history"]
        self.assertEqual([h["score"] for h in hist], [71, 79])
        self.assertEqual(workspace.last_seen(u)["score"], 80)

    def test_same_day_rereads_do_not_pad_history(self):
        u = self.make_universe()
        workspace.record(u, 71, "C", on="2026-07-01")
        workspace.record(u, 72, "C", on="2026-07-01")
        self.assertEqual(workspace.last_seen(u)["history"], [])

    def test_history_is_bounded(self):
        u = self.make_universe()
        for i in range(20):
            workspace.record(u, i, "F", on=f"2026-07-{i+1:02d}")
        self.assertLessEqual(len(workspace.last_seen(u)["history"]), 10)


class TestHumanize(unittest.TestCase):
    def test_no_fabricated_counts(self):
        """The regression: the grader AGGREGATES, so interpolating the group size
        said '1 image(s)' about 276 images."""
        for dim, tmpl in workspace.OUTCOMES.items():
            self.assertNotIn("{n}", tmpl, dim)

    def test_detail_carries_the_real_numbers(self):
        s = workspace.humanize("provenance", "18/1304 images have no provenance record")
        self.assertIn("cannot say how they were made", s)
        self.assertIn("18/1304", s)

    def test_no_command_leaks_into_a_known_dimension(self):
        """The front door's premise is that a person never sees a command."""
        s = workspace.humanize("stories", "71 stories with no record",
                               fallback="write canon/properties/<id>.json, then `abu build-canon`")
        for tell in ("canon/properties", "`abu", ".json"):
            self.assertNotIn(tell, s)

    def test_unknown_dimension_falls_back_to_PLAIN_LANGUAGE(self):
        """A fallback that reads as English is still used; that half was always right."""
        self.assertIn("something odd", workspace.humanize("mystery", "", "something odd"))

    def test_unknown_dimension_NEVER_falls_back_to_a_COMMAND(self):
        """The leak this closes (v0.49).

        `fallback` is the grader's `fix`, written for the grader's maintainer. The old
        behaviour passed it through verbatim for any dimension with no OUTCOMES sentence,
        and the old test for it was named `..._falls_back` and asserted the leak.
        """
        s = workspace.humanize("mystery", "", "write canon/properties/<id>.json, then `abu build-canon`")
        self.assertIsNone(workspace.command_in(s), s)
        self.assertNotIn("abu build-canon", s)
        s2 = workspace.humanize("mystery", "", "abu backfill-provenance (records what is knowable)")
        self.assertIsNone(workspace.command_in(s2), s2)

    def test_a_command_in_the_DETAIL_is_dropped_too(self):
        s = workspace.humanize("provenance", "18/1304 images; run `abu backfill-provenance`")
        self.assertIsNone(workspace.command_in(s), s)

    def test_every_grader_dimension_has_an_outcome_sentence(self):
        """The READBACK_GATE pattern: a new dimension cannot ship without its sentence.

        `setting_nesting` shipped without one, so its fix string -- which names two JSON
        keys in backticks -- was what `plan.headline.human` said out loud.
        """
        import importlib.util
        g = (pathlib.Path(__file__).resolve().parents[2]
             / "skills" / "universe-doctor" / "scripts" / "grade.py")
        spec = importlib.util.spec_from_file_location("_grade", g)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for key, label, _max in mod.RUBRIC:
            self.assertIn(key, workspace.OUTCOMES,
                          f"grader dimension {key!r} ({label}) has no plain-language "
                          f"sentence in workspace.OUTCOMES, so the front door would say "
                          f"the grader's own fix string, which contains commands")

    def test_plan_human_strings_carry_no_command(self):
        """Over the grader's REAL fix strings, not invented ones."""
        real_fixes = [
            ("validity", "abu validate"),
            ("setting_nesting", "split the rooms into settings with `partOf`, house rules "
                                "into `structured.houseRules`"),
            ("provenance", "abu backfill-provenance (records what is knowable; never re-renders)"),
            ("stories", "write canon/properties/<id>.json, then `abu build-canon`"),
            ("identity", "start-new-story-universe / edit universe.json"),
        ]
        issues = [{"impact": 9 - n, "dimension": d, "what": "x", "fix": f}
                  for n, (d, f) in enumerate(real_fixes)]
        p = workspace.plan(issues)
        for g in p["groups"]:
            self.assertIsNone(workspace.command_in(g["human"]), g["human"])
        for k in ("headline", "small"):
            if p[k]:
                self.assertIsNone(workspace.command_in(p[k]["human"]), p[k]["human"])


class TestCommandIn(unittest.TestCase):
    def test_catches_what_a_person_must_never_be_shown(self):
        for s in ("abu validate",
                  "run `abu build-canon` afterwards",
                  "python3 grade.py <universe>",
                  "pass --json to it",
                  "cat x && echo y",
                  "use grade.py for this",
                  "`uv run generate.py`"):
            self.assertIsNotNone(workspace.command_in(s), f"missed: {s!r}")

    def test_leaves_ordinary_sentences_alone(self):
        """Over-triggering blanks real sentences, which is worse than the leak."""
        for s in list(workspace.OUTCOMES.values()) + [
                "18/1304 images have no provenance record",
                "identity is missing register.anchor",
                "3 full stories with no canon/properties record: a, b",
                "assetRoot is 'assets' (should be '.'): refs may point outside the repo",
                "make a work out of this canon",
                "one place is modelled as several rooms at once"]:
            self.assertIsNone(workspace.command_in(s), f"false positive: {s!r}")

    def test_a_path_is_not_a_command(self):
        self.assertIsNone(workspace.command_in("canon/entities/jerry.json"))

    def test_plan_attaches_human_to_every_group(self):
        issues = [{"impact": 9, "dimension": "provenance", "what": "18/1304 images", "fix": "f"},
                  {"impact": 1, "dimension": "entities", "what": "x unlocked", "fix": "g"}]
        for g in workspace.plan(issues)["groups"]:
            self.assertTrue(g["human"])
            self.assertNotIn("{n}", g["human"])

if __name__ == "__main__":
    unittest.main()
