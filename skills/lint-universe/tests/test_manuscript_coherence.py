"""Manuscript/spec coherence: the prose and the StorySpec must agree on unit count.

Nothing checked this, so a manuscript could drift from its spec silently and the
drift only surfaced at render, when renumbering is expensive: every later unit
shifts the render-spec, the platform manifest, the staged assets and the
narration. Run against real canon on 2026-07-26 this found FIVE pre-existing
off-by-one drifts in shipped nation-of-fire books.

FOUR marker conventions are in the wild and all are canonical. A detector that
knows only one reports zero for the rest, which reads as "unchecked" and trains
people to ignore the check.
"""
import json, pathlib, subprocess, sys, tempfile, unittest

LINT = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "lint.py"


def _universe(tmp, manuscript, n_beats, mid="s"):
    root = pathlib.Path(tmp)
    (root / "stories").mkdir(parents=True)
    (root / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": ".", "identity": {}}))
    (root / f"stories/{mid}.json").write_text(json.dumps(
        {"id": mid, "status": "full", "spine": "x", "logline": "l", "refrain": "r",
         "features": [], "beats": [{"n": i + 1, "text": "t", "provenance": "p"} for i in range(n_beats)]}))
    (root / f"stories/{mid}.manuscript.md").write_text(manuscript)
    return root


def _run(root):
    r = subprocess.run([sys.executable, str(LINT), str(root)], capture_output=True, text=True)
    return r.stdout


class ManuscriptCoherenceTest(unittest.TestCase):

    def _codes(self, manuscript, n_beats):
        with tempfile.TemporaryDirectory() as tmp:
            return _run(_universe(tmp, manuscript, n_beats))

    def test_matching_counts_produce_no_drift_error(self):
        m = "\n".join(f"**Spread {i}**: *t*\nbody\n" for i in range(1, 4))
        self.assertNotIn("MANUSCRIPT-BEAT-DRIFT", self._codes(m, 3))

    def test_drift_is_an_error(self):
        m = "\n".join(f"**Spread {i}**: *t*\nbody\n" for i in range(1, 4))
        self.assertIn("MANUSCRIPT-BEAT-DRIFT", self._codes(m, 4))

    def test_convention_spread_n_colon_inside_bold(self):
        m = "\n".join(f"**Spread {i}: Title**\nbody\n" for i in range(1, 4))
        self.assertNotIn("MANUSCRIPT-UNPARSED", self._codes(m, 3))

    def test_convention_bare_numbered_bold(self):
        m = "\n".join(f"**{i}.**\nbody\n" for i in range(1, 4))
        self.assertNotIn("MANUSCRIPT-UNPARSED", self._codes(m, 3))

    def test_convention_markdown_heading(self):
        m = "\n".join(f"## {i}\nbody\n" for i in range(1, 4))
        self.assertNotIn("MANUSCRIPT-UNPARSED", self._codes(m, 3))

    def test_a_gap_in_numbering_is_an_error(self):
        m = "**Spread 1**: *t*\nb\n\n**Spread 2**: *t*\nb\n\n**Spread 4**: *t*\nb\n"
        self.assertIn("MANUSCRIPT-NUMBERING", self._codes(m, 3))

    def test_starting_at_two_is_only_a_warning_because_the_cover_may_be_one(self):
        m = "\n".join(f"**Spread {i}**: *t*\nbody\n" for i in range(2, 5))
        out = self._codes(m, 3)
        self.assertIn("MANUSCRIPT-OFFSET", out)
        self.assertNotIn("MANUSCRIPT-NUMBERING", out)

    def test_an_unrecognised_convention_warns_rather_than_silently_passing(self):
        self.assertIn("MANUSCRIPT-UNPARSED", self._codes("Scene One\nbody\n", 3))

    def test_a_manuscript_with_no_spec_is_flagged_as_orphan(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp, "**Spread 1**: *t*\nb\n", 1)
            (root / "stories/orphan.manuscript.md").write_text("**Spread 1**: *t*\nb\n")
            self.assertIn("MANUSCRIPT-ORPHAN", _run(root))


if __name__ == "__main__":
    unittest.main()
