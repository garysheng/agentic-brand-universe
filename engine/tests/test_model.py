"""Entity resolution: which sheets a render gets, and where the real-person dossier lives.

Every test here pins a defect found on 2026-08-01/02 by rendering a real person and
looking at the result. None of them would have been caught by `validate`, because each
concerns what a CORRECTLY-SHAPED entity resolves TO.
"""
import unittest

from agenticstory.model import Entity


def entity(eid="e", *, sheets=None, required=None, alt_looks=None,
           real_person=None, top_real_person=None, invariants=()):
    d = {"id": eid, "kind": "character", "name": eid,
         "structured": {"sheets": dict(sheets or {}),
                        "requiredForRender": list(required or []),
                        "invariants": list(invariants)}}
    if alt_looks:
        d["structured"]["altLooks"] = alt_looks
    if real_person is not None:
        d["structured"]["realPerson"] = real_person
    if top_real_person is not None:
        d["realPerson"] = top_real_person
    return d


class IdentitySheets(unittest.TestCase):
    """`look_sheets` answers the GATE's question; `identity_sheets` answers the RENDER's.

    Callers reused the first for the second, and the gap is invisible until you read a
    recipe: a character with NINE locked plates rendered from two, beside nine lookbook
    exemplars of other people, and came back not looking like himself.
    """

    def make(self, **kw):
        return Entity.from_dict(entity(**kw))

    def test_look_sheets_returns_only_the_required_minimum(self):
        e = self.make(sheets={"face": "a.png", "body": "b.png", "back": "c.png"},
                      required=["face"])
        self.assertEqual(set(e.look_sheets(None)), {"face"})

    def test_identity_sheets_returns_EVERY_locked_sheet(self):
        e = self.make(sheets={"face": "a.png", "body": "b.png", "back": "c.png"},
                      required=["face"])
        self.assertEqual(set(e.identity_sheets()), {"face", "body", "back"})

    def test_required_sheets_come_first_because_ref_order_is_precedence(self):
        e = self.make(sheets={"zzz": "z.png", "face": "a.png"}, required=["face"])
        self.assertEqual(list(e.identity_sheets())[0], "face")

    def test_an_alt_look_is_NOT_widened_back_to_every_base_sheet(self):
        """Widening a look would drag back exactly what `dropSheets` removed."""
        e = self.make(
            sheets={"face-neutral": "f.png", "body": "b.png", "back": "k.png"},
            required=["face-neutral", "body"],
            alt_looks={"spirit": {"sheets": {"look": "s.png"},
                                  "dropSheets": ["body"],
                                  "keepSheets": ["face-neutral"]}})
        got = set(e.identity_sheets("spirit"))
        self.assertIn("look", got)
        self.assertNotIn("body", got, "dropSheets must survive identity_sheets")
        self.assertEqual(got, set(e.look_sheets("spirit")))

    def test_a_sheet_with_no_path_is_skipped_rather_than_crashing(self):
        e = self.make(sheets={"face": "a.png", "empty": None}, required=["face"])
        self.assertEqual(set(e.identity_sheets()), {"face"})


class RealPersonDossier(unittest.TestCase):
    """TWO READERS, TWO CONVENTIONS, AND THEY DISAGREED.

    `Entity.real_person` returned the TOP-LEVEL block while `matrix.real_person_gaps`
    read `structured.realPerson`. On one entity that meant the grader and the renderer
    were reading DIFFERENT photo stacks, and nothing compared them.
    """

    def make(self, **kw):
        return Entity.from_dict(entity(**kw))

    def test_structured_wins_over_top_level(self):
        e = self.make(real_person={"photoStack": ["structured.png"]},
                      top_real_person={"photoStack": ["top.png"]})
        self.assertEqual(e.photo_stack(), ["structured.png"])

    def test_top_level_is_still_read_when_structured_is_absent(self):
        e = self.make(top_real_person={"photoStack": ["top.png"]})
        self.assertEqual(e.photo_stack(), ["top.png"])

    def test_no_dossier_yields_an_empty_stack_not_a_crash(self):
        self.assertEqual(self.make().photo_stack(), [])

    def test_an_empty_structured_block_falls_through_to_top_level(self):
        e = self.make(real_person={}, top_real_person={"photoStack": ["top.png"]})
        self.assertEqual(e.photo_stack(), ["top.png"])


class DuplicateDossierIsRefused(unittest.TestCase):
    """A canon that quietly holds two answers is worse than one that refuses to hold
    either. `validate` catches the conflict; nothing used to."""

    def conflicts(self, **kw):
        e = Entity.from_dict(entity(sheets={"face": "a.png"}, required=[], **kw))
        return [p for p in e.validate("none-required") if "DIFFER" in p]

    def test_two_dossiers_that_DIFFER_are_refused(self):
        got = self.conflicts(real_person={"photoStack": ["x.png"]},
                             top_real_person={"photoStack": ["y.png"]})
        self.assertEqual(len(got), 1, got)

    def test_two_dossiers_that_AGREE_are_fine(self):
        same = {"photoStack": ["x.png"]}
        self.assertEqual(self.conflicts(real_person=dict(same), top_real_person=dict(same)), [])

    def test_one_dossier_is_fine(self):
        self.assertEqual(self.conflicts(real_person={"photoStack": ["x.png"]}), [])
        self.assertEqual(self.conflicts(top_real_person={"photoStack": ["x.png"]}), [])

    def test_a_render_in_the_photo_stack_is_NOT_refused(self):
        """Withdrawn guard, kept as a test so it is not reintroduced.

        A stricter version refused any photoStack entry pointing at a render. It was
        removed the same hour as an opinion masquerading as a correctness check: whether
        a stack may contain renders is the universe owner's call, not the framework's
        (Gary, 2026-08-01: "im fine with ai images being references").
        """
        e = Entity.from_dict(entity(
            sheets={"face": "a.png"}, required=[],
            real_person={"photoStack": ["reference/x/blessed-renders/a.png"]}))
        self.assertEqual([p for p in e.validate("none-required") if "render" in p.lower()], [])


if __name__ == "__main__":
    unittest.main()
