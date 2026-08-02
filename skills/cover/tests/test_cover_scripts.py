"""
Cover skill scripts — tests. Stdlib unittest (mirrors agenticstory/engine/tests).

Runs against a SYNTHETIC universe built in a tempdir (no content-repo
dependency): a locked hero character with on-disk sheets, a locked setting
with a plate, a motif, and a story. Covers the happy path AND every refusal
path — the refusals are the load-bearing feature.

Run:  python3 -m unittest discover -s tests -v   (from the cover skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RENDER = Path(__file__).resolve().parents[1] / "scripts" / "render_cover.py"
COMPILE = SCRIPTS / "compile_cover.py"
CONFORM = SCRIPTS / "conform_cover.py"


def png(path: Path, size=(8, 8)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 180, 140)).save(path)


def build_universe(root: Path):
    (root / "canon" / "entities").mkdir(parents=True)
    (root / "stories").mkdir(parents=True)
    png(root / "reference" / "register" / "style-anchor.png")
    png(root / "reference" / "hero" / "fullbody.png")
    png(root / "reference" / "hero" / "face.png")
    png(root / "reference" / "isle" / "c1.png")
    (root / "universe.json").write_text(json.dumps({
        "name": "testverse", "assetRoot": ".",
        "identity": {
            "mark": "A TESTVERSE story",
            "register": {
                "name": "test register",
                "anchor": "reference/register/style-anchor.png",
                "rejectedPoles": ["photoreal", "anime"],
            },
        },
    }))
    (root / "canon" / "entities" / "hero.json").write_text(json.dumps({
        "id": "hero", "kind": "character",
        "structured": {
            "sheets": {"forward-fullbody": "reference/hero/fullbody.png",
                       "face-neutral": "reference/hero/face.png"},
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["always wears the test hat"],
            # PRESCRIBED PROMPT-CRAFT: wording an invariant slug cannot carry.
            "render": {
                "always": "HERO carries the copper compass, a four-point STAR, never a plain cross.",
                "poses": {"front": {"sheets": ["forward-fullbody"],
                                    "bake": "FRONT: both chest badges clearly visible."}},
            },
        },
    }))
    (root / "canon" / "entities" / "isle.json").write_text(json.dumps({
        "id": "isle", "kind": "setting", "status": "locked",
        "structured": {"sheets": {"c1": "reference/isle/c1.png",
                                  "c2": "reference/isle/c2.png"}},
        "contract": {"emptyPlates": ["reference/isle/c1.png", "reference/isle/c2.png"],
                     "dressing": "windswept test grass"},
    }))
    (root / "stories" / "tale.json").write_text(json.dumps({
        "id": "tale", "spine": "biography", "features": ["hero", "isle"],
    }))
    return root


def run_compile(universe: Path, *extra):
    return subprocess.run(
        [sys.executable, str(COMPILE), str(universe), "tale",
         "--title", "TEST TITLE", "--subtitle", "A Test Subtitle", *extra],
        capture_output=True, text=True)


class TestCompile(unittest.TestCase):

    def assertRefEndsWith(self, refs, rel):
        """compile_cover emits ABSOLUTE ref paths (same contract as the sibling
        assemble_prompt.py), so the caller's cwd is never load-bearing. Assert on
        the suffix, and assert absoluteness explicitly."""
        matches = [r for r in refs if r.endswith(rel)]
        self.assertTrue(matches, f"{rel} not found in {refs}")
        for m in matches:
            self.assertTrue(m.startswith("/"), f"ref must be absolute: {m}")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = build_universe(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def compiled(self, *extra):
        r = run_compile(self.u, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_anchor_is_first_ref(self):
        d = self.compiled()
        # register anchor stays FIRST, and is emitted absolute
        self.assertRefEndsWith(d["refs"][:1], "reference/register/style-anchor.png")

    def test_required_sheets_in_refs(self):
        d = self.compiled()
        self.assertRefEndsWith(d["refs"], "reference/hero/fullbody.png")
        self.assertRefEndsWith(d["refs"], "reference/hero/face.png")

    def test_text_lines_quoted_exactly_including_mark(self):
        p = self.compiled()["prompt"]
        for line in ('"TEST TITLE"', '"A Test Subtitle"', '"A TESTVERSE story"'):
            self.assertIn(line, p)

    def test_safe_margin_block_present(self):
        self.assertIn("CRITICAL SAFE MARGINS", self.compiled()["prompt"])

    def test_rejected_poles_are_negatives(self):
        p = self.compiled()["prompt"]
        self.assertIn("photoreal", p)
        self.assertIn("anime", p)

    def test_qa_compiled_from_same_canon(self):
        qa = " ".join(self.compiled()["qa"])
        self.assertIn("TEST TITLE", qa)
        self.assertIn("test hat", qa)

    def test_setting_contributes_plate_and_dressing(self):
        d = self.compiled("--with", "isle")
        self.assertRefEndsWith(d["refs"], "reference/isle/c1.png")
        self.assertIn("windswept test grass", d["prompt"])

    def test_author_byline_baked(self):
        p = self.compiled("--author", "Ada Lovelace and Alan Turing")["prompt"]
        self.assertIn('"by Ada Lovelace and Alan Turing"', p)

    def test_no_mark_omits_the_mark(self):
        p = self.compiled("--no-mark")["prompt"]
        self.assertNotIn("A TESTVERSE story", p)      # mark absent from baked text
        self.assertIn('"TEST TITLE"', p)              # title still baked

    def test_no_mark_survives_null_mark(self):
        # a universe with no mark must still compile a cover when --no-mark is set
        uni = json.loads((self.u / "universe.json").read_text())
        uni["identity"]["mark"] = None
        (self.u / "universe.json").write_text(json.dumps(uni))
        p = self.compiled("--no-mark")["prompt"]
        self.assertIn('"TEST TITLE"', p)

    def test_no_text_bakes_no_lettering(self):
        p = self.compiled("--no-text")["prompt"]
        self.assertNotIn('"TEST TITLE"', p)           # nothing quoted for the model to letter
        self.assertNotIn("A TESTVERSE story", p)
        self.assertIn("ART ONLY", p)
        self.assertIn("NO lettering", p)

    def test_no_text_still_emits_title_qa(self):
        # the spelling checks move to the TYPESET file; they must not vanish
        qa = " ".join(self.compiled("--no-text")["qa"])
        self.assertIn("TEST TITLE", qa)

    def test_no_text_keeps_refs_and_conform(self):
        d = self.compiled("--no-text")
        self.assertRefEndsWith(d["refs"], "anchor.png")   # register anchor still first
        self.assertEqual(d["conform"]["to_aspect"], "3:4")

    def test_scene_is_included_between_canon_and_safe_margins(self):
        r = subprocess.run(
            [sys.executable, str(COMPILE), str(self.u), "tale",
             "--title", "TEST TITLE", "--scene", "hero walks toward the dawn"],
            capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        p = json.loads(r.stdout)["prompt"]
        self.assertIn("hero walks toward the dawn", p)
        self.assertLess(p.index("test hat"), p.index("hero walks toward the dawn"))
        self.assertLess(p.index("hero walks toward the dawn"), p.index("CRITICAL SAFE MARGINS"))

    def test_refuses_null_anchor(self):
        uni = json.loads((self.u / "universe.json").read_text())
        uni["identity"]["register"]["anchor"] = None
        (self.u / "universe.json").write_text(json.dumps(uni))
        r = run_compile(self.u)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("anchor", r.stderr)

    def test_refuses_unlocked_required_sheet(self):
        ent = json.loads((self.u / "canon" / "entities" / "hero.json").read_text())
        ent["structured"]["sheets"]["face-neutral"] = None
        (self.u / "canon" / "entities" / "hero.json").write_text(json.dumps(ent))
        r = run_compile(self.u)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("unlocked", r.stderr)

    def test_refuses_ref_missing_on_disk(self):
        (self.u / "reference" / "hero" / "face.png").unlink()
        r = run_compile(self.u)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("does not resolve", r.stderr)

    def test_refuses_unlocked_setting(self):
        ent = json.loads((self.u / "canon" / "entities" / "isle.json").read_text())
        ent["status"] = "unlocked"
        (self.u / "canon" / "entities" / "isle.json").write_text(json.dumps(ent))
        r = run_compile(self.u, "--with", "isle")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not locked", r.stderr)

    def test_refuses_story_with_no_character(self):
        (self.u / "stories" / "tale.json").write_text(
            json.dumps({"id": "tale", "features": ["isle"]}))
        r = run_compile(self.u)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("hero", r.stderr)


    def test_render_block_reaches_the_cover_prompt(self):
        """A cover built from invariant slugs alone loses canon's steering wording
        (signature wardrobe, star-vs-crucifix). Covers are front-facing by
        definition, so the front bake applies without naming a pose."""
        d = self.compiled()
        self.assertIn("copper compass", d["prompt"])
        self.assertIn("never a plain cross", d["prompt"])
        self.assertIn("both chest badges", d["prompt"])

    def test_render_block_does_not_replace_invariant_qa(self):
        d = self.compiled()
        self.assertIn("hero: always wears the test hat", d["qa"])


class TestConform(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def render(self, name, size):
        p = self.dir / name
        png(p, size)
        return p

    def conform(self, src, out, *args):
        return subprocess.run(
            [sys.executable, str(CONFORM), str(src), str(self.dir / out), *args],
            capture_output=True, text=True)

    def size_of(self, name):
        with Image.open(self.dir / name) as im:
            return im.size

    def test_crop_tall_to_3_4(self):
        src = self.render("r.png", (1024, 1536))
        r = self.conform(src, "o.png", "--aspect", "3:4", "--mode", "crop")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.size_of("o.png"), (1024, 1365))

    def test_crop_wide_to_aspect(self):
        src = self.render("r.png", (1536, 1024))
        r = self.conform(src, "o.png", "--aspect", "3:4", "--mode", "crop")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.size_of("o.png"), (768, 1024))

    def test_pad_widens_to_square(self):
        src = self.render("r.png", (1024, 1536))
        r = self.conform(src, "o.png", "--aspect", "1:1", "--mode", "pad")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.size_of("o.png"), (1536, 1536))

    def test_pad_2_3_to_3_4_self_bleed(self):
        # the cover case: producible 2:3 -> reader 3:4, default self-bleed fill.
        src = self.render("r.png", (1024, 1536))
        r = self.conform(src, "o.webp", "--aspect", "3:4", "--mode", "pad")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.size_of("o.webp"), (1152, 1536))

    def test_pad_keyline_draws_a_frame(self):
        # a keyline (per-universe opt-in) frames the sharp art in gold.
        src = self.render("r.png", (1024, 1536))  # png() fills (200,180,140)
        r = self.conform(src, "o.png", "--aspect", "3:4", "--mode", "pad",
                          "--keyline", "#BF9540", "--inset", "0.99")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.size_of("o.png"), (1152, 1536))
        # the inset gold frame introduces a color absent from the flat source art.
        with Image.open(self.dir / "o.png") as im:
            colors = {im.getpixel((x, im.size[1] // 2)) for x in range(0, im.size[0], 4)}
        self.assertTrue(any(abs(c[0] - 0xBF) < 40 and abs(c[1] - 0x95) < 40 and c[2] < 0x80
                            for c in colors), "no gold keyline pixel found")

    def test_noop_when_already_conformed(self):
        src = self.render("r.png", (1024, 1365))
        r = self.conform(src, "o.png", "--aspect", "3:4")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(self.size_of("o.png"), (1024, 1365))

    def test_output_aspect_is_asserted(self):
        src = self.render("r.png", (1024, 1536))
        r = self.conform(src, "o.png", "--aspect", "3:4", "--mode", "crop")
        self.assertIn("OK conform", r.stdout)




class TestPlateSelection(unittest.TestCase):
    """`--with <id>:<plate>` picks WHICH plate a multi-state metaphor contributes.

    Without it the compiler always took emptyPlates[0], so a cover of a
    metaphor's LIT state could be conditioned on its UNLIT plate and fight the
    scene text. Caught on Kingdom Moments, whose cover shows the gold-lit cairn
    while emptyPlates[0] is a single unlit stone in a palm.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build_universe(Path(self.tmp.name))
        png(self.root / "reference" / "isle" / "c2.png")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_is_the_first_empty_plate(self):
        r = run_compile(self.root, "--with", "isle")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("reference/isle/c1.png", " ".join(json.loads(r.stdout)["refs"]))

    def test_named_plate_is_selected(self):
        r = run_compile(self.root, "--with", "isle:c2")
        self.assertEqual(r.returncode, 0, r.stderr)
        refs = " ".join(json.loads(r.stdout)["refs"])
        self.assertIn("reference/isle/c2.png", refs)
        self.assertNotIn("reference/isle/c1.png", refs)

    def test_unknown_plate_refuses(self):
        r = run_compile(self.root, "--with", "isle:nope")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no plate", r.stderr)

    def test_unknown_entity_refuses_instead_of_traceback(self):
        r = run_compile(self.root, "--with", "ghost")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not a canon entity", r.stderr)


class RenderCoverPassesSceneThrough(unittest.TestCase):
    """render_cover.py is a thin wrapper over compile_cover.py and silently DROPPED
    --scene and --anchor-ref, both of which the compiler has always accepted. The cost
    was a cover that could not state its own composition, so the register anchor's
    SUBJECT leaked onto the plate with no way to negate it. Earned 2026-08-01."""

    def test_wrapper_forwards_scene_and_anchor_ref(self):
        src = RENDER.read_text()
        self.assertIn('"--scene"', src)
        self.assertIn("anchor_ref", src)
        # the flags must be forwarded on the SAME cmd the wrapper builds, not merely parsed
        fwd = src.split("cmd = [")[1]
        self.assertIn('("--scene", a.scene)', fwd)
        self.assertIn('("--anchor-ref", a.anchor_ref)', fwd)

    def test_wrapper_exposes_both_flags(self):
        r = subprocess.run([sys.executable, str(RENDER), "--help"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("--scene", r.stdout)
        self.assertIn("--anchor-ref", r.stdout)

    def test_scene_text_actually_reaches_the_compiled_prompt(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        root = build_universe(Path(tmp.name))
        r = run_compile(root, "--scene", "SENTINEL_COMPOSITION_TOKEN")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("SENTINEL_COMPOSITION_TOKEN", json.loads(r.stdout)["prompt"])


class TestAnchorSubjectNegation(unittest.TestCase):
    """`identity.register.anchorSubject` names what the style anchor DEPICTS so a
    renderer can ban that subject concretely. v0.29 gave the field to `chain_matrix`
    (every matrix shot auto-negates it); the cover compiler did not read it, and a
    cover passes the anchor FIRST like everything else, so the readiness-lamp anchor
    painted an ancient burning oil lamp onto a cover wall (eleventh-hour-heroes,
    2026-08-02, one paid re-roll). Same field, same law, now read by the cover path.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.u = build_universe(Path(self.tmp.name))

    def _declare_subject(self, subject="an ancient oil lamp, a clay jar"):
        uni = json.loads((self.u / "universe.json").read_text())
        uni["identity"]["register"]["anchorSubject"] = subject
        (self.u / "universe.json").write_text(json.dumps(uni))

    def test_declared_subject_is_negated_in_the_compiled_prompt(self):
        self._declare_subject()
        r = run_compile(self.u)
        self.assertEqual(r.returncode, 0, r.stderr)
        prompt = json.loads(r.stdout)["prompt"]
        # the subject is named CONCRETELY, inside the negation sentence
        self.assertIn("an ancient oil lamp, a clay jar", prompt)
        self.assertIn("NONE OF THE FOLLOWING FROM THAT FIRST STYLE-ANCHOR REFERENCE", prompt)

    def test_no_declared_subject_means_no_guard(self):
        r = run_compile(self.u)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("STYLE-ANCHOR REFERENCE", json.loads(r.stdout)["prompt"])

    def test_anchor_ref_override_suppresses_the_registers_subject(self):
        # --anchor-ref replaces the image passed first, so the register's declared
        # subject no longer describes what that first reference depicts; negating it
        # would ban content the override may legitimately want. Mirrors chain_matrix,
        # where a register override reads the PACK's own anchorSubject instead.
        self._declare_subject()
        alt = self.u / "reference" / "register" / "alt-anchor.png"
        png(alt)
        r = run_compile(self.u, "--anchor-ref", str(alt))
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("an ancient oil lamp", json.loads(r.stdout)["prompt"])


if __name__ == "__main__":
    unittest.main()
