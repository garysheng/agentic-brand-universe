"""compose-prompts: write a NEW entity's prompts.md bodies from its own canon.

The complement of backfill-prompts. Backfill repairs an entity whose art already
exists by reading each plate's recipe; it can do nothing for an entity with no art
yet, which is every entity anyone ever adds. Without this verb, `add-entity`
scaffolds `TODO(author)` bodies, `chain_matrix` correctly refuses to shoot them,
and the only way forward is hand-typing invariants that then diverge from the ones
read-back checks against.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compose_prompts.py"

ENTITY = {
    "id": "jim",
    "kind": "character",
    "structured": {
        "sheets": {"master": "reference/jim/master.png", "face": "reference/jim/face.png"},
        "requiredForRender": ["master"],
        "invariants": ["NEVER FAIR-HAIRED", "no logos ever"],
        "render": {
            "always": "JIM: a weathered man of sixty in a canvas coat.",
            "poses": {"master": {"sheets": ["master"], "bake": "Standing square, hands at his sides."}},
        },
    },
}


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)],
                          capture_output=True, text=True)


class ComposePrompts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = Path(self.tmp.name)
        ent = self.u / "canon" / "entities"
        ent.mkdir(parents=True)
        (ent / "jim.json").write_text(json.dumps(ENTITY))
        self.md = self.u / "reference" / "jim" / "prompts.md"

    def tearDown(self):
        self.tmp.cleanup()

    def test_composes_every_sheet_and_leaves_no_todo(self):
        r = run(self.u, "jim", "--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.md.read_text()
        self.assertIn("## master (1024x1536)  -> reference/jim/master.png", body)
        self.assertIn("## face (1024x1024)  -> reference/jim/face.png", body)
        # the TODO marker is exactly what chain_matrix refuses on
        self.assertNotIn("TODO(author)", body)

    def test_body_is_the_entity_verbatim_so_it_cannot_diverge(self):
        run(self.u, "jim", "--all")
        body = self.md.read_text()
        self.assertIn("JIM: a weathered man of sixty in a canvas coat.", body)
        self.assertIn("Standing square, hands at his sides.", body)
        for inv in ENTITY["structured"]["invariants"]:
            self.assertIn("- " + inv, body)

    def test_a_face_key_gets_the_face_framing_and_a_body_key_does_not(self):
        run(self.u, "jim", "--all")
        master, face = self.md.read_text().split("## face")
        self.assertIn("Full body, standing", master)
        self.assertIn("Head and shoulders only", face)

    def test_never_overwrites_an_authored_body(self):
        self.md.parent.mkdir(parents=True, exist_ok=True)
        self.md.write_text("# jim\n\n## master  -> reference/jim/master.png\nMY OWN WORDS.\n")
        r = run(self.u, "jim", "--all")
        self.assertEqual(r.returncode, 0, r.stderr)
        body = self.md.read_text()
        self.assertIn("MY OWN WORDS.", body)
        self.assertIn("already present", r.stdout)
        # the missing sibling is still composed
        self.assertIn("## face (1024x1024)", body)

    def test_idempotent(self):
        run(self.u, "jim", "--all")
        first = self.md.read_text()
        run(self.u, "jim", "--all")
        self.assertEqual(first, self.md.read_text())

    def test_refuses_an_unknown_sheet_rather_than_guessing(self):
        r = run(self.u, "jim", "bogus")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not in structured.sheets", r.stderr + r.stdout)

    def test_refuses_an_unknown_pose_rather_than_guessing(self):
        r = run(self.u, "jim", "master=nope")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no pose 'nope'", r.stderr + r.stdout)

    def test_refuses_an_entity_with_no_render_always(self):
        broken = json.loads(json.dumps(ENTITY))
        broken["structured"]["render"]["always"] = ""
        (self.u / "canon" / "entities" / "jim.json").write_text(json.dumps(broken))
        r = run(self.u, "jim", "--all")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("render.always", r.stderr + r.stdout)

    def test_refuses_an_entity_with_no_invariants(self):
        broken = json.loads(json.dumps(ENTITY))
        broken["structured"]["invariants"] = []
        (self.u / "canon" / "entities" / "jim.json").write_text(json.dumps(broken))
        r = run(self.u, "jim", "--all")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("invariants", r.stderr + r.stdout)

    def test_dry_run_writes_nothing(self):
        r = run(self.u, "jim", "--all", "--dry-run")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertFalse(self.md.exists())

    def test_explicit_size_in_the_spec_wins(self):
        run(self.u, "jim", "master=master:1536x1024")
        self.assertIn("## master (1536x1024)", self.md.read_text())


class MultiStateScaffold(unittest.TestCase):
    """SPEC v0.34: compose the entity you were given, not a character-shaped guess.

    Earned 2026-08-05 on nation-of-fire's `the-stronghold`, where the composer emitted
    `-> None` for scaffolded sheets, defaulted a landscape site plate to portrait, wrote
    "Full body, standing" and a "warm neutral studio field" into a stone wall whose
    central invariant is that it carries no gold, composed the code-drawn blueprint, and
    treated `add-entity`'s own TODO stubs as authored so it filled nothing.
    """

    def _uni(self, tmp, folder="real-folder"):
        root = Path(tmp)
        (root / "canon" / "entities").mkdir(parents=True)
        (root / "reference" / folder).mkdir(parents=True)
        ent = {"id": "wall", "kind": "visual-metaphor", "structured": {
            "sheets": {"blueprint": f"reference/{folder}/blueprint.png",
                       "built": None, "fallen": None},
            "invariants": ["no gold anywhere"],
            "render": {"always": "A dark stone wall on a mound.",
                       "poses": {"built": {"bake": "The wall whole."},
                                 "fallen": {"bake": "Now rubble."}}}}}
        (root / "canon" / "entities" / "wall.json").write_text(json.dumps(ent))
        (root / "reference" / folder / "blueprint.png.recipe.json").write_text(
            json.dumps({"deterministic": True, "generator": "agenticstory.massing"}))
        return root, root / "reference" / folder / "prompts.md"

    def test_scaffolded_null_sheet_gets_a_real_target_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, prompts = self._uni(tmp)
            run(root, "wall", "--all")
            body = prompts.read_text()
            self.assertNotIn("-> None", body)
            self.assertIn("-> reference/real-folder/built.png", body)

    def test_place_kinds_are_landscape_and_carry_no_body_or_studio_boilerplate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, prompts = self._uni(tmp)
            run(root, "wall", "--all")
            body = prompts.read_text()
            self.assertIn("(1536x1024)", body)
            self.assertNotIn("1024x1536", body)
            self.assertNotIn("Full body, standing", body)
            self.assertNotIn("studio field", body)

    def test_code_drawn_slots_are_never_composed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, prompts = self._uni(tmp)
            run(root, "wall", "--all")
            self.assertNotIn("## blueprint", prompts.read_text())

    def test_todo_stub_is_unauthored_and_is_replaced_not_duplicated(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, prompts = self._uni(tmp)
            prompts.write_text("# wall\n\n## built\nTODO(author): replace each body below.\n")
            run(root, "wall", "--all")
            body = prompts.read_text()
            self.assertEqual(body.count("## built"), 1)
            self.assertNotIn("TODO(author)", body)

    def test_folder_comes_from_the_entity_not_its_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root, prompts = self._uni(tmp, folder="deliberately-other")
            run(root, "wall", "--all")
            self.assertTrue(prompts.exists())
            self.assertFalse((root / "reference" / "wall" / "prompts.md").exists())


if __name__ == "__main__":
    unittest.main()
