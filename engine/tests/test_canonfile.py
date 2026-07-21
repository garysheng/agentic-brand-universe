"""CANON.md as a derived artifact: the race, the corruption, and the rescue.

These tests exist because the hand-appended version of this file accumulated ten
duplicate crossover numbers in production without git ever raising a conflict.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenticstory import canonfile as cf

CANON_SKELETON = f"""# Test universe canon

## Properties registry

Some hand-authored prose that must survive a rebuild.

{cf.PROPS_BEGIN}
{cf.PROPS_END}

## Crossover log

{cf.XOVER_BEGIN}
{cf.XOVER_END}

## The mark

Trailing prose that must also survive.
"""


def prop(uroot, rid, name, order):
    (cf.props_dir(uroot) / f"{rid}.json").write_text(json.dumps({
        "id": rid, "order": order, "property": name, "form": "Picture book",
        "status": "SHIPPED", "home": f"x/{rid}", "cast": "cast notes"}, indent=2))


def xover(uroot, rid, summary, n=None):
    rec = {"id": rid, "summary": summary, "properties": "A x B", "status": "Canon"}
    if n is not None:
        rec["n"] = n
    (cf.xover_dir(uroot) / f"{rid}.json").write_text(json.dumps(rec, indent=2))


class CanonFileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        cf.props_dir(self.tmp).mkdir(parents=True)
        cf.xover_dir(self.tmp).mkdir(parents=True)
        (self.tmp / "CANON.md").write_text(CANON_SKELETON)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def build(self):
        (self.tmp / "CANON.md").write_text(cf.build(self.tmp))
        return (self.tmp / "CANON.md").read_text()

    # ---- the core property: concurrent authors cannot collide ----

    def test_unnumbered_records_get_distinct_numbers(self):
        """Two runs each author a record with NO number. The old scheme had both
        read max and write max+1; here numbers are assigned once, at build."""
        xover(self.tmp, "run-a", "first run's crossover")
        xover(self.tmp, "run-b", "second run's crossover")
        self.build()
        ns = [json.loads(p.read_text())["n"] for p in cf.xover_dir(self.tmp).glob("*.json")]
        self.assertEqual(len(ns), len(set(ns)), "two concurrent records collided on a number")

    def test_existing_numbers_are_preserved(self):
        """Prose cites 'crossover #88'; a rebuild must not renumber it."""
        xover(self.tmp, "cited", "a crossover referenced elsewhere", n=88)
        xover(self.tmp, "fresh", "a new one with no number")
        self.build()
        self.assertEqual(json.loads((cf.xover_dir(self.tmp) / "cited.json").read_text())["n"], 88)
        self.assertGreater(json.loads((cf.xover_dir(self.tmp) / "fresh.json").read_text())["n"], 88)

    def test_assignment_is_persisted_so_it_is_stable(self):
        xover(self.tmp, "fresh", "no number yet")
        self.build()
        first = json.loads((cf.xover_dir(self.tmp) / "fresh.json").read_text())["n"]
        self.build()
        second = json.loads((cf.xover_dir(self.tmp) / "fresh.json").read_text())["n"]
        self.assertEqual(first, second)

    # ---- the corruption that shipped ----

    def test_duplicate_numbers_are_detected(self):
        xover(self.tmp, "one", "a", n=7)
        xover(self.tmp, "two", "b", n=7)
        self.assertEqual(cf.duplicate_numbers(cf.load_crossovers(self.tmp)), [7])
        self.assertTrue(any("duplicate crossover number 7" in p for p in cf.check(self.tmp)))

    # ---- projection integrity ----

    def test_build_is_idempotent(self):
        prop(self.tmp, "b", "Book B", 1)
        xover(self.tmp, "x", "crossover", n=1)
        self.assertEqual(self.build(), self.build())

    def test_prose_outside_the_blocks_survives(self):
        prop(self.tmp, "b", "Book B", 1)
        out = self.build()
        self.assertIn("Some hand-authored prose that must survive a rebuild.", out)
        self.assertIn("Trailing prose that must also survive.", out)

    def test_properties_render_newest_first(self):
        prop(self.tmp, "old", "Older Book", 1)
        prop(self.tmp, "new", "Newer Book", 2)
        out = self.build()
        self.assertLess(out.index("Newer Book"), out.index("Older Book"))

    def test_check_flags_a_stale_file(self):
        prop(self.tmp, "b", "Book B", 1)
        self.build()
        prop(self.tmp, "c", "Book C", 2)  # record added, file not rebuilt
        self.assertTrue(any("stale" in p for p in cf.check(self.tmp)))

    # ---- the rescue path for a run that appended the old way ----

    def test_adopt_ingests_hand_appended_rows(self):
        prop(self.tmp, "b", "Book B", 1)
        self.build()
        canon = self.tmp / "CANON.md"
        canon.write_text(canon.read_text().replace(
            cf.XOVER_END,
            "| 999 | hand appended by a concurrent run | A x B | Canon |\n" + cf.XOVER_END))
        created = cf.adopt(self.tmp)
        self.assertEqual(len(created), 1)
        self.assertIn("| 999 |", self.build())
        self.assertEqual(cf.check(self.tmp), [])

    def test_adopt_is_idempotent(self):
        prop(self.tmp, "b", "Book B", 1)
        self.build()
        self.assertEqual(cf.adopt(self.tmp), [])

    # ---- parsing ----

    def test_separator_rows_are_not_parsed_as_data(self):
        rows = cf.parse_property_rows(
            "| Property | Form | Status | Home | Cast |\n"
            "|---|---|---|---|---|\n"
            "| Real Book | form | status | home | cast |\n")
        self.assertEqual([r["property"] for r in rows], ["Real Book"])


if __name__ == "__main__":
    unittest.main()
