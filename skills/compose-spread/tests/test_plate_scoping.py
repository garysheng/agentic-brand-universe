#!/usr/bin/env python3
"""A close-up plate must not be told the whole room's blocking law.

resolve_setting used to inject the entire contract on every render regardless of
camera. `blocking` is room-wide law ("sixteen guests seated in the tiers"), so a close
two-shot of two chairs was still told the room was full of seated people; the model put
them in and re-invented them each time, because no plate showed them at that distance.
Earned 2026-07-30 in nation-of-fire.
"""
import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
from assemble_prompt import resolve_setting

ENT = {
    "id": "the-teaching-room",
    "structured": {"sheets": {"master": "reference/r/master.png",
                              "chairsCloseUp": "reference/r/chairs.png"}},
    "contract": {
        "map": "A long directional room.",
        "blocking": "SIXTEEN GUESTS SEATED IN THE TIERS in two banks either side of a centre aisle.",
        "dressing": "Honey timber and brass.",
        "scale": "Five metres at the ridge.",
        "plates": {"chairsCloseUp": {
            "note": "Only the two chairs and the side table are in frame.",
            "includeBlocking": False}},
    },
}


class TestPlateScoping(unittest.TestCase):
    def test_wide_plate_still_gets_the_blocking_law(self):
        refs, block = resolve_setting(ENT, "master")
        self.assertEqual(refs, ["reference/r/master.png"])
        self.assertIn("SIXTEEN GUESTS", block)
        self.assertIn("A long directional room.", block)

    def test_close_plate_drops_blocking_and_gains_its_note(self):
        refs, block = resolve_setting(ENT, "chairsCloseUp")
        self.assertEqual(refs, ["reference/r/chairs.png"])
        self.assertNotIn("SIXTEEN GUESTS", block,
                         "the close-up was told the room is full of seated people")
        self.assertIn("Only the two chairs", block)
        self.assertIn("Honey timber and brass.", block, "dressing must survive scoping")

    def test_unconfigured_setting_is_unchanged(self):
        """Every existing universe must render byte-identically."""
        plain = {"id": "x", "structured": {"sheets": {"master": "m.png"}},
                 "contract": {"map": "M.", "blocking": "B.", "dressing": "D.", "scale": "S."}}
        _, block = resolve_setting(plain, "master")
        self.assertEqual(block, "x exactly as its reference plate: M. B. D. S.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
