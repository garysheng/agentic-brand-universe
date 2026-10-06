"""The scaffolded gate CHOOSES its engine (v0.60): the first of $AGENTICSTORY_ENGINE, the baked
path and the newest installed abu plugin that conforms to at least the spec the universe pins.

Earned 2026-10-06: continental-works pinned spec v0.58 while its gate ran an engine checkout at
v0.51, so every check added since was silently absent, and the first new craft kind (`kit`) then
failed there as "unknown craft kind", which reads as a defect in canon rather than in the engine.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agenticstory import scaffold


def fake_engine(where: Path, spec: str) -> Path:
    (where / "agenticstory").mkdir(parents=True)
    (where / "agenticstory" / "__init__.py").write_text(f'SPEC_VERSION = "{spec}"\n')
    return where


class AssertEngineTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="abu-engine-"))
        self.uni = self.tmp / "u"
        (self.uni / "canon" / "scripts").mkdir(parents=True)
        (self.uni / "universe.json").write_text(json.dumps({"name": "u", "spec": {"version": "0.60"}}))
        self.baked = fake_engine(self.tmp / "checkout" / "engine", "0.51")
        gate = self.uni / "canon" / "scripts" / "assert.sh"
        gate.write_text(scaffold._assert_sh(self.baked))
        self.gate = gate
        self.home = self.tmp / "home"
        self.cache = self.home / ".claude" / "plugins" / "cache" / "agentic-brand-universe" / "abu"

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_gate(self, env_engine: str | None = None):
        env = {k: v for k, v in os.environ.items() if k not in ("AGENTICSTORY_ENGINE", "CLAUDE_CONFIG_DIR")}
        env["HOME"] = str(self.home)
        if env_engine:
            env["AGENTICSTORY_ENGINE"] = env_engine
        return subprocess.run(["bash", str(self.gate), "engine"], capture_output=True, text=True, env=env)

    def test_a_stale_baked_engine_is_refused_and_every_candidate_is_named(self):
        fake_engine(self.cache / "1.39.0" / "engine", "0.58")
        r = self.run_gate()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn("conforms to spec v0.60", r.stderr)
        self.assertIn("(spec v0.51)", r.stderr)
        self.assertIn("(spec v0.58)", r.stderr)

    def test_the_newest_current_plugin_is_chosen_over_a_stale_checkout(self):
        fake_engine(self.cache / "1.39.0" / "engine", "0.58")
        fake_engine(self.cache / "1.41.0" / "engine", "0.60")
        fake_engine(self.cache / "1.9.0" / "engine", "0.20")   # 1.9 < 1.41: numeric, not lexical
        r = self.run_gate()
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(r.stdout.strip(), str(self.cache / "1.41.0" / "engine"))

    def test_a_current_override_wins_and_a_stale_one_falls_through(self):
        cur = fake_engine(self.tmp / "wt" / "engine", "0.61")
        self.assertEqual(self.run_gate(str(cur)).stdout.strip(), str(cur))
        old = fake_engine(self.tmp / "old" / "engine", "0.40")
        fake_engine(self.cache / "1.41.0" / "engine", "0.60")
        self.assertEqual(self.run_gate(str(old)).stdout.strip(), str(self.cache / "1.41.0" / "engine"))

    def test_a_current_baked_engine_is_used(self):
        (self.baked / "agenticstory" / "__init__.py").write_text('SPEC_VERSION = "0.60"\n')
        self.assertEqual(self.run_gate().stdout.strip(), str(self.baked))


if __name__ == "__main__":
    unittest.main()
