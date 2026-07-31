#!/usr/bin/env python3
"""An explicit JSON `null` must not kill the linter.

`d.get("k", [])` returns the DEFAULT only when the key is ABSENT. When the key is
present and null it returns None, and iterating None raises. A linter that dies
mid-run reports nothing at all, so one null field in one recipe hides every real
finding in the universe — the failure mode is silence, not a message.

Found on a real universe 2026-07-31 via `"inputs": null` in a golden recipe. It was
the SECOND crash from that same line; the first was bare-string inputs. Hence these
tests cover every field where a hand-written or tool-written null is plausible.
"""
import ast, pathlib, re, unittest

LINT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "lint.py"
SRC = LINT.read_text()


class TestNullSafety(unittest.TestCase):
    def test_no_get_with_a_list_default_is_iterated_unguarded(self):
        """The bug class, caught structurally rather than by example.

        Any `.get("k", [])` is a latent crash the moment someone writes `"k": null`.
        The house idiom is `(.get("k") or [])`, which handles absent AND null.
        """
        bad = re.findall(r'\.get\("([a-zA-Z]+)", \[\]\)', SRC)
        self.assertEqual(bad, [], f"unguarded .get(...,[]) on: {bad}. Use (.get(x) or []).")

    def test_lint_still_parses(self):
        ast.parse(SRC)

    def test_the_inputs_site_is_guarded(self):
        self.assertIn('for inp in (rec.get("inputs") or []):', SRC)

    def test_the_guard_is_explained_not_just_applied(self):
        """A bare `or []` reads as style. The next person needs to know it is a fix."""
        i = SRC.index('for inp in (rec.get("inputs") or []):')
        self.assertIn("null", SRC[max(0, i - 500):i].lower())


class TestNoneIterationIsSafe(unittest.TestCase):
    def test_the_idiom_itself(self):
        """Pin the semantics the fix depends on, so nobody 'simplifies' it back."""
        absent, null = {}, {"inputs": None}
        self.assertEqual(absent.get("inputs", []), [])
        self.assertIsNone(null.get("inputs", []))      # the whole bug, in one line
        self.assertEqual(null.get("inputs") or [], [])  # the fix


if __name__ == "__main__":
    unittest.main()
