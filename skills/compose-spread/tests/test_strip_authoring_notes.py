"""assemble_prompt.strip_authoring_notes — tests.

A setting's contract map/blocking/dressing/scale is injected into the prompt verbatim,
and authors write notes to each other in those fields. A model cannot tell a description
of the place from an instruction about the book, so it renders the instruction AS the
place: on 2026-08-04 encounter-san-antonio's sign board, whose canon map reads
"(BLANK on the plate; spread 30 bakes exactly ENCOUNTER SAN ANTONIO)", came back
lettered "30 BAKES EXACTLY ENCOUNTER SAN ANTONIO".

These tests pin BOTH directions: authoring meta is removed, and ordinary description
(including parentheticals and the word "plate" meaning a dinner plate) survives.

Run:  python3 -m unittest discover -s tests -v   (from the compose-spread skill dir)
"""
import sys
import unittest
from importlib import util
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_spec = util.spec_from_file_location("ap", SCRIPTS / "assemble_prompt.py")
ap = util.module_from_spec(_spec)
sys.modules["ap"] = ap
_spec.loader.exec_module(ap)
strip = ap.strip_authoring_notes


class StripsAuthoringMeta(unittest.TestCase):
    def test_the_encounter_san_antonio_case(self):
        got = strip("one large display window left of the glass front door; plain wooden "
                    "sign board above the door (BLANK on the plate; spread 30 bakes exactly "
                    "ENCOUNTER SAN ANTONIO); mesquite tree at the curb.")
        self.assertNotIn("bakes", got.lower())
        self.assertNotIn("spread 30", got.lower())
        self.assertIn("sign board above the door", got)
        self.assertIn("mesquite tree", got)

    def test_note_to_a_reviewer_is_dropped(self):
        got = strip("Warm wood floors. This is REMOVED in the overflow spreads; "
                    "record so QA does not 'fix' its presence/absence.")
        self.assertIn("Warm wood floors.", got)
        self.assertNotIn("QA", got)
        self.assertNotIn("record so", got)

    def test_a_spread_citing_parenthetical_is_dropped(self):
        got = strip("Cords hang from the rafters (spread 23 on) above the table.")
        self.assertNotIn("spread 23", got.lower())
        self.assertIn("Cords hang from the rafters", got)
        self.assertIn("above the table", got)

    def test_earned_on_date_author_note_is_dropped(self):
        got = strip("The congregation faces the platform. Earned 2026-08-01 on this "
                    "book's spreads 24 and 26, where a front camera returned backs of heads.")
        self.assertIn("congregation faces the platform", got)
        self.assertNotIn("Earned 2026", got)

    def test_gabr_and_render_spec_references_are_dropped(self):
        self.assertNotIn("gabr", strip("Fixed floor plan (blueprint gabr-23): north wall is glass.").lower())
        self.assertNotIn("render-spec", strip("Oak beams. The render-spec picks the camera.").lower())


class KeepsRealDescription(unittest.TestCase):
    def test_ordinary_parentheticals_survive(self):
        got = strip("Fixed floor plan (north up). The piano (the teaching bench) sits west.")
        self.assertIn("(north up)", got)
        self.assertIn("(the teaching bench)", got)

    def test_a_dinner_plate_is_not_authoring_vocabulary(self):
        got = strip("A blue dinner plate sits on the table beside a folded napkin.")
        self.assertEqual(got, "A blue dinner plate sits on the table beside a folded napkin.")

    def test_the_word_bakes_alone_survives(self):
        got = strip("The baker bakes bread in the stone oven each morning.")
        self.assertIn("bakes bread", got)

    def test_empty_and_non_string_are_safe(self):
        self.assertEqual(strip(""), "")
        self.assertEqual(strip("   "), "")
        self.assertEqual(strip(None), "")

    def test_clean_prose_is_returned_unchanged(self):
        s = "One long room, polished concrete floor, rows of black stacking chairs."
        self.assertEqual(strip(s), s)


class DoesNotEatContinuityRules(unittest.TestCase):
    """A sentence that merely CITES a spread number usually carries a durable rule.
    Dropping those caused a worse defect than the noise this function removes: an
    earlier draft ate "After spread 19 Malik has none, forever" out of the-cords'
    blocking, which would put cords back on a character canon says is free of them."""

    def test_a_rule_that_cites_where_it_starts_survives(self):
        s = ("Cords attach ONLY to Malik (1-19) and Curtis (22); never to Naomi. "
             "After spread 19 Malik has none, forever.")
        got = strip(s)
        self.assertIn("After spread 19 Malik has none, forever.", got)

    def test_per_spread_state_in_a_global_field_is_left_alone(self):
        """Per-spread state in a global field is a canon-SHAPE problem whose real fix is
        contract.plates. A prompt filter must not paper over it by deleting the content."""
        s = ("Spread 25 state: open to a page with one empty drawn box. "
             "Spread 35 state: open to page one, a single handwritten sentence.")
        self.assertNotEqual(strip(s), "")
        self.assertIn("empty drawn box", strip(s))

    def test_a_parenthetical_that_names_people_survives_its_spread_cite(self):
        """(Nyanya, Neema, Baraka, and the child in spread 30) says WHO a rule applies
        to. Deleting it leaves the rule with its subjects removed, which is a continuity
        defect, not a cleanup."""
        s = ("The gold thread attaches to the clean bloodline (Nyanya, Neema, Baraka, "
             "and the child in spread 30). The grey cord attaches ONLY to the Linked "
             "(Jabari after spread 17).")
        got = strip(s)
        self.assertIn("Nyanya", got)
        self.assertIn("Baraka", got)
        self.assertIn("Jabari", got)

    def test_a_bookkeeping_only_parenthetical_is_still_dropped(self):
        self.assertNotIn("spread", strip("Cords hang from the rafters (spreads 1-2).").lower())
        self.assertNotIn("spread", strip("A lamp on the sill (spread 23 on).").lower())


if __name__ == "__main__":
    unittest.main()
