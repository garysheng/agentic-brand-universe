#!/usr/bin/env python3
"""LAPTOP_FORM_GUARD: the laptop is the most-drawn object in these universes.

Earned 2026-08-28 on a Nation of Fire cover — a field of laptops receding to a
horizon, every one of them rendered with TWO bases (a deck in front of the screen
and a second slab behind it), and the distant ranks drawn as half-remembered
shapes on plinths.

The scene text had said "a screen standing up from the FAR edge of that base",
which never states WHICH SIDE the deck extends. The model drew one on each side
and was not wrong to. That is the shape of this whole class of bug: the prompt was
ambiguous, not the renderer.

It belongs in the framework rather than in one book because hyperagentic-age's
central motif IS `supercharged-laptop`, and every article hero across eleven wikis
passes it through on-brand-image. Fixing it per-book would have left all of them
wrong.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import importlib.util

_p = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                  "scripts", "assemble_prompt.py")
_spec = importlib.util.spec_from_file_location("assemble_prompt", _p)
ap = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ap)


class Predicate(unittest.TestCase):
    def test_it_fires_on_a_laptop_merely_being_present(self):
        """WIDER than the device-USE guard on purpose. An empty room of laptops
        gets the geometry wrong just as readily as one somebody is typing on."""
        self.assertTrue(ap._has_laptop("A laptop alone on a kitchen table at first light."))

    def test_it_fires_on_a_field_of_them(self):
        self.assertTrue(ap._has_laptop("a regular grid of identical laptops receding to a horizon"))

    def test_it_fires_regardless_of_case(self):
        self.assertTrue(ap._has_laptop("A MACBOOK on the desk"))
        self.assertTrue(ap._has_laptop("an open Clamshell machine"))

    def test_it_does_not_fire_when_no_laptop_is_present(self):
        """A guard that fires on everything costs prompt budget on every spread
        and teaches authors to ignore it."""
        self.assertFalse(ap._has_laptop("A phone lying flat on a table, screen up."))
        self.assertFalse(ap._has_laptop("Two men talking on a porch at sunset."))
        self.assertFalse(ap._has_laptop(""))
        self.assertFalse(ap._has_laptop(None))


class GuardText(unittest.TestCase):
    def test_it_names_the_direction_the_deck_extends(self):
        """The whole defect was an unstated direction."""
        g = ap.LAPTOP_FORM_GUARD
        self.assertIn("TOWARD THE VIEWER", g)
        self.assertIn("BACK edge", g)

    def test_it_forbids_the_second_base_explicitly(self):
        g = ap.LAPTOP_FORM_GUARD
        self.assertIn("EXACTLY ONE BASE", g)
        self.assertIn("BEHIND THE SCREEN THERE IS NOTHING", g)

    def test_it_tells_the_renderer_what_to_do_when_the_form_cannot_resolve(self):
        """The second half of the fix: at distance, draw glow rather than a
        malformed object. Without this the far ranks come back as guesses."""
        g = ap.LAPTOP_FORM_GUARD
        self.assertIn("dissolve", g.lower())
        self.assertIn("draw glow instead", g)


class Wiring(unittest.TestCase):
    def test_the_guard_is_actually_emitted_into_the_prompt(self):
        """A guard defined and never applied is decoration. Read the source of
        the assembly to prove the constant is referenced beside its predicate."""
        src = open(_p, encoding="utf8").read()
        self.assertIn("LAPTOP_FORM_GUARD if _has_laptop(scene)", src,
                      "the guard must be wired into the assembled prompt")


if __name__ == "__main__":
    unittest.main(verbosity=2)
