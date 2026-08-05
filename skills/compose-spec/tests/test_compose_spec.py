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




class TestSettingIsNotClobbered(unittest.TestCase):
    """A re-sync must never move a spread to a different room behind your back.

    `setting` was classed as derived and refreshed from beat.location every run. A
    render-spec legitimately diverges: a beat says "their house", the book stages it in a
    room that did not exist when the beat was written. Refreshing reverted 16 spreads of
    gain-everything-lose-nothing to a banned room, and the run reported nothing, because
    only the setting had moved. Earned by this tool on the book it was built for.
    """

    def test_existing_setting_is_kept_and_the_divergence_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            (root / "canon" / "entities" / "other-room.json").write_text(json.dumps({
                "id": "other-room", "kind": "setting",
                "structured": {"sheets": {"wide": "w.png"}}}))
            spec["spreads"][0]["setting"] = "other-room"
            spec["spreads"][0]["plate"] = "wide"
            out.write_text(json.dumps(spec))

            r = _run(root, out)
            got = json.loads(out.read_text())["spreads"][0]
            self.assertEqual(got["setting"], "other-room",
                             "a re-sync must not move the spread back to the beat's location")
            self.assertEqual(got["plate"], "wide")
            self.assertIn("DIVERGENCE", r.stdout)
            self.assertIn("other-room", r.stdout)

    def test_a_plate_that_is_not_a_sheet_of_its_setting_is_flagged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            spec["spreads"][0]["plate"] = "notAPlate"
            out.write_text(json.dumps(spec))
            r = _run(root, out)
            self.assertIn("is NOT a sheet of setting", r.stdout)
            self.assertIn("notAPlate", r.stdout)


class TestWhen(unittest.TestCase):
    """SPEC v0.18: `when` is DERIVED from the beat when the story records it, and
    it is NEVER invented, because a wrong `when` is worse than none: it would
    refuse the correct look."""

    def _dated(self, tmp, when=1933, windows=True):
        root = _universe(tmp)
        st = {"render": {"poses": {"ql-shirt": {}}}}
        if windows:
            st["validFor"] = {"from": 1935, "to": 1973}
            st["altLooks"] = {"bedfast": {"validFor": {"from": 1932, "to": 1934}},
                              "elder": {"validFor": {"from": 1974}}}
        (root / "canon" / "entities" / "her.json").write_text(json.dumps(
            {"id": "her", "kind": "character", "structured": st}))
        story = json.loads((root / "stories" / "s.json").read_text())
        if when is not None:
            story["beats"][0]["when"] = when
        (root / "stories" / "s.json").write_text(json.dumps(story))
        return root

    def test_when_is_carried_from_the_beat(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dated(tmp); out = Path(tmp) / "spec.json"
            r = _run(root, out); self.assertEqual(r.returncode, 0, r.stderr)
            spec = json.loads(out.read_text())
            self.assertEqual(spec["spreads"][0]["when"], 1933)
            self.assertNotIn("when", spec["spreads"][1])

    def test_a_dated_spread_with_windowed_looks_asks_for_a_decision(self):
        """It says which look the date makes legal. It never chooses: compose-spec
        fills what canon determines and enumerates what canon constrains."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dated(tmp); out = Path(tmp) / "spec.json"
            r = _run(root, out)
            self.assertIn("era-windowed looks", r.stdout)
            self.assertIn("bedfast", r.stdout)
            self.assertIsNone(json.loads(out.read_text())["spreads"][0]["cast"][0].get("look"))

    def test_an_authored_when_survives_a_resync(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dated(tmp, when=None); out = Path(tmp) / "spec.json"
            _run(root, out)
            spec = json.loads(out.read_text())
            spec["spreads"][0]["when"] = 1950
            out.write_text(json.dumps(spec))
            _run(root, out)
            self.assertEqual(json.loads(out.read_text())["spreads"][0]["when"], 1950)

    def test_no_when_anywhere_stays_absent(self):
        """Every already-shipped book. The key must not appear from nowhere."""
        with tempfile.TemporaryDirectory() as tmp:
            root = self._dated(tmp, when=None, windows=False); out = Path(tmp) / "spec.json"
            _run(root, out)
            for sp in json.loads(out.read_text())["spreads"]:
                self.assertNotIn("when", sp)


class TestPoseIsCharacterOnly(unittest.TestCase):
    """compose-spec must not advertise a selector compose-spread will REFUSE.

    `pose` is a character selector. assemble_prompt.py raises Refuse on a pose
    given to any other kind ("A POSE ON A NON-CHARACTER SELECTS NOTHING"), a
    guard that exists because nine spreads of a real book shipped showing the
    wrong state on 2026-08-03.

    poses_for() read structured.render.poses off ANY kind, so a `group` that
    declares poses was told to pick one, and the resulting spec was refused by
    the compiler. Two shipped tools contradicting each other. Earned 2026-08-04
    on You Didn't Have To (jerry-and-selahs-kids, a group declaring the-three /
    the-growing-brood).
    """

    def setUp(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
        import compose_spec
        self.poses_for = compose_spec.poses_for

    def _ent(self, kind):
        return {"id": "x", "kind": kind,
                "structured": {"render": {"poses": {"a": {}, "b": {}}}}}

    def test_character_poses_are_offered(self):
        self.assertEqual(sorted(self.poses_for(self._ent("character"))), ["a", "b"])

    def test_group_poses_are_not_offered(self):
        """A group selects with `plate`; offering its poses authors a refused spec."""
        self.assertEqual(self.poses_for(self._ent("group")), [])

    def test_other_kinds_are_not_offered(self):
        for kind in ("prop", "motif", "setting", "visual-metaphor"):
            with self.subTest(kind=kind):
                self.assertEqual(self.poses_for(self._ent(kind)), [])

    def test_missing_entity_is_still_empty(self):
        self.assertEqual(self.poses_for(None), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
