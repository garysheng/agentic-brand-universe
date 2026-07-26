"""chain_matrix.py — tests. Stdlib unittest, synthetic universe in a tempdir.

The load-bearing behaviours, in order of how badly each one bit us for real:
  1. the chain is SEQUENTIAL and each shot conditions on the seed + every shot
     accepted before it (this is the whole point; parallel produced N different
     rooms that merely shared a description)
  2. GOLDEN IS A HUMAN GATE: refuse to chain off an unblessed seed
  3. the seed is chosen KIND-AWARELY (most-geometry-first), one meta-process
     for characters, settings, props, motifs and visual-metaphors alike

Run:  python3 -m unittest discover -s tests -v   (from the lock-references skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
CHAIN = SCRIPTS / "chain_matrix.py"


def png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (180, 160, 120)).save(path)


def build(root: Path, kind="setting", shots=("c1-wide", "c2-work", "c3-light-wall")):
    (root / "canon" / "entities").mkdir(parents=True)
    png(root / "reference" / "register" / "anchor.png")
    (root / "universe.json").write_text(json.dumps({
        "name": "testverse", "assetRoot": ".",
        "identity": {"register": {"name": "test register",
                                  "anchor": "reference/register/anchor.png",
                                  "rejectedPoles": ["photoreal", "anime"]}},
    }))
    (root / "canon" / "entities" / "room.json").write_text(json.dumps({
        "id": "room", "kind": kind, "structured": {"sheets": {}, "invariants": []},
    }))
    md = "# room prompts\n\n"
    for s in shots:
        md += f"## {s} → `reference/room/{s}.png`\nRender the {s} view of the room.\n\n"
    (root / "reference" / "room").mkdir(parents=True, exist_ok=True)
    (root / "reference" / "room" / "prompts.md").write_text(md)
    return root


def run(root: Path, *extra):
    return subprocess.run([sys.executable, str(CHAIN), str(root), "room", *extra],
                          capture_output=True, text=True)


class TestChain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    # --- the point of the whole script -------------------------------------
    def test_plan_conditions_each_shot_on_all_prior_goldens(self):
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("1. c1-wide", out)
        self.assertIn("HUMAN-BLESSED SEED", out)
        # shot 3 must be conditioned on BOTH prior shots, not just the seed
        line = [l for l in out.splitlines() if "3. c3-light-wall" in l][0]
        self.assertIn("c1-wide", line)
        self.assertIn("c2-work", line)

    def test_seed_is_kind_aware_most_geometry_first(self):
        # setting -> the establishing wide seeds, even though it is listed first
        # only by luck; prove it by reordering the shots.
        root = build(Path(tempfile.mkdtemp()), kind="setting",
                     shots=("c2-work", "c3-light-wall", "c1-wide"))
        r = subprocess.run([sys.executable, str(CHAIN), str(root), "room", "--print-plan"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("seed (hero) = c1-wide", r.stdout)

    def test_character_kind_seeds_on_turnaround(self):
        root = build(Path(tempfile.mkdtemp()), kind="character",
                     shots=("face-neutral", "turnaround", "profile-left"))
        r = subprocess.run([sys.executable, str(CHAIN), str(root), "room", "--print-plan"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("seed (hero) = turnaround", r.stdout)

    # --- golden is a human gate --------------------------------------------
    def test_refuses_to_chain_off_an_unblessed_seed(self):
        png(self.root / "reference" / "room" / "c1-wide.png")
        r = run(self.root)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not blessed", r.stderr)

    def test_bless_seed_records_a_marker_with_the_hash(self):
        png(self.root / "reference" / "room" / "c1-wide.png")
        r = run(self.root, "--bless-seed", "c1-wide")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.root / "reference" / "room" / "c1-wide.golden.json").read_text())
        self.assertEqual(m["shot"], "c1-wide")
        self.assertEqual(m["blessedBy"], "human")
        self.assertTrue(m["sha256_16"])

    def test_cannot_bless_a_shot_that_does_not_exist(self):
        r = run(self.root, "--bless-seed", "c1-wide")
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not exist", r.stderr)

    # --- refusals -----------------------------------------------------------
    def test_refuses_null_anchor(self):
        uni = json.loads((self.root / "universe.json").read_text())
        uni["identity"]["register"]["anchor"] = None
        (self.root / "universe.json").write_text(json.dumps(uni))
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("anchor", r.stderr)

    def test_refuses_shot_with_no_prompt_block(self):
        r = run(self.root, "--shots", "c1-wide,nonexistent", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no prompt block", r.stderr)

    def test_refuses_bad_seed_override(self):
        r = run(self.root, "--seed", "not-a-shot", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not one of", r.stderr)




class TestNegativesAndCrossRefs(unittest.TestCase):
    """Two silent-drop bugs: the entity's own negatives and its cross-entity REFS
    were parsed by nobody and never reached the model, so prompts.md implied
    guarantees it did not provide."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_prompts(self, body: str):
        (self.root / "reference" / "room" / "prompts.md").write_text(body)

    def _locked_other(self, eid="the-door", shot="master"):
        png(self.root / "reference" / eid / f"{shot}.png")
        (self.root / "canon" / "entities" / f"{eid}.json").write_text(json.dumps({
            "id": eid, "kind": "visual-metaphor",
            "structured": {"sheets": {shot: f"reference/{eid}/{shot}.png"},
                           "requiredForRender": [shot]},
        }))

    def test_entity_negatives_are_merged_with_universe_rejected_poles(self):
        self._write_prompts(
            "# room\n\n**Negatives (every shot):** no clocks, no signage\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("photoreal", r.stdout)      # universe rejectedPoles survive
        self.assertIn("no clocks", r.stdout)      # entity negatives now reach the plan
        self.assertIn("no signage", r.stdout)

    def test_negatives_line_is_not_parsed_as_a_shot(self):
        self._write_prompts(
            "# room\n\n**Negatives (every shot):** no clocks\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1. c1-wide", r.stdout)
        self.assertNotIn("Negatives", r.stdout.split("negatives:")[0])

    def test_per_shot_refs_are_planned_and_stripped_from_the_prompt(self):
        self._locked_other()
        self._write_prompts(
            "# room\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\nREFS: the-door\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("refs(the-door)", r.stdout)
        # the REFS line must not leak into the prompt text
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        parsed = cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        self.assertNotIn("REFS", parsed["prompts"]["c2-work"])
        self.assertEqual(parsed["refs"]["c2-work"], ["the-door"])

    def test_header_refs_apply_to_every_shot(self):
        self._locked_other()
        self._write_prompts(
            "# room\n\n**Refs (every shot):** the-door\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\n")
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        parsed = cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        self.assertEqual(parsed["refs"]["c1-wide"], ["the-door"])
        self.assertEqual(parsed["refs"]["c2-work"], ["the-door"])

    def test_refs_to_an_unlocked_entity_refuse_rather_than_pass_prose(self):
        (self.root / "canon" / "entities" / "ghost.json").write_text(json.dumps({
            "id": "ghost", "kind": "visual-metaphor",
            "structured": {"sheets": {"master": None}, "requiredForRender": []},
        }))
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        with self.assertRaises(cm.Refuse):
            cm.entity_ref_images(self.root, "ghost")
        with self.assertRaises(cm.Refuse):
            cm.entity_ref_images(self.root, "not-an-entity")

    def test_refs_resolve_to_locked_art_on_disk(self):
        self._locked_other()
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        paths = cm.entity_ref_images(self.root, "the-door")
        self.assertEqual(len(paths), 1)
        self.assertTrue(Path(paths[0]).exists())


class TestRealPersonPhotoStack(unittest.TestCase):
    """A real person's PHOTOGRAPHS are the ground truth for the likeness.

    Without this, every downstream shot is conditioned only on paintings of the
    person, so the chain drifts off the real face while each plate still looks
    internally consistent. That is the worst failure shape: nothing looks wrong
    until someone who knows the person sees it.
    """

    def _with_photos(self, stack):
        root = build(Path(self.tmp.name), kind="character",
                     shots=("face-neutral", "face-3q"))
        ent = root / "canon" / "entities" / "room.json"
        d = json.loads(ent.read_text())
        d["realPerson"] = {"photoStack": stack,
                           "approval": {"state": "gated", "by": "someone", "on": None}}
        ent.write_text(json.dumps(d))
        return root

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_photo_stack_refuses_when_a_declared_photo_is_missing(self):
        root = self._with_photos(["reference/room/photos/01.png"])
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("NOT ON DISK", r.stderr)

    def test_photo_stack_refuses_a_directory_instead_of_an_image(self):
        root = self._with_photos(["reference/room/photos"])
        (root / "reference" / "room" / "photos").mkdir(parents=True, exist_ok=True)
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("DIRECTORY", r.stderr)

    def test_photo_stack_resolves_and_the_plan_builds(self):
        root = self._with_photos(["reference/room/photos/01.png"])
        png(root / "reference" / "room" / "photos" / "01.png")
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_an_entity_with_no_real_person_block_still_plans(self):
        root = build(Path(self.tmp.name), kind="character",
                     shots=("face-neutral", "face-3q"))
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)


class PerShotSize(unittest.TestCase):
    """A reference matrix legitimately MIXES aspects: full-bodies and profiles want
    portrait, multi-panel sheets (expressions, era rows) want landscape. The sizes
    were always declared in the prompts.md headings; the chain used to ignore them
    and apply one --size to everything, letterboxing every sheet into dead bands.
    Earned live 2026-07-26 on shelby-mullen's expressions sheet."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _mixed(self):
        root = Path(self.tmp.name)
        build(root, kind="character", shots=())
        md = ("# room prompts\n\n"
              "## face-neutral → `reference/room/face-neutral.png` (1024x1024)\nA face macro.\n\n"
              "## forward-fullbody → `reference/room/forward-fullbody.png` (1024x1536)\nFull figure.\n\n"
              "## expressions → `reference/room/expressions.png` (1536x1024)\nFour panels.\n\n"
              "## back → `reference/room/back.png`\nNo size declared here.\n\n")
        (root / "reference" / "room" / "prompts.md").write_text(md)
        return root

    def test_each_shot_reports_the_size_its_heading_declares(self):
        r = run(self._mixed(), "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[1024x1024]", r.stdout)   # face macro, square
        self.assertIn("[1024x1536]", r.stdout)   # full figure, portrait
        self.assertIn("[1536x1024]", r.stdout)   # multi-panel sheet, landscape

    def test_a_shot_with_no_declared_size_falls_back_to_the_size_flag(self):
        r = run(self._mixed(), "--print-plan", "--size", "777x333")
        self.assertEqual(r.returncode, 0, r.stderr)
        back = [l for l in r.stdout.splitlines() if "back" in l][0]
        self.assertIn("[777x333]", back)

    def test_a_declared_size_beats_the_size_flag(self):
        r = run(self._mixed(), "--print-plan", "--size", "777x333")
        expressions = [l for l in r.stdout.splitlines() if "expressions" in l][0]
        self.assertIn("[1536x1024]", expressions)
        self.assertNotIn("777x333", expressions)


class ConditioningWindow(unittest.TestCase):
    """Identity is carried by the blessed seed plus the most recent accepted shots,
    not by every golden ever made. Unbounded accumulation grew the request at every
    step until the TAIL of a big matrix died on openai.APITimeoutError, which is the
    worst place to fail because those shots are the most expensive to redo.
    Earned live 2026-07-26 on shelby-mullen's 9-shot matrix (era-sheet, shot 9)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _nine(self):
        shots = ("forward-fullbody", "face-neutral", "face-3q", "expressions",
                 "profile-left", "profile-right", "back", "signature-pose", "era-sheet")
        return build(Path(self.tmp.name), kind="character", shots=shots)

    def test_the_plan_shows_a_truncated_window_on_a_long_matrix(self):
        r = run(self._nine(), "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        last = [l for l in r.stdout.splitlines() if "era-sheet" in l][0]
        self.assertIn("...", last)

    def test_the_window_always_keeps_the_blessed_seed(self):
        r = run(self._nine(), "--print-plan")
        last = [l for l in r.stdout.splitlines() if "era-sheet" in l][0]
        self.assertIn("forward-fullbody", last)

    def test_max_conditioning_zero_restores_the_unbounded_behaviour(self):
        r = run(self._nine(), "--print-plan", "--max-conditioning", "0")
        self.assertEqual(r.returncode, 0, r.stderr)
        last = [l for l in r.stdout.splitlines() if "era-sheet" in l][0]
        self.assertNotIn("...", last)
        for s in ("face-neutral", "profile-left", "back", "signature-pose"):
            self.assertIn(s, last)

    def test_a_short_matrix_is_never_truncated(self):
        root = build(Path(self.tmp.name), kind="character",
                     shots=("forward-fullbody", "face-neutral", "face-3q"))
        r = run(root, "--print-plan")
        self.assertNotIn("...", r.stdout)


if __name__ == "__main__":
    unittest.main()
