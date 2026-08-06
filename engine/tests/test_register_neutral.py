"""`structured.registerNeutral` (SPEC v0.37 §12) — the declaration itself.

The shooter FAILS CLOSED on this reader, so the reader's contract is load-bearing:
a malformed declaration must RAISE, never return None, because None means "shoot
this matrix against the register anchor" and that is the exact outcome the field
exists to forbid.
"""
import unittest

from agenticstory.matrix import (REGISTER_NEUTRAL_CONTRACT, register_neutral,
                                 register_neutral_untyped_slots)
from agenticstory.model import Entity


def ent(rn=None, sheets=None, eid="russ"):
    st = {"sheets": sheets if sheets is not None else {"face-neutral": "a.png"}}
    if rn is not None:
        st["registerNeutral"] = rn
    return {"id": eid, "kind": "character", "structured": st}


GOOD = {"medium": "hyper-realistic documentary photography",
        "why": "one photoreal master; every register is a conversion of it"}


class TestReader(unittest.TestCase):
    def test_absent_is_none(self):
        self.assertIsNone(register_neutral(ent()))
        self.assertIsNone(register_neutral(ent(rn=False)))
        self.assertIsNone(register_neutral({}))

    def test_a_well_formed_declaration_is_returned(self):
        self.assertEqual(register_neutral(ent(rn=GOOD))["medium"], GOOD["medium"])

    def test_a_bare_true_raises_rather_than_reading_as_absent(self):
        """FAIL CLOSED. Returning None here would shoot the master in-register."""
        with self.assertRaises(ValueError) as c:
            register_neutral(ent(rn=True))
        self.assertIn("must be an OBJECT", str(c.exception))

    def test_no_medium_raises(self):
        with self.assertRaises(ValueError) as c:
            register_neutral(ent(rn={"why": "x"}))
        self.assertIn("no `medium`", str(c.exception))

    def test_a_blank_medium_is_not_a_medium(self):
        with self.assertRaises(ValueError):
            register_neutral(ent(rn={"medium": "   ", "why": "x"}))

    def test_no_why_raises(self):
        with self.assertRaises(ValueError) as c:
            register_neutral(ent(rn={"medium": "photoreal"}))
        self.assertIn("no `why`", str(c.exception))


class TestUntypedSlots(unittest.TestCase):
    def test_untyped_slots_are_reported(self):
        e = ent(rn=GOOD, sheets={"face-neutral": "a.png",
                                 "face-3q": {"path": "b.png", "role": "identity"},
                                 "back": "c.png"})
        self.assertEqual(register_neutral_untyped_slots(e), ["back", "face-neutral"])

    def test_a_fully_typed_entity_reports_nothing(self):
        e = ent(rn=GOOD, sheets={"face-neutral": {"path": "a.png", "role": "identity"}})
        self.assertEqual(register_neutral_untyped_slots(e), [])

    def test_an_entity_without_the_declaration_reports_nothing(self):
        self.assertEqual(register_neutral_untyped_slots(ent()), [])


class TestValidate(unittest.TestCase):
    def problems(self, raw):
        return Entity(id=raw["id"], kind=raw["kind"], raw=raw).validate()

    def test_a_good_declaration_adds_no_problem(self):
        self.assertEqual([p for p in self.problems(ent(rn=GOOD))
                          if "registerNeutral" in p], [])

    def test_a_malformed_declaration_is_refused(self):
        self.assertTrue(any("must be an OBJECT" in p for p in self.problems(ent(rn=True))))

    def test_role_medium_is_refused_on_a_register_neutral_entity(self):
        """A contradiction in terms: the entity declares its plates carry no register,
        so no plate of it may be passed AS the medium."""
        e = ent(rn=GOOD, sheets={"face-neutral": {"path": "a.png", "role": "medium"}})
        self.assertTrue(any("role is 'medium'" in p for p in self.problems(e)))

    def test_role_medium_is_fine_on_an_ordinary_entity(self):
        e = ent(sheets={"face-neutral": {"path": "a.png", "role": "medium"}})
        self.assertEqual([p for p in self.problems(e) if "role is 'medium'" in p], [])


class TestContract(unittest.TestCase):
    def test_the_contract_names_the_thing_that_is_not_passed(self):
        """The SPEC block is PROJECTED from this list, so the list is the contract."""
        joined = " ".join(REGISTER_NEUTRAL_CONTRACT)
        self.assertIn("anchor IMAGE is not passed", joined)
        self.assertIn("--no-style-pack", joined)


if __name__ == "__main__":
    unittest.main()
