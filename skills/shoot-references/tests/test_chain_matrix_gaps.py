"""chain_matrix.py — the gap-register fixes (#4 G3, #12 G11, #13 G12, #24 G19, #28 G26).

Each test reproduces the run that filed the gap, against a synthetic universe.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from importlib import util
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_chain_matrix import CHAIN, build, drawn_png, png, run  # noqa: E402

_spec = util.spec_from_file_location("cm_gaps", CHAIN)
cm = util.module_from_spec(_spec)
_spec.loader.exec_module(cm)


def _ent(root: Path) -> Path:
    return root / "canon" / "entities" / "room.json"


def _edit(root: Path, fn):
    p = _ent(root)
    d = json.loads(p.read_text())
    fn(d)
    p.write_text(json.dumps(d))


def _look(root: Path, look="era", body="Era portrait."):
    d = root / "reference" / "room" / look
    d.mkdir(parents=True, exist_ok=True)
    (d / "prompts.md").write_text(
        f"# room @ {look}\n\n## face-neutral -> reference/room/{look}/face-neutral.png\n{body}\n")


class TestAltLookFaceFallback(unittest.TestCase):
    """G3: the fallback read three literal keys and missed the legacy `face` key."""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = build(Path(self.t.name), kind="character", shots=("face",))
        png(self.root / "reference" / "room" / "face.png")
        _edit(self.root, lambda d: d["structured"].update(
            {"sheets": {"face": "reference/room/face.png"},
             "altLooks": {"era": {"invariants": ["older"]}}}))
        _look(self.root)

    def tearDown(self):
        self.t.cleanup()

    def test_legacy_face_key_seeds_the_look(self):
        plan = cm.build_plan(self.root, "room", look="era")
        self.assertTrue(any(p.endswith("reference/room/face.png") for p in plan["lookRefs"]),
                        plan["lookRefs"])

    def test_a_declared_face_sheet_missing_from_disk_refuses(self):
        (self.root / "reference" / "room" / "face.png").unlink()
        with self.assertRaises(cm.Refuse) as e:
            cm.build_plan(self.root, "room", look="era")
        self.assertIn("NOT ON DISK", str(e.exception))

    def test_no_face_sheet_at_all_is_still_allowed(self):
        """the-lord's revealed look: a look that DEFINES a face the matrix never had."""
        _edit(self.root, lambda d: d["structured"].update({"sheets": {}}))
        plan = cm.build_plan(self.root, "room", look="era")
        self.assertEqual(plan["lookRefs"], [])


class TestLookPhotoStackReplacesBase(unittest.TestCase):
    """G26: a look's own photographs lead, and the base stack rides only with keepPhotos."""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = build(Path(self.t.name), kind="character", shots=("face-neutral",))
        for n in ("adult1", "adult2", "young1", "young2"):
            png(self.root / "reference" / "room" / "photos" / f"{n}.png")
        _edit(self.root, lambda d: (
            d.__setitem__("realPerson", {"photoStack": ["reference/room/photos/adult1.png",
                                                        "reference/room/photos/adult2.png"],
                                         "approval": {"state": "gated"}}),
            d["structured"].update({"altLooks": {"college": {
                "anchorPhoto": "reference/room/photos/young1.png",
                "photoStack": ["reference/room/photos/young2.png"]}}})))
        _look(self.root, "college")

    def tearDown(self):
        self.t.cleanup()

    def names(self, paths):
        return [Path(p).stem for p in paths]

    def test_look_photos_replace_the_base_stack_anchor_first(self):
        plan = cm.build_plan(self.root, "room", look="college")
        self.assertEqual(self.names(plan["photos"]), ["young1", "young2"])

    def test_keep_photos_appends_the_base_stack_after(self):
        _edit(self.root, lambda d: d["structured"]["altLooks"]["college"].update(
            {"keepPhotos": True}))
        plan = cm.build_plan(self.root, "room", look="college")
        self.assertEqual(self.names(plan["photos"]), ["young1", "young2", "adult1", "adult2"])

    def test_default_matrix_still_uses_the_base_stack(self):
        plan = cm.build_plan(self.root, "room")
        self.assertEqual(self.names(plan["photos"]), ["adult1", "adult2"])


class TestNotUsedStubIsNotAPrompt(unittest.TestCase):
    """G19: a 'NOT USED' body is a live shot whenever its PNG is missing."""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = build(Path(self.t.name), kind="setting", shots=("c1-wide",))
        md = self.root / "reference" / "room" / "prompts.md"
        md.write_text(md.read_text() + "## blueprint -> `reference/room/blueprint.png`\n"
                      "NOT USED. Code-drawn by `abu elevation`.\n")

    def tearDown(self):
        self.t.cleanup()

    def test_refuses_when_the_stub_would_be_painted(self):
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("NOT USED", r.stderr)

    def test_harmless_when_the_code_drawn_plate_is_on_disk(self):
        drawn_png(self.root / "reference" / "room" / "blueprint.png")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)


class TestBodyDeferringToASharedBlock(unittest.TestCase):
    """G28b (#30): a body that says 'described above' defers to text no shot is sent."""

    def test_refused_before_any_spend(self):
        with tempfile.TemporaryDirectory() as t:
            root = build(Path(t), kind="character", shots=("face-neutral",))
            md = root / "reference" / "room" / "prompts.md"
            md.write_text("# room\n\nTHE MAN, restated in full on every shot: tweed, pipe.\n\n"
                          "## face-neutral -> `reference/room/face-neutral.png`\n"
                          "The full signature wardrobe described above, head and shoulders.\n")
            r = run(root, "--print-plan")
            self.assertEqual(r.returncode, 2, r.stdout)
            self.assertIn("described above", r.stderr)
            self.assertIn("render.always", r.stderr)

    def test_the_skeleton_says_every_body_is_self_contained(self):
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "engine"))
        from agenticstory.authoring import prompts_skeleton, scaffold_entity
        md = prompts_skeleton(scaffold_entity("character", "jo", "Jo"), {"anchor": "a.png"})
        self.assertIn("SELF-CONTAINED", md)


class TestCodeDrawnWithNoSection(unittest.TestCase):
    """G11: compose_prompts writes no `## blueprint` section; detection must not need one."""

    def test_blueprint_with_no_prompts_section_rides_every_shot(self):
        with tempfile.TemporaryDirectory() as t:
            root = build(Path(t), kind="visual-metaphor", shots=("master", "lit"))
            drawn_png(root / "reference" / "room" / "blueprint.png")
            plan = cm.build_plan(root, "room")
            self.assertIn("blueprint", plan["codeDrawn"])
            r = run(root, "--print-plan")
            numbered = [l for l in r.stdout.splitlines() if l.strip()[:2] in ("1.", "2.")]
            self.assertTrue(numbered, r.stdout)
            for l in numbered:
                self.assertIn("code-drawn: blueprint", l)


class TestBlessSeedBy(unittest.TestCase):
    """G12: --bless-seed recorded blessedBy 'human' even for an agent readback."""

    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = build(Path(self.t.name))
        png(self.root / "reference" / "room" / "c1-wide.png")

    def tearDown(self):
        self.t.cleanup()

    def marker(self):
        return json.loads((self.root / "reference/room/c1-wide.golden.json").read_text())

    def test_by_is_recorded_verbatim(self):
        r = run(self.root, "--bless-seed", "c1-wide", "--by", "agent-readback (steward, for Gary)")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = self.marker()
        self.assertEqual(m["blessedBy"], "agent-readback (steward, for Gary)")
        self.assertIn("AGENT", m["note"])
        self.assertTrue(m["blessedOn"])

    def test_default_is_still_human(self):
        run(self.root, "--bless-seed", "c1-wide")
        self.assertEqual(self.marker()["blessedBy"], "human")

    def test_an_agent_blessed_seed_still_unblocks_the_chain(self):
        run(self.root, "--bless-seed", "c1-wide", "--by", "agent-readback")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)


if __name__ == "__main__":
    unittest.main()
