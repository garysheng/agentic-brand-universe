"""Tests for the standing prompt guards.

This file had NO tests until 2026-08-06, which is how the guards' own docstring came to
claim the rules "live HERE, once, and both generators import them" while two byte-identical
copies of the file sat in two provider directories. `run-tests.sh` discovered
`skills/*/tests/` and `engine/tests` and never looked in `providers/`, so the chokepoint
every render passes through was the least tested file in the repo.
"""
import importlib.util
import pathlib
import sys
import unittest

HERE = pathlib.Path(__file__).resolve()
PROVIDERS = HERE.parents[2]
GPT = PROVIDERS / "gpt-image-2" / "prompt_guards.py"
NANO = PROVIDERS / "nano-banana-pro" / "prompt_guards.py"


def load(path):
    spec = importlib.util.spec_from_file_location(f"pg_{path.parent.name}", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


pg = load(GPT)


class TestCopiesAgree(unittest.TestCase):
    def test_both_provider_copies_are_byte_identical(self):
        """A duplicated rule is almost never duplicated exactly twice. The file says so
        itself, and then was duplicated. If these ever diverge, one generator silently
        renders under a different rulebook."""
        self.assertEqual(GPT.read_bytes(), NANO.read_bytes(),
                         "the two provider prompt_guards.py copies have diverged")


class TestSeatedAtTable(unittest.TestCase):
    """Earned on he-kept-the-appointment spreads 17 and 19: a seated man painted emerging
    out of the tabletop with no waist, no lap and no seat under him. It survived a
    contact-sheet read-back, a per-spread negatives list, book-doctor, and shipping."""

    def test_fires_on_a_person_seated_at_a_table(self):
        out, added = pg.apply_prompt_guards(
            "Two men sit facing each other across a laminate table in a restaurant booth.")
        self.assertIn("seated-at-table", added)
        self.assertIn("SEATED ANATOMY AT A TABLE", out)

    def test_guard_states_the_gap_and_the_lap(self):
        out, _ = pg.apply_prompt_guards("A man sitting at a desk.")
        low = out.lower()
        self.assertIn("visible gap", low)
        self.assertIn("lap", low)
        self.assertIn("never through them", low.replace("never THROUGH them".lower(), "never through them"))

    def test_quiet_on_a_table_with_nobody_at_it(self):
        """An empty-plate render of a table must not be told about seated anatomy."""
        _, added = pg.apply_prompt_guards(
            "An empty architectural plate of a laminate table, no people anywhere.")
        self.assertNotIn("seated-at-table", added)

    def test_quiet_on_a_seated_person_with_no_table(self):
        _, added = pg.apply_prompt_guards(
            "A boy sits alone on a wooden pew in an empty room.")
        self.assertNotIn("seated-at-table", added)

    def test_idempotent_second_application_does_not_restack(self):
        once, added1 = pg.apply_prompt_guards("A man seated at a table.")
        twice, added2 = pg.apply_prompt_guards(once)
        self.assertIn("seated-at-table", added1)
        self.assertNotIn("seated-at-table", added2)
        self.assertEqual(once.count("SEATED ANATOMY AT A TABLE"), 1)
        self.assertEqual(twice.count("SEATED ANATOMY AT A TABLE"), 1)

    def test_the_guards_own_wording_does_not_retrigger_a_sibling_guard(self):
        """The scan strips already-appended guard text before looking for trigger words.
        _GUARD_SEATED contains the word 'table', so it must be stripped too or a second
        pass re-fires on the guard's own prose."""
        once, _ = pg.apply_prompt_guards("A man seated at a table.")
        _, added2 = pg.apply_prompt_guards(once)
        self.assertEqual(added2, [], f"a second pass added {added2}")

    def test_disabled_adds_nothing(self):
        out, added = pg.apply_prompt_guards("A man seated at a table.", enabled=False)
        self.assertEqual(added, [])
        self.assertNotIn("SEATED ANATOMY", out)


class TestTwoHanderStaging(unittest.TestCase):
    """Two failures, in sequence, because the fix for the first causes the second.
    Both earned on he-kept-the-appointment spreads 17 and 19, both by operator correction.
    Naming the shot `over-shoulder` in the render-spec prevented neither."""

    # This is the shape of the ROUND-ONE prompt, the one that produced a man growing out
    # of the tabletop. The guard has to fire on THIS, not merely on prompts that already
    # say "over-the-shoulder" -- a scene that already knew the answer never needed a guard.
    ROUND_ONE = ("Two men sit facing each other across a laminate table in a restaurant booth, "
                 "both seen from the waist up, side-on to the camera at seated eye height.")

    def test_fires_on_the_prompt_shape_that_actually_failed(self):
        out, added = pg.apply_prompt_guards(self.ROUND_ONE)
        self.assertIn("two-hander-staging", added)
        self.assertIn("ONE OF THEM IS NEAR AND ONE IS FAR", out)

    def test_states_the_near_far_split(self):
        out, _ = pg.apply_prompt_guards(self.ROUND_ONE)
        low = out.lower()
        self.assertIn("cropped by the frame edge", low)
        self.assertIn("out of focus", low)
        self.assertIn("sharp subject", low)

    def test_states_the_torso_follows_the_head(self):
        """Round two: head swivelled ninety degrees on a chest still square to the lens."""
        out, _ = pg.apply_prompt_guards(self.ROUND_ONE)
        low = out.lower()
        self.assertIn("torso follows the head", low)
        self.assertIn("chest and shirt front are not in frame", low)
        self.assertIn("ninety degrees", low)

    def test_quiet_on_a_lone_person_at_a_table(self):
        """A solo scene has no near/far split to make, so the guard must stay out of it."""
        _, added = pg.apply_prompt_guards(
            "A young man sits alone at a desk at night, bent over a spiral notebook.")
        self.assertNotIn("two-hander-staging", added)

    def test_quiet_on_two_people_with_no_table(self):
        _, added = pg.apply_prompt_guards(
            "Two men stand facing each other in a wide empty forecourt.")
        self.assertNotIn("two-hander-staging", added)

    def test_seated_guard_still_fires_alongside_it(self):
        _, added = pg.apply_prompt_guards(self.ROUND_ONE)
        self.assertIn("seated-at-table", added)

    def test_idempotent(self):
        once, a1 = pg.apply_prompt_guards(self.ROUND_ONE)
        twice, a2 = pg.apply_prompt_guards(once)
        self.assertIn("two-hander-staging", a1)
        self.assertEqual(a2, [], f"a second pass added {a2}")
        self.assertEqual(twice.count("TWO-HANDER STAGING"), 1)


class TestExistingGuardsStillFire(unittest.TestCase):
    """Regression net: the new guard must not disturb the ones already shipped."""

    def test_device_guard(self):
        _, added = pg.apply_prompt_guards("She looks at her phone.")
        self.assertIn("device-anatomy", added)

    def test_surface_guard(self):
        _, added = pg.apply_prompt_guards("An open notebook on a bare floor.")
        self.assertIn("readable-surface", added)


if __name__ == "__main__":
    unittest.main(verbosity=1)
