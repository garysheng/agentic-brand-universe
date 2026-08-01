"""compose-spread render_spread.py — BATCH MODE tests. Stdlib unittest.

Every case runs with `--dry-run`, so the model is never called and the suite
costs nothing. What is under test is the batch PLUMBING: id resolution, `--all`,
`--out-dir` naming, the mutual-exclusion errors, and the exit-code contract.

WHY BATCH MODE EXISTS (2026-07-31). This script took exactly ONE spread id, so
every book grew the same throwaway parallel driver beside it: a ThreadPoolExecutor
over this same subprocess plus a skip-if-exists the script already implemented.
`pave-the-path` flagged "the renderer's own batch mode" after
she-had-everything-but-peace and it was not built; the-power-of-obeying wrote the
identical driver again a day later. The second occurrence is the bar.

The load-bearing test is `test_one_bad_spread_does_not_abort_the_batch`: a
69-spread render is expensive, and a driver that aborts on the first refusal
throws away every spread that would have landed after it.

Run:  python3 -m unittest discover -s tests -v   (from the compose-spread skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RENDER = SCRIPTS / "render_spread.py"
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_assemble_prompt import build_universe, png  # noqa: E402


def spec_with(root: Path, ids, bad=()):
    """A render-spec of N renderable spreads, plus any `bad` ones that will
    refuse (they cast an entity the synthetic universe does not have)."""
    spreads = [{"id": i, "setting": "home", "plate": "kitchen",
                "scene": "the two brothers at the table",
                "cast": [{"id": "clean"}]} for i in ids]
    for b in bad:
        spreads.append({"id": b, "setting": "home", "plate": "kitchen",
                        "scene": "someone who does not exist",
                        "cast": [{"id": "nobody-at-all"}]})
    p = root / "render-spec.json"
    p.write_text(json.dumps({
        "size": "1536x1024",
        "style": "warm test style.",
        "negatives": ["no text anywhere"],
        "spreads": spreads,
    }))
    return p


def run(root, spec, *args):
    r = subprocess.run([sys.executable, str(RENDER), str(root), str(spec), *args],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


class TestBatchRender(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    # ── the single-spread path must be untouched ─────────────────────────────

    def test_single_spread_with_out_is_unchanged(self):
        spec = spec_with(self.root, ["s1"])
        code, out = run(self.root, spec, "s1", "--out",
                        str(self.root / "x.png"), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("s1: DRY RUN ok", out)

    def test_single_spread_still_needs_an_output_path(self):
        spec = spec_with(self.root, ["s1"])
        code, out = run(self.root, spec, "s1", "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("--out", out)

    def test_no_ids_and_no_all_is_an_error(self):
        spec = spec_with(self.root, ["s1"])
        code, out = run(self.root, spec, "--out-dir", str(self.root / "o"), "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("--all", out)

    # ── batch ────────────────────────────────────────────────────────────────

    def test_named_ids_render_to_out_dir(self):
        spec = spec_with(self.root, ["s1", "s2", "s3"])
        code, out = run(self.root, spec, "s1", "s3",
                        "--out-dir", str(self.root / "o"), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("s1: DRY RUN ok", out)
        self.assertIn("s3: DRY RUN ok", out)
        self.assertNotIn("s2:", out)
        self.assertIn("2/2 ok", out)

    def test_all_renders_every_declared_spread(self):
        spec = spec_with(self.root, ["s1", "s2", "s3", "s4"])
        code, out = run(self.root, spec, "--all",
                        "--out-dir", str(self.root / "o"), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("4/4 ok", out)

    def test_out_and_out_dir_are_mutually_exclusive(self):
        spec = spec_with(self.root, ["s1", "s2"])
        code, out = run(self.root, spec, "--all", "--out", str(self.root / "x.png"),
                        "--out-dir", str(self.root / "o"), "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("mutually exclusive", out)

    def test_out_alone_refuses_to_name_many_files(self):
        spec = spec_with(self.root, ["s1", "s2"])
        code, out = run(self.root, spec, "s1", "s2",
                        "--out", str(self.root / "x.png"), "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("--out-dir", out)

    def test_skip_existing_skips_only_what_is_on_disk(self):
        spec = spec_with(self.root, ["s1", "s2"])
        outdir = self.root / "o"
        png(outdir / "s1.png")
        code, out = run(self.root, spec, "--all", "--out-dir", str(outdir),
                        "--skip-existing", "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("s1: exists, skip", out)
        self.assertIn("s2: DRY RUN ok", out)

    # ── the reason batch mode is not just a for-loop ─────────────────────────

    def test_one_bad_spread_does_not_abort_the_batch(self):
        """A 69-spread book is expensive. A driver that stops at the first
        refusal throws away every spread that would have landed after it."""
        spec = spec_with(self.root, ["s1", "s2", "s3"], bad=["oops"])
        code, out = run(self.root, spec, "--all",
                        "--out-dir", str(self.root / "o"), "--dry-run")
        self.assertEqual(code, 2, out)
        self.assertIn("s1: DRY RUN ok", out)
        self.assertIn("s2: DRY RUN ok", out)
        self.assertIn("s3: DRY RUN ok", out)
        self.assertIn("REFUSED", out)
        self.assertIn("oops", out)

    def test_parallel_batch_reports_every_spread(self):
        spec = spec_with(self.root, [f"s{i}" for i in range(1, 9)])
        code, out = run(self.root, spec, "--all", "--jobs", "4",
                        "--out-dir", str(self.root / "o"), "--dry-run")
        self.assertEqual(code, 0, out)
        self.assertIn("8/8 ok", out)
        for i in range(1, 9):
            self.assertIn(f"s{i}: DRY RUN ok", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
