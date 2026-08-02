"""Nested settings (SPEC v0.29): LAW inherits, ART never does.

Earned 2026-08-02 on nation-of-fire. `christofuturist-home` held nine rooms under one
flat contract, so the sunken pit's FIXED LETTERED SEATING had nowhere to live and the
room had to be promoted to a top-level sibling. Promotion then silently dropped the
house rules, and `everyone-indoors-wears-the-house-slippers` was hand-copied onto the
child. These tests pin the fix and, just as importantly, pin what must NOT inherit.
"""
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agenticstory.nesting import (
    resolve, parent_chain, problems, NestingError, MAX_DEPTH,
)

HOUSE = {
    "id": "a-house", "kind": "setting",
    "contract": {
        "map": "the whole house", "blocking": "house-wide", "dressing": "cream plaster and oak.",
        "scale": "a house", "turnaround": "reference/a-house/turnaround.png",
        "blueprint": "reference/a-house/blueprint.png",
        "scalePlate": "reference/a-house/scale.png",
        "blockingPlate": "reference/a-house/blocking.png",
        "emptyPlates": ["reference/a-house/hearth.png"],
    },
    "structured": {
        "sheets": {"hearth": "reference/a-house/hearth.png"},
        # the parent's OWN, room-scoped rules. These must NOT reach a child.
        "invariants": ["studyNook ONLY: exactly two armchairs"],
        "render": {"always": "House master plate.", "qa": ["the study nook has two armchairs"]},
        # the block a parent explicitly shares with every nested room
        "houseRules": {
            "invariants": ["shoes-come-off-indoors"],
            "dressing": "cream plaster and oak.",
        },
    },
}
ROOM = {
    "id": "a-room", "kind": "setting", "partOf": "a-house",
    "contract": {
        "map": "one sunken room", "blocking": "SEAT A left, SEAT B right", "scale": "one room",
        "dressing": "two benches and a low table.",
        "turnaround": "reference/a-room/turnaround.png",
        "blueprint": "reference/a-room/blueprint.png",
        "emptyPlates": ["reference/a-room/wide.png"],
    },
    "structured": {
        "sheets": {"wide": "reference/a-room/wide.png"},
        "invariants": ["seat-a-is-left-and-never-swaps"],
        "render": {"always": "A sunken conversation pit.", "qa": ["the pit reads as sunken"]},
    },
}

def loader(*ents):
    d = {e["id"]: e for e in ents}
    return lambda eid: d.get(eid)


class TestLawInherits(unittest.TestCase):
    def setUp(self):
        self.m = resolve(loader(HOUSE, ROOM), "a-room")

    def test_house_rule_reaches_the_room(self):
        """The bug this feature exists for: the child got no house rules."""
        self.assertIn("shoes-come-off-indoors", self.m["structured"]["invariants"])
        self.assertIn("seat-a-is-left-and-never-swaps", self.m["structured"]["invariants"])

    def test_house_rules_come_first_and_dedup(self):
        inv = self.m["structured"]["invariants"]
        self.assertEqual(inv.index("shoes-come-off-indoors"), 0)
        dup = resolve(loader(HOUSE, {**ROOM, "structured": {
            **ROOM["structured"], "invariants": ["shoes-come-off-indoors", "x"]}}), "a-room")
        self.assertEqual(dup["structured"]["invariants"].count("shoes-come-off-indoors"), 1)

    def test_a_parents_OWN_room_scoped_rules_never_reach_a_sibling_room(self):
        """The bug that blind inheritance introduced, caught on real canon.

        Every setting invariant becomes a render-readback QA check, so leaking
        `studyNook ONLY: exactly two armchairs` into the pit would grade the pit on
        furniture it is not supposed to have.
        """
        inv = self.m["structured"]["invariants"]
        self.assertNotIn("studyNook ONLY: exactly two armchairs", inv)
        self.assertNotIn("the study nook has two armchairs",
                         self.m["structured"]["render"]["qa"])
        self.assertNotIn("House master plate", self.m["structured"]["render"]["always"])

    def test_a_parent_with_no_houseRules_shares_nothing(self):
        bare = {**HOUSE, "structured": {k: v for k, v in HOUSE["structured"].items()
                                        if k != "houseRules"}}
        m = resolve(loader(bare, ROOM), "a-room")
        self.assertEqual(m["structured"]["invariants"], ["seat-a-is-left-and-never-swaps"])
        self.assertEqual(m["contract"]["dressing"], "two benches and a low table.")

    def test_dressing_appends_parent_then_child(self):
        self.assertEqual(self.m["contract"]["dressing"],
                         "cream plaster and oak. two benches and a low table.")

    def test_the_childs_own_render_block_is_untouched(self):
        """Only invariants and dressing inherit; the child's render block is its own."""
        self.assertEqual(self.m["structured"]["render"]["always"], "A sunken conversation pit.")
        self.assertEqual(self.m["structured"]["render"]["qa"], ["the pit reads as sunken"])

    def test_child_wins_on_geometry(self):
        for f, want in (("map", "one sunken room"),
                        ("blocking", "SEAT A left, SEAT B right"),
                        ("scale", "one room")):
            self.assertEqual(self.m["contract"][f], want)


class TestArtNeverInherits(unittest.TestCase):
    """The failure mode that would be worse than the one we are fixing."""
    def test_parent_plates_do_not_leak_into_the_child(self):
        m = resolve(loader(HOUSE, ROOM), "a-room")
        self.assertEqual(m["contract"]["emptyPlates"], ["reference/a-room/wide.png"])
        self.assertEqual(list(m["structured"]["sheets"]), ["wide"])
        self.assertNotIn("hearth", m["structured"]["sheets"])
        self.assertEqual(m["contract"]["turnaround"], "reference/a-room/turnaround.png")

    def test_a_child_missing_a_file_field_does_not_borrow_one(self):
        bare = {k: v for k, v in ROOM.items()}
        bare["contract"] = {k: v for k, v in ROOM["contract"].items() if k != "blueprint"}
        m = resolve(loader(HOUSE, bare), "a-room")
        self.assertIsNone(m["contract"].get("blueprint"),
                          "a child with no blueprint must FAIL the gate, never inherit one")
        self.assertIsNone(m["contract"].get("scalePlate"))
        self.assertIsNone(m["contract"].get("blockingPlate"))


class TestNoOpKeysRefuse(unittest.TestCase):
    """A field that silently does nothing is worse than one that errors."""
    def test_always_and_qa_are_refused_by_name(self):
        for bad in ("always", "qa"):
            house = {**HOUSE, "structured": {**HOUSE["structured"],
                     "houseRules": {"invariants": ["r"], bad: "x"}}}
            with self.assertRaises(NestingError) as cm:
                resolve(loader(house, ROOM), "a-room")
            msg = str(cm.exception)
            self.assertIn(bad, msg)
            self.assertIn("dressing", msg, "the error must name the field that DOES work")


class TestChainSafety(unittest.TestCase):
    def test_no_partOf_is_unchanged(self):
        self.assertEqual(resolve(loader(HOUSE), "a-house"), dict(HOUSE))
        self.assertEqual(parent_chain(loader(HOUSE), "a-house"), [])
        self.assertEqual(problems(loader(HOUSE), "a-house"), [])

    def test_cycle_is_named_not_recursed(self):
        a = {"id": "a", "kind": "setting", "partOf": "b"}
        b = {"id": "b", "kind": "setting", "partOf": "a"}
        with self.assertRaises(NestingError) as cm:
            parent_chain(loader(a, b), "a")
        self.assertIn("cycle", str(cm.exception))
        self.assertIn("a", str(cm.exception)); self.assertIn("b", str(cm.exception))
        self.assertTrue(problems(loader(a, b), "a"))

    def test_missing_parent_is_named(self):
        orphan = {"id": "o", "kind": "setting", "partOf": "ghost"}
        with self.assertRaises(NestingError) as cm:
            parent_chain(loader(orphan), "o")
        self.assertIn("ghost", str(cm.exception))

    def test_parent_must_be_a_setting(self):
        guy = {"id": "guy", "kind": "character"}
        bad = {"id": "r", "kind": "setting", "partOf": "guy"}
        with self.assertRaises(NestingError) as cm:
            parent_chain(loader(guy, bad), "r")
        self.assertIn("character", str(cm.exception))

    def test_depth_is_bounded(self):
        ents = [{"id": f"n{i}", "kind": "setting", "partOf": f"n{i+1}"}
                for i in range(MAX_DEPTH + 3)]
        ents.append({"id": f"n{MAX_DEPTH + 3}", "kind": "setting"})
        with self.assertRaises(NestingError) as cm:
            parent_chain(loader(*ents), "n0")
        self.assertIn("deeper than", str(cm.exception))

    def test_grandparent_law_reaches_the_grandchild(self):
        estate = {"id": "estate", "kind": "setting",
                  "structured": {"houseRules": {"invariants": ["estate-rule"]}}}
        house = {**HOUSE, "partOf": "estate"}
        m = resolve(loader(estate, house, ROOM), "a-room")
        self.assertEqual(m["structured"]["invariants"][:2],
                         ["estate-rule", "shoes-come-off-indoors"])
        self.assertEqual(m["_inheritedFrom"], ["estate", "a-house"])


if __name__ == "__main__":
    unittest.main()
