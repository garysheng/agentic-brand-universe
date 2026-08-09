#!/usr/bin/env python3
"""The migrator the BAKE-USED-AS-A-SELECTOR refusal names must exist and must agree
with the guard.

The refusal has pointed at `migrate_render_spec.py translate` since the guard shipped,
and the file shipped nowhere: takeoff-thursdays (hyperagentic-age, 2026-08) hand-rolled
the translation as declared debt, the second hand-roll of the same translation. These
tests pin the contract: detection is the guard's own predicate (a translated entry can
never still be refused), prose bakes survive untouched, and --write is explicit.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
from assemble_prompt import Refuse, _selector_bake_guard  # noqa: E402
from migrate_render_spec import translate  # noqa: E402

METAPHOR = {
    "id": "the-candle",
    "kind": "visual-metaphor",
    "structured": {"sheets": {"againstTheLight": "reference/c/against-the-light.png"}},
}
CHARACTER = {
    "id": "jerry-man",
    "kind": "character",
    "structured": {"sheets": {"man": "reference/j/man.png"},
                   "render": {"poses": {"front": {}, "work-back": {}}}},
}
PROSE_BAKE = ("Render the candle in exactly one state, the against-the-light state "
              "shown in its reference plate, and no other.")


def scaffold(tmp: Path) -> Path:
    ents = tmp / "canon" / "entities"
    ents.mkdir(parents=True)
    for e in (METAPHOR, CHARACTER):
        (ents / f"{e['id']}.json").write_text(json.dumps(e))
    return tmp


def spec_dict():
    return {
        "book": "b", "story": "s",
        "spreads": [
            {"id": "spread-01", "cast": [{"id": "the-candle", "bake": "against-the-light"}]},
            {"id": "spread-02", "cast": [{"id": "jerry-man", "bake": "work-back"}]},
            {"id": "spread-03", "cast": [{"id": "the-candle", "bake": PROSE_BAKE}]},
        ],
    }


class TestTranslate(unittest.TestCase):
    def test_selector_bakes_become_selectors_and_prose_survives(self):
        with tempfile.TemporaryDirectory() as d:
            uroot = scaffold(Path(d))
            spec = spec_dict()
            rows = translate(uroot, spec)
            self.assertEqual(len(rows), 2)
            c1 = spec["spreads"][0]["cast"][0]
            self.assertEqual(c1.get("plate"), "againstTheLight")
            self.assertNotIn("bake", c1)
            c2 = spec["spreads"][1]["cast"][0]
            self.assertEqual(c2.get("pose"), "work-back")
            self.assertNotIn("bake", c2)
            c3 = spec["spreads"][2]["cast"][0]
            self.assertEqual(c3.get("bake"), PROSE_BAKE, "a prose bake is not a selector")

    def test_translated_entries_pass_the_guard(self):
        """The whole point: a migrated spec cannot still be refused for what it migrated."""
        with tempfile.TemporaryDirectory() as d:
            uroot = scaffold(Path(d))
            spec = spec_dict()
            with self.assertRaises(Refuse):
                _selector_bake_guard(spec["spreads"][0]["cast"][0], METAPHOR, "spread-01")
            translate(uroot, spec)
            for sp, ent in zip(spec["spreads"], (METAPHOR, CHARACTER, METAPHOR)):
                _selector_bake_guard(sp["cast"][0], ent, sp["id"])  # must not raise

    def test_cli_dry_run_leaves_the_file_alone_and_write_backs_up(self):
        with tempfile.TemporaryDirectory() as d:
            uroot = scaffold(Path(d))
            spec_path = Path(d) / "render-spec.json"
            spec_path.write_text(json.dumps(spec_dict(), indent=2))
            before = spec_path.read_text()
            env = dict(os.environ)
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "migrate_render_spec.py"),
                 "translate", str(uroot), str(spec_path)],
                capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertIn("DRY RUN", r.stdout)
            self.assertEqual(spec_path.read_text(), before, "dry run must not write")
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "migrate_render_spec.py"),
                 "translate", str(uroot), str(spec_path), "--write"],
                capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            after = json.loads(spec_path.read_text())
            self.assertEqual(after["spreads"][0]["cast"][0].get("plate"), "againstTheLight")
            bak = spec_path.with_suffix(".json.pre-migrate.bak")
            self.assertTrue(bak.exists(), "previous bytes must survive beside the spec")
            self.assertEqual(bak.read_text(), before)


if __name__ == "__main__":
    unittest.main()
