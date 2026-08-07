#!/usr/bin/env python3
"""reroll_from_recipe.py: the recipe chain resolver and its refusals.

The expensive bug this guards is NOT the regeneration call — it is resolving the WRONG
generation (or silently resolving none) and then spending a paid image call reproducing
something other than what the recipe recorded. So the tests pin: chain walking across
both recipe dialects, the broken-chain recovery (sourceRender prompt + sibling refs,
exactly the shape the incident book has on disk), the note append, and every refusal
(missing refs, zero recovered refs, unknown derive tools, --out against a chain).
No test makes a network call.
"""
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reroll_from_recipe.py"

spec = importlib.util.spec_from_file_location("reroll_from_recipe", SCRIPT)
rr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rr)

PROMPT = ("PORTRAIT picture-book COVER in the warm editorial style. The plain door, "
          "open a little, warm light through the gap. NEGATIVES: neon, 3D, any person, "
          "any human figure, anyone standing in the room.")
# A sibling roll of the SAME plate: identical but for the NEGATIVES tail — the real
# on-disk shape (two rolls of one plate differ only there).
PROMPT_SIBLING = PROMPT.replace("any person, any human figure, anyone standing in the room",
                                "any person or figure, any lettering, plaque, frame or rope")


def write(p: Path, obj) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(obj) if not isinstance(obj, str) else obj)
    return p


def build_direct(root: Path):
    """A plain spread: adapter-shape generation recipe directly beside the asset."""
    ref = write(root / "refs" / "anchor.png", "REF")
    png = write(root / "book" / "spread-03.png", "OLD ART")
    write(root / "book" / "spread-03.png.recipe.json", {
        "provider": "gpt-image-2", "model": "gpt-image-2", "prompt": PROMPT,
        "refs": [{"path": str(ref)}], "size": "1536x1024", "quality": "high",
        "sha256": "x",
    })
    return png, ref


def build_endcap(root: Path):
    """The incident's exact shape: final copy-derive -> raw conform-derive whose
    derivedFrom.recipe is null (pre-v0.33 in-place conform) but whose sourceRender
    carries the prompt; the full ref list survives only in the sibling -gen recipe."""
    ref1 = write(root / "u" / "swatch.png", "R1")
    ref2 = write(root / "u" / "master.png", "R2")
    book = root / "book"
    final = write(book / "closing-plate.png", "FINAL")
    raw = write(book / "closing-plate-raw.png", "RAW")
    raw_recipe = write(book / "closing-plate-raw.png.recipe.json", {
        "asset": str(raw), "model": "none (deterministic image transform, no model call)",
        "mode": "derive", "tool": "abu:cover/scripts/conform_cover.py",
        "args": {"aspect": "3:4", "mode": "pad", "inset": 1.0, "blur": 40, "keyline": None},
        "prompt": None,
        "sourceRender": {"prompt": PROMPT, "model": "gpt-image-2",
                         "size": "1024x1536", "quality": "high"},
        "transform": "1024x1536 -> 1152x1536",
        "derivedFrom": {"path": str(raw), "recipe": None, "sha256_16": "a"},
    })
    write(book / "closing-plate.png.recipe.json", {
        "asset": str(final), "model": "none (deterministic image transform, no model call)",
        "mode": "derive", "tool": "abu:cover/scripts/render_cover.py",
        "args": {"publish": "platform-facing copy of the conformed cover"},
        "prompt": None, "transform": "copy (byte-identical; no resample, no crop, no repaint)",
        "derivedFrom": {"path": str(raw), "recipe": str(raw_recipe), "sha256_16": "a"},
    })
    write(book / "closing-plate-gen.recipe.json", {
        "asset": "/tmp/closing-gen.png", "model": "gpt-image-2", "mode": "edit",
        "prompt": PROMPT_SIBLING, "inputs": [str(ref1), str(ref2)],
        "size": "1024x1536", "quality": "high",
        "generator": "chatgpt-images/scripts/generate_image.py",
    })
    return final, raw, ref1, ref2


class ResolveDirect(unittest.TestCase):
    def test_direct_generation(self):
        with tempfile.TemporaryDirectory() as td:
            png, ref = build_direct(Path(td))
            chain = rr.resolve_chain(png)
            self.assertEqual(chain["derives"], [])
            self.assertEqual(chain["generation"]["refs"], [str(ref)])
            self.assertEqual(chain["generation"]["model"], "gpt-image-2")
            self.assertEqual(chain["generation"]["size"], "1536x1024")
            self.assertTrue(chain["source"].startswith("generation recipe"))
            self.assertFalse(chain["refs_recovered"])

    def test_accepts_recipe_path_too(self):
        with tempfile.TemporaryDirectory() as td:
            png, _ = build_direct(Path(td))
            chain = rr.resolve_chain(png.with_name(png.name + ".recipe.json"))
            self.assertEqual(chain["final"], png)

    def test_no_recipe_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            orphan = write(Path(td) / "orphan.png", "X")
            with self.assertRaises(SystemExit):
                rr.resolve_chain(orphan)


class ResolveEndcapChain(unittest.TestCase):
    def test_walks_derives_and_recovers_refs_from_sibling(self):
        with tempfile.TemporaryDirectory() as td:
            final, raw, ref1, ref2 = build_endcap(Path(td))
            chain = rr.resolve_chain(final)
            kinds = [d["kind"] for d in chain["derives"]]
            self.assertEqual(kinds, ["conform", "publish"])  # generation-forward order
            # the conform replays with the RECORDED args
            self.assertEqual(chain["derives"][0]["args"]["aspect"], "3:4")
            self.assertEqual(chain["derives"][0]["args"]["mode"], "pad")
            # the prompt is the sourceRender's (the roll that shipped), the refs the
            # sibling's (the only place they survived)
            self.assertEqual(chain["generation"]["prompt"], PROMPT)
            self.assertEqual(chain["generation"]["refs"], [str(ref1), str(ref2)])
            self.assertTrue(chain["refs_recovered"])
            self.assertIn("closing-plate-gen.recipe.json", chain["source"])

    def test_unknown_derive_tool_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            png = write(Path(td) / "b" / "x.png", "X")
            write(Path(td) / "b" / "x.png.recipe.json", {
                "asset": str(png), "mode": "derive", "model": "none (transform)",
                "tool": "somebody-elses/mystery_step.py", "args": {},
                "transform": "resample 2x", "derivedFrom": {"path": "y", "recipe": None},
            })
            with self.assertRaises(SystemExit):
                rr.resolve_chain(png)

    def test_dissimilar_sibling_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as td:
            final, raw, ref1, ref2 = build_endcap(Path(td))
            gen = final.parent / "closing-plate-gen.recipe.json"
            rec = json.loads(gen.read_text())
            rec["prompt"] = "a completely unrelated pencil sketch of a lighthouse at sea"
            gen.write_text(json.dumps(rec))
            chain = rr.resolve_chain(final)
            self.assertEqual(chain["generation"]["refs"], [])
            self.assertFalse(chain["refs_recovered"])


class Plan(unittest.TestCase):
    def test_note_is_appended_and_only_when_given(self):
        self.assertEqual(rr.with_note(PROMPT, None), PROMPT)
        noted = rr.with_note(PROMPT, "slightly warmer light")
        self.assertIn(PROMPT, noted)
        self.assertIn("CHANGE FOR THIS RE-ROLL", noted)
        self.assertIn("slightly warmer light", noted)

    def test_missing_ref_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            png, ref = build_direct(Path(td))
            ref.unlink()
            chain = rr.resolve_chain(png)
            with self.assertRaises(SystemExit):
                rr.build_plan(chain, None, {}, None)

    def test_zero_recovered_refs_refuses_without_flag(self):
        with tempfile.TemporaryDirectory() as td:
            final, raw, ref1, ref2 = build_endcap(Path(td))
            (final.parent / "closing-plate-gen.recipe.json").unlink()
            chain = rr.resolve_chain(final)
            with self.assertRaises(SystemExit):
                rr.build_plan(chain, None, {}, None)
            plan = rr.build_plan(chain, None, {}, None, allow_no_refs=True)
            self.assertEqual(plan["generation"]["refs"], [])

    def test_out_refuses_against_a_derive_chain(self):
        with tempfile.TemporaryDirectory() as td:
            final, *_ = build_endcap(Path(td))
            chain = rr.resolve_chain(final)
            with self.assertRaises(SystemExit):
                rr.build_plan(chain, None, {}, Path(td) / "elsewhere.png")

    def test_overrides_apply(self):
        with tempfile.TemporaryDirectory() as td:
            png, _ = build_direct(Path(td))
            chain = rr.resolve_chain(png)
            plan = rr.build_plan(chain, None, {"model": "nano-banana-pro"}, None)
            self.assertEqual(plan["generation"]["model"], "nano-banana-pro")
            # a direct generation regenerates IN PLACE
            self.assertEqual(plan["gen_target"], png)


class Backup(unittest.TestCase):
    def test_backup_covers_assets_their_sidecars_and_bare_recipes(self):
        # The `<slot>-gen.recipe.json` is an ATTESTATION of the previous roll; the
        # first live run overwrote it un-backed-up, which is the never-rewrite-a-
        # historical-record rule broken by the tool itself. It must ride the backup.
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            png = write(root / "a.png", "ART")
            write(root / "a.png.recipe.json", {"prompt": "p"})
            bare = write(root / "a-gen.recipe.json", {"prompt": "p", "inputs": []})
            dest = rr.backup([png, bare], root)
            names = sorted(p.name for p in dest.iterdir())
            self.assertEqual(names, ["a-gen.recipe.json", "a.png", "a.png.recipe.json"])

    def test_backup_returns_none_when_nothing_exists(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertIsNone(rr.backup([Path(td) / "ghost.png"], Path(td)))


class CliDryRun(unittest.TestCase):
    def test_dry_run_prints_plan_and_reminder_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            final, raw, ref1, ref2 = build_endcap(Path(td))
            before = sorted(p.name for p in final.parent.iterdir())
            r = subprocess.run([sys.executable, str(SCRIPT), str(final),
                                "--note", "warmer light", "--dry-run"],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("DRY RUN", r.stdout)
            self.assertIn("gpt-image-2", r.stdout)
            self.assertIn(str(ref1), r.stdout)
            self.assertIn("conform", r.stdout)
            self.assertIn("verify_render.py", r.stdout)  # the readback reminder
            after = sorted(p.name for p in final.parent.iterdir())
            self.assertEqual(before, after)

    def test_cli_refuses_orphan_asset(self):
        with tempfile.TemporaryDirectory() as td:
            orphan = write(Path(td) / "orphan.png", "X")
            r = subprocess.run([sys.executable, str(SCRIPT), str(orphan), "--dry-run"],
                               capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("no recipe", (r.stdout + r.stderr).lower())


if __name__ == "__main__":
    unittest.main()
