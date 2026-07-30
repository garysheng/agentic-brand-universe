"""Universe discovery, progress memory, and next-move selection."""
import json
import os
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


if __name__ == "__main__":
    unittest.main()
