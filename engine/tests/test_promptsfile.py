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


if __name__ == "__main__":
    unittest.main()
