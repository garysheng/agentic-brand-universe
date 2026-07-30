#!/usr/bin/env python3
"""compose-spec must refresh what canon determines and never touch what a human wrote.

The failure it exists to prevent: a per-book authoring script that regenerates the spec
wholesale, so hand edits made after the first run are silently reverted on the next one.
Observed 2026-07-30 in nation-of-fire, where the stale generator still carried an
identity-overriding bake and crowd prose that six hours of fixes had removed.
"""
import json, os, subprocess, sys, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "compose_spec.py"


def _universe(tmp):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "stories").mkdir(parents=True)
    (root / "canon" / "entities" / "a-room.json").write_text(json.dumps({
        "id": "a-room", "kind": "setting",
        "structured": {"sheets": {"master": "m.png", "closeUp": "c.png", "blueprint": "b.png"}}}))
    (root / "canon" / "entities" / "her.json").write_text(json.dumps({
        "id": "her", "kind": "character",
        "structured": {"render": {"poses": {"ql-shirt": {}, "ql-gown": {}}}}}))
    (root / "stories" / "s.json").write_text(json.dumps({
        "id": "s", "beats": [
            {"n": 1, "text": "Beat one.", "location": "a-room", "characters": ["her"]},
            {"n": 2, "text": "Beat two.", "location": "a-room", "characters": ["her"]}]}))
    return root


def _run(root, out, *extra):
    return subprocess.run([sys.executable, str(SCRIPT), str(root), "s",
                           "--book", "b-book", "--out", str(out)] + list(extra),
                          capture_output=True, text=True)


class TestComposeSpec(unittest.TestCase):
    def test_derives_setting_and_cast_and_enumerates_choices(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            r = _run(root, out); self.assertEqual(r.returncode, 0, r.stderr)
            spec = json.loads(out.read_text())
            self.assertEqual(len(spec["spreads"]), 2)
            sp = spec["spreads"][0]
            self.assertEqual(sp["setting"], "a-room")
            self.assertEqual([c["id"] for c in sp["cast"]], ["her"])
            self.assertIsNone(sp["plate"], "a plate must never be chosen for the author")
            self.assertIn("ql-shirt", sp["cast"][0]["_choices"])
            self.assertNotIn("blueprint", str(sp), "a blueprint is not a camera")
            self.assertIn("no plate chosen", r.stdout)
            self.assertIn("none selected", r.stdout)

    def test_rerun_preserves_authored_scene_and_chosen_plate_and_pose(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            spec["spreads"][0]["scene"] = "A carefully authored scene."
            spec["spreads"][0]["plate"] = "closeUp"
            spec["spreads"][0]["cast"][0]["pose"] = "ql-gown"
            out.write_text(json.dumps(spec))

            r = _run(root, out); self.assertEqual(r.returncode, 0, r.stderr)
            again = json.loads(out.read_text())["spreads"][0]
            self.assertEqual(again["scene"], "A carefully authored scene.",
                             "a re-run must never revert an authored scene")
            self.assertEqual(again["plate"], "closeUp")
            self.assertEqual(again["cast"][0]["pose"], "ql-gown")

    def test_a_new_beat_is_inserted_without_disturbing_the_others(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            spec["spreads"][0]["scene"] = "Authored."
            out.write_text(json.dumps(spec))
            s = json.loads((root / "stories" / "s.json").read_text())
            s["beats"].append({"n": 3, "text": "Beat three.", "location": "a-room", "characters": ["her"]})
            (root / "stories" / "s.json").write_text(json.dumps(s))

            _run(root, out)
            got = json.loads(out.read_text())["spreads"]
            self.assertEqual(len(got), 3)
            self.assertEqual(got[0]["scene"], "Authored.")
            self.assertEqual(got[2]["id"], "spread-03")

    def test_a_spread_not_in_the_story_is_kept_and_reported(self):
        """Covers and closing plates are not beats and must survive a re-sync."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            spec["spreads"].append({"id": "spread-99", "scene": "The closing plate."})
            out.write_text(json.dumps(spec))
            r = _run(root, out)
            ids = [s["id"] for s in json.loads(out.read_text())["spreads"]]
            self.assertIn("spread-99", ids, "a non-beat spread must never be deleted")
            self.assertIn("kept, not deleted", r.stdout)

    def test_force_is_the_only_way_to_lose_authored_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            spec["spreads"][0]["scene"] = "Authored."
            out.write_text(json.dumps(spec))
            _run(root, out, "--force")
            self.assertEqual(json.loads(out.read_text())["spreads"][0]["scene"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
