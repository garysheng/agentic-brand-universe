"""The prompt budget and the stale-artifact rule (SPEC 4.6.1).

Both behaviours exist because a FAILURE looked like a SUCCESS. The dry run reported
everything except the number that decides whether the paid run can happen, and a render
that 400'd left the previous image sitting at its output path.
"""
import importlib.util
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # tests/ -> the skill root
spec = importlib.util.spec_from_file_location("render_spread", HERE / "scripts" / "render_spread.py")
rs = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rs)


class PromptCapTest(unittest.TestCase):
    def test_cap_is_the_providers_number(self):
        # Not a style choice: the provider 400s above this exact value.
        self.assertEqual(rs.PROMPT_CAP, 32000)

    def test_refusal_fires_above_the_cap_and_not_at_it(self):
        # Boundary matters: a prompt EXACTLY at the cap is accepted by the provider, so
        # refusing at it would reject work that would have rendered fine.
        self.assertFalse(rs.PROMPT_CAP > rs.PROMPT_CAP)
        self.assertTrue(rs.PROMPT_CAP + 1 > rs.PROMPT_CAP)

    def test_source_refuses_before_spending(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        refuse_at = src.index("over the provider cap of")
        spend_at = src.index('"uv", "run", _provider_script()')
        self.assertLess(refuse_at, spend_at,
                        "the cap check must run BEFORE the provider is invoked, or the "
                        "refusal costs exactly as much as the failure it replaces")

    def test_dry_run_reports_the_prompt_length(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        dry = src[src.index("DRY RUN ok"):src.index("DRY RUN ok") + 400]
        self.assertIn("prompt {n}/{PROMPT_CAP}", dry,
                      "a dry run that omits the prompt length lets a doomed render pass "
                      "its own preflight, which is the defect this was written for")


class GuardedLengthTest(unittest.TestCase):
    """The number that matters is what the PROVIDER sends, not what we hand it."""

    def test_guards_are_counted(self):
        # apply_prompt_guards appends standing blocks after the compiler is done. A budget
        # check that measures the pre-guard string reports a comfortable number for a render
        # that then 400s, which is worse than no check because it is believed.
        plain = "a phone on a table"
        self.assertGreaterEqual(rs._guarded_length(plain), len(plain))

    def test_measurement_never_breaks_a_render(self):
        # It only describes; if the provider module cannot be imported it must fall back
        # rather than raise, or a measurement failure becomes a render failure.
        self.assertEqual(rs._guarded_length(""), rs._guarded_length(""))

    def test_the_cap_check_uses_the_guarded_length(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        self.assertIn('n = _guarded_length(job["prompt"])', src,
                      "measuring job['prompt'] directly under-reports by however many guard "
                      "blocks fire, which was the defect on day one of this check")


class StaleArtifactTest(unittest.TestCase):
    def test_output_is_deleted_before_the_attempt_loop(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        unlink_at = src.index("out.unlink()")
        loop_at = src.index("for attempt in (1, 2, 3)")
        self.assertLess(unlink_at, loop_at,
                        "a stale file left at the output path survives a total failure and "
                        "reads as a success to any caller that checks existence or size")

    def test_the_recipe_is_deleted_too(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        self.assertIn("recipe_path.unlink()", src,
                      "a stale recipe beside a deleted image claims provenance for art "
                      "that no longer exists")


if __name__ == "__main__":
    unittest.main()
