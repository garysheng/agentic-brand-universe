"""A relation side may name another universe as `<universe>:<id>` (#54).

Twice, in two universes five weeks apart, a copied entity could not record where it came from,
because a relation side resolved only inside one universe and `nof-universe:the-wingman` failed
as an unknown id. A foreign side is now well-formed: accepted when the sibling is not on disk,
checked when it is.
"""
import json
import tempfile
import unittest
from pathlib import Path

from agenticstory.store import CanonStore


def _universe(root: Path, name: str, entities=()):
    u = root / name
    (u / "canon" / "entities").mkdir(parents=True)
    (u / "canon" / "relations").mkdir(parents=True)
    (u / "universe.json").write_text(json.dumps({"name": name, "assetRoot": "."}))
    for e in entities:
        (u / "canon" / "entities" / f"{e}.json").write_text(json.dumps(
            {"id": e, "kind": "doctrine", "structured": {"sheets": {}, "requiredForRender": []}}))
    return u


def _relate(u: Path, frm: str, to: str):
    (u / "canon" / "relations" / "r.json").write_text(json.dumps(
        {"from": frm, "rel": "derived-from", "to": to}))


def _rel_problems(u: Path):
    return [p for p in CanonStore(u).validate_canon() if "relation" in p]


class TestForeignRelationSide(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        self.cw = _universe(self.root, "continental-works-universe", ["freedom-character"])

    def tearDown(self):
        self.t.cleanup()

    def test_a_foreign_side_with_no_sibling_on_disk_is_accepted(self):
        _relate(self.cw, "freedom-character", "nof-universe:the-wingman")
        self.assertEqual(_rel_problems(self.cw), [])

    def test_a_present_sibling_that_has_the_id_resolves(self):
        _universe(self.root, "nof-universe", ["the-wingman"])
        _relate(self.cw, "freedom-character", "nof-universe:the-wingman")
        self.assertEqual(_rel_problems(self.cw), [])

    def test_a_present_sibling_that_lost_the_id_is_named(self):
        _universe(self.root, "nof-universe", ["someone-else"])
        _relate(self.cw, "freedom-character", "nof-universe:the-wingman")
        probs = _rel_problems(self.cw)
        self.assertTrue(any("moved or gone" in p for p in probs), probs)

    def test_a_plain_unknown_id_is_still_unknown(self):
        _relate(self.cw, "freedom-character", "the-wingman")
        self.assertTrue(any("unknown id 'the-wingman'" in p for p in _rel_problems(self.cw)))

    def test_the_edge_is_queryable_from_the_foreign_id(self):
        _relate(self.cw, "freedom-character", "nof-universe:the-wingman")
        rels = CanonStore(self.cw).relations_of("nof-universe:the-wingman")
        self.assertEqual([r.from_ for r in rels], ["freedom-character"])


if __name__ == "__main__":
    unittest.main()
