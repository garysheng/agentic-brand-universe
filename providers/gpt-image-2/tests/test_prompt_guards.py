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
