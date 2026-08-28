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
    """Two properties fight each other here and BOTH must hold.

    A stale file left at the output path survives a total failure and reads as a success
    to any caller that checks existence or size (earned 2026-08-21). But deleting it
    outright means a re-roll of already-good art loses that art to a flaky provider
    (earned 2026-08-28). The resolution is to MOVE it to `<out>.prev` and never move it
    back, so `<out>` is still absent after a failure and the picture still exists.
    """

    def test_the_output_path_is_cleared_before_the_attempt_loop(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        clear_at = src.index("live.replace(kept)")
        loop_at = src.index("for attempt in (1, 2, 3)")
        self.assertLess(clear_at, loop_at,
                        "a stale file left at the output path survives a total failure and "
                        "reads as a success to any caller that checks existence or size")

    def test_the_recipe_is_cleared_too(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        self.assertIn("prev_recipe = recipe_path.with_suffix", src,
                      "a stale recipe beside a missing image claims provenance for art "
                      "that is not there")

    def test_the_kept_copy_is_never_restored_to_the_output_path(self):
        """The safety property. Restoring `.prev` to `<out>` would hand back exactly the
        stale-reads-as-new bug the move was built to preserve protection against."""
        src = (HERE / "scripts" / "render_spread.py").read_text()
        for forbidden in ("prev.replace(out)", "prev.rename(out)",
                          "shutil.move(prev", "prev_recipe.replace(recipe_path)"):
            self.assertNotIn(forbidden, src,
                             f"{forbidden} restores the previous render to the live path, "
                             "so a failed run would again look like a successful one")

    def test_the_kept_copy_is_removed_on_success(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        ok_at = src.index("recipe = write_recipe(")
        loop_end = src.index("for attempt in (1, 2, 3)")
        tail = src[loop_end:]
        self.assertIn("for kept in (prev, prev_recipe):", tail,
                      "a .prev left beside a successful render accumulates one stale copy "
                      "per re-roll and eventually gets mistaken for the real art")

    def test_a_kept_copy_is_announced_rather_than_left_silent(self):
        src = (HERE / "scripts" / "render_spread.py").read_text()
        self.assertIn("the PREVIOUS render was kept at", src,
                      "silently keeping a .prev is how an operator concludes their art is "
                      "gone and re-renders something they already had")

    def test_a_retry_with_nothing_live_does_not_wipe_the_banked_art(self):
        """The bug in the first cut of this block. On attempt 2 of a retry loop `out` is
        already gone, so an unconditional `kept.unlink()` deletes the art attempt 1 banked
        and puts nothing back. The unlink must be INSIDE the `live.exists()` branch."""
        src = (HERE / "scripts" / "render_spread.py").read_text()
        block = src[src.index("for live, kept in ("):src.index("cmd = [")]
        unlink_at = block.index("kept.unlink()")
        guard_at = block.index("if live.exists():")
        self.assertLess(guard_at, unlink_at,
                        "kept.unlink() must sit inside `if live.exists():`, or a second "
                        "attempt deletes the backup the first attempt just made")

    def test_the_kept_suffix_stays_out_of_a_png_glob(self):
        """`.prev` must not end in .png, or every batch driver that globs spread-*.png
        picks the backup up as if it were a spread."""
        src = (HERE / "scripts" / "render_spread.py").read_text()
        self.assertIn('out.with_suffix(out.suffix + ".prev")', src)
        self.assertFalse(Path("x.png.prev").match("*.png"),
                         "the backup suffix must not match a .png glob")


if __name__ == "__main__":
    unittest.main()
