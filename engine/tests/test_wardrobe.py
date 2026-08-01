"""Wardrobe + lookbook resolution (SPEC v0.28 §4.7.1, §12.4).

The defect these cover: lookbooks were specified in v0.12 and consumed by nobody, so
craft canon in two universes described renderer behaviour that had never been written.
Every test here asserts something that was silently false for four spec versions.
"""
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from agenticstory.store import CanonStore
from agenticstory import wardrobe as wr


def _png(p: Path):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)


class WardrobeTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-wardrobe-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        (self.dir / "canon" / "craft").mkdir(parents=True)
        (self.dir / "universe.json").write_text(json.dumps({
            "id": "t", "name": "T", "assetRoot": ".",
            "identity": {"register": "photoreal"},
        }))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _lookbook(self, lid, refs=6, **extra):
        d = self.dir / "reference/lookbook" / lid
        names = [f"r{i}.png" for i in range(refs)]
        for n in names:
            _png(d / "refs" / n)
        body = {"id": lid, "kind": "lookbook", "name": lid,
                "refs": [f"refs/{n}" for n in names],
                "aesthetic": f"{lid} aesthetic", "varietyRule": f"{lid} variety",
                "gate": [f"{lid} gate"], "minRefs": 3}
        body.update(extra)
        (d / "lookbook.json").write_text(json.dumps(body))
        return d

    def _entity(self, eid, **structured):
        st = {"sheets": {"face-neutral": "a.png", "forward-fullbody": "b.png"},
              "requiredForRender": ["face-neutral"]}
        st.update(structured)
        _png(self.dir / "a.png"); _png(self.dir / "b.png")
        (self.dir / "canon/entities" / f"{eid}.json").write_text(json.dumps({
            "id": eid, "kind": "character", "name": eid, "structured": st}))

    # --- the sampling contract -------------------------------------------------

    def test_sample_varies_membership_not_just_order(self):
        """A lookbook that always hands over refs[:n] is a Style Pack with extra steps."""
        lb = wr.Lookbook.load(self._lookbook("lb"))
        a = {p.name for p in lb.sample(3, seed="out-1.png")}
        b = {p.name for p in lb.sample(3, seed="out-2.png")}
        self.assertEqual(len(a), 3)
        self.assertNotEqual(a, b, "different seeds must draw a different SUBSET")

    def test_sample_is_deterministic_so_a_recipe_replays(self):
        lb = wr.Lookbook.load(self._lookbook("lb"))
        self.assertEqual(lb.sample(3, seed="x"), lb.sample(3, seed="x"))

    def test_sample_terminates_and_returns_n_distinct_for_every_size(self):
        """Regression: the first cut strode by a value sharing a factor with the ref
        count, so it walked a proper subgroup (stride 2 over 6 refs reaches only
        {0,2,4}) and spun forever when asked for more than the subgroup held. The whole
        test run died on SIGKILL. Every (count, n, seed) must terminate with n distinct.
        """
        for count in range(1, 13):
            lb = wr.Lookbook.load(self._lookbook(f"lb{count}", refs=count))
            for n in range(1, count + 1):
                for seed in ("a", "b", "c", "zzz", "out-7.png"):
                    got = lb.sample(n, seed=seed)
                    self.assertEqual(len(got), n, (count, n, seed))
                    self.assertEqual(len(set(got)), n, f"duplicates at {(count, n, seed)}")

    def test_sample_never_exceeds_available_refs(self):
        lb = wr.Lookbook.load(self._lookbook("lb", refs=2))
        self.assertEqual(len(lb.sample(4, seed="x")), 2)

    # --- validation ------------------------------------------------------------

    def test_gate_is_required_and_must_be_non_empty(self):
        """SPEC 4.7.1 said this since v0.12 and nothing enforced it."""
        d = self._lookbook("lb")
        body = json.loads((d / "lookbook.json").read_text())
        body["gate"] = []
        (d / "lookbook.json").write_text(json.dumps(body))
        problems = wr.Lookbook.load(d).validate()
        self.assertTrue(any("gate" in p for p in problems), problems)

    def test_ref_declared_but_missing_on_disk_is_a_problem(self):
        d = self._lookbook("lb")
        (d / "refs/r0.png").unlink()
        self.assertTrue(any("not on disk" in p for p in wr.Lookbook.load(d).validate()))

    def test_too_few_refs_for_min_refs(self):
        d = self._lookbook("lb", refs=2, minRefs=5)
        self.assertTrue(any("minRefs" in p for p in wr.Lookbook.load(d).validate()))

    def test_binding_a_lookbook_that_does_not_exist_is_caught(self):
        """The same failure class as requiredForRender naming a sheet with no path."""
        self._lookbook("real")
        self._entity("e", wardrobe={"lookbooks": ["ghost"]})
        problems = CanonStore(self.dir).validate_canon()
        self.assertTrue(any("ghost" in p and "does not exist" in p for p in problems),
                        problems)

    def test_unknown_wardrobe_key_is_caught(self):
        self._entity("e", wardrobe={"lookbookz": ["x"]})
        problems = CanonStore(self.dir).validate_canon()
        self.assertTrue(any("unknown key" in p for p in problems), problems)

    def test_wardrobe_scalar_where_a_list_belongs(self):
        self._lookbook("real")
        self._entity("e", wardrobe={"lookbooks": "real"})
        problems = CanonStore(self.dir).validate_canon()
        self.assertTrue(any("must be a list" in p for p in problems), problems)

    # --- resolution ------------------------------------------------------------

    def test_always_is_the_universe_baseline(self):
        self._lookbook("base", always=True)
        self._entity("e")
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        self.assertEqual(res["lookbooks"], ["base"])

    def test_entity_binding_applies(self):
        self._lookbook("base", always=True)
        self._lookbook("mens")
        self._entity("e", wardrobe={"lookbooks": ["mens"]})
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        self.assertEqual(set(res["lookbooks"]), {"base", "mens"})
        self.assertIn("e", res["why"]["mens"])

    def test_context_triggers_pull_a_lookbook_in(self):
        self._lookbook("kids", appliesWhen=["children"])
        self._entity("e")
        store = CanonStore(self.dir)
        self.assertEqual(wr.resolve_wardrobe(store, ["e"])["lookbooks"], [])
        self.assertEqual(
            wr.resolve_wardrobe(store, ["e"], context=["children"])["lookbooks"], ["kids"])

    def test_craft_binding_alone_does_NOT_apply_to_every_render(self):
        """The bug this replaced: resolving two people dragged in the MEAL vocabulary.

        A craft binding says "this vocabulary is canon here", not "every render obeys
        it". Being bound must make a lookbook AVAILABLE, never automatically active.
        """
        self._lookbook("table", appliesWhen=["meal"])
        (self.dir / "canon/craft/food.json").write_text(json.dumps({
            "id": "food", "kind": "register-rule", "name": "Food",
            "summary": "s", "rules": "r", "lookbook": "table"}))
        self._entity("e")
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        self.assertEqual(res["lookbooks"], [])
        avail = {a["id"]: a for a in res["available"]}
        self.assertEqual(avail["table"]["boundBy"], "food")
        self.assertEqual(avail["table"]["triggerTags"], ["meal"])

    def test_also_binds_is_read(self):
        self._lookbook("womens")
        (self.dir / "canon/craft/r.json").write_text(json.dumps({
            "id": "r", "kind": "register-rule", "name": "R", "summary": "s", "rules": "x",
            "lookbook": "other", "alsoBinds": ["womens"]}))
        self._entity("e")
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        self.assertEqual({a["id"]: a["boundBy"] for a in res["available"]}["womens"], "r")

    def test_negatives_and_eras_reach_the_prompt_block(self):
        self._lookbook("base", always=True, negatives=["no kaftans"])
        self._entity("e", wardrobe={"lookbooks": [], "era": "the house line",
                                    "alwaysWears": ["the pendant"],
                                    "negatives": ["no beads"]})
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        block = wr.wardrobe_prompt_block(res)
        for s in ("no kaftans", "no beads", "the house line", "the pendant"):
            self.assertIn(s, block)

    def test_an_entity_with_no_binding_is_reported_not_silently_baselined(self):
        self._lookbook("base", always=True)
        self._entity("e")
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        self.assertEqual(res["entitiesWithNoWardrobe"], ["e"])

    def test_nothing_applies_is_a_reportable_state_not_a_crash(self):
        self._entity("e")
        res = wr.resolve_wardrobe(CanonStore(self.dir), ["e"])
        self.assertEqual(res["lookbooks"], [])
        self.assertEqual(wr.wardrobe_prompt_block(res), "")

    def test_a_universe_with_no_lookbook_dir_resolves_empty(self):
        self._entity("e")
        self.assertEqual(wr.lookbooks(CanonStore(self.dir)), {})


if __name__ == "__main__":
    unittest.main()
