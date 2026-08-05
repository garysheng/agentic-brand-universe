"""
compose-spread assemble_prompt.py — tests. Stdlib unittest (mirrors the cover
skill's tests). Runs against a SYNTHETIC universe in a tempdir: two brothers
(one clean-shaven by canon, one with a mustache ALT-LOOK), a locked setting, and
a render-spec whose guarded negative would forbid facial hair.

The load-bearing test is `test_altlook_defeats_guarded_negative`: it reproduces
the abundant-color spread-7 drift (a global "everyone is clean-shaven" negative
silently fighting a canon facial-hair alt-look) and proves the assembler now
resolves it from the SAME canon look.

Run:  python3 -m unittest discover -s tests -v   (from the compose-spread skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
ASSEMBLE = SCRIPTS / "assemble_prompt.py"


def png(path: Path, size=(8, 8)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, (200, 180, 140)).save(path)


def build_universe(root: Path):
    (root / "canon" / "entities").mkdir(parents=True)
    for p in ["register/anchor", "clean/full", "clean/face",
              "stache/full", "stache/face", "stache/alt-photo", "home/kitchen",
              "lord/full", "jv/full"]:
        png(root / "reference" / (p + ".png"))
    (root / "universe.json").write_text(json.dumps({
        "name": "testverse", "assetRoot": ".",
        "identity": {
            "mark": "A TESTVERSE story",
            "register": {
                "name": "test register",
                "anchor": "reference/register/anchor.png",
                "rejectedPoles": ["photoreal", "anime"],
            },
        },
    }))
    # brother A: clean-shaven by canon
    (root / "canon" / "entities" / "clean.json").write_text(json.dumps({
        "id": "clean", "kind": "character",
        "structured": {
            "sheets": {"forward-fullbody": "reference/clean/full.png",
                       "face-neutral": "reference/clean/face.png"},
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["real-person-depicted-with-dignity",
                           "completely-clean-shaven-never-a-mustache",
                           "short-swept-back-hair"],
        },
    }))
    # brother C: carries PRESCRIBED PROMPT-CRAFT in structured.render (always +
    # per-pose bake and per-pose sheets). Mirrors the real jerry-man record whose
    # signature wardrobe/pendant wording lived in canon but never reached a prompt.
    png(root / "reference" / "scout" / "full.png")
    png(root / "reference" / "scout" / "face.png")
    png(root / "reference" / "scout" / "coat-back.png")
    (root / "canon" / "entities" / "scout.json").write_text(json.dumps({
        "id": "scout", "kind": "character",
        "structured": {
            "sheets": {"forward-fullbody": "reference/scout/full.png",
                       "face-neutral": "reference/scout/face.png",
                       "coatBack": "reference/scout/coat-back.png"},
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["signature-badge-front"],
            "render": {
                "always": "SCOUT always wears the copper compass, a four-point STAR, never a plain cross.",
                "poses": {
                    "front": {"sheets": ["forward-fullbody", "face-neutral"],
                              "bake": "FRONT: both chest badges clearly visible, a round SUN badge and a RIVER badge."},
                    "back": {"sheets": ["coatBack"],
                             "bake": "BACK: the coat back carries EXACTLY ONE badge."},
                },
            },
        },
    }))

    # brother B: clean-shaven default + a mustache-wavy ALT LOOK
    (root / "canon" / "entities" / "stache.json").write_text(json.dumps({
        "id": "stache", "kind": "character",
        "structured": {
            "sheets": {"forward-fullbody": "reference/stache/full.png",
                       "face-neutral": "reference/stache/face.png"},
            "requiredForRender": ["forward-fullbody", "face-neutral"],
            "invariants": ["real-person-depicted-with-dignity",
                           "completely-clean-shaven-no-facial-hair",
                           "short-neat-hair"],
            "altLooks": {
                "mustache-wavy": {
                    "anchorPhoto": "reference/stache/alt-photo.png",
                    "supersedes": ["completely-clean-shaven-no-facial-hair", "short-neat-hair"],
                    "invariants": ["dark-mustache-and-wispy-chin-goatee", "longer-wavy-tousled-hair"],
                },
            },
        },
    }))
    # The real nation-of-fire collision, in miniature: an entity whose id LEADS with a
    # stopword, and a different real person who merely shares one of its name words.
    (root / "canon" / "entities" / "the-lord-jesus-christ.json").write_text(json.dumps({
        "id": "the-lord-jesus-christ", "kind": "character",
        "structured": {"sheets": {"forward-fullbody": "reference/lord/full.png"},
                       "requiredForRender": ["forward-fullbody"],
                       "invariants": ["awe-not-horror"]},
    }))
    (root / "canon" / "entities" / "jesus-villavicencio.json").write_text(json.dumps({
        "id": "jesus-villavicencio", "kind": "character",
        "structured": {"sheets": {"forward-fullbody": "reference/jv/full.png"},
                       "requiredForRender": ["forward-fullbody"],
                       "invariants": ["real-person-depicted-with-dignity"]},
    }))
    (root / "canon" / "entities" / "home.json").write_text(json.dumps({
        "id": "home", "kind": "setting", "status": "locked",
        "contract": {"dressing": "warm test kitchen"},
    }))
    # A PROP with more than one sheet: the case a motif/prop could not express before
    # (it could only ever be passed its requiredForRender default).
    for p in ["tome/shut", "tome/open"]:
        png(root / "reference" / (p + ".png"))
    (root / "canon" / "entities" / "tome.json").write_text(json.dumps({
        "id": "tome", "kind": "prop", "status": "locked",
        "structured": {"sheets": {"shut": "reference/tome/shut.png",
                                  "open": "reference/tome/open.png"},
                       "requiredForRender": ["shut"]},
        "prose": {"rules": "a plain blue book, shut on the table"},
    }))


def write_spec(root: Path, cast, **extra):
    spec = {
        "size": "1536x1024",
        "style": "warm test style.",
        "negatives": ["no text anywhere"],
        "guardedNegatives": [
            {"text": "no facial hair on any character, bare smooth upper lips",
             "satisfiedByInvariantMatching": "mustache|goatee|beard"},
        ],
        "spreads": [{"id": "s1", "setting": "home", "plate": "kitchen",
                     "scene": "the two brothers at the table", "cast": cast}],
    }
    spec.update(extra)
    p = root / "render-spec.json"
    p.write_text(json.dumps(spec))
    return p


def run(root: Path, spec: Path, spread="s1"):
    r = subprocess.run([sys.executable, str(ASSEMBLE), str(root), str(spec), spread],
                       capture_output=True, text=True)
    return r


class TestAssemble(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, spec):
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_altlook_defeats_guarded_negative(self):
        """THE REGRESSION: a castmate whose selected look has facial hair must
        drop the blanket 'no facial hair' negative, while the clean-shaven
        castmate stays bound by his own positive invariant."""
        spec = write_spec(self.root, [{"id": "clean"},
                                      {"id": "stache", "look": "mustache-wavy"}])
        out = self.out(spec)
        p = out["prompt"].lower()
        self.assertNotIn("no facial hair on any character", p)
        self.assertIn("dark mustache and wispy chin goatee", p)         # alt look asserted
        self.assertIn("completely clean shaven never a mustache", p)     # clean brother still bound

    def test_guarded_negative_present_when_nobody_has_the_feature(self):
        """Both brothers default (clean) -> the blanket negative IS emitted."""
        spec = write_spec(self.root, [{"id": "clean"}, {"id": "stache"}])
        out = self.out(spec)
        self.assertIn("no facial hair on any character", out["prompt"].lower())

    def test_anchor_is_first_ref(self):
        spec = write_spec(self.root, [{"id": "clean"}])
        out = self.out(spec)
        self.assertTrue(out["refs"][0].endswith("register/anchor.png"))

    def test_altlook_swaps_face_ref_keeps_body(self):
        """Alt look pulls its OWN anchor photo and the base BODY sheet (pose),
        but drops the base FACE sheet (which would fight the alt look)."""
        spec = write_spec(self.root, [{"id": "stache", "look": "mustache-wavy"}])
        refs = " ".join(self.out(spec)["refs"])
        self.assertIn("stache/alt-photo.png", refs)   # alt face/hair anchor
        self.assertIn("stache/full.png", refs)        # base body sheet kept for pose
        self.assertNotIn("stache/face.png", refs)     # default face sheet dropped

    def test_disambiguation_names_differences(self):
        spec = write_spec(self.root, [{"id": "clean"},
                                      {"id": "stache", "look": "mustache-wavy"}])
        p = self.out(spec)["prompt"].lower()
        self.assertIn("tell them apart", p)
        self.assertIn("dark mustache and wispy chin goatee", p)  # a distinguishing trait surfaced

    def test_anchor_override(self):
        png(self.root.parent / "sibling" / "painterly.png")
        spec = write_spec(self.root, [{"id": "clean"}],
                          anchorRef="../sibling/painterly.png")
        out = self.out(spec)
        self.assertTrue(out["refs"][0].endswith("sibling/painterly.png"))

    def test_refuse_unknown_spread(self):
        spec = write_spec(self.root, [{"id": "clean"}])
        r = subprocess.run([sys.executable, str(ASSEMBLE), str(self.root), str(spec), "nope"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not in render-spec", r.stderr)

    def test_refuse_unknown_altlook(self):
        spec = write_spec(self.root, [{"id": "stache", "look": "does-not-exist"}])
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 2)
        self.assertIn("altLook", r.stderr)

    def test_refuse_missing_ref_on_disk(self):
        (self.root / "reference" / "clean" / "face.png").unlink()
        spec = write_spec(self.root, [{"id": "clean"}])
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not resolve", r.stderr)

    # --- structured.render (prescribed prompt-craft) ---------------------------
    def test_render_always_reaches_the_prompt(self):
        """Canon's render.always is wording an invariant slug cannot carry."""
        spec = write_spec(self.root, [{"id": "scout"}])
        out = self.out(spec)
        self.assertIn("copper compass", out["prompt"])
        self.assertIn("never a plain cross", out["prompt"])

    def test_front_pose_is_the_default_bake(self):
        """Front-facing is the common case and the one canon warns about, so the
        signature front detail must appear WITHOUT the author naming a pose."""
        spec = write_spec(self.root, [{"id": "scout"}])
        out = self.out(spec)
        self.assertIn("both chest badges", out["prompt"])
        self.assertNotIn("EXACTLY ONE badge", out["prompt"])

    def test_explicit_pose_selects_its_bake_and_sheets(self):
        spec = write_spec(self.root, [{"id": "scout", "pose": "back"}])
        out = self.out(spec)
        self.assertIn("EXACTLY ONE badge", out["prompt"])
        self.assertNotIn("both chest badges", out["prompt"])
        self.assertTrue(any(r.endswith("coat-back.png") for r in out["refs"]),
                        f"back pose must pass its own sheet: {out['refs']}")

    def test_invariants_still_drive_qa_alongside_render_block(self):
        """The render block STEERS; the invariants remain the readback keys."""
        spec = write_spec(self.root, [{"id": "scout"}])
        out = self.out(spec)
        self.assertIn("scout: signature-badge-front", out["qa"])

    def test_refuse_unknown_pose(self):
        spec = write_spec(self.root, [{"id": "scout", "pose": "sideways"}])
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 2)
        self.assertIn("no render pose", r.stderr)

    def test_entity_without_render_block_is_unaffected(self):
        spec = write_spec(self.root, [{"id": "clean"}])
        out = self.out(spec)
        self.assertIn("clean rendered exactly per the supplied reference images", out["prompt"])
        self.assertNotIn("copper compass", out["prompt"])


class TestAltLookDropSheets(unittest.TestCase):
    """An alt look must be able to drop base sheets it CONTRADICTS.

    Guarded negatives already stop a blanket negative fighting a canon look, but
    nothing did the same for REFS. A look whose invariant said "neck completely
    bare" still had the adult PENDANT sheet passed to the model, and a reference
    image outranks a word. Caught while adding jerry-man's age eras: young Jerry
    was being conditioned on the adult North Star pendant and the red low-tops.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)
        png(self.root / "reference" / "stache" / "pendant.png")
        ent = self.root / "canon" / "entities" / "stache.json"
        d = json.loads(ent.read_text())
        st = d["structured"]
        st["sheets"]["pendant"] = "reference/stache/pendant.png"
        st["requiredForRender"].append("pendant")
        ent.write_text(json.dumps(d))
        self.ent = ent

    def tearDown(self):
        self.tmp.cleanup()

    def _refs(self):
        spec = write_spec(self.root, [{"id": "stache", "look": "mustache-wavy"}])
        out = run(self.root, spec)
        self.assertEqual(out.returncode, 0, out.stderr)
        return " ".join(json.loads(out.stdout)["refs"])

    def test_without_dropsheets_the_base_sheet_still_rides_along(self):
        self.assertIn("pendant.png", self._refs())

    def test_dropsheets_removes_the_contradicted_base_sheet(self):
        d = json.loads(self.ent.read_text())
        d["structured"]["altLooks"]["mustache-wavy"]["dropSheets"] = ["pendant"]
        self.ent.write_text(json.dumps(d))
        refs = self._refs()
        self.assertNotIn("pendant.png", refs)
        self.assertIn("alt-photo.png", refs)

    def test_dropsheets_does_not_affect_the_default_look(self):
        d = json.loads(self.ent.read_text())
        d["structured"]["altLooks"]["mustache-wavy"]["dropSheets"] = ["pendant"]
        self.ent.write_text(json.dumps(d))
        spec = write_spec(self.root, [{"id": "stache"}])
        out = run(self.root, spec)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("pendant.png", " ".join(json.loads(out.stdout)["refs"]))


class TestAltLookRenderBlock(unittest.TestCase):
    """An alt look may REPLACE the entity's render block.

    dropSheets stops a contradicted base SHEET reaching the model. This stops the
    contradicted base PROSE. Caught rendering jerry-man's college era: the sheet
    was gone but `render.always` still said "his gold NORTH STAR pendant" and the
    front pose still baked the adult denim jacket, so the model drew a necklace on
    a twenty-year-old whose invariants say his neck is bare.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)
        self.ent = self.root / "canon" / "entities" / "stache.json"
        d = json.loads(self.ent.read_text())
        d["structured"]["render"] = {
            "always": "ADULT PROSE: he always wears the gold pendant.",
            "poses": {"front": {"sheets": [], "bake": "FRONT: the adult jacket."}},
        }
        self.ent.write_text(json.dumps(d))

    def tearDown(self):
        self.tmp.cleanup()

    def _prompt(self, cast):
        spec = write_spec(self.root, cast)
        out = run(self.root, spec)
        self.assertEqual(out.returncode, 0, out.stderr)
        return json.loads(out.stdout)["prompt"]

    def test_base_render_block_applies_to_the_default_look(self):
        p = self._prompt([{"id": "stache"}])
        self.assertIn("ADULT PROSE", p)
        self.assertIn("FRONT: the adult jacket.", p)

    def test_alt_look_without_its_own_render_block_still_inherits_the_base(self):
        p = self._prompt([{"id": "stache", "look": "mustache-wavy"}])
        self.assertIn("ADULT PROSE", p)

    def test_alt_look_render_block_replaces_the_base_entirely(self):
        d = json.loads(self.ent.read_text())
        d["structured"]["altLooks"]["mustache-wavy"]["render"] = {
            "always": "YOUNGER PROSE: his neck is completely bare."
        }
        self.ent.write_text(json.dumps(d))
        p = self._prompt([{"id": "stache", "look": "mustache-wavy"}])
        self.assertIn("YOUNGER PROSE", p)
        self.assertNotIn("ADULT PROSE", p)
        self.assertNotIn("FRONT: the adult jacket.", p)
        # and the default look is untouched
        self.assertIn("ADULT PROSE", self._prompt([{"id": "stache"}]))


class TestPromotedGuards(unittest.TestCase):
    """The four guards promoted OUT of the Nation of Fire fork into the framework
    compiler on 2026-07-25, plus the per-spread register override earned on
    jerry-and-the-game-that-beat-gta. Each was paid for with defective renders and
    each lived in exactly one universe until now, invisible to every other."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def spec(self, spreads, **book):
        s = {"size": "1536x1024", "style": "warm test style.",
             "negatives": ["no text anywhere"], "spreads": spreads}
        s.update(book)
        p = self.root / "render-spec.json"
        p.write_text(json.dumps(s))
        return p

    def out(self, spreads, spread="s1", **book):
        r = run(self.root, self.spec(spreads, **book), spread)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def refuse(self, spreads, spread="s1", **book):
        r = run(self.root, self.spec(spreads, **book), spread)
        self.assertEqual(r.returncode, 2, f"expected REFUSE, got 0:\n{r.stdout[:400]}")
        return r.stderr

    # --- ANCHOR_STYLE_GUARD (earned: the-vision-of-the-ocean) ---------------------

    def test_anchor_style_guard_is_always_emitted(self):
        """The anchor is ref[0] on EVERY render, so its subject leaks on a bare
        spread. The guard is a property of passing an anchor at all."""
        out = self.out([{"id": "s1", "scene": "an empty room", "cast": []}])
        self.assertIn("STYLE ANCHOR ONLY", out["prompt"])
        self.assertIn("take NO subject from it", out["prompt"])

    def test_anchor_style_guard_survives_a_bare_spread(self):
        """The exact shape that failed: no setting, no characters, two refs total."""
        out = self.out([{"id": "s1", "scene": "look down into the water", "cast": []}])
        self.assertEqual(len(out["refs"]), 1)          # anchor only
        self.assertIn("STYLE ANCHOR ONLY", out["prompt"])

    # --- SINGLE_IMAGE_GUARD (earned: why-do-i-get-to-meet-them) -------------------

    def test_single_image_guard_on_by_default(self):
        out = self.out([{"id": "s1", "scene": "a quiet room", "cast": [{"id": "clean"}]}])
        self.assertIn("ONE SINGLE CONTINUOUS FULL-BLEED PAINTING", out["prompt"])

    def test_single_image_guard_opt_out_book_level(self):
        out = self.out([{"id": "s1", "scene": "a quiet room", "cast": []}],
                       allowMultiPanel=True)
        self.assertNotIn("ONE SINGLE CONTINUOUS", out["prompt"])

    def test_single_image_guard_opt_out_per_spread(self):
        out = self.out([{"id": "s1", "scene": "a quiet room", "cast": [],
                         "allowMultiPanel": True}])
        self.assertNotIn("ONE SINGLE CONTINUOUS", out["prompt"])

    # --- uncast-character refusal (earned: why-do-i-get-to-meet-them, 5 spreads) --

    def test_uncast_character_named_in_scene_refuses(self):
        """The most expensive silent defect: the model invents a stranger."""
        err = self.refuse([{"id": "s1", "scene": "clean sits with stache at the table",
                            "cast": [{"id": "clean"}]}])
        self.assertIn("UNCAST CHARACTERS", err)
        self.assertIn("stache", err)

    def test_uncast_refusal_costs_nothing_when_everyone_is_cast(self):
        out = self.out([{"id": "s1", "scene": "clean sits with stache at the table",
                         "cast": [{"id": "clean"}, {"id": "stache"}]}])
        self.assertIn("SCENE:", out["prompt"])

    def test_uncast_allows_an_explicit_override(self):
        """A mention that is genuinely not an in-frame person."""
        out = self.out([{"id": "s1", "scene": "clean thinks about stache",
                         "cast": [{"id": "clean"}], "allowUncast": True}])
        self.assertIn("SCENE:", out["prompt"])

    def test_uncast_does_not_flag_a_name_that_is_designed_text(self):
        """A name in QUOTED lettering is a thing to render, not a body to draw.

        Earned on nation-of-fire/the-higher-law: a book cover reading
        'APOSTLE DELMAR COWARD JR.' AND 'GARY SHENG' tripped the guard and demanded
        two characters be cast who are not in the scene at all, and the tempting
        move was the allowUncast escape hatch.
        """
        out = self.out([{"id": "s1", "cast": [{"id": "clean"}],
                         "scene": "clean holds a book whose cover reads 'stache' in gold capitals"}])
        self.assertIn("SCENE:", out["prompt"])

    def test_a_cast_entity_accounts_for_its_own_name(self):
        """Casting the Lord must license writing "Jesus" in the scene.

        `_name_tokens` took only the HEAD token, so `the-lord-jesus-christ` yielded
        nothing at all ("the" is three letters) and casting Him contributed zero
        tokens. "Jesus" in the prose then matched `jesus-villavicencio`, a different
        real person who shares the given name, and the spread was REFUSED. The
        universe absorbed that as a writing rule -- "say THE LORD, never JESUS" --
        which is a human working around a tool bug. Gary, 2026-08-05: "you can write
        Jesus. Dumb ass rule."
        """
        out = self.out([{"id": "s1", "cast": [{"id": "the-lord-jesus-christ"}],
                         "scene": "Jesus stands on the shore at dawn"}])
        self.assertIn("SCENE:", out["prompt"])

    def test_the_shared_name_still_refuses_when_nobody_is_cast(self):
        """The guard must not go blind: uncast + named is still the expensive defect."""
        err = self.refuse([{"id": "s1", "cast": [{"id": "clean"}],
                            "scene": "clean waits while Jesus walks up the beach"}])
        self.assertIn("UNCAST CHARACTERS", err)

    def test_detection_stays_conservative_on_qualifier_tokens(self):
        """Generosity applies to what a CAST id covers, never to detection.

        A common noun that happens to be an id's qualifier must still not summon a
        character, which is why `_name_tokens` keeps the head-only rule.
        """
        import importlib.util, pathlib
        _p = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "assemble_prompt.py"
        _spec = importlib.util.spec_from_file_location("_ap", _p)
        _ap = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(_ap)
        _name_tokens, _cast_name_tokens = _ap._name_tokens, _ap._cast_name_tokens
        self.assertEqual(_name_tokens("silas-driver"), {"silas"})
        self.assertEqual(_cast_name_tokens("the-lord-jesus-christ"),
                         {"lord", "jesus", "christ"})

    def test_uncast_still_flags_an_unquoted_mention_next_to_designed_text(self):
        """The quote-stripping must not blind the guard to a real body in frame."""
        err = self.refuse([{"id": "s1", "cast": [{"id": "clean"}],
                            "scene": "a sign reads 'welcome' while stache waits by the door"}])
        self.assertIn("UNCAST CHARACTERS", err)
        self.assertIn("stache", err)

    # --- promoted from the nation-of-fire fork 2026-07-25 (measured: 325 uses) ------

    def test_prop_can_select_a_non_default_sheet(self):
        """A prop that is sometimes open and sometimes shut needs to say which."""
        out = self.out([{"id": "s1", "scene": "the book lies open",
                         "cast": [{"id": "tome", "plate": "open"}]}])
        joined = " ".join(out["refs"])
        self.assertIn("reference/tome/open.png", joined)
        self.assertNotIn("reference/tome/shut.png", joined)

    def test_prop_without_a_plate_still_uses_its_locked_default(self):
        out = self.out([{"id": "s1", "scene": "the book lies there",
                         "cast": [{"id": "tome"}]}])
        self.assertIn("reference/tome/shut.png", " ".join(out["refs"]))

    def test_bake_replaces_a_cast_entrys_derived_block(self):
        """Load-bearing for a multi-state metaphor: the derived block describes EVERY
        state, so handing it over whole makes the model draw all of them at once."""
        out = self.out([{"id": "s1", "scene": "the book lies open",
                         "cast": [{"id": "tome", "plate": "open",
                                   "bake": "ONLY the open state, nothing else"}]}])
        self.assertIn("ONLY the open state, nothing else", out["prompt"])
        self.assertNotIn("shut on the table", out["prompt"])

    def test_setting_rule_appends_without_editing_canon(self):
        """The same room reads colder in a cancellation beat than in a homecoming."""
        out = self.out([{"id": "s1", "setting": "home", "plate": "kitchen",
                         "scene": "a cold morning", "cast": []}],
                       settingRule={"home": "TODAY IT IS COLD AND UNLIT."})
        self.assertIn("warm test kitchen", out["prompt"])
        self.assertIn("TODAY IT IS COLD AND UNLIT.", out["prompt"])

    def test_setting_rule_is_overridable_per_spread(self):
        out = self.out([{"id": "s1", "setting": "home", "plate": "kitchen",
                         "scene": "a warm evening", "cast": [],
                         "settingRule": {"home": "TONIGHT IT GLOWS."}}],
                       settingRule={"home": "TODAY IT IS COLD."})
        self.assertIn("TONIGHT IT GLOWS.", out["prompt"])
        self.assertNotIn("TODAY IT IS COLD.", out["prompt"])

    def test_uncast_does_not_flag_a_setting(self):
        """`home` is a setting, not a character: naming it is never a missing person."""
        out = self.out([{"id": "s1", "setting": "home", "plate": "kitchen",
                         "scene": "a warm home in the evening", "cast": []}])
        self.assertIn("SCENE:", out["prompt"])

    # --- per-spread register override (earned: jerry-and-the-game-that-beat-gta) --

    def test_spread_overrides_anchor_style_and_negatives(self):
        """A book that argues in its own paint: one spread renders a SECOND
        register (a game world, a vision, a dream) without a second render-spec."""
        png(self.root / "reference" / "register" / "anime.png")
        out = self.out([{"id": "s1", "scene": "inside the game", "cast": [],
                         "anchorRef": "reference/register/anime.png",
                         "style": "blazing heroic anime.",
                         "negatives": ["never soft oil painting"]}])
        self.assertTrue(out["refs"][0].endswith("register/anime.png"))
        self.assertIn("blazing heroic anime.", out["prompt"])
        self.assertIn("never soft oil painting", out["prompt"])
        self.assertNotIn("warm test style.", out["prompt"])
        self.assertNotIn("no text anywhere", out["prompt"])

    def test_a_spread_that_overrides_nothing_is_unchanged(self):
        """Backward compatibility: every existing spec compiles as before."""
        png(self.root / "reference" / "register" / "anime.png")
        out = self.out([
            {"id": "s1", "scene": "the real world", "cast": []},
            {"id": "s2", "scene": "inside the game", "cast": [],
             "anchorRef": "reference/register/anime.png", "style": "anime."},
        ], spread="s1")
        self.assertTrue(out["refs"][0].endswith("register/anchor.png"))
        self.assertIn("warm test style.", out["prompt"])
        self.assertNotIn("anime.", out["prompt"])

    def test_spread_override_of_size(self):
        out = self.out([{"id": "s1", "scene": "a tall plate", "cast": [],
                         "size": "1024x1536"}])
        self.assertEqual(out["size"], "1024x1536")

    def test_universe_rejected_poles_survive_a_spread_negatives_override(self):
        """A spread may replace the BOOK's negatives; it may not shed the
        universe's own rejectedPoles, which are identity, not book style."""
        out = self.out([{"id": "s1", "scene": "inside the game", "cast": [],
                         "negatives": ["never soft oil painting"]}])
        self.assertIn("photoreal", out["prompt"])


class TestDeclaredFutureLook(unittest.TestCase):
    """A DECLARED-FUTURE (prophetic) look keeps the face and changes the body.

    Every other alt look changes the FACE (a beard, an age era) and supplies its
    own anchorPhoto, so the compiler auto-drops the base face sheets to stop them
    fighting it. A declared-future look inverts that: the face is CONTINUOUS and
    the BODY changes, and the future has no photograph to anchor. Under the old
    rule such a look reached the model with no identity reference at all and it
    drew a stranger wearing the right build. Earned 2026-07-26 adding beef-jones'
    2028/2030 prophetic eras to a Nation of Fire book whose final act is set there.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)
        png(self.root / "reference" / "stache" / "photo-a.png")
        self.ent = self.root / "canon" / "entities" / "stache.json"
        d = json.loads(self.ent.read_text())
        d["realPerson"] = {"photoStack": ["reference/stache/photo-a.png"]}
        d["structured"]["altLooks"]["era-2030"] = {
            "era": "2030",
            "supersedes": ["short-neat-hair"],
            "invariants": ["lean-and-powerfully-built"],
        }
        self.d = d

    def tearDown(self):
        self.tmp.cleanup()

    def write(self):
        self.ent.write_text(json.dumps(self.d))

    def run_look(self):
        spec = write_spec(self.root, [{"id": "stache", "look": "era-2030"}])
        return run(self.root, spec)

    def test_future_look_without_keep_is_refused_not_silently_faceless(self):
        """The failure this exists to prevent: no anchorPhoto, face sheets
        auto-dropped, so nothing anchors identity. Refuse loudly at compile time
        (free) rather than pay for a render of a stranger."""
        self.write()
        r = self.run_look()
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("NO identity reference", r.stderr)

    def test_keep_sheets_passes_the_base_face(self):
        self.d["structured"]["altLooks"]["era-2030"]["keepSheets"] = ["face-neutral"]
        self.write()
        r = self.run_look()
        self.assertEqual(r.returncode, 0, r.stderr)
        refs = json.loads(r.stdout)["refs"]
        self.assertTrue(any(x.endswith("stache/face.png") for x in refs),
                        "the continuous face must reach the model")

    def test_keep_photos_passes_the_real_photo_stack(self):
        """A real person's photos are default-look only, because an alt look
        normally contradicts them. A declared future does not: the man's face is
        the same face."""
        self.d["structured"]["altLooks"]["era-2030"]["keepPhotos"] = True
        self.write()
        r = self.run_look()
        self.assertEqual(r.returncode, 0, r.stderr)
        refs = json.loads(r.stdout)["refs"]
        self.assertTrue(any(x.endswith("stache/photo-a.png") for x in refs))

    def test_future_invariants_still_supersede_the_body(self):
        self.d["structured"]["altLooks"]["era-2030"]["keepSheets"] = ["face-neutral"]
        self.write()
        r = self.run_look()
        out = json.loads(r.stdout)
        self.assertIn("stache: lean-and-powerfully-built", out["qa"])
        self.assertNotIn("stache: short-neat-hair", out["qa"])

    def test_keep_sheets_cannot_resurrect_a_dropped_sheet(self):
        """dropSheets stays authoritative: an explicit contradiction outranks a
        keep, so the two fields can never fight to a coin flip."""
        self.d["structured"]["altLooks"]["era-2030"]["keepSheets"] = ["face-neutral"]
        self.d["structured"]["altLooks"]["era-2030"]["dropSheets"] = ["face-neutral"]
        self.d["structured"]["altLooks"]["era-2030"]["keepPhotos"] = True
        self.write()
        r = self.run_look()
        self.assertEqual(r.returncode, 0, r.stderr)
        refs = json.loads(r.stdout)["refs"]
        self.assertFalse(any(x.endswith("stache/face.png") for x in refs))


class TestRelativeScale(unittest.TestCase):
    """Two characters in one frame have a height relationship and nothing in the
    matrix could state it, so the model made them the same height and the drift was
    invisible until somebody who knows them said "he is much shorter than that."
    Same reasoning as the v0.9 setting scalePlate: a dimension nothing depicts
    cannot be judged."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)
        for cid, scale in [
            ("stache", {"height": "5 ft 8 in",
                        "relativeTo": {"scout": "several inches shorter than"}}),
            ("scout", {"height": "6 ft 1 in",
                       "relativeTo": {"stache": "several inches taller than"}}),
        ]:
            p = self.root / "canon" / "entities" / f"{cid}.json"
            d = json.loads(p.read_text())
            d["structured"]["scale"] = scale
            p.write_text(json.dumps(d))

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, cast):
        r = run(self.root, write_spec(self.root, cast))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_relation_is_emitted_when_both_are_in_frame(self):
        p = self.out([{"id": "stache"}, {"id": "scout"}])["prompt"]
        self.assertIn("RELATIVE SCALE", p)
        self.assertIn("stache is several inches shorter than scout", p)
        self.assertIn("5 ft 8 in", p)

    def test_solo_spread_is_unchanged(self):
        """A relation to an absent character says nothing about this frame."""
        self.assertNotIn("RELATIVE SCALE", self.out([{"id": "stache"}])["prompt"])

    def test_character_with_no_scale_block_is_fine(self):
        p = self.root / "canon" / "entities" / "scout.json"
        d = json.loads(p.read_text())
        del d["structured"]["scale"]
        p.write_text(json.dumps(d))
        out = self.out([{"id": "stache"}, {"id": "scout"}])
        self.assertIn("stache is several inches shorter than scout", out["prompt"])


class TestNegativesAcceptsAString(unittest.TestCase):
    """A string `negatives` must be ONE negative, never a list of characters.

    `list("NO TEXT")` is `['N','O',' ','T',...]`, so a book that wrote its
    negatives as a string had every one of them delivered to the model as a
    comma-separated spray of single letters. Silent: nothing raised, the render
    just came back without its negatives applied. Two shipped books carried a
    string.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, **extra):
        spec = write_spec(self.root, [{"id": "clean"}], **extra)
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["prompt"]

    def test_string_survives_intact(self):
        p = self.out(negatives="NO STRAY TEXT ANYWHERE")
        self.assertIn("NO STRAY TEXT ANYWHERE", p)

    def test_string_is_not_shredded_into_characters(self):
        """The actual regression: single letters comma-joined."""
        p = self.out(negatives="NO STRAY TEXT")
        self.assertNotIn("N, O,", p)
        self.assertNotIn("S, T, R, A, Y", p)

    def test_list_is_unchanged(self):
        p = self.out(negatives=["no text anywhere", "no logos"])
        self.assertIn("no text anywhere", p)
        self.assertIn("no logos", p)

    def test_empty_string_contributes_nothing(self):
        p = self.out(negatives="   ")
        self.assertIn("NEGATIVES:", p)
        self.assertNotIn(" ,  ,", p)

    def test_rejected_poles_still_emitted(self):
        p = self.out(negatives="NO STRAY TEXT")
        self.assertIn("photoreal", p)
        self.assertIn("anime", p)


class TestSettingContractGeometry(unittest.TestCase):
    """A setting's map/blocking/scale must reach the prompt, not just dressing.

    These three fields exist to fix what the place is, which way round it is, and
    how big it is. They were dropped, so a setting's consistency rested entirely
    on its plate image, which gets diluted by character refs: the same shed drifted
    handedness across a picture book.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _setting(self, contract):
        p = self.root / "canon" / "entities" / "home.json"
        d = json.loads(p.read_text())
        d["contract"] = contract
        p.write_text(json.dumps(d))

    def out(self):
        spec = write_spec(self.root, [{"id": "clean"}])
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["prompt"]

    def test_all_four_fields_are_emitted(self):
        self._setting({"map": "A LONG KITCHEN.", "blocking": "DOORWAY IS ALWAYS CAMERA-LEFT.",
                       "dressing": "warm test kitchen", "scale": "small enough for two."})
        p = self.out()
        for frag in ("A LONG KITCHEN.", "DOORWAY IS ALWAYS CAMERA-LEFT.",
                     "warm test kitchen", "small enough for two."):
            self.assertIn(frag, p)

    def test_handedness_precedes_dressing(self):
        """Blocking is the load-bearing field, so it is read before the clutter."""
        self._setting({"map": "A LONG KITCHEN.", "blocking": "DOORWAY IS ALWAYS CAMERA-LEFT.",
                       "dressing": "warm test kitchen"})
        p = self.out()
        self.assertLess(p.index("DOORWAY IS ALWAYS CAMERA-LEFT."), p.index("warm test kitchen"))

    def test_dressing_only_setting_is_unchanged(self):
        """Back-compat: every existing universe compiles as it did before."""
        self._setting({"dressing": "warm test kitchen"})
        p = self.out()
        self.assertIn("home exactly as its reference plate: warm test kitchen", p)

    def test_empty_contract_emits_no_block(self):
        self._setting({})
        self.assertNotIn("home exactly as its reference plate", self.out())

    def test_blank_fields_are_skipped(self):
        self._setting({"map": "   ", "blocking": None, "dressing": "warm test kitchen"})
        p = self.out()
        self.assertIn("home exactly as its reference plate: warm test kitchen", p)


class TestAbsoluteScale(unittest.TestCase):
    """A recurring PROP must be able to state how big it is.

    The relative-scale block only fires when two or more CHARACTERS declare a
    relation to each other, and scale was only ever read off characters. So a prop
    could not contribute scale at all, and a solo entity's own size was never
    stated. That is how one laptop ended up ranging from a notebook to a small
    television across a single book.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _scale(self, eid, scale):
        p = self.root / "canon" / "entities" / f"{eid}.json"
        d = json.loads(p.read_text())
        d.setdefault("structured", {})["scale"] = scale
        p.write_text(json.dumps(d))

    def out(self, cast):
        r = run(self.root, write_spec(self.root, cast))
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["prompt"]

    def test_prop_absolute_scale_is_emitted(self):
        self._scale("tome", {"absolute": "a paperback, about as tall as a mug"})
        p = self.out([{"id": "clean"}, {"id": "tome"}])
        self.assertIn("TRUE SIZE", p)
        self.assertIn("a paperback, about as tall as a mug", p)

    def test_solo_entity_absolute_scale_is_emitted(self):
        """The old relative block needed TWO characters; absolute needs nobody."""
        self._scale("clean", {"absolute": "about six foot"})
        p = self.out([{"id": "clean"}])
        self.assertIn("TRUE SIZE", p)
        self.assertIn("about six foot", p)

    def test_no_scale_declared_emits_nothing(self):
        self.assertNotIn("TRUE SIZE", self.out([{"id": "clean"}]))

    def test_absolute_and_relative_coexist(self):
        """The two blocks are independent and must not suppress each other."""
        self._scale("tome", {"absolute": "a paperback"})
        self._scale("stache", {"relativeTo": {"scout": "several inches shorter than"}})
        p = self.out([{"id": "stache"}, {"id": "scout"}, {"id": "tome"}])
        self.assertIn("RELATIVE SCALE", p)
        self.assertIn("TRUE SIZE", p)

    def test_offframe_entity_scale_is_not_emitted(self):
        self._scale("tome", {"absolute": "a paperback"})
        self.assertNotIn("a paperback", self.out([{"id": "clean"}]))


class TestCastClosure(unittest.TestCase):
    """The prompt must state that the cast is CLOSED, on every render.

    A book-wide `style` string is prepended to every spread, so a figure it
    mentions is present on every spread whether or not that spread cast them, and
    the uncast-character refusal cannot see it because that guard reads the SCENE.
    Nor is it catchable by name: the styles that caused this described the cast
    generically ("a small hand-made helper"), so no entity name appears to match on.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def out(self, cast, anonymous=None, **extra):
        spec = write_spec(self.root, cast, **extra)
        if anonymous is not None:
            d = json.loads(spec.read_text())
            d["spreads"][0]["anonymous"] = anonymous
            spec.write_text(json.dumps(d))
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)["prompt"]

    def test_named_cast_is_closed(self):
        p = self.out([{"id": "clean"}])
        self.assertIn("THE ONLY CHARACTERS IN THIS IMAGE ARE: clean.", p)
        self.assertIn("NOBODY ELSE APPEARS", p)

    def test_every_cast_member_is_listed(self):
        p = self.out([{"id": "clean"}, {"id": "stache"}])
        self.assertIn("clean, stache", p)

    def test_a_spread_with_no_characters_says_so(self):
        """The empty-room case, which is where invented people actually appear."""
        p = self.out([{"id": "tome"}])
        self.assertIn("THERE ARE NO PEOPLE AND NO CHARACTERS OF ANY KIND", p)
        self.assertNotIn("THE ONLY CHARACTERS IN THIS IMAGE ARE", p)

    def test_props_do_not_count_as_characters(self):
        p = self.out([{"id": "clean"}, {"id": "tome"}])
        self.assertIn("THE ONLY CHARACTERS IN THIS IMAGE ARE: clean.", p)

    def test_closure_survives_a_style_that_describes_the_cast(self):
        """The actual regression: a preamble implying a figure nobody cast."""
        p = self.out([{"id": "tome"}],
                     style="a quiet account of a man at a desk with a small helper.")
        self.assertIn("THERE ARE NO PEOPLE AND NO CHARACTERS OF ANY KIND", p)

    def test_anonymous_figures_widen_an_empty_closure(self):
        """A scene whose people are deliberately not canon must not empty out.

        Earned 2026-07-29 (Atlas Surrendered): three spreads whose subject was an
        unnamed stranger rendered as still lifes of the room, because the closure
        said nobody was there and the model obeyed it.
        """
        p = self.out([{"id": "tome"}], anonymous="one widow in her eighties at her table")
        self.assertIn("ANONYMOUS FIGURES", p)
        self.assertIn("one widow in her eighties at her table", p)
        self.assertNotIn("THERE ARE NO PEOPLE AND NO CHARACTERS OF ANY KIND", p)
        self.assertIn("NOBODY ELSE APPEARS", p)

    def test_anonymous_figures_coexist_with_a_named_cast(self):
        p = self.out([{"id": "clean"}], anonymous="a few visitors seen from behind")
        self.assertIn("THE ONLY NAMED CHARACTERS IN THIS IMAGE ARE: clean.", p)
        self.assertIn("a few visitors seen from behind", p)
        self.assertIn("NOBODY ELSE APPEARS", p)

    def test_no_anonymous_field_leaves_the_closure_exactly_as_before(self):
        p = self.out([{"id": "clean"}])
        self.assertIn("THE ONLY CHARACTERS IN THIS IMAGE ARE: clean.", p)
        self.assertNotIn("ANONYMOUS FIGURES", p)


# MUST be the LAST statement in this file. Any test class defined AFTER it never
# runs: unittest.main() executes and exits at import time. TestAltLookDropSheets and
# TestAltLookRenderBlock sat below it and were dead for weeks while the suite still
# reported ALL GREEN, which is the same silent-omission failure run-tests.sh was
# hardened against one level up. Append new classes ABOVE this block, never below.
class TestArchivedRefusal(unittest.TestCase):
    """An ARCHIVED entity is refused at the point of NEW casting, before any spend.

    Archiving is editorial standing, not reference-completeness: the art stays valid and
    every book that already shipped keeps rendering. So the refusal lives HERE, where a
    new spread picks the retired thing up, and never in the pre-render gate.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        build_universe(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def _archive(self, eid, **extra):
        p = self.root / "canon" / "entities" / f"{eid}.json"
        d = json.loads(p.read_text())
        d["lifecycle"] = "archived"
        d["archived"] = {"on": "2026-07-29", "reason": "overused"}
        d["archived"].update(extra)
        p.write_text(json.dumps(d))

    def test_archived_setting_refuses_and_names_the_replacement(self):
        self._archive("home", supersededBy="the-creek-path")
        spec = write_spec(self.root, [])
        r = run(self.root, spec)
        self.assertNotEqual(r.returncode, 0)
        msg = r.stdout + r.stderr
        self.assertIn("ARCHIVED", msg)
        self.assertIn("the-creek-path", msg)

    def test_allow_archived_waives_it_for_a_deliberate_re_render(self):
        self._archive("home")
        spec = write_spec(self.root, [])
        s = json.loads(spec.read_text())
        s["spreads"][0]["allowArchived"] = True
        spec.write_text(json.dumps(s))
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_an_active_universe_is_unaffected(self):
        spec = write_spec(self.root, [])
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("ARCHIVED", r.stdout)


if __name__ == "__main__":
    unittest.main()


# ── ADDRESSING GUARD ──────────────────────────────────────────────────────
# Earned 2026-08-01 on The Power of Obeying, three times in one book: a
# congregation seated facing the back wall of its own church (spreads 24, 26),
# and a preacher at a pulpit with his audience arrayed BEHIND him (spread 67).
import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("_ap", ASSEMBLE)
_ap = _ilu.module_from_spec(_spec); _spec.loader.exec_module(_ap)
_has_audience, ADDRESSING_GUARD = _ap._has_audience, _ap.ADDRESSING_GUARD


class AddressingGuardTest(unittest.TestCase):
    def test_fires_when_someone_addresses_a_group(self):
        self.assertTrue(_has_audience(
            "The preacher stands behind a pulpit and the congregation sits before him."))
        self.assertTrue(_has_audience(
            "He is teaching about fifty students seated in rows of folding chairs."))

    def test_silent_when_there_is_no_audience(self):
        # A lone figure, and a crowd nobody is addressing, must NOT trip it:
        # a guard that fires on everything is a guard nobody reads.
        self.assertFalse(_has_audience(
            "A man kneels alone on bare floorboards in an empty room at night."))
        self.assertFalse(_has_audience(
            "A great crowd stands ranked up the slope, looking down out of frame."))

    def test_guard_states_both_legal_cameras(self):
        # The defect was never a missing negative, it was a missing geometry, so
        # the guard has to name what IS allowed, not only what is forbidden.
        self.assertIn("BEHIND OR AMONG THE AUDIENCE", ADDRESSING_GUARD)
        self.assertIn("AT THE SPEAKER", ADDRESSING_GUARD)
        self.assertIn("NEVER ARRAYED BEHIND THE SPEAKER", ADDRESSING_GUARD)


# ── BEDCLOTHES GUARD ──────────────────────────────────────────────────────
# Earned 2026-08-01 on The Power of Obeying: three spreads put a man in a
# business suit and necktie in his own bed, because his canon asserted a default
# outfit and the scene never said "pyjamas". Fixed on that entity; guarded here
# because ANY character with a stated default outfit will be put to bed in it.
_in_bed, BEDCLOTHES_GUARD = _ap._in_bed, _ap.BEDCLOTHES_GUARD


class BedclothesGuardTest(unittest.TestCase):
    def test_fires_on_waking_and_sleeping(self):
        self.assertTrue(_in_bed(
            "He has sat bolt upright in bed as though touched on the shoulder."))
        self.assertTrue(_in_bed(
            "The old man lies asleep under the quilt at half past one in the morning."))
        self.assertTrue(_in_bed(
            "He swung both legs off the bedstead and put his feet on the floorboards."))

    def test_silent_when_nobody_is_sleeping(self):
        # Someone who lies down on a bed still dressed, having just walked in,
        # must NOT be forced into pyjamas: that is a real beat, not a defect.
        self.assertFalse(_in_bed(
            "He sets the case down and stands at the foot of the bed, hand on his chest."))
        self.assertFalse(_in_bed(
            "A man kneels alone on bare floorboards in an empty room at night."))

    def test_guard_names_the_dressed_exception(self):
        # A guard that cannot be overridden by the scene would break the beats
        # where the character genuinely is dressed on a bed.
        self.assertIn("NIGHTCLOTHES", BEDCLOTHES_GUARD)
        self.assertIn("business suit", BEDCLOTHES_GUARD)
        self.assertIn("EXCEPTION", BEDCLOTHES_GUARD)


# ── SPEC/CODE DRIFT ───────────────────────────────────────────────────────
class GuardsDocumentedTest(unittest.TestCase):
    """Every guard in the code must be named in SPEC.md §4.6.

    This section drifted once already: MOTION_GUARD shipped 2026-07-28 and the
    SPEC still said "four rules" months later, so a reader of the spec could not
    learn what the compiler actually emits. Writing a paragraph about that hazard
    would not have stopped it; this assertion does.
    """

    def test_every_guard_constant_is_documented(self):
        import re as _re
        spec = (Path(__file__).resolve().parents[3] / "SPEC.md").read_text().lower()
        src = ASSEMBLE.read_text()
        guards = sorted(set(_re.findall(r"^([A-Z_]+_GUARD)\s*=", src, _re.M)))
        self.assertTrue(guards, "no guard constants found: the regex is wrong, not the code")
        undocumented = []
        for g in guards:
            # ANCHOR_STYLE_GUARD -> "anchor-style guard" / "anchor style guard"
            # Require a real ENTRY ("bedclothes guard"), not a bare mention of the
            # word. The first version of this test looked for the word alone and
            # was satisfied by a passing reference in this very section's own
            # summary line, so it passed with a guard deliberately undocumented.
            stem = g[: -len("_GUARD")].replace("_", " ").lower()
            wanted = {f"{stem} guard", f"{stem.replace(' ', '-')} guard"}
            if not any(w in spec for w in wanted):
                undocumented.append(g)
        self.assertEqual(
            [], undocumented,
            f"guards missing from SPEC.md 4.6: {undocumented}. Document them there; "
            "a guard the spec does not name is one a universe author cannot rely on.")


# ── BED-LENGTH AND CROWD-MEMBER GUARDS ────────────────────────────────────
# Both earned 2026-08-01 on The Power of Obeying, both reported by Gary.
_person_lying_on_bed = _ap._person_lying_on_bed
_cast_inside_crowd = _ap._cast_inside_crowd
BED_LENGTH_GUARD = _ap.BED_LENGTH_GUARD
CROWD_MEMBER_GUARD = _ap.CROWD_MEMBER_GUARD


class BedLengthGuardTest(unittest.TestCase):
    def test_fires_when_someone_is_lying_on_a_bed(self):
        self.assertTrue(_person_lying_on_bed(
            "The old man lies back against the pillows, the covers to his chest."))
        self.assertTrue(_person_lying_on_bed(
            "A gaunt boy propped against two flat pillows on a dark iron bedstead."))

    def test_silent_with_no_bed_or_nobody_on_it(self):
        self.assertFalse(_person_lying_on_bed(
            "He kneels alone on bare floorboards in an empty room."))
        self.assertFalse(_person_lying_on_bed(
            "An empty bedroom, the quilt smooth and the pillow undented."))

    def test_guard_forbids_the_specific_defect(self):
        # The footboard at the hips is the thing that actually went wrong.
        self.assertIn("NEVER AT THE HIPS", BED_LENGTH_GUARD)
        self.assertIn("run out of frame rather than shortening it", BED_LENGTH_GUARD)


class CrowdMemberGuardTest(unittest.TestCase):
    def test_fires_when_a_character_sits_inside_an_audience(self):
        self.assertTrue(_cast_inside_crowd(
            "Among the seated attendees the white-haired man sits in an aisle seat."))
        self.assertTrue(_cast_inside_crowd(
            "He is in the congregation, three rows back."))

    def test_silent_when_the_character_is_addressing_the_crowd(self):
        # The bare phrase "sits in" describes the CROWD, not a member of it, and
        # firing here confused a speaker scene the guard has nothing to say about.
        self.assertFalse(_cast_inside_crowd(
            "The congregation sits in two distinct blocks either side of the aisle."))
        self.assertFalse(_cast_inside_crowd(
            "The preacher stands at the pulpit facing the congregation."))

    def test_guard_moves_the_camera_not_the_person(self):
        self.assertIn("MOVE THE CAMERA, NOT THE PERSON", CROWD_MEMBER_GUARD)
        self.assertIn("FACE THE SAME WAY EVERYONE ELSE FACES", CROWD_MEMBER_GUARD)
