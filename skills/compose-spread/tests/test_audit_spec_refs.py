#!/usr/bin/env python3
"""A whole-spec ref audit, because "dry-run and LOOK AT the ref count" is a check nobody runs.

The defect these tests pin: the spread-level `plate` key selects the SETTING's plate, so
on a spread with no `setting` it is SILENTLY IGNORED. A spec can therefore name a spine
object's state on every single spread and pass none of its plates, with nothing erroring.
Shipped once on Looked Like Hate (five candle spreads, zero spine-object plates) and hit
again on God Does Not Need Our Help (26 spreads, zero arch plates), which is the second
instance that earns the tool.
"""
import json, os, sys, tempfile, unittest
from pathlib import Path

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(HERE, "scripts"))
from audit_spec_refs import audit, declared_ref_dirs  # noqa: E402


def _universe(tmp):
    root = Path(tmp)
    (root / "canon" / "entities").mkdir(parents=True)
    for d in ("anchor", "the-object", "a-room"):
        (root / "reference" / d).mkdir(parents=True)
    (root / "reference" / "anchor" / "hero.png").write_bytes(b"\x89PNG")
    (root / "reference" / "the-object" / "master.png").write_bytes(b"\x89PNG")
    (root / "reference" / "the-object" / "state-b.png").write_bytes(b"\x89PNG")
    (root / "reference" / "a-room" / "master.png").write_bytes(b"\x89PNG")
    (root / "universe.json").write_text(json.dumps({
        "name": "t", "assetRoot": ".",
        "identity": {"register": {"name": "r", "anchor": "reference/anchor/hero.png"}}}))
    (root / "canon" / "entities" / "the-object.json").write_text(json.dumps({
        "id": "the-object", "kind": "visual-metaphor", "status": "locked",
        "structured": {"sheets": {"master": "reference/the-object/master.png",
                                  "state-b": "reference/the-object/state-b.png"},
                       "requiredForRender": ["master"]},
        "contract": {"map": "An object.", "blocking": "b", "dressing": "d", "scale": "s"},
        "prose": {"rules": "It never changes."}}))
    (root / "canon" / "entities" / "a-room.json").write_text(json.dumps({
        "id": "a-room", "kind": "setting", "status": "locked",
        "structured": {"sheets": {"master": "reference/a-room/master.png"},
                       "requiredForRender": ["master"]},
        "contract": {"map": "A room.", "blocking": "b", "dressing": "d", "scale": "s"}}))
    return root


def _refoldered_person(root):
    """An entity whose id is NOT its reference folder, shaped like nation-of-fire's
    Apostle: canon id `apostle-lee`, every plate under
    `reference/apostle-delmar-lee-coward-jr/` by explicit universe law."""
    d = root / "reference" / "apostle-delmar-lee-coward-jr"
    d.mkdir(parents=True, exist_ok=True)
    for f in ("now.png", "suit-no-tie.png", "photo-1.png"):
        (d / f).write_bytes(b"\x89PNG")
    (root / "canon" / "entities" / "apostle-lee.json").write_text(json.dumps({
        "id": "apostle-lee", "kind": "character", "status": "locked",
        "structured": {
            "sheets": {"now": "reference/apostle-delmar-lee-coward-jr/now.png",
                       "suitNoTie": "reference/apostle-delmar-lee-coward-jr/suit-no-tie.png"},
            "requiredForRender": ["now", "suitNoTie"],
            "invariants": ["bald-head"]},
        "realPerson": {"photoStack": ["reference/apostle-delmar-lee-coward-jr/photo-1.png"]},
        "prose": {"rules": "He is himself."}}))
    return root


def _spec(spreads):
    return {"book": "b", "story": "s", "size": "1536x1024",
            "preamble": {"register": "r"}, "spreads": spreads}


class TestAuditSpecRefs(unittest.TestCase):
    def test_spread_level_plate_without_a_setting_is_reported(self):
        """THE regression. Silently ignored by the compiler, so nothing else catches it."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            spec = _spec([{"id": "spread-01", "plate": "state-b",
                           "scene": "The object alone in a field.", "cast": []}])
            _, problems = audit(root, spec)
        joined = " ".join(problems)
        self.assertIn("spread-01", joined)
        self.assertIn("silently ignored", joined.lower())
        self.assertIn("cast", joined.lower())

    def test_cast_entity_that_contributes_no_ref_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            # Entity exists in canon but its sheets are removed from disk resolution.
            (root / "reference" / "the-object" / "master.png").unlink()
            spec = _spec([{"id": "spread-01", "scene": "The object alone.",
                           "cast": [{"id": "the-object", "plate": "master"}]}])
            _, problems = audit(root, spec)
        self.assertTrue(problems, "a cast entity passing no image must be reported")

    def test_anchor_only_spread_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            spec = _spec([{"id": "spread-01", "scene": "An empty field at dawn.",
                           "cast": []}])
            _, problems = audit(root, spec)
        self.assertIn("anchor", " ".join(problems).lower())

    def test_a_correct_spec_passes_clean(self):
        """The fix must not buy its silence by flagging everything."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            spec = _spec([
                {"id": "spread-01", "scene": "The object alone in a field.",
                 "cast": [{"id": "the-object", "plate": "state-b"}]},
                {"id": "spread-02", "setting": "a-room", "plate": "master",
                 "scene": "A quiet room.",
                 "cast": [{"id": "the-object", "plate": "master"}]},
            ])
            rows, problems = audit(root, spec)
        self.assertEqual(problems, [], problems)
        self.assertEqual(len(rows), 2)
        self.assertIn("the-object", rows[0]["entities"])


class TestIdIsNotTheFolder(unittest.TestCase):
    """THE 2026-08-04 false positive: an entity whose art was deliberately re-foldered.

    An Amazing Sex Life reported four times that spread-13 "casts 'apostle-lee' but NO
    reference image from reference/apostle-lee/ was passed... it is being drawn from
    prose", on the same line that listed ten refs from
    reference/apostle-delmar-lee-coward-jr/. The check read the id and the plates read
    canon.
    """

    def test_refoldered_entity_is_not_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _refoldered_person(_universe(tmp))
            spec = _spec([{"id": "spread-13", "setting": "a-room", "plate": "master",
                           "scene": "The Apostle in his study, telling the truth plainly.",
                           "cast": [{"id": "apostle-lee"}]}])
            rows, problems = audit(root, spec)
        self.assertEqual(problems, [], problems)
        self.assertIn("apostle-delmar-lee-coward-jr", rows[0]["entities"])

    def test_refoldered_entity_IS_reported_when_its_plates_really_are_missing(self):
        """The true positive must survive the fix, in the same re-foldered shape."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _refoldered_person(_universe(tmp))
            for f in ("now.png", "suit-no-tie.png", "photo-1.png"):
                (root / "reference" / "apostle-delmar-lee-coward-jr" / f).unlink()
            spec = _spec([{"id": "spread-13", "setting": "a-room", "plate": "master",
                           "scene": "The Apostle in his study.",
                           "cast": [{"id": "apostle-lee"}]}])
            _, problems = audit(root, spec)
        self.assertTrue(problems, "a cast entity whose plates never arrive must be reported")

    def test_declared_ref_dirs_reads_canon_not_the_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _refoldered_person(_universe(tmp))
            self.assertEqual(declared_ref_dirs(root, "apostle-lee"),
                             {"apostle-delmar-lee-coward-jr"})
            self.assertEqual(declared_ref_dirs(root, "the-object"), {"the-object"})

    def test_alt_look_and_contract_folders_count(self):
        """A folder named ONLY by an altLook or by a contract plate is still the
        entity's own art. Both were invisible when the check read the id."""
        with tempfile.TemporaryDirectory() as tmp:
            root = _universe(tmp)
            (root / "canon" / "entities" / "wanderer.json").write_text(json.dumps({
                "id": "wanderer", "kind": "character", "status": "locked",
                "structured": {"sheets": {}, "requiredForRender": [],
                               "altLooks": {"elder": {
                                   "anchorPhoto": "reference/wanderer-elder/face.png",
                                   "sheets": {"body": "reference/wanderer-elder/body.png"}}}}}))
            (root / "canon" / "entities" / "the-hall.json").write_text(json.dumps({
                "id": "the-hall", "kind": "setting", "status": "locked",
                "contract": {"turnaround": "reference/great-hall/turnaround.png",
                             "emptyPlates": ["reference/great-hall/c1-wide.png"],
                             "map": "m", "blocking": "b", "dressing": "d", "scale": "s"}}))
            self.assertEqual(declared_ref_dirs(root, "wanderer"), {"wanderer-elder"})
            self.assertEqual(declared_ref_dirs(root, "the-hall"), {"great-hall"})


if __name__ == "__main__":
    unittest.main()
