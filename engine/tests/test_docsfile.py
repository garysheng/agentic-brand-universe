"""The docs generator, and the staleness gate that is the actual point of it."""
import unittest
from pathlib import Path

from agenticstory import docsfile, SPEC_VERSION

ROOT = docsfile.repo_root()


class TestSources(unittest.TestCase):
    def test_repo_root_is_the_framework(self):
        self.assertTrue((ROOT / "SPEC.md").is_file())
        self.assertTrue((ROOT / "skills").is_dir())

    def test_spec_version_parses_and_matches_engine(self):
        version, date = docsfile.spec_version(ROOT)
        self.assertRegex(version, r"^\d+\.\d+$")
        self.assertRegex(date, r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(version, SPEC_VERSION)

    def test_changelog_entries_found(self):
        entries = docsfile.spec_changelog(ROOT)
        self.assertGreater(len(entries), 3)
        for e in entries:
            self.assertRegex(e["version"], r"^\d+\.\d+$")
            self.assertTrue(e["headline"])
            self.assertNotIn("\n", e["headline"])

    def test_every_skill_has_name_and_description(self):
        """A skill whose frontmatter cannot be read is invisible to an agent
        choosing a verb, which is the failure this index exists to prevent."""
        missing = []
        for d in sorted((ROOT / "skills").iterdir()):
            f = d / "SKILL.md"
            if not f.is_file():
                continue
            fm = docsfile.frontmatter(f)
            if not fm.get("name") or not fm.get("description"):
                missing.append(d.name)
        self.assertEqual(missing, [])

    def test_skill_id_matches_directory(self):
        for d in sorted((ROOT / "skills").iterdir()):
            f = d / "SKILL.md"
            if f.is_file():
                self.assertEqual(docsfile.frontmatter(f).get("name"), d.name)

    def test_every_cli_verb_has_help(self):
        """A blank help string renders as a blank documentation row, which is how
        an undocumented verb hides in plain sight."""
        blank = [v["verb"] for v in docsfile.cli_verbs() if not v["help"]]
        self.assertEqual(blank, [])

    def test_static_test_count_is_plausible(self):
        counts = docsfile.test_counts(ROOT)
        self.assertGreater(counts["tests"], 100)
        self.assertGreater(counts["files"], 5)

    def test_first_sentence_does_not_truncate_on_abbreviations(self):
        text = "Scaffold a Style Pack (SPEC §4.7) — a portable folder. And more prose after it."
        self.assertTrue(docsfile.first_sentence(text).startswith("Scaffold a Style Pack"))
        self.assertNotIn("And more prose", docsfile.first_sentence(text))

    def test_first_sentence_rejoins_short_fragments(self):
        self.assertEqual(docsfile.first_sentence("Do it. Then the longer explanation follows here."),
                         "Do it. Then the longer explanation follows here.")


class TestRendering(unittest.TestCase):
    def test_tables_have_header_and_separator(self):
        for render in (docsfile.render_status, docsfile.render_skills, docsfile.render_cli,
                       docsfile.render_forms, docsfile.render_providers,
                       docsfile.render_spec_changelog):
            rows = render(ROOT)
            self.assertTrue(rows[0].startswith("|"), render.__name__)
            self.assertRegex(rows[1], r"^\|(-{3}\|)+$", render.__name__)

    def test_pipes_in_content_are_escaped(self):
        """An unescaped pipe from a skill description silently shatters the table."""
        for row in docsfile.render_skills(ROOT)[2:]:
            self.assertEqual(row.count("|") - row.count("\\|"), 4, row[:80])

    def test_replace_block_is_idempotent(self):
        text = "before\n<!-- BEGIN GENERATED: x -->\nold\n<!-- END GENERATED: x -->\nafter\n"
        once = docsfile._replace_block(text, "x", ["new"])
        self.assertIn("new", once)
        self.assertNotIn("old", once)
        self.assertEqual(once, docsfile._replace_block(once, "x", ["new"]))
        self.assertTrue(once.startswith("before"))
        self.assertTrue(once.endswith("after\n"))

    def test_replace_block_refuses_missing_markers(self):
        with self.assertRaises(ValueError):
            docsfile._replace_block("no markers here", "x", ["new"])


class TestGate(unittest.TestCase):
    def test_docs_are_current(self):
        """THE test. If this fails, run `abu build-docs` and commit the result.

        It is the whole reason this module exists: a generated doc that nobody is
        forced to regenerate rots exactly like the hand-written one it replaced."""
        self.assertEqual(docsfile.check(ROOT), [])

    def test_build_is_idempotent(self):
        """A second build with no source change must be a no-op, or `--check` would
        report stale forever and the gate would be noise."""
        self.assertEqual(docsfile.build(ROOT, write=False), [])

    def test_check_catches_a_stale_block(self):
        text = (ROOT / "docs" / "REFERENCE.md").read_text()
        tampered = docsfile._replace_block(text, "cli", ["| Verb | What it does |", "|---|---|"])
        self.assertNotEqual(tampered, text)

    def test_check_catches_spec_version_drift(self):
        """The one invariant prose cannot hold: two files bumped by hand, in lockstep."""
        import tempfile, shutil
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "repo"
            fake.mkdir()
            (fake / "SPEC.md").write_text("# Spec\n\n**v9.99 — 2026-01-01.** nope\n")
            for rel in ("README.md", "docs/REFERENCE.md"):
                (fake / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy(ROOT / rel, fake / rel)
            shutil.copytree(ROOT / "skills", fake / "skills")
            problems = docsfile.check(fake)
            self.assertTrue(any("spec version mismatch" in p for p in problems), problems)


if __name__ == "__main__":
    unittest.main()
