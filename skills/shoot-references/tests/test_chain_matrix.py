"""chain_matrix.py — tests. Stdlib unittest, synthetic universe in a tempdir.

The load-bearing behaviours, in order of how badly each one bit us for real:
  1. the chain is SEQUENTIAL and each shot conditions on the seed + every shot
     accepted before it (this is the whole point; parallel produced N different
     rooms that merely shared a description)
  2. GOLDEN IS A HUMAN GATE: refuse to chain off an unblessed seed
  3. the seed is chosen KIND-AWARELY (most-geometry-first), one meta-process
     for characters, settings, props, motifs and visual-metaphors alike

Run:  python3 -m unittest discover -s tests -v   (from the shoot-references skill dir)
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
CHAIN = SCRIPTS / "chain_matrix.py"


def png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (180, 160, 120)).save(path)


def build(root: Path, kind="setting", shots=("c1-wide", "c2-work", "c3-light-wall"),
          anchor_subject=None):
    (root / "canon" / "entities").mkdir(parents=True)
    png(root / "reference" / "register" / "anchor.png")
    register = {"name": "test register",
                "anchor": "reference/register/anchor.png",
                "rejectedPoles": ["photoreal", "anime"]}
    if anchor_subject:
        register["anchorSubject"] = anchor_subject
    (root / "universe.json").write_text(json.dumps({
        "name": "testverse", "assetRoot": ".",
        "identity": {"register": register},
    }))
    (root / "canon" / "entities" / "room.json").write_text(json.dumps({
        "id": "room", "kind": kind, "structured": {"sheets": {}, "invariants": []},
    }))
    md = "# room prompts\n\n"
    for s in shots:
        md += f"## {s} → `reference/room/{s}.png`\nRender the {s} view of the room.\n\n"
    (root / "reference" / "room").mkdir(parents=True, exist_ok=True)
    (root / "reference" / "room" / "prompts.md").write_text(md)
    return root


def run(root: Path, *extra):
    return subprocess.run([sys.executable, str(CHAIN), str(root), "room", *extra],
                          capture_output=True, text=True)


class TestChain(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    # --- the point of the whole script -------------------------------------
    def test_plan_conditions_each_shot_on_all_prior_goldens(self):
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = r.stdout
        self.assertIn("1. c1-wide", out)
        self.assertIn("HUMAN-BLESSED SEED", out)
        # shot 3 must be conditioned on BOTH prior shots, not just the seed
        line = [l for l in out.splitlines() if "3. c3-light-wall" in l][0]
        self.assertIn("c1-wide", line)
        self.assertIn("c2-work", line)

    def test_seed_is_kind_aware_most_geometry_first(self):
        # setting -> the establishing wide seeds, even though it is listed first
        # only by luck; prove it by reordering the shots.
        root = build(Path(tempfile.mkdtemp()), kind="setting",
                     shots=("c2-work", "c3-light-wall", "c1-wide"))
        r = subprocess.run([sys.executable, str(CHAIN), str(root), "room", "--print-plan"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("seed (hero) = c1-wide", r.stdout)

    def test_character_kind_seeds_on_turnaround(self):
        root = build(Path(tempfile.mkdtemp()), kind="character",
                     shots=("face-neutral", "turnaround", "profile-left"))
        r = subprocess.run([sys.executable, str(CHAIN), str(root), "room", "--print-plan"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("seed (hero) = turnaround", r.stdout)

    # --- golden is a human gate --------------------------------------------
    def test_refuses_to_chain_off_an_unblessed_seed(self):
        png(self.root / "reference" / "room" / "c1-wide.png")
        r = run(self.root)
        self.assertEqual(r.returncode, 2)
        self.assertIn("not blessed", r.stderr)

    def test_bless_seed_records_a_marker_with_the_hash(self):
        png(self.root / "reference" / "room" / "c1-wide.png")
        r = run(self.root, "--bless-seed", "c1-wide")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads((self.root / "reference" / "room" / "c1-wide.golden.json").read_text())
        self.assertEqual(m["shot"], "c1-wide")
        self.assertEqual(m["blessedBy"], "human")
        self.assertTrue(m["sha256_16"])

    def test_cannot_bless_a_shot_that_does_not_exist(self):
        r = run(self.root, "--bless-seed", "c1-wide")
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not exist", r.stderr)

    # --- refusals -----------------------------------------------------------
    def test_refuses_null_anchor(self):
        uni = json.loads((self.root / "universe.json").read_text())
        uni["identity"]["register"]["anchor"] = None
        (self.root / "universe.json").write_text(json.dumps(uni))
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("anchor", r.stderr)

    def test_refuses_shot_with_no_prompt_block(self):
        r = run(self.root, "--shots", "c1-wide,nonexistent", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no prompt block", r.stderr)

    def test_refuses_bad_seed_override(self):
        r = run(self.root, "--seed", "not-a-shot", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not one of", r.stderr)




class TestNegativesAndCrossRefs(unittest.TestCase):
    """Two silent-drop bugs: the entity's own negatives and its cross-entity REFS
    were parsed by nobody and never reached the model, so prompts.md implied
    guarantees it did not provide."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def _write_prompts(self, body: str):
        (self.root / "reference" / "room" / "prompts.md").write_text(body)

    def _locked_other(self, eid="the-door", shot="master"):
        png(self.root / "reference" / eid / f"{shot}.png")
        (self.root / "canon" / "entities" / f"{eid}.json").write_text(json.dumps({
            "id": eid, "kind": "visual-metaphor",
            "structured": {"sheets": {shot: f"reference/{eid}/{shot}.png"},
                           "requiredForRender": [shot]},
        }))

    def test_entity_negatives_are_merged_with_universe_rejected_poles(self):
        self._write_prompts(
            "# room\n\n**Negatives (every shot):** no clocks, no signage\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("photoreal", r.stdout)      # universe rejectedPoles survive
        self.assertIn("no clocks", r.stdout)      # entity negatives now reach the plan
        self.assertIn("no signage", r.stdout)

    def test_negatives_line_is_not_parsed_as_a_shot(self):
        self._write_prompts(
            "# room\n\n**Negatives (every shot):** no clocks\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("1. c1-wide", r.stdout)
        self.assertNotIn("Negatives", r.stdout.split("negatives:")[0])

    def test_per_shot_refs_are_planned_and_stripped_from_the_prompt(self):
        self._locked_other()
        self._write_prompts(
            "# room\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\nREFS: the-door\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("refs: the-door(master)", r.stdout)
        # the REFS line must not leak into the prompt text
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        parsed = cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        self.assertNotIn("REFS", parsed["prompts"]["c2-work"])
        self.assertEqual(parsed["refs"]["c2-work"], ["the-door"])

    def test_two_headings_writing_one_file_refuse(self):
        """A shot is keyed by the file it writes, so a duplicate `->` target used to
        make the LATER heading silently replace the earlier one's prompt. That cost two
        paid renders on 2026-08-04 and looked like a style-anchor leak, because the
        clobbered shot went to the model as a two-sentence alias stub."""
        self._locked_other()
        self._write_prompts(
            "# room\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nThe real prompt for this plate.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\n\n"
            "## alias-of-c1 -> `reference/room/c1-wide.png`\nALIAS. Do not shoot.\n")
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        with self.assertRaises(cm.Refuse) as ctx:
            cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        msg = str(ctx.exception)
        self.assertIn("c1-wide.png", msg)
        self.assertIn("alias-of-c1", msg)
        self.assertIn("structured.sheets", msg)

    def test_one_heading_per_output_still_parses(self):
        """The refusal must not fire on a normal matrix."""
        self._locked_other()
        self._write_prompts(
            "# room\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\n")
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        parsed = cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        self.assertEqual(parsed["prompts"]["c1-wide"], "Wide view.")
        self.assertEqual(parsed["prompts"]["c2-work"], "Work view.")

    def test_alt_look_nested_paths_parse_and_strip_their_size(self):
        """An ALT-LOOK's plates live one directory deeper, at
        `reference/<id>/<look>/<shot>.png`. The heading pattern used to allow exactly
        ONE path segment, so every alt-look heading failed to match, fell through to the
        `->` split, and produced a shot name with its "(WxH)" size still glued on. The
        chain then refused against the entity's declared sheets and blamed the author's
        headings for a file that was correct. Earned 2026-08-06 on nation-of-fire's
        josh-howerton, whose three age eras all refused."""
        self._locked_other()
        self._write_prompts(
            "# room @ era\n\n"
            # heading TEXT deliberately differs from the FILENAME, because a shot is
            # keyed by the file it writes. Only the path branch can get this right;
            # the `->` fallback would key these as "era wide" and "era work".
            "## era wide (1024x1536)  -> reference/room/era/c1-wide.png\nWide view.\n\n"
            "## era work (1536x1024)  -> reference/room/era/c2-work.png\nWork view.\n")
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        parsed = cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        # keyed by the BARE shot name, with no size suffix
        self.assertEqual(sorted(parsed["prompts"]), ["c1-wide", "c2-work"])
        self.assertEqual(parsed["prompts"]["c1-wide"], "Wide view.")
        # and the size is still read into its own channel
        self.assertEqual(parsed["sizes"]["c1-wide"], "1024x1536")
        self.assertEqual(parsed["sizes"]["c2-work"], "1536x1024")

    def test_header_refs_apply_to_every_shot(self):
        self._locked_other()
        self._write_prompts(
            "# room\n\n**Refs (every shot):** the-door\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide view.\n\n"
            "## c2-work -> `reference/room/c2-work.png`\nWork view.\n")
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        parsed = cm.parse_prompts_full(self.root / "reference" / "room" / "prompts.md")
        self.assertEqual(parsed["refs"]["c1-wide"], ["the-door"])
        self.assertEqual(parsed["refs"]["c2-work"], ["the-door"])

    def test_refs_to_an_unlocked_entity_refuse_rather_than_pass_prose(self):
        (self.root / "canon" / "entities" / "ghost.json").write_text(json.dumps({
            "id": "ghost", "kind": "visual-metaphor",
            "structured": {"sheets": {"master": None}, "requiredForRender": []},
        }))
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        with self.assertRaises(cm.Refuse):
            cm.entity_ref_images(self.root, "ghost")
        with self.assertRaises(cm.Refuse):
            cm.entity_ref_images(self.root, "not-an-entity")

    def test_refs_resolve_to_locked_art_on_disk(self):
        self._locked_other()
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        cm = util.module_from_spec(spec); spec.loader.exec_module(cm)
        paths = cm.entity_ref_images(self.root, "the-door")
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0]["sheet"], "master")
        self.assertTrue(Path(paths[0]["path"]).exists())


class TestRefSheetSelector(unittest.TestCase):
    """`REFS: <id>@<sheet>+<sheet>` (SPEC v0.25).

    THE GAP: only `requiredForRender` ever resolved, so an entity's EXTRA sheets
    were unreachable from a shoot. On christofuturism's `north-star-cross` the
    canonical multi-angle `turnaround` and the `worn-pendant` plate were both
    registered, both carried provenance, and were both named by that entity's own
    `render.always` -- and no shot could ask for them. Three flat front plates
    were all the resolver could pass, and the pendant rendered at 1.79:1
    height-to-width against a fabrication spec of 1.24:1.

    THE RULE: a selector may RAISE the ref set and must never LOWER it, which is
    the v0.24 lock rule one layer out.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))
        for s in ("hero", "turnaround", "worn"):
            png(self.root / "reference" / "mark" / f"{s}.png")
        (self.root / "canon" / "entities" / "mark.json").write_text(json.dumps({
            "id": "mark", "kind": "motif",
            "structured": {
                "sheets": {"hero": "reference/mark/hero.png",
                           "turnaround": "reference/mark/turnaround.png",
                           # a TYPED slot (SPEC v0.23) must resolve here too; the
                           # resolver used to concatenate the dict onto a Path
                           "worn": {"path": "reference/mark/worn.png",
                                    "role": "geometry"}},
                "requiredForRender": ["hero"]},
        }))
        self.cm = self._mod()

    def tearDown(self):
        self.tmp.cleanup()

    def _mod(self):
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        m = util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def test_a_bare_id_is_unchanged(self):
        got = self.cm.entity_ref_images(self.root, "mark")
        self.assertEqual([r["sheet"] for r in got], ["hero"])

    def test_selected_sheets_come_first_and_required_still_follows(self):
        got = self.cm.entity_ref_images(self.root, "mark@turnaround+worn")
        # ADDITIVE, and in the author's order: `hero` is the entity's gate and
        # cannot be dropped by naming other plates.
        self.assertEqual([r["sheet"] for r in got], ["turnaround", "worn", "hero"])

    def test_a_selector_cannot_drop_a_required_sheet(self):
        got = self.cm.entity_ref_images(self.root, "mark@turnaround")
        self.assertIn("hero", [r["sheet"] for r in got])

    def test_a_typed_slot_resolves(self):
        got = self.cm.entity_ref_images(self.root, "mark@worn")
        self.assertTrue(Path(got[0]["path"]).exists())

    def test_an_unknown_sheet_name_refuses_rather_than_being_ignored(self):
        with self.assertRaises(self.cm.Refuse) as e:
            self.cm.entity_ref_images(self.root, "mark@turnround")
        self.assertIn("declares no sheet", str(e.exception))

    def test_a_declared_but_unshot_sheet_refuses(self):
        ent = self.root / "canon" / "entities" / "mark.json"
        d = json.loads(ent.read_text())
        d["structured"]["sheets"]["ghost"] = None
        ent.write_text(json.dumps(d))
        with self.assertRaises(self.cm.Refuse):
            self.cm.entity_ref_images(self.root, "mark@ghost")

    def test_a_required_sheet_not_yet_shot_is_dropped_not_refused(self):
        # The blueprint-seeded chain make-a-book prescribes for a multi-state object:
        # the blueprint is on disk, every state plate is what the shoot is about to
        # create, and requiredForRender legitimately names one of those states. Before
        # this, the seed shot refused, and the only way past it was to temporarily
        # rewrite requiredForRender, which is lying about the entity's render gate.
        ent = self.root / "canon" / "entities" / "mark.json"
        d = json.loads(ent.read_text())
        d["structured"]["sheets"]["blueprint"] = "reference/mark/blueprint.png"
        d["structured"]["requiredForRender"] = ["master"]
        d["structured"]["sheets"]["master"] = "reference/mark/master.png"  # declared, unshot
        ent.write_text(json.dumps(d))
        png(self.root / "reference" / "mark" / "blueprint.png")
        got = self.cm.entity_ref_images(self.root, "mark@blueprint")
        self.assertEqual([r["sheet"] for r in got], ["blueprint"])

    def test_an_explicitly_selected_sheet_not_on_disk_still_refuses(self):
        # The asymmetry is the point: dropping a REQUIRED plate the shoot has not made
        # yet is normal; silently dropping one the author NAMED would send the shoot off
        # with exactly the reference they were trying to add.
        ent = self.root / "canon" / "entities" / "mark.json"
        d = json.loads(ent.read_text())
        d["structured"]["sheets"]["ghost"] = "reference/mark/ghost.png"
        ent.write_text(json.dumps(d))
        with self.assertRaises(self.cm.Refuse) as e:
            self.cm.entity_ref_images(self.root, "mark@ghost")
        self.assertIn("NOT ON DISK", str(e.exception))

    def test_refuses_when_dropping_would_leave_no_refs_at_all(self):
        ent = self.root / "canon" / "entities" / "mark.json"
        d = json.loads(ent.read_text())
        d["structured"]["sheets"] = {"master": "reference/mark/master.png"}
        d["structured"]["requiredForRender"] = ["master"]
        ent.write_text(json.dumps(d))
        with self.assertRaises(self.cm.Refuse) as e:
            self.cm.entity_ref_images(self.root, "mark")
        self.assertIn("on disk yet", str(e.exception))

    def test_header_and_per_shot_tokens_merge_by_entity_not_by_string(self):
        (self.root / "reference" / "room" / "prompts.md").write_text(
            "# room\n\n**Refs (every shot):** mark\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide.\n"
            "REFS: mark@turnaround\n")
        parsed = self.cm.parse_prompts_full(
            self.root / "reference" / "room" / "prompts.md")
        # One token, not two: resolving both would pass `hero` twice.
        self.assertEqual(parsed["refs"]["c1-wide"], ["mark@turnaround"])

    def test_the_plan_resolves_refs_on_the_seed_too(self):
        # Gated on `i > 0` before, so shot 1's refs were invisible in --print-plan
        # -- the seed being both the most expensive thing to get wrong and the
        # shot every later one inherits from.
        (self.root / "reference" / "room" / "prompts.md").write_text(
            "# room\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide.\nREFS: mark@turnaround\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("mark(turnaround, hero)", r.stdout)

    def test_a_mistyped_selector_refuses_during_print_plan_not_mid_render(self):
        (self.root / "reference" / "room" / "prompts.md").write_text(
            "# room\n\n"
            "## c1-wide -> `reference/room/c1-wide.png`\nWide.\nREFS: mark@nope\n")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("REFUSE", r.stderr)
        self.assertNotIn("Traceback", r.stderr)


class TestRealPersonPhotoStack(unittest.TestCase):
    """A real person's PHOTOGRAPHS are the ground truth for the likeness.

    Without this, every downstream shot is conditioned only on paintings of the
    person, so the chain drifts off the real face while each plate still looks
    internally consistent. That is the worst failure shape: nothing looks wrong
    until someone who knows the person sees it.
    """

    def _with_photos(self, stack):
        root = build(Path(self.tmp.name), kind="character",
                     shots=("face-neutral", "face-3q"))
        ent = root / "canon" / "entities" / "room.json"
        d = json.loads(ent.read_text())
        d["realPerson"] = {"photoStack": stack,
                           "approval": {"state": "gated", "by": "someone", "on": None}}
        ent.write_text(json.dumps(d))
        return root

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_photo_stack_refuses_when_a_declared_photo_is_missing(self):
        root = self._with_photos(["reference/room/photos/01.png"])
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("does not resolve on disk", r.stderr)

    def test_photo_stack_EXPANDS_a_directory(self):
        """v0.21. This used to REFUSE, and the refusal was the bug.

        SPEC §12 has called `["reference/<id>/photos"]` the idiomatic whole-stack form
        since v0.17, and compose-spread expanded it at render time, so the recommended
        form could be rendered from and not shot from. Earned on christofuturism `gary`.
        """
        root = self._with_photos(["reference/room/photos"])
        d = root / "reference" / "room" / "photos"
        d.mkdir(parents=True, exist_ok=True)
        png(d / "b.png")
        png(d / "a.png")
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("a.png", r.stdout)
        self.assertIn("b.png", r.stdout)

    def test_photo_stack_refuses_a_directory_with_no_images(self):
        """An empty folder must not silently resolve to zero photographs: that is a
        downgrade to inventing the face from prose, wearing the costume of success."""
        root = self._with_photos(["reference/room/photos"])
        (root / "reference" / "room" / "photos").mkdir(parents=True, exist_ok=True)
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no images", r.stderr)

    def test_photo_limit_caps_the_expanded_stack(self):
        root = self._with_photos(["reference/room/photos"])
        ent = root / "canon" / "entities" / "room.json"
        d = json.loads(ent.read_text())
        d["realPerson"]["photoLimit"] = 1
        ent.write_text(json.dumps(d))
        pd = root / "reference" / "room" / "photos"
        pd.mkdir(parents=True, exist_ok=True)
        png(pd / "a.png")
        png(pd / "b.png")
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("a.png", r.stdout)
        self.assertNotIn("b.png", r.stdout)

    def test_photo_stack_resolves_and_the_plan_builds(self):
        root = self._with_photos(["reference/room/photos/01.png"])
        png(root / "reference" / "room" / "photos" / "01.png")
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_an_entity_with_no_real_person_block_still_plans(self):
        root = build(Path(self.tmp.name), kind="character",
                     shots=("face-neutral", "face-3q"))
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)


class PerShotSize(unittest.TestCase):
    """A reference matrix legitimately MIXES aspects: full-bodies and profiles want
    portrait, multi-panel sheets (expressions, era rows) want landscape. The sizes
    were always declared in the prompts.md headings; the chain used to ignore them
    and apply one --size to everything, letterboxing every sheet into dead bands.
    Earned live 2026-07-26 on shelby-mullen's expressions sheet."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _mixed(self):
        root = Path(self.tmp.name)
        build(root, kind="character", shots=())
        md = ("# room prompts\n\n"
              "## face-neutral → `reference/room/face-neutral.png` (1024x1024)\nA face macro.\n\n"
              "## forward-fullbody → `reference/room/forward-fullbody.png` (1024x1536)\nFull figure.\n\n"
              "## expressions → `reference/room/expressions.png` (1536x1024)\nFour panels.\n\n"
              "## back → `reference/room/back.png`\nNo size declared here.\n\n")
        (root / "reference" / "room" / "prompts.md").write_text(md)
        return root

    def test_each_shot_reports_the_size_its_heading_declares(self):
        r = run(self._mixed(), "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("[1024x1024]", r.stdout)   # face macro, square
        self.assertIn("[1024x1536]", r.stdout)   # full figure, portrait
        self.assertIn("[1536x1024]", r.stdout)   # multi-panel sheet, landscape

    def test_a_shot_with_no_declared_size_falls_back_to_the_size_flag(self):
        r = run(self._mixed(), "--print-plan", "--size", "777x333")
        self.assertEqual(r.returncode, 0, r.stderr)
        back = [l for l in r.stdout.splitlines() if "back" in l][0]
        self.assertIn("[777x333]", back)

    def test_a_declared_size_beats_the_size_flag(self):
        r = run(self._mixed(), "--print-plan", "--size", "777x333")
        expressions = [l for l in r.stdout.splitlines() if "expressions" in l][0]
        self.assertIn("[1536x1024]", expressions)
        self.assertNotIn("777x333", expressions)


class ConditioningWindow(unittest.TestCase):
    """Identity is carried by the blessed seed plus the most recent accepted shots,
    not by every golden ever made. Unbounded accumulation grew the request at every
    step until the TAIL of a big matrix died on openai.APITimeoutError, which is the
    worst place to fail because those shots are the most expensive to redo.
    Earned live 2026-07-26 on shelby-mullen's 9-shot matrix (era-sheet, shot 9)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def _nine(self):
        shots = ("forward-fullbody", "face-neutral", "face-3q", "expressions",
                 "profile-left", "profile-right", "back", "signature-pose", "era-sheet")
        return build(Path(self.tmp.name), kind="character", shots=shots)

    def test_the_plan_shows_a_truncated_window_on_a_long_matrix(self):
        r = run(self._nine(), "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        last = [l for l in r.stdout.splitlines() if "era-sheet" in l][0]
        self.assertIn("...", last)

    def test_the_window_always_keeps_the_blessed_seed(self):
        r = run(self._nine(), "--print-plan")
        last = [l for l in r.stdout.splitlines() if "era-sheet" in l][0]
        self.assertIn("forward-fullbody", last)

    def test_max_conditioning_zero_restores_the_unbounded_behaviour(self):
        r = run(self._nine(), "--print-plan", "--max-conditioning", "0")
        self.assertEqual(r.returncode, 0, r.stderr)
        last = [l for l in r.stdout.splitlines() if "era-sheet" in l][0]
        self.assertNotIn("...", last)
        for s in ("face-neutral", "profile-left", "back", "signature-pose"):
            self.assertIn(s, last)

    def test_a_short_matrix_is_never_truncated(self):
        root = build(Path(self.tmp.name), kind="character",
                     shots=("forward-fullbody", "face-neutral", "face-3q"))
        r = run(root, "--print-plan")
        self.assertNotIn("...", r.stdout)


# --- multi-register universes ----------------------------------------------
# A universe where `identity.register` names only the DEFAULT and each look is
# its own Style Pack. Without an override, every entity's matrix is shot in the
# default medium, including entities that are only ever rendered in another one,
# and a sheet in the wrong medium is a weak identity reference.
class TestRegisterOverride(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))
        pack = self.root / "reference" / "style" / "inky"
        png(pack / "refs" / "anchor.png")
        (pack / "pack.json").write_text(json.dumps({
            "id": "inky", "name": "Inky",
            "anchor": "refs/anchor.png",
            "rejectedPoles": ["crayon", "pastel"],
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def test_defaults_to_the_universe_register(self):
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("register=test register", r.stdout)
        self.assertIn("photoreal", r.stdout)

    def test_override_uses_the_named_packs_poles_not_the_universes(self):
        r = run(self.root, "--register", "inky", "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("register=Inky", r.stdout)  # the pack's NAME, never its slug
        neg = [l for l in r.stdout.splitlines() if l.startswith("negatives:")][0]
        self.assertIn("crayon", neg)
        # The default register's poles must not leak into an overridden shoot:
        # "photoreal" is the universe's, and a pack that permits it would be
        # silently fighting a negative it never declared.
        self.assertNotIn("photoreal", neg)

    def test_the_register_reaches_every_shot_body_not_just_the_header(self):
        # The scaffolded prompts.md writes the register into the file HEADER,
        # which the parser never sent. Four character seeds in a row came back
        # photoreal in a universe that explicitly rejects it, off a painted
        # anchor (2026-07-30, The Lord Saw). The medium must be named
        # POSITIVELY in the body of every shot.
        sys.path.insert(0, str(SCRIPTS))
        import chain_matrix
        line = chain_matrix.style_line("test register", ["photoreal", "anime"])
        self.assertIn("test register", line)
        self.assertIn("never anime", line)
        self.assertIn("photoreal", line)

    def test_style_line_is_empty_when_a_register_has_no_name(self):
        sys.path.insert(0, str(SCRIPTS))
        import chain_matrix
        self.assertEqual(chain_matrix.style_line(None, ["photoreal"]), "")

    def test_the_plan_carries_the_registers_own_poles_separate_from_negatives(self):
        # The style line names the MEDIUM's opposites; it must not inherit every
        # prop the entity happens to forbid, or it grows unbounded per entity.
        sys.path.insert(0, str(SCRIPTS))
        import chain_matrix
        plan = chain_matrix.build_plan(self.root, "room")
        self.assertIn("photoreal", plan["poles"])
        for p in plan["poles"]:
            self.assertIn(p, plan["negatives"])

    def test_refuses_an_unknown_register_rather_than_falling_back(self):
        r = run(self.root, "--register", "ghost", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("no Style Pack", r.stderr)

    def test_refuses_a_pack_whose_anchor_is_not_on_disk(self):
        pack = self.root / "reference" / "style" / "hollow"
        pack.mkdir(parents=True)
        (pack / "pack.json").write_text(json.dumps({
            "id": "hollow", "anchor": "refs/missing.png"}))
        r = run(self.root, "--register", "hollow", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not on disk", r.stderr)


class TestDeclaredStylePack(unittest.TestCase):
    """A universe that DECLARES identity.register.stylePack must not be shot against
    identity.register.anchor by accident.

    THE DEFECT, 2026-08-04, nation-of-fire. That universe declares both:

        identity.register.stylePack = reference/style/nof-soft-painterly
        identity.register.anchor    = reference/the-readiness-lamp/hero.png

    and its own stylePackNote says the pack exists BECAUSE the lamp anchor has a
    SUBJECT that is returned wholesale on a sparse render, naming two failures that
    same day where it was. This resolver went to the lamp anyway, the seed for
    `the-sealed-spring` came back fully PHOTOREAL — the register's own top rejected
    pole — and it was only recovered by finding the pack by hand and passing
    `--register nof-soft-painterly`, which was right on the first re-shot. One wasted
    paid image, and a whole seven-shot matrix if the seed had been blessed.

    SPEC 4.7 has described the field since v0.12 and no compiler read it, which made
    it possible to declare a pack, score for it in universe-doctor, and never shoot
    against it.
    """

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))
        pack = self.root / "reference" / "style" / "inky"
        png(pack / "refs" / "anchor.png")
        (pack / "pack.json").write_text(json.dumps({
            "id": "inky", "name": "Inky", "anchor": "refs/anchor.png",
            "rejectedPoles": ["crayon", "pastel"]}))

    def tearDown(self):
        self.tmp.cleanup()

    def _register(self, **changes):
        uni = json.loads((self.root / "universe.json").read_text())
        reg = uni["identity"]["register"]
        for k, v in changes.items():
            if v is None:
                reg.pop(k, None)
            else:
                reg[k] = v
        (self.root / "universe.json").write_text(json.dumps(uni))

    def test_declaring_both_refuses_at_plan_time_and_names_both_ways_out(self):
        self._register(stylePack="inky")
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("reference/register/anchor.png", r.stderr)
        self.assertIn("inky", r.stderr)
        self.assertIn("--register inky", r.stderr)
        self.assertIn("--no-style-pack", r.stderr)

    def test_the_refusal_costs_nothing(self):
        """It fires from build_plan, before any generation, so the ambiguity is
        resolved for free rather than for the price of a seed."""
        self._register(stylePack="inky")
        sys.path.insert(0, str(SCRIPTS))
        import chain_matrix
        with self.assertRaises(chain_matrix.Refuse):
            chain_matrix.build_plan(self.root, "room")

    def test_register_override_still_wins_over_a_declared_pack(self):
        self._register(stylePack="inky")
        r = run(self.root, "--register", "inky", "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("register=Inky", r.stdout)  # the pack's NAME, never its slug

    def test_no_style_pack_shoots_the_identity_anchor_deliberately(self):
        self._register(stylePack="inky")
        r = run(self.root, "--no-style-pack", "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("register=test register", r.stdout)
        neg = [l for l in r.stdout.splitlines() if l.startswith("negatives:")][0]
        self.assertIn("photoreal", neg)

    def test_a_pack_only_register_resolves_from_the_pack(self):
        """SPEC 4.7 full mode, which no compiler implemented. This branch cannot
        change any existing render: a register with no inline anchor previously hit
        the 'anchor is null' refusal and could not shoot at all."""
        self._register(stylePack="inky", anchor=None)
        sys.path.insert(0, str(SCRIPTS))
        import chain_matrix
        plan = chain_matrix.build_plan(self.root, "room")
        self.assertEqual(plan["anchor"], "reference/style/inky/refs/anchor.png")
        self.assertEqual(plan["register"], "Inky")  # name over slug: a slug names no medium
        self.assertIn("crayon", plan["poles"])
        self.assertNotIn("photoreal", plan["poles"])

    def test_style_pack_may_be_a_path_because_real_universes_write_one(self):
        """SPEC 4.7 spells the field "<id-or-path>"; nation-of-fire uses the path."""
        self._register(stylePack="reference/style/inky", anchor=None)
        sys.path.insert(0, str(SCRIPTS))
        import chain_matrix
        plan = chain_matrix.build_plan(self.root, "room")
        self.assertEqual(plan["anchor"], "reference/style/inky/refs/anchor.png")
        self.assertEqual(plan["register"], "Inky")  # name over slug: a slug names no medium

    def test_a_universe_with_no_style_pack_is_completely_unchanged(self):
        """The whole point of shipping this as a refusal: every universe that has not
        declared a pack shoots exactly what it shot yesterday."""
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("register=test register", r.stdout)

    def test_null_anchor_with_no_pack_still_refuses_as_before(self):
        self._register(anchor=None)
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("not locked", r.stderr)


class TestMultiLineHeaders(unittest.TestCase):
    """A header that spans lines must contribute ALL of it.

    Both the Negatives and Refs headers were read with a single-line regex, so a
    four-line negatives block sent only its first line and the rest vanished in
    silence. On gary's first seed that meant 5 of 18 negatives reached the model and
    `a crucifix` was among the thirteen dropped, so the pendant rendered as exactly
    the crucifix his invariant forbids. A render was spent proving a parser bug.
    """

    def _mod(self):
        import importlib.util
        here = Path(__file__).resolve().parent.parent / "scripts" / "chain_matrix.py"
        spec = importlib.util.spec_from_file_location("cm_hdr", here)
        m = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(m)
        return m

    MD = """# prompts

**Negatives (every shot):** a crucifix, a Latin cross,
an equal-armed star, stubble,
- a beard
- glasses

**Refs (every shot):** north-star-cross,
selah

## face-neutral -> reference/gary/face-neutral.png
Body text.
"""

    def test_every_negative_survives_the_line_breaks(self):
        got = self._mod()._header_block(self.MD, "Negatives")
        self.assertEqual(got, ["a crucifix", "a Latin cross", "an equal-armed star",
                               "stubble", "a beard", "glasses"])
        self.assertIn("a crucifix", got)

    def test_refs_span_lines_too(self):
        self.assertEqual(self._mod()._header_block(self.MD, "Refs"),
                         ["north-star-cross", "selah"])

    def test_trailing_prose_is_not_absorbed_as_negatives(self):
        """The SECOND bug: making multi-line safe made trailing prose unsafe.

        Ending the block only at the next header or EOF meant a blank line did not end
        it, so ordinary prose written under the list parsed as negatives. One run sent 15
        junk items to the model including raw markdown. A fix for a silent-drop must not
        become a silent-absorb.
        """
        md = (
            "**Negatives (every shot):** a crucifix, a Latin cross,\n"
            "- stubble\n"
            "- a thick rope chain\n"
            "\n"
            "> NOTE: a blockquote explaining the file must never become a negative.\n"
            "\n"
            "Trailing prose that explains the file and **must never** be a negative.\n"
            "\n"
            "## face-neutral\nbody\n"
        )
        got = self._mod()._header_block(md, "Negatives")
        self.assertEqual(got, ["a crucifix", "a Latin cross", "stubble",
                               "a thick rope chain"])

    def test_a_blank_line_between_list_items_does_not_end_the_block(self):
        """A gap inside the list is formatting, not a terminator."""
        md = "**Negatives (every shot):** a\n- b\n\n- c\n\nprose here.\n\n## x\nbody\n"
        self.assertEqual(self._mod()._header_block(md, "Negatives"), ["a", "b", "c"])

    def test_markdown_fragments_are_dropped_not_sent(self):
        """A negative the author never wrote is as wrong as one they never got."""
        md = ("**Negatives (every shot):** a crucifix\n"
              "- this one carries `backticks` and **bold** and is really a sentence\n"
              "\n## x\nbody\n")
        self.assertEqual(self._mod()._header_block(md, "Negatives"), ["a crucifix"])

    def test_single_line_still_works(self):
        md = "**Negatives (every shot):** a, b, c\n\n## x\nbody\n"
        self.assertEqual(self._mod()._header_block(md, "Negatives"), ["a", "b", "c"])

    def test_absent_header_is_empty_not_an_error(self):
        self.assertEqual(self._mod()._header_block("## x\nbody\n", "Negatives"), [])


SUBJECT = "an ancient oil lamp, a clay jar, robed figures"


class TestAnchorSubjectNegation(unittest.TestCase):
    """`identity.register.anchorSubject` (declared once per universe) names what the
    register anchor DEPICTS so it can be banned concretely on every render.
    compose-spread honoured it; this shooter did not, so every matrix shoot leaked the
    anchor's subject unless the author hand-negated it in prompts.md — three stewards
    did, on one book run, 2026-08-02."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_print_plan_names_the_auto_negated_subject(self):
        root = build(Path(self.tmp.name), anchor_subject=SUBJECT)
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("anchor subject (auto-negated on every shot): " + SUBJECT, r.stdout)

    def test_a_universe_without_the_field_plans_without_the_line(self):
        root = build(Path(self.tmp.name))
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("anchor subject", r.stdout)


class FakeShoot(unittest.TestCase):
    """In-process _shoot with a monkeypatched provider call, so prompt assembly and
    provenance behaviour are testable without a network or a key. The fake plays the
    ADAPTER's role: it writes the image and `<image>.recipe.json` beside it, exactly
    as every real provider script does."""

    def _mod(self):
        from importlib import util
        spec = util.spec_from_file_location("cm", CHAIN)
        m = util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _shoot_one(self, root, shot="c2-work"):
        import argparse as _ap
        import types
        m = self._mod()
        m._provider_script = lambda provider="gpt-image-2": "/dev/null/fake-provider.py"
        captured = {}

        def fake_run(cmd, *a, **kw):
            captured["prompt"] = cmd[cmd.index("--prompt") + 1]
            out = Path(cmd[cmd.index("--filename") + 1])
            Image.new("RGB", (8, 8), (10, 20, 30)).save(out)
            (out.parent / (out.name + ".recipe.json")).write_text(json.dumps({
                "asset": str(out), "model": "gpt-image-2",
                "prompt": captured["prompt"],
                "inputs": [c for c in cmd if str(c).endswith(".png")],
                "generatedAt": "2026-08-02T00:00:00+00:00"}))
            return types.SimpleNamespace(returncode=0)

        m.subprocess = types.SimpleNamespace(run=fake_run)
        plan = m.build_plan(root, "room")
        refdir = plan["refdir"]
        seed_png = refdir / (plan["seed"] + ".png")
        png(seed_png)
        args = _ap.Namespace(size="1024x1024", max_conditioning=4)
        anchor_abs = str((root / plan["anchor"]).resolve())
        rc = m._shoot(plan, shot, [str(seed_png)], args, anchor_abs, "", refdir, root)
        self.assertEqual(rc, 0)
        return captured, refdir

    def test_the_declared_anchor_subject_reaches_every_shot_prompt(self):
        root = build(Path(self.tmp.name), anchor_subject=SUBJECT)
        captured, _ = self._shoot_one(root)
        self.assertIn(SUBJECT, captured["prompt"])
        self.assertIn("NONE OF THE FOLLOWING", captured["prompt"])

    def test_no_declaration_means_no_guard_sentence(self):
        root = build(Path(self.tmp.name))
        captured, _ = self._shoot_one(root)
        self.assertNotIn("NONE OF THE FOLLOWING", captured["prompt"])

    def test_exactly_one_recipe_per_asset(self):
        """chain_matrix used to write `<shot>.recipe.json` while the provider wrote
        `<shot>.png.recipe.json`: two sidecars for one asset, free to diverge. Now the
        chain merges into the provider's file and removes the stale legacy twin."""
        root = build(Path(self.tmp.name))
        # a stale legacy twin from the old code, describing bytes about to be replaced
        (root / "reference" / "room").mkdir(parents=True, exist_ok=True)
        (root / "reference" / "room" / "c2-work.recipe.json").write_text("{}")
        _, refdir = self._shoot_one(root)
        recipes = sorted(p.name for p in refdir.glob("c2-work*recipe.json"))
        self.assertEqual(recipes, ["c2-work.png.recipe.json"], recipes)

    def test_the_single_recipe_holds_both_provider_and_chain_provenance(self):
        root = build(Path(self.tmp.name))
        _, refdir = self._shoot_one(root)
        rec = json.loads((refdir / "c2-work.png.recipe.json").read_text())
        # the adapter's facts survive the merge...
        self.assertIn("generatedAt", rec)
        self.assertIn("inputs", rec)
        # ...and the chain's conditioning metadata is in the SAME file
        self.assertIn("conditionedOn", rec)
        self.assertIn("method", rec)
        self.assertEqual(rec["shot"], "c2-work")
        self.assertEqual(rec["entity"], "room")


# --- code-drawn shots are conditioning, never work ---------------------------
# Earned 2026-08-03 on nation-of-fire `the-shelter-he-held-up` (What a Relief).
# `pick_seed` chose `master`, then planned `blueprint` as shot 2 conditioned on the
# anchor: a deterministic `abu elevation` output about to be overwritten by an AI render,
# destroying the geometry seed every later shot was meant to inherit. `make-a-book`
# prescribes the exact opposite ("Seed a multi-state object's chain on a CODE-DRAWN
# BLUEPRINT, not a state plate"), and reaching that shape meant hand-adding
# `REFS: <id>@blueprint` to four prompts.md sections plus hand-declaring
# `structured.sheets.blueprint` before the selector would resolve.
def drawn_png(path: Path, generator="agenticstory.elevation"):
    """A shot that already exists on disk AND whose recipe records a code generator."""
    png(path)
    (path.parent / (path.name + ".recipe.json")).write_text(json.dumps({
        "asset": str(path), "generator": generator,
        "mode": "deterministic-2d-elevation", "model": None, "inputs": []}))


class TestCodeDrawnShots(unittest.TestCase):
    SHOTS = ("blueprint", "master", "strained", "beside-the-house", "let-go")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = build(Path(self.tmp.name), kind="visual-metaphor", shots=self.SHOTS)
        drawn_png(self.root / "reference" / "room" / "blueprint.png")

    def test_a_code_drawn_shot_is_not_planned_for_generation(self):
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        numbered = [l for l in r.stdout.splitlines()
                    if l.strip().startswith(tuple(f"{i}." for i in range(1, 10)))]
        self.assertTrue(numbered)
        self.assertFalse([l for l in numbered if "blueprint" in l.split("conditioned on:")[0]],
                         "blueprint is still planned as a shot:\n" + "\n".join(numbered))

    def test_it_is_passed_as_conditioning_to_every_shot_instead(self):
        r = run(self.root, "--print-plan")
        numbered = [l for l in r.stdout.splitlines()
                    if l.strip().startswith(tuple(f"{i}." for i in range(1, 10)))]
        for l in numbered:
            self.assertIn("code-drawn: blueprint", l, l)

    def test_a_painted_plate_of_the_same_name_is_still_shot(self):
        """The RECIPE decides, never the filename. `blueprint` is a convention and a
        painted plate may legitimately carry it; guessing from the name would refuse to
        re-shoot real art."""
        p = self.root / "reference" / "room" / "blueprint.png"
        (p.parent / (p.name + ".recipe.json")).write_text(json.dumps(
            {"asset": str(p), "model": "gpt-image-2", "prompt": "a painted blueprint"}))
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("code-drawn (never generated", r.stdout)
        self.assertIn("blueprint", r.stdout)

    def test_an_asset_with_no_recipe_at_all_is_still_shot(self):
        """The pre-provenance library is real art with no sidecar. It must not be
        mistaken for a deterministic output nobody may overwrite."""
        (self.root / "reference" / "room" / "blueprint.png.recipe.json").unlink()
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotIn("code-drawn (never generated", r.stdout)

    def test_naming_it_in_shots_refuses_rather_than_overwriting(self):
        r = run(self.root, "--shots", "blueprint,master", "--print-plan")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("CODE-DRAWN", r.stderr)
        self.assertIn("agenticstory.elevation", r.stderr)

    def test_naming_it_as_the_seed_refuses(self):
        r = run(self.root, "--seed", "blueprint", "--print-plan")
        self.assertEqual(r.returncode, 2, r.stdout)
        self.assertIn("CODE-DRAWN", r.stderr)

    def test_the_seed_is_picked_from_the_paint_shots(self):
        r = run(self.root, "--print-plan")
        self.assertIn("seed (hero) = master", r.stdout)

    def test_a_massing_blueprint_is_recognised_too(self):
        drawn_png(self.root / "reference" / "room" / "blueprint.png",
                  generator="agenticstory.massing (code-built 3D massing render)")
        r = run(self.root, "--print-plan")
        self.assertIn("code-drawn (never generated", r.stdout)

    def test_a_deterministic_flag_with_no_model_is_recognised(self):
        """SPEC 4.11 generators are not named `agenticstory.*`, so the second tell has
        to work on its own or every universe-authored generator is invisible here."""
        p = self.root / "reference" / "room" / "blueprint.png"
        (p.parent / (p.name + ".recipe.json")).write_text(json.dumps(
            {"asset": str(p), "generator": "starfield", "deterministic": True,
             "model": None}))
        r = run(self.root, "--print-plan")
        self.assertIn("code-drawn (never generated", r.stdout)

    def test_a_matrix_that_is_entirely_code_drawn_refuses_clearly(self):
        root = build(Path(tempfile.mkdtemp()), kind="visual-metaphor", shots=("blueprint",))
        drawn_png(root / "reference" / "room" / "blueprint.png")
        r = subprocess.run([sys.executable, str(CHAIN), str(root), "room", "--print-plan"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 2)
        self.assertIn("nothing for this chain to paint", r.stderr)


# --- star topology: every state off the SEED, never off a sibling ------------
# The default cumulative chain is right for ANGLES on one unchanging subject and wrong
# for a multi-state OBJECT: on `the-shelter-he-held-up` the states are a cold night
# plate, a warm-gold daylight plate and a cool overcast morning, and serial chaining
# walks each state's light into the next. The workaround was invoking this script three
# separate times as `--shots master,<one-state> --skip-existing`, and
# `the-broken-cisterns`'s authority.note already recorded the same finding in prose.
class TestStarTopology(unittest.TestCase):
    SHOTS = ("master", "strained", "beside-the-house", "let-go")

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = build(Path(self.tmp.name), kind="visual-metaphor", shots=self.SHOTS)

    def _shot4(self, *extra):
        r = run(self.root, "--print-plan", *extra)
        self.assertEqual(r.returncode, 0, r.stderr)
        return r.stdout, [l for l in r.stdout.splitlines() if "4. let-go" in l][0]

    def test_the_default_is_still_cumulative(self):
        """Nothing changes for the matrices this behaviour is correct for."""
        out, line = self._shot4()
        self.assertIn("CUMULATIVE", out)
        self.assertIn("strained", line)
        self.assertIn("beside-the-house", line)

    def test_star_conditions_shot_four_on_the_seed_and_no_sibling(self):
        out, line = self._shot4("--star")
        self.assertIn("STAR", out)
        self.assertIn("master", line)
        self.assertNotIn("strained", line)
        self.assertNotIn("beside-the-house", line)

    def test_no_sibling_chain_is_the_same_flag(self):
        _, line = self._shot4("--no-sibling-chain")
        self.assertNotIn("strained", line)

    def test_max_conditioning_cannot_let_a_sibling_back_in(self):
        """A sibling is never a candidate under --star, so it is not a window that a
        larger `--max-conditioning` widens."""
        _, line = self._shot4("--star", "--max-conditioning", "0")
        self.assertNotIn("strained", line)
        self.assertIn("master", line)

    def test_the_actual_run_passes_only_the_seed(self):
        """The plan and the run must agree; the plan is a printout and the run is what
        costs money. This asserts the --input-image list the provider is handed."""
        import argparse as _ap, importlib.util, types
        spec = importlib.util.spec_from_file_location("cm", CHAIN)
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        m._provider_script = lambda provider="gpt-image-2": "/dev/null/fake-provider.py"
        seen = {}

        def fake_run(cmd, *a, **kw):
            seen["inputs"] = [cmd[i + 1] for i, c in enumerate(cmd) if c == "--input-image"]
            out = Path(cmd[cmd.index("--filename") + 1])
            Image.new("RGB", (8, 8), (10, 20, 30)).save(out)
            return types.SimpleNamespace(returncode=0)

        m.subprocess = types.SimpleNamespace(run=fake_run)
        drawn_png(self.root / "reference" / "room" / "blueprint.png")
        (self.root / "reference" / "room" / "prompts.md").write_text(
            (self.root / "reference" / "room" / "prompts.md").read_text()
            + "## blueprint → `reference/room/blueprint.png`\nThe blueprint.\n\n")
        plan = m.build_plan(self.root, "room")
        refdir = plan["refdir"]
        goldens = []
        for s in ("master", "strained", "beside-the-house"):
            png(refdir / f"{s}.png")
            goldens.append(str((refdir / f"{s}.png").resolve()))
        args = _ap.Namespace(size="1024x1024", max_conditioning=4, star=True)
        m._shoot(plan, "let-go", goldens, args,
                 str((self.root / plan["anchor"]).resolve()), "", refdir, self.root)
        names = [Path(p).name for p in seen["inputs"]]
        self.assertIn("master.png", names)
        self.assertIn("blueprint.png", names, "code-drawn geometry must ride along")
        self.assertNotIn("strained.png", names)
        self.assertNotIn("beside-the-house.png", names)
        rec = json.loads((refdir / "let-go.png.recipe.json").read_text())
        self.assertIn("star-chain", rec["method"])
        self.assertEqual([r["shot"] for r in rec["codeDrawnRefs"]], ["blueprint"])


if __name__ == "__main__":
    unittest.main()


class TestShootSeedCodeDrawn(unittest.TestCase):
    """A CODE-DRAWN plate must not block --shoot-seed.

    The 'already has plates on disk' guard refuses because the locked place would not ride
    along on a seed render. That premise is FALSE for code-drawn geometry: _shoot passes
    plan["codeDrawn"] as an --input-image on every shot INCLUDING the seed. While the guard
    counted it anyway the two guards deadlocked, and an entity scaffolded blueprint-first
    (which add-setting, add-visual-metaphor and make-a-book all instruct) had no legal first
    shot: --shoot-seed refused and named --seed <blueprint>, and --seed refused that same
    plate as 'already the seed'.

    Tested against the extracted predicate rather than through the CLI, because the guard
    sits inside main() after the dry-run early return, so a --dry-run subprocess test passes
    whether the fix is present or not. (It did, before this was rewritten.)
    """

    def _mod(self):
        from importlib import util
        spec = util.spec_from_file_location("cm_pp", CHAIN)
        m = util.module_from_spec(spec); spec.loader.exec_module(m)
        return m

    def _sheets(self, root, generator):
        bp = root / "reference" / "room" / "blueprint.png"
        png(bp)
        png(root / "reference" / "room" / "empty-meadow.png")
        if generator is not None:
            Path(str(bp) + ".recipe.json").write_text(json.dumps({
                "asset": str(bp), "generator": generator, "deterministic": True}))
        return {"blueprint": "reference/room/blueprint.png",
                "master": "reference/room/master.png",
                "empty-meadow": "reference/room/empty-meadow.png"}

    def test_code_drawn_blueprint_is_not_a_painted_plate(self):
        root = Path(tempfile.mkdtemp())
        sheets = self._sheets(root, "agenticstory.massing")
        got = self._mod().painted_plates_on_disk(root, sheets, "master")
        self.assertNotIn("blueprint", got)
        self.assertEqual(got, ["empty-meadow"], "the painted sibling must still count")

    def test_a_plate_with_no_recipe_still_counts(self):
        """The guard keeps its teeth. Code-drawn is read from the RECIPE, never from the
        filename, so a painted plate merely named `blueprint` still blocks the seed."""
        root = Path(tempfile.mkdtemp())
        sheets = self._sheets(root, None)
        got = self._mod().painted_plates_on_disk(root, sheets, "master")
        self.assertIn("blueprint", got)

    def test_the_seed_itself_never_counts(self):
        root = Path(tempfile.mkdtemp())
        sheets = self._sheets(root, "agenticstory.elevation")
        self.assertEqual(self._mod().painted_plates_on_disk(root, sheets, "empty-meadow"), [])


class StylePackCarriesTheMedium(Base):
    """A Style Pack must contribute MEDIUM WORDS to the prompt, never its slug.

    `nof-soft-painterly` is a filesystem name. To an image model it names no medium
    at all, which made `--register <packid>` strictly WEAKER than shooting through
    the universe register, whose `name` is a real description. Two nation-of-fire
    seeds came back photoreal against a register that rejects `photoreal` by name
    (2026-08-21, the-composers-phone) before the pack's own `styleLine` was read.
    """

    def _pack(self, **extra):
        pack = self.root / "reference" / "style" / "inky"
        (pack / "refs").mkdir(parents=True, exist_ok=True)
        png(pack / "refs" / "anchor.png")
        body = {"id": "inky", "name": "Inky", "anchor": "refs/anchor.png"}
        body.update(extra)
        (pack / "pack.json").write_text(json.dumps(body))
        self._register(stylePack="inky", anchor=None)

    def test_style_line_prefers_the_packs_own_styleLine(self):
        self._pack(styleLine="Dense india-ink linework with dry-brush shading.")
        r = run(self.root, "--register", "inky", "--print-plan")
        self.assertIn("Dense india-ink linework", r.stdout)
        self.assertNotIn("register=inky", r.stdout)

    def test_style_line_falls_back_to_the_name_then_the_slug(self):
        self._pack()  # name but no styleLine
        r = run(self.root, "--register", "inky", "--print-plan")
        self.assertIn("register=Inky", r.stdout)
