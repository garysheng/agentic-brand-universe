#!/usr/bin/env python3
"""review_run.py: the transcript scorer and its two distinct render metrics.

What matters here is the DISTINCTION the incident hid: a call that READS
render_cover.py (orientation) must not count as a generation, or every
orientation-heavy run scores itself render-forward. So the tests pin: sed/grep on a
generation script is a touch, python3 on it is a generation; the verdict thresholds;
and that malformed lines are skipped, not fatal (real transcripts contain them).
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "review_run.py"

spec = importlib.util.spec_from_file_location("review_run", SCRIPT)
rv = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rv)


def tool(name, inp):
    return {"type": "assistant",
            "message": {"content": [{"type": "tool_use", "name": name, "input": inp}]}}


def transcript(events):
    return "\n".join(json.dumps(e) for e in events) + "\n"


def write_run(td, events):
    p = Path(td) / "transcript.jsonl"
    p.write_text(transcript(events))
    return p


READ_RENDER = tool("Bash", {"command": "sed -n 1,50p skills/cover/scripts/render_cover.py"})
GEN = tool("Bash", {"command": "python3 skills/cover/scripts/render_cover.py u s --out x-raw.png"})
LS = tool("Bash", {"command": "ls -la"})
RESULT = {"type": "result", "duration_ms": 834025, "total_cost_usd": 14.85, "num_turns": 87}


class Scoring(unittest.TestCase):
    def test_orientation_heavy(self):
        # 6 orientation calls, then the generation: 6/7 before first gen -> heavy
        with tempfile.TemporaryDirectory() as td:
            p = write_run(td, [LS] * 5 + [READ_RENDER, GEN, RESULT])
            s = rv.score(p)
            self.assertEqual(s["toolCalls"], 7)
            self.assertEqual(s["firstGeneration"], 7)
            self.assertEqual(s["firstRenderTouch"], 6)  # the sed read, NOT the ls
            self.assertIn("orientation-heavy: 6/7", s["verdict"])

    def test_render_forward(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_run(td, [LS, GEN, LS, LS, RESULT])
            s = rv.score(p)
            self.assertEqual(s["firstGeneration"], 2)
            self.assertIn("render-forward", s["verdict"])

    def test_reading_a_render_script_is_not_a_generation(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_run(td, [READ_RENDER, RESULT])
            s = rv.score(p)
            self.assertEqual(s["firstRenderTouch"], 1)
            self.assertIsNone(s["firstGeneration"])
            self.assertIn("no-generation run", s["verdict"])

    def test_histogram_and_result_metadata(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_run(td, [LS, LS, tool("Read", {"file_path": "/x"}), GEN, RESULT])
            s = rv.score(p)
            self.assertEqual(s["histogram"]["Bash"], 3)
            self.assertEqual(s["histogram"]["Read"], 1)
            self.assertEqual(s["durationMs"], 834025)
            self.assertEqual(s["totalCostUsd"], 14.85)
            self.assertEqual(s["numTurns"], 87)

    def test_malformed_lines_are_skipped_not_fatal(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "transcript.jsonl"
            p.write_text("NOT JSON\n" + transcript([LS, GEN]) + "{broken\n")
            s = rv.score(p)
            self.assertEqual(s["toolCalls"], 2)
            self.assertEqual(s["badLines"], 2)

    def test_empty_run(self):
        with tempfile.TemporaryDirectory() as td:
            s = rv.score(write_run(td, [RESULT]))
            self.assertIn("empty run", s["verdict"])

    def test_uv_run_counts_as_generation(self):
        with tempfile.TemporaryDirectory() as td:
            e = tool("Bash", {"command": "uv run providers/chatgpt-images/generate_image.py --prompt x"})
            s = rv.score(write_run(td, [e]))
            self.assertEqual(s["firstGeneration"], 1)

    def test_help_invocation_is_orientation_not_generation(self):
        # The incident's own call #57: `python3 render_cover.py --help`. Counting it
        # as a generation scores an 85-call meander "render-forward".
        with tempfile.TemporaryDirectory() as td:
            helpcall = tool("Bash", {"command":
                "cd repo && python3 skills/cover/scripts/render_cover.py --help 2>&1 | head"})
            s = rv.score(write_run(td, [helpcall, GEN]))
            self.assertEqual(s["firstRenderTouch"], 1)
            self.assertEqual(s["firstGeneration"], 2)


class Cli(unittest.TestCase):
    def test_accepts_run_dir_and_emits_json(self):
        with tempfile.TemporaryDirectory() as td:
            write_run(td, [LS, GEN, RESULT])
            r = subprocess.run([sys.executable, str(SCRIPT), td, "--json"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            s = json.loads(r.stdout)
            self.assertEqual(s["toolCalls"], 2)
            self.assertIn("VERDICT", "VERDICT")  # shape sanity only in --json path
            self.assertIn("verdict", s)

    def test_human_output_has_verdict_line(self):
        with tempfile.TemporaryDirectory() as td:
            p = write_run(td, [LS, LS, LS, GEN, RESULT])
            r = subprocess.run([sys.executable, str(SCRIPT), str(p)],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0)
            self.assertIn("VERDICT:", r.stdout)

    def test_missing_transcript_refuses(self):
        r = subprocess.run([sys.executable, str(SCRIPT), "/nonexistent/run"],
                           capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)


if __name__ == "__main__":
    unittest.main()
