"""Provenance backfill: what is recovered, what is admitted, and what is never touched."""
import json
import tempfile
import unittest
from pathlib import Path

from agenticstory import provenance as pv

ARROW_MD = """# prompts

## hero  -> reference/lamp/hero.png
A small brass lamp, one gold flame.

## detail  -> reference/lamp/detail.png
Close study of the wick.
"""

STEM_MD = """# Generation prompts

## face-3q
Three-quarter view of the face.

## profile-left
Left profile.
"""


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = Path(self.tmp.name)
        (self.u / "universe.json").write_text("{}")

    def tearDown(self):
        self.tmp.cleanup()

    def art(self, rel, prompts_md=None):
        p = self.u / "reference" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"\x89PNG fake")
        if prompts_md:
            (p.parent / "prompts.md").write_text(prompts_md)
        return p


class TestPromptRecovery(Base):
    def test_arrow_dialect(self):
        p = self.art("lamp/hero.png", ARROW_MD)
        self.assertIn("brass lamp", pv.prompts_for(p))

    def test_stem_dialect(self):
        """The second heading style. Supporting only the arrow form recovered 27 of
        232 real prompts and silently downgraded the rest to attested."""
        p = self.art("abbie/face-3q.png", STEM_MD)
        self.assertIn("Three-quarter", pv.prompts_for(p))

    def test_picks_the_right_section(self):
        p = self.art("lamp/detail.png", ARROW_MD)
        self.assertIn("wick", pv.prompts_for(p))
        self.assertNotIn("brass lamp", pv.prompts_for(p))

    def test_no_prompts_md(self):
        self.assertIsNone(pv.prompts_for(self.art("x/y.png")))

    def test_heading_present_but_no_body(self):
        p = self.art("z/empty.png", "# p\n\n## empty\n\n## other\nbody here\n")
        self.assertIsNone(pv.prompts_for(p))


class TestClassification(Base):
    def test_source_photos_are_not_generated_output(self):
        for name in ("photo-1.png", "photo_2.png", "photo.png"):
            p = self.art(f"person/{name}")
            self.assertEqual(pv.classify(p, None), "source", name)

    def test_photos_directory_is_source(self):
        self.assertEqual(pv.classify(self.art("person/photos/anything.png"), None), "source")

    def test_deterministic_by_name(self):
        for name in ("x-blueprint.png", "massing.png", "front-elevation.png"):
            self.assertEqual(pv.classify(self.art(f"s/{name}"), None), "deterministic", name)

    def test_prompt_beats_deterministic(self):
        self.assertEqual(pv.classify(self.art("s/blueprint.png"), "a prompt"), "reconstructed")

    def test_source_beats_everything(self):
        """A photograph is never a render, whatever else matches."""
        self.assertEqual(pv.classify(self.art("p/photo-1.png"), "a prompt"), "source")

    def test_plain_render_is_attested(self):
        self.assertEqual(pv.classify(self.art("s/hero.png"), None), "attested")


class TestRecords(Base):
    def test_attested_admits_it(self):
        r = pv.build_record(self.art("s/hero.png"), self.u, {}, "0.16")
        self.assertTrue(r["unrecorded"])
        self.assertIn("predates", r["note"])
        self.assertEqual(len(r["sha256"]), 64)

    def test_reconstructed_does_not_guess_the_unknown(self):
        """A plausible reconstruction sold as a captured call is worse than a gap."""
        r = pv.build_record(self.art("lamp/hero.png", ARROW_MD), self.u, {}, "0.16")
        self.assertEqual(r["provenance"], "reconstructed")
        self.assertFalse(r["unrecorded"])
        self.assertIn("brass lamp", r["prompt"])
        self.assertIsNone(r["inputs"])
        self.assertIsNone(r["model"])

    def test_source_is_not_marked_unrecorded(self):
        r = pv.build_record(self.art("p/photo-1.png"), self.u, {}, "0.16")
        self.assertFalse(r["unrecorded"])
        self.assertIn("not generated output", r["note"])

    def test_every_record_is_flagged_as_backfilled(self):
        for rel in ("s/hero.png", "p/photo-1.png", "s/blueprint.png"):
            self.assertTrue(pv.build_record(self.art(rel), self.u, {}, "0")["backfilled"])


class TestPlanAndApply(Base):
    def test_plan_writes_nothing(self):
        p = self.art("s/hero.png")
        pv.plan(self.u)
        self.assertFalse((p.parent / (p.name + ".recipe.json")).exists())

    def test_apply_writes_valid_json(self):
        p = self.art("s/hero.png")
        pv.apply(self.u, "0.16")
        rec = json.loads((p.parent / (p.name + ".recipe.json")).read_text())
        self.assertEqual(rec["provenance"], "attested")

    def test_existing_recipes_are_never_overwritten(self):
        """A real captured recipe outranks anything this module can reconstruct."""
        p = self.art("s/hero.png")
        real = p.parent / (p.name + ".recipe.json")
        real.write_text(json.dumps({"model": "gpt-image-2", "prompt": "the real one"}))
        pv.apply(self.u, "0.16")
        self.assertEqual(json.loads(real.read_text())["prompt"], "the real one")

    def test_apply_is_idempotent(self):
        self.art("s/hero.png")
        pv.apply(self.u, "0")
        self.assertEqual(pv.apply(self.u, "0")["written"], 0)

    def test_counts_add_up(self):
        self.art("s/hero.png")
        self.art("p/photo-1.png")
        self.art("lamp/hero.png", ARROW_MD)
        p = pv.plan(self.u)
        self.assertEqual(p["to_backfill"], 3)
        self.assertEqual(sum(p["by_kind"].values()), 3)

    def test_no_images_is_not_an_error(self):
        self.assertEqual(pv.plan(self.u)["to_backfill"], 0)


if __name__ == "__main__":
    unittest.main()
