"""backfill-prompts: recover a scaffolded prompts.md from the recipes beside it."""
import json
import tempfile
import unittest
from pathlib import Path

from agenticstory import promptsfile

SCAFFOLD = """# jim — generation prompts

TODO(author): replace each body below.

## face-neutral  -> reference/jim/face-neutral.png
TODO(author): the prompt for this shot.

## back  -> reference/jim/back.png
TODO(author): the prompt for this shot.

## signature-pose  -> reference/jim/signature-pose.png
An authored prompt that must survive untouched.
"""

PROMPT = "A head and shoulders portrait."


class BackfillPrompts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = Path(self.tmp.name)
        self.d = self.u / "reference" / "jim"
        self.d.mkdir(parents=True)
        self.md = self.d / "prompts.md"
        self.md.write_text(SCAFFOLD)
        ent = self.u / "canon" / "entities"
        ent.mkdir(parents=True)
        (ent / "jim.json").write_text(json.dumps({"structured": {"sheets": {
            "face-neutral": None, "back": None, "signature-pose": None, "empty-slope": None}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def recipe(self, name, prompt=PROMPT):
        (self.d / name).write_text(json.dumps({"prompt": prompt}))

    def test_plan_reports_without_writing(self):
        self.recipe("face-neutral.png.recipe.json")
        before = self.md.read_text()
        r = promptsfile.run(self.u)
        self.assertEqual(r["filled"], 1)
        self.assertEqual(r["still_todo"], 1)          # `back` was never shot
        self.assertEqual(self.md.read_text(), before)

    def test_apply_fills_only_the_todo_with_a_recipe(self):
        self.recipe("face-neutral.png.recipe.json")
        promptsfile.run(self.u, apply=True)
        text = self.md.read_text()
        self.assertIn(PROMPT, text)
        self.assertIn("An authored prompt that must survive untouched.", text)
        # `back` has no recipe, so it stays honestly unfilled.
        self.assertEqual(text.count("TODO(author): the prompt for this shot."), 1)

    def test_never_overwrites_an_authored_body(self):
        self.recipe("face-neutral.png.recipe.json")
        self.recipe("signature-pose.png.recipe.json", "STALE recipe prompt.")
        promptsfile.run(self.u, apply=True)
        text = self.md.read_text()
        self.assertIn("An authored prompt that must survive untouched.", text)
        self.assertNotIn("STALE recipe prompt.", text)

    def test_is_idempotent(self):
        self.recipe("face-neutral.png.recipe.json")
        promptsfile.run(self.u, apply=True)
        once = self.md.read_text()
        again = promptsfile.run(self.u, apply=True)
        self.assertEqual(again["filled"], 0)
        self.assertEqual(self.md.read_text(), once)

    def test_accepts_the_shot_named_recipe_convention(self):
        self.recipe("face-neutral.recipe.json")
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["filled"], 1)
        self.assertIn(PROMPT, self.md.read_text())

    def test_an_empty_prompt_in_a_recipe_is_not_a_fill(self):
        self.recipe("face-neutral.png.recipe.json", "   ")
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["filled"], 0)
        self.assertEqual(r["still_todo"], 2)

    def test_a_recipe_with_no_slot_gets_a_slot_appended(self):
        # The entity's angles were renamed after the scaffold was written, so the art on
        # disk has no heading to be recorded under.
        self.recipe("empty-slope.png.recipe.json", "A slope of singing flowers.")
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["appended"], 1)
        text = self.md.read_text()
        self.assertIn("## empty-slope", text)
        self.assertIn("A slope of singing flowers.", text)
        self.assertIn("RECOVERED", text)

    def test_appending_is_idempotent(self):
        self.recipe("empty-slope.png.recipe.json", "A slope of singing flowers.")
        promptsfile.run(self.u, apply=True)
        once = self.md.read_text()
        again = promptsfile.run(self.u, apply=True)
        self.assertEqual(again["appended"], 0)
        self.assertEqual(self.md.read_text(), once)

    def test_a_recipe_that_is_not_a_declared_slot_is_never_appended(self):
        # A rejected candidate or an era plate is art, not a matrix slot.
        self.recipe("candidate-b.png.recipe.json", "A roll that was thrown away.")
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["appended"], 0)
        self.assertNotIn("candidate-b", self.md.read_text())

    def test_both_recipe_conventions_for_one_shot_append_once(self):
        self.recipe("empty-slope.recipe.json", "A slope of singing flowers.")
        self.recipe("empty-slope.png.recipe.json", "A slope of singing flowers.")
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["appended"], 1)
        self.assertEqual(self.md.read_text().count("## empty-slope"), 1)

    def test_a_universe_with_no_reference_dir_is_not_an_error(self):
        empty = Path(tempfile.mkdtemp())
        r = promptsfile.run(empty, apply=True)
        self.assertEqual(r["filled"], 0)
        self.assertEqual(r["files"], [])


class ScaffoldsAMissingPromptsFile(unittest.TestCase):
    """An entity older than the scaffolder has no `prompts.md`, and nothing wrote one.

    Three tools each behaved correctly and the net effect was a dead end: `add-entity`
    only ever writes the file for entities it creates, `chain_matrix.py` refuses to
    shoot a matrix whose prompts are TODO, and this sweep walks the files that EXIST, so
    an entity with no file at all was invisible to it and the run reported clean.
    Earned on the cast step of The Tithe Is a Test (2026-08-02): a locked, actively-cast
    character that could not be re-shot without hand-typing the file the framework owns.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = Path(self.tmp.name)
        (self.u / "canon" / "entities").mkdir(parents=True)
        (self.u / "reference").mkdir(parents=True)
        (self.u / "universe.json").write_text(json.dumps(
            {"identity": {"register": {"name": "warm ink", "anchor": "reference/a.png"}}}))
        (self.u / "canon" / "entities" / "theo.json").write_text(json.dumps({
            "id": "theo", "kind": "character",
            "structured": {"sheets": {"face-neutral": "reference/theo/face-neutral.png",
                                      "back": None}}}))

    def tearDown(self):
        self.tmp.cleanup()

    def md(self):
        return self.u / "reference" / "theo" / "prompts.md"

    def test_plan_names_it_and_writes_nothing(self):
        r = promptsfile.run(self.u)
        self.assertEqual(r["scaffolded"], ["theo"])
        self.assertFalse(self.md().exists())

    def test_apply_writes_the_skeleton(self):
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["scaffolded"], ["theo"])
        text = self.md().read_text()
        self.assertIn("## face-neutral", text)
        self.assertIn("TODO(author)", text)
        self.assertIn("reference/a.png", text, "the register anchor leads every shot")

    def test_it_invents_no_prompt(self):
        """A scaffold is not an attestation: every body stays TODO until a recipe or a
        human fills it. Inventing the prompt that made an existing plate is exactly the
        falsified provenance `backfill-provenance` exists to prevent."""
        promptsfile.run(self.u, apply=True)
        self.assertNotIn("RECOVERED", self.md().read_text())

    def test_it_never_touches_an_existing_file(self):
        d = self.u / "reference" / "theo"
        d.mkdir(parents=True)
        (d / "prompts.md").write_text("## face-neutral\nAn authored prompt.\n")
        r = promptsfile.run(self.u, apply=True)
        self.assertEqual(r["scaffolded"], [])
        self.assertIn("An authored prompt.", self.md().read_text())

    def test_scoping_to_one_entity_leaves_the_rest_alone(self):
        (self.u / "canon" / "entities" / "other.json").write_text(json.dumps({
            "id": "other", "kind": "character",
            "structured": {"sheets": {"face-neutral": None}}}))
        r = promptsfile.run(self.u, apply=True, only=["theo"])
        self.assertEqual(r["scaffolded"], ["theo"])
        self.assertFalse((self.u / "reference" / "other" / "prompts.md").exists())

    def test_an_entity_with_no_slots_is_not_given_a_file(self):
        (self.u / "canon" / "entities" / "a-doctrine.json").write_text(json.dumps({
            "id": "a-doctrine", "kind": "doctrine", "prose": {"rules": "x"}}))
        r = promptsfile.run(self.u, apply=True)
        self.assertNotIn("a-doctrine", r["scaffolded"])


if __name__ == "__main__":
    unittest.main()


class ProseSectionsAreNotShots(unittest.TestCase):
    """A `##` heading that names no output is PROSE, not a shot.

    Earned 2026-08-03: a "## The chain, and why it is shaped this way" section
    written to explain a matrix's conditioning became shot 2 of 6 in that matrix.
    The parser invented a shot named after a sentence, lengthened the chain, and
    conditioned every later shot on a plate that would never exist. Authors should
    be able to explain a chain inside the file that defines it.
    """

    def parse(self, md):
        import importlib.util, pathlib, tempfile
        p = pathlib.Path(__file__).resolve().parents[2] / "skills/shoot-references/scripts/chain_matrix.py"
        spec = importlib.util.spec_from_file_location("cm", p)
        cm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cm)
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(md)
            tmp = pathlib.Path(f.name)
        return cm.parse_prompts_full(tmp)

    MD = """# e — prompts

## Why this chain is shaped this way
Prose explaining the conditioning. Names no output at all.

## master (1024x1024)  -> reference/e/master.png
The real shot.
"""

    def test_a_heading_with_no_output_is_skipped(self):
        got = self.parse(self.MD)
        shots = got["prompts"] if isinstance(got, dict) and "prompts" in got else got
        keys = set(shots.keys()) if hasattr(shots, "keys") else set()
        self.assertNotIn("Why this chain is shaped this way", keys)

    def test_the_real_shot_still_parses(self):
        got = self.parse(self.MD)
        shots = got["prompts"] if isinstance(got, dict) and "prompts" in got else got
        keys = set(shots.keys()) if hasattr(shots, "keys") else set()
        self.assertIn("master", keys)

    def test_prose_body_does_not_leak_into_the_next_shot(self):
        got = self.parse(self.MD)
        shots = got["prompts"] if isinstance(got, dict) and "prompts" in got else got
        self.assertNotIn("Prose explaining", shots["master"])
