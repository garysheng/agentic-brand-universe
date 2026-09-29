"""SPEC v0.57 §4.1.1: a recurring visual element that already exists as code or a locked
render points at that implementation, and new work reuses it rather than redrawing it
from prose.

Earned 2026-09-29 on continental-works. The "continent" motif (a mosaic of figured tiles
with multi-stripe ribbons threading up through the gutters) was canon only as a sentence,
"a tile = a seat, dim vs lit". An agent building a new surface from that sentence produced
flat squares beside the ribbon. Gary, with a screenshot of the live site: "This is what i
meant by team squares dawg notice how the ribbons relate to it."

These pin the SHAPE rules (Entity.validate is filesystem-free) and the one consumer
behaviour the engine owns: the original an implemented element is compared against is
offered as a referenceable sheet, so every renderer that asks the engine what it may pass
is handed the original without knowing the field exists.
"""
import sys, pathlib, unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from agenticstory.model import Entity


def motif(impl, sheets=None):
    raw = {"id": "continent", "kind": "motif",
           "structured": {"sheets": sheets or {}, "requiredForRender": [],
                          "implementation": impl}}
    return Entity(id="continent", kind="motif", raw=raw)


COMPONENT = {"kind": "component", "repo": "freedom-site",
             "path": "components/home/Continent.tsx",
             "compareAgainst": "reference/continent/live-original.png"}


class ShapeTest(unittest.TestCase):
    def problems(self, impl):
        return [p for p in motif(impl).validate() if "implementation" in p]

    def test_well_formed_component_is_clean(self):
        self.assertEqual(self.problems(COMPONENT), [])

    def test_absent_or_null_is_clean(self):
        self.assertEqual(self.problems(None), [])
        e = Entity(id="m", kind="motif", raw={"id": "m", "kind": "motif", "structured": {}})
        self.assertEqual([p for p in e.validate() if "implementation" in p], [])

    def test_component_without_compare_against_is_refused(self):
        impl = {k: v for k, v in COMPONENT.items() if k != "compareAgainst"}
        self.assertTrue(any("compareAgainst" in p for p in self.problems(impl)))

    def test_unknown_kind_is_refused(self):
        self.assertTrue(self.problems({"kind": "figma", "path": "x"}))

    def test_path_is_required_for_a_real_implementation(self):
        for k in ("component", "generator", "asset"):
            impl = {"kind": k, "compareAgainst": "a.png"}
            self.assertTrue(any("'path'" in p for p in self.problems(impl)), k)

    def test_none_must_say_why(self):
        self.assertTrue(self.problems({"kind": "none"}))
        self.assertEqual(self.problems({"kind": "none", "reason": "not built yet"}), [])

    def test_a_bare_string_is_refused(self):
        self.assertTrue(self.problems("components/home/Continent.tsx"))


class ReferenceableTest(unittest.TestCase):
    def test_component_offers_its_original(self):
        self.assertEqual(motif(COMPONENT).referenceable_sheets().get("implementation"),
                         "reference/continent/live-original.png")

    def test_asset_is_its_own_original(self):
        e = motif({"kind": "asset", "path": "reference/continent/locked.png"})
        self.assertEqual(e.implementation_image(), "reference/continent/locked.png")
        self.assertIn("reference/continent/locked.png", e.referenceable_sheets().values())

    def test_declared_sheets_are_kept_and_the_original_is_added(self):
        e = motif(COMPONENT, sheets={"hero": "reference/continent/hero.png"})
        rs = e.referenceable_sheets()
        self.assertEqual(rs["hero"], "reference/continent/hero.png")
        self.assertIn("implementation", rs)

    def test_none_offers_nothing(self):
        e = motif({"kind": "none", "reason": "prose only for now"})
        self.assertIsNone(e.implementation_image())
        self.assertNotIn("implementation", e.referenceable_sheets())


if __name__ == "__main__":
    unittest.main()
