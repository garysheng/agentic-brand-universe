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
              "stache/full", "stache/face", "stache/alt-photo", "home/kitchen"]:
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
    (root / "canon" / "entities" / "home.json").write_text(json.dumps({
        "id": "home", "kind": "setting", "status": "locked",
        "contract": {"dressing": "warm test kitchen"},
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


if __name__ == "__main__":
    unittest.main()


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
