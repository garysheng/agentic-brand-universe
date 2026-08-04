"""voice-gate voice_gate.py — tests. Stdlib unittest, no network, no API keys.

Every test here is a real regression. The two that matter most:

- `test_totalizing_inside_dialogue_is_caught` reproduces the bug that let Gary's
  complaint be true. Quoted spans used to be blanked wholesale, and a picture book is
  almost entirely authored dialogue inside quotes, so the manuscript was exempt from its
  own voice rules and "That is the whole shape of a sermon" shipped through a gate that
  had already run.
- `test_the_entire_is_the_same_rule_as_the_whole` covers the wordlist that only ever
  said "whole", which is why every "the entire ___" passed for months.

Run:  python3 -m unittest discover -s tests -v   (from the voice-gate skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "voice_gate.py"
sys.path.insert(0, str(SCRIPT.parent))
import voice_gate as vg  # noqa: E402


def run(tmp: Path, body: str, waivers=None, universe: dict | None = None):
    """Check a manuscript, offline. Returns (exit code, stdout)."""
    (tmp / "universe.json").write_text(json.dumps(
        universe if universe is not None
        else {"identity": {"voice": {"capitalize": [], "oneWord": []}}}))
    man = tmp / "story.manuscript.md"
    man.write_text(body)
    if waivers is not None:
        vg.default_waivers(man).write_text(json.dumps({"waived": waivers}))
    p = subprocess.run([sys.executable, str(SCRIPT), "--offline", str(tmp), str(man)],
                       capture_output=True, text=True)
    return p.returncode, p.stdout


class VoiceGate(unittest.TestCase):

    def check(self, body, **kw):
        with tempfile.TemporaryDirectory() as d:
            return run(Path(d), body, **kw)

    # --- the rule Gary named -------------------------------------------------

    def test_totalizing_inside_dialogue_is_caught(self):
        code, out = self.check('"That is the whole shape of a sermon, Des."')
        self.assertEqual(code, 1)
        self.assertIn("totalizing-emphasis", out)
        self.assertIn("the whole shape", out)

    def test_the_entire_is_the_same_rule_as_the_whole(self):
        code, out = self.check("That is what we were building the entire time.")
        self.assertEqual(code, 1)
        self.assertIn("the entire time", out)

    def test_two_hits_on_one_line_stay_distinguishable(self):
        """A waiver is keyed on the matched text, so duplicates must not collide."""
        _, out = self.check("the only place in the whole Bible. Bring the whole tenth.")
        self.assertIn("the whole Bible", out)
        self.assertIn("the whole tenth", out)

    # --- what must NOT fire --------------------------------------------------

    def test_scripture_blockquote_is_exempt(self):
        code, out = self.check("> Bring the whole tithe into the storehouse.")
        self.assertEqual(code, 0, out)

    def test_closing_verse_convention_is_exempt(self):
        """Books end on Scripture under this marker, not as a blockquote."""
        code, out = self.check("**Closing verse.**\n"
                               '"Bring the whole tithe into the storehouse."\n')
        self.assertEqual(code, 0, out)

    def test_temporal_just_is_not_filler(self):
        code, out = self.check("Every single thing you just told me is true.")
        self.assertEqual(code, 0, out)

    def test_filler_just_still_fires(self):
        code, out = self.check("This is just better than the old way.")
        self.assertEqual(code, 1)
        self.assertIn("filler", out)

    # --- severity tiers ------------------------------------------------------

    def test_em_dash_blocks(self):
        code, out = self.check("He waited — and then he obeyed.")
        self.assertEqual(code, 1)
        self.assertIn("BLOCKING", out)

    def test_capitalize_term_is_advisory_and_never_blocks(self):
        code, out = self.check(
            "He walked in the spirit.",
            universe={"identity": {"voice": {"capitalize": ["Spirit"], "oneWord": []}}})
        self.assertIn("ADVISORY", out)
        self.assertEqual(code, 0, out)

    def test_clean_text_passes(self):
        code, out = self.check("He obeyed on Friday, and the light held.")
        self.assertEqual(code, 0, out)

    # --- waivers -------------------------------------------------------------

    def test_waiver_with_a_reason_clears_the_gate(self):
        line = "She read it under the covers, the whole thing."
        code, out = self.check(line, waivers=[{
            "rule": "totalizing-emphasis", "match": "the whole thing", "line": line,
            "reason": "concrete: she read all of it, and cutting it loses that"}])
        self.assertEqual(code, 0, out)
        self.assertIn("waived: 1", out)

    def test_todo_reason_waives_nothing(self):
        """An emitted stub is not a decision."""
        line = "She read it under the covers, the whole thing."
        code, _ = self.check(line, waivers=[{
            "rule": "totalizing-emphasis", "match": "the whole thing", "line": line,
            "reason": "TODO: why this one stays"}])
        self.assertEqual(code, 1)

    def test_waiver_retires_when_the_line_changes(self):
        """The reasoning was about a sentence that no longer exists."""
        code, out = self.check(
            "She read it under the covers, the whole series.",
            waivers=[{"rule": "totalizing-emphasis", "match": "the whole thing",
                      "line": "She read it under the covers, the whole thing.",
                      "reason": "concrete"}])
        self.assertEqual(code, 1)
        self.assertIn("STALE WAIVERS", out)

    def test_emit_waivers_produces_parseable_stubs(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            (tmp / "universe.json").write_text('{"identity":{"voice":{}}}')
            man = tmp / "story.manuscript.md"
            man.write_text("That is the whole point of it.")
            p = subprocess.run([sys.executable, str(SCRIPT), "--offline", str(tmp),
                                str(man), "--emit-waivers"], capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
            stubs = json.loads(p.stdout)["waived"]
            self.assertTrue(stubs)
            self.assertEqual(stubs[0]["rule"], "totalizing-emphasis")

    # --- universe-local oneWord terms ----------------------------------------

    def test_one_word_term_does_not_fire_on_a_shared_prefix(self):
        """The regression that blocked a whole manuscript over the word 'Christ'.

        `oneWord: ["Christofuturist"]` used to compile to `Christ[ -]\\w`, so in a
        universe whose books are about Jesus, every ordinary "Christ will", "Christ
        was", "Christ and" was a BLOCKING misspelling. Caught on the Nation of Fire
        book God Does Not Need Our Help, on the line "Christ will not come back
        because we ended homelessness".
        """
        uni = {"identity": {"voice": {"capitalize": [], "oneWord": ["Christofuturist"]}}}
        with tempfile.TemporaryDirectory() as d:
            code, out = run(Path(d), "Christ will not come back because we ended it.\n",
                            universe=uni)
        self.assertNotIn("one-word-term", out)
        self.assertEqual(code, 0, out)

    def test_one_word_term_still_catches_a_real_split(self):
        """The fix must not buy its silence by checking nothing."""
        uni = {"identity": {"voice": {"capitalize": [], "oneWord": ["Christofuturist"]}}}
        for bad in ("A Christo futurist village.", "A Christo-futurist village."):
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as d:
                code, out = run(Path(d), bad + "\n", universe=uni)
            self.assertIn("one-word-term", out, bad)
            self.assertNotEqual(code, 0, bad)

    def test_one_word_term_leaves_the_correct_spelling_alone(self):
        uni = {"identity": {"voice": {"capitalize": [], "oneWord": ["Christofuturist"]}}}
        with tempfile.TemporaryDirectory() as d:
            code, out = run(Path(d), "A Christofuturist village stands there.\n",
                            universe=uni)
        self.assertNotIn("one-word-term", out)
        self.assertEqual(code, 0, out)

    # --- the published spec --------------------------------------------------

    def test_offline_falls_back_to_the_vendored_spec(self):
        spec = vg.fetch_spec(offline=True)
        self.assertEqual(spec.origin, "vendored")
        self.assertTrue(spec.text, "the vendored spec copy is missing or empty")

    def test_vendored_spec_matches_the_hash_the_rules_were_derived_from(self):
        """The drift alarm is only meaningful if the baseline is honest."""
        self.assertTrue(vg.fetch_spec(offline=True).current,
                        "vendored voice.md does not match RULES_DERIVED_FROM: run "
                        "`voice_gate.py --adopt-spec` and port any new rule")

    def test_drift_fails_the_gate(self):
        """A rule added upstream is a rule this gate silently stops enforcing."""
        moved = vg.SpecSource("deadbeef", "network", "# Voice\nnew rule\n")
        self.assertFalse(moved.current)


if __name__ == "__main__":
    unittest.main()
