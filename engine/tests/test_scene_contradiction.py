"""The scene must not assert what a cast entity's invariants forbid.

Earned 2026-08-27. An entity was recoloured from gold to blue and 22 of 42 spreads still
said "warm gold volume of light" in their scene text. The plates were blue and canon was
blue, and every one of those spreads rendered GOLD, because the scene is the instruction
and the plate is only conditioning. Fixing the ENTITY and re-rendering produced the same
gold, which is what makes this worth a guard: the obvious fix does not work.

NOTE: unittest TestCases on purpose. run-tests.sh drives `unittest discover`, which does
not collect bare pytest-style functions, so a pytest-shaped test here would "pass" by
never running at all.
"""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills" / "compose-spread" / "scripts"))

import audit_spec_refs as A  # noqa: E402


def _ent(invariants):
    return {"structured": {"invariants": invariants}}


class ForbiddenPhrases(unittest.TestCase):
    def test_extracts_the_forbidden_half(self):
        self.assertIn("gold", A.forbidden_phrases(_ent(["cool-white-blue-light-never-gold"])))

    def test_several_negatives_in_one_slug(self):
        got = A.forbidden_phrases(_ent(["coral-orange-light-never-blue-never-sacred-gold"]))
        self.assertIn("blue", got)
        self.assertIn("sacred gold", got)

    def test_strips_the_article(self):
        self.assertIn("full beard", A.forbidden_phrases(_ent(["clean-shaven-never-a-full-beard"])))

    def test_ignores_words_too_short_to_be_signal(self):
        self.assertEqual([], A.forbidden_phrases(_ent(["never-two", "no-ui"])))


class ClaimedPhrases(unittest.TestCase):
    def test_stops_at_the_negative_half(self):
        claimed = A.claimed_phrases(_ent(["cool-white-blue-light-never-gold"]))
        self.assertIn("blue", claimed)
        self.assertNotIn("gold", claimed,
                         "the forbidden half must not read as a positive claim")


class SceneContradictions(unittest.TestCase):
    def setUp(self):
        self._real = A.ap.load_entity

    def tearDown(self):
        A.ap.load_entity = self._real

    def _with(self, ents):
        A.ap.load_entity = lambda uroot, eid: ents[eid]

    def test_a_word_another_entity_claims_is_not_a_contradiction(self):
        # An orange kernel that forbids blue, in frame with a blue shell that claims
        # blue, is a CORRECT picture. Flagging it buries the real signal: the first
        # version of this guard fired 12 times on a clean spec for exactly this reason.
        self._with({"kernel": _ent(["coral-orange-light-never-blue"]),
                    "shell": _ent(["cool-white-blue-light-never-gold"])})
        self.assertEqual([], A.scene_contradictions(
            Path("."), "a blue phone above an orange cube", ["kernel", "shell"]))

    def test_the_real_defect_is_caught(self):
        self._with({"shell": _ent(["cool-white-blue-light-never-gold"])})
        self.assertEqual(
            [("shell", "gold")],
            A.scene_contradictions(Path("."), "A WARM GOLD VOLUME OF LIGHT", ["shell"]))

    def test_a_missing_entity_never_crashes_the_audit(self):
        A.ap.load_entity = lambda uroot, eid: (_ for _ in ()).throw(KeyError(eid))
        self.assertEqual([], A.scene_contradictions(Path("."), "gold", ["nope"]))


if __name__ == "__main__":
    unittest.main()
