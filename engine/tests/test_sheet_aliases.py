"""`structured.sheetAliases: {newKey: oldKey}` — declared, intentional sheet aliases.

The add-keys-never-remove pattern (a camera slot renamed without breaking every story
that names the old key: retired-hearthRotunda precedent; the-park-bench and
apostle-lee-study camera aliases, 2026-08-02) used to be encoded by writing BOTH keys
into `sheets` pointing at one file, which is indistinguishable from a dead duplicate.
`sheetAliases` makes the intent a record: the resolver treats a declared alias as a
sheet-lookup fallback (one hop), validate refuses an alias that resolves to nothing,
and lint (tested in lint-universe's own suite) skips declared aliases while still
warning on undeclared duplicates.
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ENGINE_DIR))

from agenticstory import CanonStore, refs  # noqa: E402
from agenticstory.model import Entity  # noqa: E402


def ent(**structured) -> Entity:
    return Entity.from_dict({"id": "bench", "kind": "prop", "structured": structured})


class TestResolverFallback(unittest.TestCase):
    def test_sheet_path_follows_a_declared_alias(self):
        e = ent(sheets={"the-park-bench-cam": "reference/bench/wide.png"},
                sheetAliases={"c1-wide": "the-park-bench-cam"})
        self.assertEqual(e.sheet_path("c1-wide"), "reference/bench/wide.png")

    def test_a_real_sheet_key_wins_over_an_alias(self):
        e = ent(sheets={"c1-wide": "reference/bench/new.png",
                        "old": "reference/bench/old.png"},
                sheetAliases={"c1-wide": "old"})
        self.assertEqual(e.sheet_path("c1-wide"), "reference/bench/new.png")

    def test_an_undeclared_key_still_resolves_to_nothing(self):
        e = ent(sheets={"hero": "reference/bench/hero.png"})
        self.assertIsNone(e.sheet_path("c1-wide"))

    def test_sheet_role_follows_the_alias_too(self):
        e = ent(sheets={"old": {"path": "reference/bench/old.png", "role": "geometry"}},
                sheetAliases={"new": "old"})
        self.assertEqual(e.sheet_role("new"), "geometry")

    def test_required_for_render_may_name_an_alias(self):
        # validate's "requiredForRender has no path in sheets" check goes through
        # sheet_path, so a required key that is a declared alias is not a false gap
        e = Entity.from_dict({"id": "c", "kind": "character", "structured": {
            "sheets": {"old": "reference/c/old.png"},
            "sheetAliases": {"new": "old"},
            "requiredForRender": ["new"]}})
        problems = [p for p in e.validate() if "requiredForRender" in p]
        self.assertEqual(problems, [], problems)


class TestValidate(unittest.TestCase):
    def test_alias_to_a_missing_target_is_refused(self):
        e = ent(sheets={"hero": "reference/bench/hero.png"},
                sheetAliases={"new": "gone"})
        self.assertTrue(any("sheetAliases['new']" in p for p in e.validate()),
                        e.validate())

    def test_alias_to_itself_is_refused(self):
        e = ent(sheets={"hero": "reference/bench/hero.png"},
                sheetAliases={"hero": "hero"})
        self.assertTrue(any("points at itself" in p for p in e.validate()), e.validate())

    def test_non_dict_aliases_are_refused(self):
        e = ent(sheets={"hero": "reference/bench/hero.png"}, sheetAliases=["hero"])
        self.assertTrue(any("sheetAliases" in p for p in e.validate()), e.validate())

    def test_a_diverged_alias_is_refused(self):
        # declared alias whose two keys point at DIFFERENT files: two truths, one name
        e = ent(sheets={"new": "reference/bench/a.png", "old": "reference/bench/b.png"},
                sheetAliases={"new": "old"})
        self.assertTrue(any("DIFFERENT files" in p for p in e.validate()), e.validate())

    def test_a_clean_declared_alias_validates_green(self):
        e = ent(sheets={"new": "reference/bench/a.png", "old": "reference/bench/a.png"},
                sheetAliases={"new": "old"})
        self.assertEqual([p for p in e.validate() if "sheetAliases" in p], [])


class TestLockLevelAgreesWithTheResolver(unittest.TestCase):
    def test_a_required_alias_key_counts_as_on_disk(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "canon" / "entities").mkdir(parents=True)
            (root / "reference" / "bench").mkdir(parents=True)
            (root / "reference" / "bench" / "old.png").write_bytes(b"\x89PNG")
            (root / "universe.json").write_text(json.dumps({"name": "t", "assetRoot": "."}))
            (root / "canon" / "entities" / "bench.json").write_text(json.dumps({
                "id": "bench", "kind": "prop", "structured": {
                    "sheets": {"old": "reference/bench/old.png"},
                    "sheetAliases": {"new": "old"},
                    "requiredForRender": ["new"]}}))
            store = CanonStore(root)
            self.assertNotEqual(refs.lock_level(store, "bench"), "stub")


if __name__ == "__main__":
    unittest.main()
