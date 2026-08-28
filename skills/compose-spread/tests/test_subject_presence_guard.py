#!/usr/bin/env python3
"""SUBJECT_PRESENCE_GUARD: an anonymity rule must not delete the subject.

Earned 2026-08-28 on a Nation of Fire book. Seven spreads carried BOTH a
person-as-subject line and a boilerplate anonymity line ("any other people are
distant, small and softly out of focus"). Two came back as beautiful EMPTY
ROOMS: a hall of screens with nobody arguing in front of it, and a study with an
empty chair where a man was meant to be explaining himself to a laptop.

The two instructions look unrelated when written and are in direct conflict when
read. The model resolved it the cheapest way: render the room, omit the person.
Nothing errored. Both renders were competent. Only a human looking at the
pictures caught it.
"""
import importlib.util
import os
import unittest

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "scripts", "assemble_prompt.py")
_spec = importlib.util.spec_from_file_location("assemble_prompt", _p)
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)

ANON = "Any other people are distant, small and softly out of focus, and no face is recognisable."


class Predicate(unittest.TestCase):
    def test_it_fires_on_the_conflict(self):
        """The exact shape that produced two empty rooms."""
        self.assertTrue(ap._subject_vs_background_conflict(
            "A PERSON SEEN FROM BEHIND at a desk, explaining themselves to a laptop. " + ANON))
        self.assertTrue(ap._subject_vs_background_conflict(
            "A CROWD OF PEOPLE ARGUING, seen from behind and above. " + ANON))

    def test_it_does_NOT_fire_on_an_anonymity_line_alone(self):
        """An unpeopled scene with the boilerplate is fine and must not pay for
        this guard's prompt budget."""
        self.assertFalse(ap._subject_vs_background_conflict(
            "A laptop alone on a kitchen table at first light. " + ANON))

    def test_it_does_NOT_fire_on_a_person_subject_alone(self):
        """No conflict without a de-emphasis instruction; the guard exists for
        the PAIR, not for either half."""
        self.assertFalse(ap._subject_vs_background_conflict(
            "A person seated at a desk, mid-sentence, hands raised."))

    def test_it_does_not_fire_on_empty_input(self):
        self.assertFalse(ap._subject_vs_background_conflict(""))
        self.assertFalse(ap._subject_vs_background_conflict(None))


class GuardText(unittest.TestCase):
    def test_it_says_an_empty_frame_is_a_defect(self):
        g = ap.SUBJECT_PRESENCE_GUARD
        self.assertIn("DEFECT", g)
        self.assertIn("empty", g.lower())

    def test_it_scopes_the_anonymity_rule_to_BACKGROUND_people(self):
        self.assertIn("INCIDENTAL BACKGROUND people ONLY", ap.SUBJECT_PRESENCE_GUARD)

    def test_it_names_the_RESOLUTION_not_only_the_ban(self):
        """A guard that only forbids leaves the author stuck. This one says how to
        keep anonymity AND the subject: move the camera."""
        g = ap.SUBJECT_PRESENCE_GUARD
        self.assertIn("CAMERA AND FRAMING", g)
        self.assertIn("never by removing them", g)


class Wiring(unittest.TestCase):
    def test_the_guard_is_actually_emitted(self):
        src = open(_p, encoding="utf8").read()
        self.assertIn("SUBJECT_PRESENCE_GUARD if _subject_vs_background_conflict(scene)", src,
                      "a guard defined and never applied is decoration")


if __name__ == "__main__":
    unittest.main(verbosity=2)
