"""shoot-references backfill_prompts.py — tests. Stdlib unittest, no network.

THE HOLE. `chain_matrix.py` refuses to shoot while prompts.md says TODO(author),
which is the right refusal. But for art that already got made some other way the
refusal is PERMANENT: the entity becomes un-reshootable, and nobody can add one
more angle without re-authoring every prompt, while the prompts sit right there in
each plate's `.recipe.json`. 74 detector findings across ~60 nation-of-fire
entities, all recoverable and none recovered, because there was no verb.

The two tests that matter most are the ones about what it REFUSES to do:
`test_an_authored_body_is_never_overwritten` (a human's words always win) and
`test_a_plate_with_no_recipe_is_reported_not_invented` (a plausible reconstruction
would look like provenance while being fiction, which is worse than an admitted
gap).

Run:  python3 tests/test_backfill_prompts.py
"""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location(
    "backfill_prompts", HERE.parent / "scripts" / "backfill_prompts.py")
bf = importlib.util.module_from_spec(_s)
_s.loader.exec_module(bf)

TODO_BODY = "TODO(author): the prompt for this shot."


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.d = self.root / "reference" / "someone"
        self.d.mkdir(parents=True)

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, bodies: dict):
        md = self.d / "prompts.md"
        text = ["# someone — generation prompts", "",
                "TODO(author): replace each body below.", ""]
        for shot, body in bodies.items():
            text += [f"## {shot}  -> reference/someone/{shot}.png", body, ""]
        md.write_text("\n".join(text))
        return md

    def plate(self, shot, prompt=None):
        p = self.d / f"{shot}.png"
        p.write_bytes(b"\x89PNG")
        if prompt is not None:
            (self.d / f"{shot}.png.recipe.json").write_text(
                json.dumps({"provider": "gpt-image-2", "prompt": prompt}))
        return p


class TestBackfill(Base):

    def test_a_todo_body_is_filled_from_the_recipe(self):
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "A three-quarter portrait of the man.")
        new, notes = bf.backfill_file(md, [])
        self.assertIn("A three-quarter portrait of the man.", new)
        self.assertNotIn("TODO(author): the prompt for this shot.", new)
        self.assertIn("recovered", " ".join(notes))

    def test_an_authored_body_is_never_overwritten(self):
        """A human's words always win, even against a recipe that disagrees."""
        md = self.write({"face-3q": "The prompt a human actually wrote."})
        self.plate("face-3q", "something else entirely")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("The prompt a human actually wrote.", new)
        self.assertNotIn("something else entirely", new)

    def test_a_plate_with_no_recipe_is_reported_not_invented(self):
        """A plausible reconstruction would look like provenance while being
        fiction, which is worse than an admitted gap."""
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q")                       # art, no recipe
        new, notes = bf.backfill_file(md, [])
        self.assertIn("TODO(author)", new)
        self.assertIn("UNRECOVERABLE", " ".join(notes))

    def test_a_shot_with_no_plate_is_left_alone(self):
        md = self.write({"profile-left": TODO_BODY})
        new, notes = bf.backfill_file(md, [])
        self.assertIn("TODO(author)", new)
        self.assertIn("no plate on disk", " ".join(notes))

    def test_only_the_todo_shots_of_a_mixed_file_are_touched(self):
        md = self.write({"face-3q": TODO_BODY, "back": "Authored already."})
        self.plate("face-3q", "Recovered three-quarter.")
        self.plate("back", "would have overwritten")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("Recovered three-quarter.", new)
        self.assertIn("Authored already.", new)
        self.assertNotIn("would have overwritten", new)

    def test_the_file_header_survives_the_rewrite(self):
        """The header carries the REQUIRED-before-render list and the negatives,
        which chain_matrix parses. Losing it would break the shoot."""
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "Recovered.")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("# someone — generation prompts", new)

    def test_the_result_parses_back_as_the_shot_it_came_from(self):
        md = self.write({"face-3q": TODO_BODY, "back": TODO_BODY})
        self.plate("face-3q", "THREE QUARTER VIEW.")
        self.plate("back", "SEEN FROM BEHIND.")
        md.write_text(bf.backfill_file(md, [])[0])
        text = md.read_text()
        self.assertIn("## face-3q", text)
        # each recovered body sits under its OWN heading
        i3q, iback = text.index("## face-3q"), text.index("## back")
        self.assertLess(i3q, text.index("THREE QUARTER VIEW."))
        self.assertLess(text.index("THREE QUARTER VIEW."), iback)
        self.assertLess(iback, text.index("SEEN FROM BEHIND."))


class TestStripping(Base):
    """Only what the SHOOTER re-adds comes off, or the next shoot doubles it."""

    def test_the_framework_register_line_is_stripped(self):
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q",
                   "STYLE, AND IT OVERRIDES ANY OTHER READING: render this in oil.\n\n"
                   "A three-quarter portrait.")
        new, notes = bf.backfill_file(md, [])
        self.assertNotIn("STYLE, AND IT OVERRIDES", new)
        self.assertIn("A three-quarter portrait.", new)
        self.assertIn("register style line", " ".join(notes))

    def test_the_same_subject_and_negatives_blocks_are_stripped(self):
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q",
                   "A three-quarter portrait.\n\n"
                   "CRITICAL: every reference image after the first shows THE SAME "
                   "SINGLE SUBJECT, already locked.\n\n"
                   "NEGATIVES: no text, no border.")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("A three-quarter portrait.", new)
        self.assertNotIn("CRITICAL: every reference image", new)
        self.assertNotIn("NEGATIVES:", new)

    def test_the_real_person_clause_is_stripped(self):
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "IDENTITY GROUND TRUTH: the PHOTOGRAPHS are real.\n\n"
                              "A three-quarter portrait.")
        new, _ = bf.backfill_file(md, [])
        self.assertNotIn("IDENTITY GROUND TRUTH", new)

    def test_an_unrecognised_paragraph_is_KEPT(self):
        """A stripper that guesses deletes somebody's prompt. Anything the
        framework does not own survives verbatim."""
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "A portrait.\n\nA universe guard block nobody registered.")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("A universe guard block nobody registered.", new)

    def test_strip_regex_removes_a_universe_guard_on_request(self):
        import re
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "A portrait.\n\nNO USER INTERFACE ANYWHERE: no windows.")
        new, _ = bf.backfill_file(md, [re.compile("NO USER INTERFACE", re.I)])
        self.assertNotIn("NO USER INTERFACE", new)
        self.assertIn("A portrait.", new)

    def test_a_paragraph_merely_mentioning_negatives_survives(self):
        """Matching is on the paragraph OPENING, so authored prose that talks
        about negatives is not mistaken for the negatives block."""
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "A portrait whose NEGATIVES: are stated inline below.")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("A portrait whose NEGATIVES:", new)


class TestOrphansAndCircles(Base):

    def test_a_locked_plate_with_no_section_is_ADOPTED(self):
        """An entity's real matrix drifts from its scaffold: `beyonce` holds
        master / plain / incognito / at-peace while its prompts.md still lists the
        eight scaffolded portrait slots, so four locked plates had their intent
        recorded only in a build artifact."""
        md = self.write({"face-3q": TODO_BODY})
        self.plate("master", "A master plate of her.")
        new, notes = bf.backfill_file(md, [])
        self.assertIn("## master  -> reference/someone/master.png", new)
        self.assertIn("A master plate of her.", new)
        self.assertIn("ADOPTED", " ".join(notes))

    def test_adoption_never_removes_a_scaffolded_slot(self):
        """Whether a declared-but-never-shot slot is still wanted is a judgement
        call, and this tool does not make judgement calls."""
        md = self.write({"face-3q": TODO_BODY})
        self.plate("master", "A master plate.")
        new, _ = bf.backfill_file(md, [])
        self.assertIn("## face-3q", new)
        self.assertIn("TODO(author)", new)

    def test_an_already_headed_plate_is_not_adopted_twice(self):
        md = self.write({"face-3q": TODO_BODY})
        self.plate("face-3q", "Recovered.")
        new, _ = bf.backfill_file(md, [])
        self.assertEqual(new.count("## face-3q"), 1)

    def test_a_code_built_plate_is_not_adopted(self):
        """A massing blueprint has `"prompt": null` by design: its provenance is a
        declarative spec plus deterministic code, which is better than a prompt."""
        p = self.d / "blueprint.png"
        p.write_bytes(b"\x89PNG")
        (self.d / "blueprint.png.recipe.json").write_text(json.dumps(
            {"generator": "agenticstory.massing", "deterministic": True, "prompt": None}))
        md = self.write({"face-3q": "Authored."})
        new, _ = bf.backfill_file(md, [])
        self.assertNotIn("## blueprint", new)

    def test_a_recipe_whose_prompt_is_itself_a_TODO_is_refused(self):
        """THE CIRCLE. `abu backfill-provenance` recovers a recipe by reading
        prompts.md, so where that file was a stub it faithfully recorded the stub.
        Writing it back would look like a repair and leave the entity exactly as
        un-reproducible, with the gap disguised as provenance."""
        md = self.write({"blueprint": TODO_BODY})
        self.plate("blueprint", TODO_BODY)
        new, notes = bf.backfill_file(md, [])
        self.assertIn("TODO(author)", new)
        self.assertIn("UNRECOVERABLE", " ".join(notes))
        self.assertIn("TODO stub", " ".join(notes))

    def test_a_recipe_recording_a_null_prompt_says_which_failure_it_is(self):
        """A lock-shot provenance record can carry digests and inputs with
        `"prompt": null`. The remedy differs from having no recipe at all."""
        p = self.plate("face-3q")
        (self.d / "face-3q.png.recipe.json").write_text(
            json.dumps({"goldenDigest": "abc", "inputs": [], "prompt": None}))
        md = self.write({"face-3q": TODO_BODY})
        _, notes = bf.backfill_file(md, [])
        self.assertIn("records NO PROMPT", " ".join(notes))


if __name__ == "__main__":
    unittest.main(verbosity=2)
