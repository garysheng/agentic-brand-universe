"""
Cover skill scripts — tests. Stdlib unittest (mirrors agenticstory/engine/tests).

Runs against a SYNTHETIC universe built in a tempdir (no content-repo
dependency): a locked hero character with on-disk sheets, a locked setting
with a plate, a motif, and a story. Covers the happy path AND every refusal
path — the refusals are the load-bearing feature.

Run:  python3 -m unittest discover -s tests -v   (from the cover skill dir)
"""
import hashlib
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
    png(root / "reference" / "hero" / "back.png")
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
                       "face-neutral": "reference/hero/face.png",
                       "back-fullbody": "reference/hero/back.png"},
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["always wears the test hat"],
            # PRESCRIBED PROMPT-CRAFT: wording an invariant slug cannot carry.
            "render": {
                "always": "HERO carries the copper compass, a four-point STAR, never a plain cross.",
                "poses": {"front": {"sheets": ["forward-fullbody"],
                                    "bake": "FRONT: both chest badges clearly visible."},
                          "back": {"sheets": ["back-fullbody"],
                                   "bake": "BACK: the shoulder mark, and NO chest badges."}},
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


class TestConformWritesProvenance(unittest.TestCase):
    """The conformed cover is the asset the PLATFORM ships, so it needs a recipe.

    `cover-raw.png` gets one from the provider adapter; `cover.png` got none, so
    `book-doctor` reported "provenance cover.png: no recipe.json beside the asset" and
    FAILED every book that conformed a cover. Two book runs hand-wrote the missing file
    rather than fixing the tool (Why We Are the Luckiest Generation, 2026-08-04, wrote it
    twice in one session because the cover was re-rolled).
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def conform(self, src, out, *args):
        return subprocess.run(
            [sys.executable, str(CONFORM), str(src), str(self.dir / out), *args],
            capture_output=True, text=True)

    def test_a_recipe_lands_beside_the_output(self):
        src = self.dir / "cover-raw.png"
        png(src, (1024, 1536))
        r = self.conform(src, "cover.png", "--aspect", "3:4", "--mode", "pad")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec_path = self.dir / "cover.png.recipe.json"
        self.assertTrue(rec_path.exists(), "no provenance beside the conformed cover")
        rec = json.loads(rec_path.read_text())
        self.assertEqual(rec["mode"], "derive")
        self.assertIsNone(rec["prompt"], "a conform is not a generation")
        self.assertIn("none", rec["model"], "the model field must not imply a model ran")
        self.assertEqual(rec["derivedFrom"]["path"], str(src))
        self.assertEqual(rec["args"]["mode"], "pad")
        self.assertIn("1024x1536 -> ", rec["transform"])

    def test_it_carries_spec_universe_and_story_from_the_source_recipe(self):
        """The chain back to the canon that made the art must not break at the conform."""
        src = self.dir / "cover-raw.png"
        png(src, (1024, 1536))
        (self.dir / "cover-raw.png.recipe.json").write_text(json.dumps({
            "asset": str(src), "model": "gpt-image-2", "prompt": "...",
            "spec": {"framework": "agenticstory", "version": "0.10"},
            "universe": "u", "story": "s"}))
        r = self.conform(src, "cover.png", "--aspect", "3:4", "--mode", "pad")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads((self.dir / "cover.png.recipe.json").read_text())
        self.assertEqual(rec["universe"], "u")
        self.assertEqual(rec["story"], "s")
        self.assertEqual(rec["spec"]["version"], "0.10")
        self.assertTrue(rec["derivedFrom"]["recipe"].endswith("cover-raw.png.recipe.json"))

    def test_a_missing_source_recipe_is_not_fatal(self):
        """An older cover with no recipe beside it still gets provenance for the output."""
        src = self.dir / "loose.png"
        png(src, (1024, 1536))
        r = self.conform(src, "cover.png", "--aspect", "3:4", "--mode", "pad")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads((self.dir / "cover.png.recipe.json").read_text())
        self.assertIsNone(rec["derivedFrom"]["recipe"])
        self.assertNotIn("universe", rec)

    def test_crop_mode_records_its_own_mode(self):
        src = self.dir / "cover-raw.png"
        png(src, (1024, 1536))
        r = self.conform(src, "cover.png", "--aspect", "3:4", "--mode", "crop")
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads((self.dir / "cover.png.recipe.json").read_text())
        self.assertEqual(rec["args"]["mode"], "crop")

    def test_the_recorded_hash_matches_the_file_on_disk(self):
        src = self.dir / "cover-raw.png"
        png(src, (1024, 1536))
        self.conform(src, "cover.png", "--aspect", "3:4", "--mode", "pad")
        rec = json.loads((self.dir / "cover.png.recipe.json").read_text())
        actual = hashlib.sha256((self.dir / "cover.png").read_bytes()).hexdigest()[:16]
        self.assertEqual(rec["sha256_16"], actual)




class TestHeroPose(unittest.TestCase):
    """A pose is a WARDROBE SELECTOR, so the cover must be able to pick one.

    compile_cover hardcoded poses["front"], on the assumption that covers are
    front-facing by definition. make-a-book says the opposite in as many words:
    "A character seen from behind on a cover is a `back` pose, with its sheet."
    Earned 2026-08-04 on You Didn't Have To, whose behind-the-hero cover came
    back wearing the FRONT chest patches on his back. One paid re-roll.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = build_universe(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def compiled(self, *extra):
        r = run_compile(self.u, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_defaults_to_front(self):
        """Unchanged behaviour: no flag means the front pose, bake and sheet."""
        d = self.compiled("--hero", "hero")
        self.assertIn("both chest badges", d["prompt"])
        self.assertNotIn("NO chest badges", d["prompt"])
        self.assertTrue(any(r.endswith("hero/fullbody.png") for r in d["refs"]), d["refs"])

    def test_back_pose_selects_its_own_bake_and_sheet(self):
        """--hero-pose back must pass the BACK sheet and the BACK bake, and must
        NOT leak the front bake, which is the sentence that actually steers the
        model and is what put chest patches on a back view.

        The pose's own sheets are what the selector controls. `requiredForRender`
        is the identity FLOOR and is passed whatever the pose is, so the front
        fullbody sheet legitimately stays in refs; asserting its absence here
        would be asserting against the identity contract, not the pose.
        """
        d = self.compiled("--hero", "hero", "--hero-pose", "back")
        self.assertIn("NO chest badges", d["prompt"])
        self.assertNotIn("both chest badges", d["prompt"])
        self.assertTrue(any(r.endswith("hero/back.png") for r in d["refs"]), d["refs"])

    def test_unknown_pose_refuses_and_lists_what_exists(self):
        """A typo in a selector is a REFUSAL, matching compose-spread. Silently
        falling back to the default is how the wrong wardrobe ships."""
        r = run_compile(self.u, "--hero", "hero", "--hero-pose", "sideways")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("no pose", r.stderr)
        self.assertIn("back", r.stderr)
        self.assertIn("front", r.stderr)


class TestBylineFromCanon(unittest.TestCase):
    """A byline must not depend on the operator remembering a flag.

    `--author` was optional with no default, so every cover relied on somebody
    typing the author's name. You Didn't Have To shipped a cover with no byline
    on 2026-08-04 for exactly that reason. identity.author now supplies it, the
    same way identity.mark already did.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = build_universe(Path(self.tmp.name))

    def _declare_author(self, name="Gary Sheng"):
        f = self.u / "universe.json"
        d = json.loads(f.read_text())
        d["identity"]["author"] = name
        f.write_text(json.dumps(d))

    def tearDown(self):
        self.tmp.cleanup()

    def test_identity_author_is_baked_without_the_flag(self):
        self._declare_author()
        r = run_compile(self.u)
        self.assertEqual(r.returncode, 0, r.stderr)
        d = json.loads(r.stdout)
        self.assertIn("by Gary Sheng", d["textLines"])

    def test_explicit_author_overrides_canon(self):
        self._declare_author()
        d = json.loads(run_compile(self.u, "--author", "Someone Else").stdout)
        self.assertIn("by Someone Else", d["textLines"])
        self.assertNotIn("by Gary Sheng", d["textLines"])

    def test_no_author_opts_out_deliberately(self):
        self._declare_author()
        d = json.loads(run_compile(self.u, "--no-author").stdout)
        self.assertFalse([t for t in d["textLines"] if t.startswith("by ")], d["textLines"])

    def test_universe_without_an_author_is_unchanged(self):
        """Back-compatible: declaring no author still yields no byline."""
        d = json.loads(run_compile(self.u).stdout)
        self.assertFalse([t for t in d["textLines"] if t.startswith("by ")], d["textLines"])

    def test_author_and_no_author_together_refuse(self):
        self._declare_author()
        r = run_compile(self.u, "--author", "X", "--no-author")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("contradictory", r.stderr)


class TextRoomIsCompiled(unittest.TestCase):
    """The compiled prompt must reserve ROOM for the lettering, not just name it.

    Four of twelve Nation of Fire covers came back with the title alone on
    2026-08-05, byline and series mark silently dropped, because the prompt asked
    for text and never asked for anywhere to put it; a scene composing edge to edge
    simply won. One book took three attempts, its lower third filled by a lit lamp
    exactly where the series mark belongs.

    The first fix was hand-typed into that one book's scene. Gary: "why is the
    prompt hand rolled though". This is the rule living in the generator instead.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = build_universe(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def compiled(self, *extra):
        r = run_compile(self.u, *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_prompt_demands_room_for_the_lettering(self):
        p = self.compiled("--author", "Gary Sheng")["prompt"]
        self.assertIn("ROOM FOR THEM", p)
        self.assertIn("uncluttered", p)

    def test_prompt_names_the_failure_so_it_cannot_be_ignored(self):
        p = self.compiled("--author", "Gary Sheng")["prompt"]
        self.assertIn("IF ANY OF THESE LINES IS MISSING", p)

    def test_prompt_counts_the_required_lines(self):
        """title + subtitle + byline + mark = 4 in the test universe."""
        p = self.compiled("--author", "Gary Sheng")["prompt"]
        self.assertIn("CARRIES 4 LINE(S)", p)

    def test_no_text_mode_does_not_reserve_room_for_text_it_forbids(self):
        p = self.compiled("--no-text")["prompt"]
        self.assertIn("ART ONLY", p)
        self.assertNotIn("ROOM FOR THEM", p)


class TextBlockComesLast(unittest.TestCase):
    """A long, prescriptive scene must not be able to bury the text requirement.

    the-king-is-coming dropped its byline and series mark on four consecutive
    attempts. Its scene is 4,400 characters and assigns the lower third of the
    frame to a lit lamp, which is exactly where the series mark goes; the text
    requirement was emitted above it and lost.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.u = build_universe(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_text_requirement_is_after_the_scene(self):
        r = run_compile(self.u, "--author", "Gary Sheng",
                        "--scene", "A VERY SPECIFIC COMPOSITION filling every inch of the frame.")
        self.assertEqual(r.returncode, 0, r.stderr)
        p = json.loads(r.stdout)["prompt"]
        self.assertLess(p.index("A VERY SPECIFIC COMPOSITION"), p.index("LINE(S) OF HAND-LETTERED"),
                        "the scene must come first; the text requirement must arrive after it")

    def test_negatives_still_close_the_prompt(self):
        p = json.loads(run_compile(self.u, "--author", "Gary Sheng").stdout)["prompt"]
        self.assertLess(p.index("LINE(S) OF HAND-LETTERED"), p.index("NEGATIVES:"))


class ConformPreservesTheGeneration(unittest.TestCase):
    """An in-place conform must not delete the record of what made the pixels.

    render_cover conforms IN PLACE, so the derivative recipe overwrites the
    generation recipe at the same path. Measured on nation-of-fire 2026-08-05:
    30 of 39 cover recipes had lost their generation prompt and 25 had a
    derivedFrom pointer looping back to themselves. The cost was concrete --
    rebuilding 28 covers to add a byline meant reconstructing each composition by
    looking at the art, because the scene that made it no longer existed anywhere.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = Path(self.tmp.name)
        self.img = self.d / "cover-raw.png"
        png(self.img, size=(1024, 1536))
        Path(str(self.img) + ".recipe.json").write_text(json.dumps({
            "prompt": "PORTRAIT COVER. the scene that made this art",
            "refs": [{"path": "/x/anchor.png"}],
            "provider": "gpt-image-2", "model": "gpt-image-2",
            "textLines": ["A Title", "by Gary Sheng"],
            "universe": "testverse", "story": "tale",
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def conform_in_place(self):
        return subprocess.run(
            [sys.executable, str(CONFORM), str(self.img), str(self.img),
             "--aspect", "3:4", "--mode", "pad"], capture_output=True, text=True)

    def test_generation_prompt_survives_an_in_place_conform(self):
        r = self.conform_in_place()
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(Path(str(self.img) + ".recipe.json").read_text())
        self.assertIn("sourceRender", rec, "the generation record was destroyed")
        self.assertIn("the scene that made this art", rec["sourceRender"]["prompt"])
        self.assertEqual(rec["sourceRender"]["refs"], [{"path": "/x/anchor.png"}])

    def test_the_derivative_is_still_honest_about_itself(self):
        """Preserving the generation must not make the conform claim to BE one."""
        self.conform_in_place()
        rec = json.loads(Path(str(self.img) + ".recipe.json").read_text())
        self.assertIsNone(rec["prompt"])
        self.assertIn("no model call", rec["model"])

    def test_no_self_referential_derivedFrom(self):
        self.conform_in_place()
        rec = json.loads(Path(str(self.img) + ".recipe.json").read_text())
        self.assertIsNone(rec["derivedFrom"]["recipe"],
                          "an in-place conform must not point derivedFrom at itself")

    def test_a_two_path_conform_still_links_to_the_source_recipe(self):
        out = self.d / "cover.png"
        r = subprocess.run([sys.executable, str(CONFORM), str(self.img), str(out),
                            "--aspect", "3:4", "--mode", "pad"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        rec = json.loads(Path(str(out) + ".recipe.json").read_text())
        self.assertTrue(rec["derivedFrom"]["recipe"].endswith("cover-raw.png.recipe.json"))
        self.assertIn("sourceRender", rec)

    def test_a_source_with_no_generation_adds_no_sourceRender(self):
        Path(str(self.img) + ".recipe.json").write_text(json.dumps({"universe": "testverse"}))
        self.conform_in_place()
        rec = json.loads(Path(str(self.img) + ".recipe.json").read_text())
        self.assertNotIn("sourceRender", rec)


class RenderWrapperForwardsClosingPlateFlags(unittest.TestCase):
    """render_cover.py must expose --no-cast/--no-text/--negative, the closing-plate mode.

    compile_cover accepted all three and the wrapper dropped them, so every closing plate
    was hand-chained (compile -> provider -> conform -> provenance) and two books' recipes
    record that chain verbatim (the-smoke-test and nobody-labeled-the-door, hyperagentic-age
    2026-08-07). A --help probe is deliberate: no network, no provider, and it fails the
    moment a refactor drops the wiring.
    """

    def test_help_lists_the_forwarded_flags(self):
        r = subprocess.run([sys.executable, str(RENDER), "--help"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        for flag in ("--no-cast", "--no-text", "--negative"):
            self.assertIn(flag, r.stdout, f"render_cover.py --help no longer lists {flag}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
