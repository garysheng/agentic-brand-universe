"""`abu import-asset`: an asset from outside arrives WITH its chain, or it does not arrive.

The defect these pin (2026-08-01, christofuturism `gary`): twelve blessed crops of known
gpt-image-2 renders in another repo had to enter a photo stack, and the framework's only
paths were `backfill-provenance` (which would have stamped them `source`, i.e. "there is
no generating call to record", which was false) or a hand-written `.recipe.json`.
"""
import json
import tempfile
import unittest
from pathlib import Path

from agenticstory import importing as im


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.u = self.root / "uni"
        (self.u).mkdir()
        (self.u / "universe.json").write_text("{}")
        self.srcdir = self.root / "elsewhere"
        self.srcdir.mkdir()

    def tearDown(self):
        self.tmp.cleanup()

    def src(self, name="face.png", body=b"\x89PNG fake"):
        p = self.srcdir / name
        p.write_bytes(body)
        return p

    def recipe(self, rel):
        return json.loads((self.u / (rel + ".recipe.json")).read_text())


class ImportOne(Base):
    def test_copies_and_writes_the_recipe_as_a_side_effect(self):
        rec = im.import_one(self.u, self.src(), "reference/gary/photos/face.png",
                            spec_version="0.21",
                            derived_from={"repo": "other-os", "path": "public/a.webp",
                                          "sha256": "0a270523ea2adb29"},
                            transform={"crop": [1, 2, 3, 4]},
                            prompt="the prompt that made the source",
                            blessed_by="Gary, 2026-08-01")
        self.assertTrue((self.u / "reference/gary/photos/face.png").is_file())
        on_disk = self.recipe("reference/gary/photos/face.png")
        self.assertEqual(on_disk, rec)
        self.assertEqual(rec["provenance"], "derived")
        self.assertFalse(rec["unrecorded"])
        self.assertEqual(rec["derivedFrom"]["repo"], "other-os")
        self.assertEqual(rec["transform"]["crop"], [1, 2, 3, 4])
        self.assertEqual(rec["sourcePrompt"], "the prompt that made the source")
        self.assertEqual(rec["generator"], "abu import-asset")

    def test_a_short_hash_is_kept_as_a_prefix_not_passed_off_as_a_digest(self):
        rec = im.import_one(self.u, self.src(), "reference/x/a.png", spec_version="0.21",
                            derived_from={"repo": "r", "sha256": "0a270523ea2adb29"})
        self.assertEqual(rec["derivedFrom"]["sha256_16"], "0a270523ea2adb29")
        self.assertNotIn("sha256", rec["derivedFrom"])

    def test_derived_with_no_chain_is_refused(self):
        with self.assertRaises(im.ImportRefusal):
            im.import_one(self.u, self.src(), "reference/x/a.png", spec_version="0.21")

    def test_source_provenance_needs_no_chain(self):
        rec = im.import_one(self.u, self.src(), "reference/x/a.png", spec_version="0.21",
                            provenance="source")
        self.assertEqual(rec["provenance"], "source")
        self.assertNotIn("derivedFrom", rec)

    def test_refuses_a_destination_outside_the_universe(self):
        with self.assertRaises(im.ImportRefusal):
            im.import_one(self.u, self.src(), "../escaped.png", spec_version="0.21",
                          provenance="source")

    def test_refuses_to_clobber_without_force(self):
        im.import_one(self.u, self.src(), "reference/x/a.png", spec_version="0.21",
                      provenance="source")
        with self.assertRaises(im.ImportRefusal):
            im.import_one(self.u, self.src(), "reference/x/a.png", spec_version="0.21",
                          provenance="source")
        im.import_one(self.u, self.src(), "reference/x/a.png", spec_version="0.21",
                      provenance="source", force=True)

    def test_hash_is_of_the_installed_bytes(self):
        import hashlib
        body = b"\x89PNG distinct bytes"
        rec = im.import_one(self.u, self.src("b.png", body), "reference/x/b.png",
                            spec_version="0.21", provenance="source")
        self.assertEqual(rec["sha256"], hashlib.sha256(body).hexdigest())


class Manifest(Base):
    def write_manifest(self, items, **top):
        m = {"items": items, **top}
        p = self.srcdir / "MANIFEST.json"
        p.write_text(json.dumps(m))
        return p

    def test_batch_import_with_shared_repo_and_dest(self):
        self.src("a.png")
        self.src("b.png")
        mf = self.write_manifest(
            [{"file": "a.png", "derivedFrom": {"path": "public/a.webp"}},
             {"file": "b.png", "derivedFrom": {"path": "public/b.webp"}}],
            sourceRepo="other-os")
        r = im.import_manifest(self.u, mf, spec_version="0.21", dest="reference/g/photos")
        self.assertEqual(r["written"], 2)
        rec = self.recipe("reference/g/photos/a.png")
        self.assertEqual(rec["derivedFrom"]["repo"], "other-os")

    def test_prompt_archive_is_matched_by_source_path_or_stem(self):
        self.src("a.png")
        mf = self.write_manifest([{"file": "a.png",
                                   "derivedFrom": {"path": "public/decl/limitless.webp"}}],
                                 sourceRepo="other-os")
        pf = self.srcdir / "PROMPTS.json"
        pf.write_text(json.dumps({"limitless": "the original call"}))
        im.import_manifest(self.u, mf, spec_version="0.21", dest="ref", prompts=pf)
        self.assertEqual(self.recipe("ref/a.png")["sourcePrompt"], "the original call")

    def test_cropbox_sugar_lands_in_transform(self):
        self.src("a.png")
        mf = self.write_manifest([{"file": "a.png", "cropBox": [5, 6, 7, 8],
                                   "derivedFrom": {"path": "p"}}])
        im.import_manifest(self.u, mf, spec_version="0.21", dest="ref")
        self.assertEqual(self.recipe("ref/a.png")["transform"]["crop"], [5, 6, 7, 8])

    def test_the_whole_batch_is_refused_before_anything_is_copied(self):
        self.src("a.png")
        mf = self.write_manifest([{"file": "a.png", "derivedFrom": {"path": "p"}},
                                  {"file": "missing.png", "derivedFrom": {"path": "q"}}])
        with self.assertRaises(im.ImportRefusal):
            im.import_manifest(self.u, mf, spec_version="0.21", dest="ref")
        self.assertFalse((self.u / "ref").exists())

    def test_a_derived_item_with_no_chain_refuses_the_batch(self):
        self.src("a.png")
        mf = self.write_manifest([{"file": "a.png"}])
        with self.assertRaises(im.ImportRefusal):
            im.import_manifest(self.u, mf, spec_version="0.21", dest="ref")

    def test_dry_run_copies_nothing(self):
        self.src("a.png")
        mf = self.write_manifest([{"file": "a.png", "derivedFrom": {"path": "p"}}])
        r = im.import_manifest(self.u, mf, spec_version="0.21", dest="ref", dry_run=True)
        self.assertEqual(r["written"], 0)
        self.assertEqual(r["planned"], 1)
        self.assertFalse((self.u / "ref").exists())

    def test_an_empty_manifest_is_refused(self):
        p = self.srcdir / "M.json"
        p.write_text(json.dumps({"items": []}))
        with self.assertRaises(im.ImportRefusal):
            im.import_manifest(self.u, p, spec_version="0.21")


if __name__ == "__main__":
    unittest.main()
