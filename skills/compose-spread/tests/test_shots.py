"""The declared SHOT (SPEC 4.13): validation, injection, and blocking scope.

The defect these cover: a conversation book rendering as one picture N times,
because the plate's composition wins over scene prose and nothing could read
the framing an author intended.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ASSEMBLE = ROOT / "skills/compose-spread/scripts/assemble_prompt.py"
AUDIT = ROOT / "skills/compose-spec/scripts/audit_spec_shots.py"
sys.path.insert(0, str(ROOT / "engine"))
from agenticstory.shots import SHOTS, RELIEF_SHOTS  # noqa: E402


def _universe(tmp: Path) -> Path:
    u = tmp / "u"
    (u / "canon" / "entities").mkdir(parents=True)
    (u / "reference" / "room").mkdir(parents=True)
    (u / "reference" / "style").mkdir(parents=True)
    for p in ("anchor.png", "wide.png"):
        (u / "reference" / ("style" if p == "anchor.png" else "room") / p).write_bytes(b"\x89PNG\r\n\x1a\n")
    (u / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"mark": "M", "register": {
            "name": "test register", "anchor": "reference/style/anchor.png",
            "rejectedPoles": ["anime"]}}}))
    (u / "canon" / "entities" / "room.json").write_text(json.dumps({
        "id": "room", "kind": "setting", "status": "locked",
        "authority": {"lockedBy": "t", "lockedOn": "2026-01-01"},
        "contract": {"map": "A room.",
                     "blocking": "SIXTEEN GUESTS ARE SEATED IN THE TIERS.",
                     "dressing": "Chairs.", "scale": "Big."},
        "structured": {"sheets": {"wide": "reference/room/wide.png"},
                       "requiredForRender": ["wide"], "invariants": []}}))
    return u


def _spec(shot=None):
    sp = {"id": "spread-01", "setting": "room", "plate": "wide",
          "cast": [], "scene": "An empty room."}
    if shot is not None:
        sp["shot"] = shot
    return {"book": "b", "story": "s", "spreads": [sp]}


def _assemble(u: Path, spec: dict):
    f = Path(tempfile.mkstemp(suffix=".json")[1])
    f.write_text(json.dumps(spec))
    return subprocess.run([sys.executable, str(ASSEMBLE), str(u), str(f), "spread-01"],
                          capture_output=True, text=True)


class ShotVocabularyTest(unittest.TestCase):
    def test_every_shot_declares_the_fields_both_consumers_read(self):
        for name, cfg in SHOTS.items():
            for key in ("summary", "framing", "dropsBlocking", "peopleInFrame"):
                self.assertIn(key, cfg, f"{name} is missing {key}")
            self.assertTrue(cfg["framing"].strip(), name)

    def test_relief_shots_are_real_shots(self):
        for s in RELIEF_SHOTS:
            self.assertIn(s, SHOTS)

    def test_relief_shots_all_drop_blocking(self):
        # A relief shot leaves the room, so the room-wide blocking law cannot apply.
        for s in RELIEF_SHOTS:
            self.assertTrue(SHOTS[s]["dropsBlocking"], s)


class ShotAssemblyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = _universe(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_absent_shot_changes_nothing(self):
        """Back-compat is load-bearing: 200+ shipped books declare no shot."""
        r = _assemble(self.u, _spec())
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertNotIn("FRAMING,", out["prompt"])
        self.assertIn("SIXTEEN GUESTS", out["prompt"])

    def test_unknown_shot_refuses_and_lists_the_vocabulary(self):
        r = _assemble(self.u, _spec("closeup"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("unknown shot", r.stderr)
        self.assertIn("close", r.stderr)

    def test_close_injects_the_plate_override(self):
        out = json.loads(_assemble(self.u, _spec("close")).stdout)
        self.assertIn("FRAMING, CLOSE-UP", out["prompt"])
        self.assertIn("IGNORE THE CAMERA DISTANCE", out["prompt"])

    def test_close_drops_the_room_wide_blocking_law(self):
        out = json.loads(_assemble(self.u, _spec("close")).stdout)
        self.assertNotIn("SIXTEEN GUESTS", out["prompt"])

    def test_wide_keeps_the_blocking_law(self):
        out = json.loads(_assemble(self.u, _spec("wide")).stdout)
        self.assertIn("SIXTEEN GUESTS", out["prompt"])

    def test_framing_precedes_the_entity_blocks(self):
        """The framing must outrank the plate block that carries the composition."""
        out = json.loads(_assemble(self.u, _spec("close")).stdout)
        self.assertLess(out["prompt"].index("FRAMING, CLOSE-UP"),
                        out["prompt"].index("room exactly as its reference plate"))

    def test_thought_bubble_forbids_the_comic_outline(self):
        out = json.loads(_assemble(self.u, _spec("thought-bubble")).stdout)
        self.assertIn("NEVER a hard black comic-book outline", out["prompt"])

    def test_every_shot_assembles(self):
        for name in SHOTS:
            r = _assemble(self.u, _spec(name))
            self.assertEqual(r.returncode, 0, f"{name}: {r.stderr}")


class ShotAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = _universe(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, spreads):
        f = Path(tempfile.mkstemp(suffix=".json")[1])
        f.write_text(json.dumps({"book": "b", "story": "s", "spreads": spreads}))
        r = subprocess.run([sys.executable, str(AUDIT), str(self.u), str(f), "--json"],
                           capture_output=True, text=True)
        return r.returncode, json.loads(r.stdout)["problems"]

    def _talk(self, n, shot=None):
        out = []
        for i in range(1, n + 1):
            sp = {"id": f"spread-{i:02d}", "setting": "room", "plate": "wide",
                  "cast": [{"id": "a"}, {"id": "b"}]}
            if shot:
                sp["shot"] = shot
            out.append(sp)
        return out

    def test_a_run_of_identical_spreads_is_refused(self):
        code, probs = self._run(self._talk(15))
        self.assertEqual(code, 2)
        self.assertTrue(any("R1 SAMENESS RUN" in p for p in probs))
        self.assertTrue(any("15 consecutive" in p for p in probs))

    def test_pose_variation_alone_does_not_rescue_a_run(self):
        """The defect that shipped: same place, same camera, different expressions."""
        sp = self._talk(15)
        for i, s in enumerate(sp):
            s["cast"] = [{"id": "a", "pose": f"p{i}"}, {"id": "b", "pose": "q"}]
        code, probs = self._run(sp)
        self.assertEqual(code, 2)
        self.assertTrue(any("R1 SAMENESS RUN" in p for p in probs))

    def test_varied_shots_break_the_run(self):
        sp = self._talk(12)
        for i, s in enumerate(sp):
            s["shot"] = ["wide", "two-shot", "close", "thought-bubble"][i % 4]
        code, probs = self._run(sp)
        self.assertFalse(any("R1 SAMENESS RUN" in p for p in probs), probs)

    def test_a_talking_book_with_no_relief_is_refused(self):
        sp = self._talk(12)
        for i, s in enumerate(sp):
            s["shot"] = ["wide", "two-shot", "close"][i % 3]
        code, probs = self._run(sp)
        self.assertEqual(code, 2)
        self.assertTrue(any("R3 NO RELIEF" in p for p in probs))

    def test_relief_satisfies_the_talking_book_rule(self):
        sp = self._talk(12)
        rhythm = ["wide", "two-shot", "close", "thought-bubble", "close", "imagined"]
        for i, s in enumerate(sp):
            s["shot"] = rhythm[i % len(rhythm)]
        code, probs = self._run(sp)
        self.assertEqual(code, 0, probs)

    def test_unknown_shot_is_caught_before_any_render(self):
        sp = self._talk(4)
        sp[0]["shot"] = "nope"
        code, probs = self._run(sp)
        self.assertEqual(code, 2)
        self.assertTrue(any("unknown shot" in p for p in probs))

    def test_a_short_varied_book_passes(self):
        sp = [{"id": "spread-01", "setting": "room", "plate": "wide", "cast": [], "shot": "wide"},
              {"id": "spread-02", "setting": "room", "plate": "wide", "cast": [], "shot": "close"}]
        code, probs = self._run(sp)
        self.assertEqual(code, 0, probs)


if __name__ == "__main__":
    unittest.main()
