#!/usr/bin/env python3
"""
on-brand-image generate.py — the framework's single generate path, and until now
its only wholly untested one. 293 works have gone through this file; the composer
that was deleted last week had 91 tests and zero works. This suite closes that
inversion.

NO API CALLS, NO NETWORK, NO IMAGE GENERATION. Every test stops at the provider
boundary: `provider_script` is stubbed to a path that is never executed, and
`subprocess.run` is replaced by a fake that records the argv it was handed and
writes the bytes the real provider would have written. That fake is the seam. It
means the tests exercise the REAL `main()` — the real prompt compilation, the real
ref ordering, the real recipe write — rather than a refactored shadow of it.

Nothing in generate.py was refactored to make this testable. The one behavioral
claim these tests cannot make for free (that the CLI still emits the identical
prompt string) is therefore trivially true; the refusal paths are additionally
exercised through a real `subprocess` invocation of the CLI, which never reaches a
provider because every one of them exits first.

Run:  python3 tests/test_generate.py        (from the on-brand-image skill dir)
"""
import contextlib
import datetime
import hashlib
import importlib.util
import io
import json
import os
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
GENERATE = HERE.parent / "scripts" / "generate.py"

_spec = importlib.util.spec_from_file_location("obi_generate", GENERATE)
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

# A real, decodable 1x1 PNG. Used wherever a file merely has to exist and be an image.
PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c4944415408d763f8cfc0000003010100b5e2e8250000000049454e44ae426082"
)


def png(path, extra=b""):
    """A tiny unique PNG on disk. `extra` makes the bytes differ between fixtures."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_bytes(PNG_1x1 + extra)
    return str(p)


def real_png(path, size, mode="RGB"):
    """A genuinely-sized image, for the shrink tests that actually decode it."""
    from PIL import Image
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    color = (255, 0, 0) if mode == "RGB" else (255, 0, 0, 128)
    Image.new(mode, size, color).save(p)
    return str(p)


def make_pack(root, *, style_line="Neo-expressionist oil, heavy impasto.",
              rejected=("photorealism", "any text or lettering"),
              refs=("refs/anchor.png", "refs/b.png", "refs/c.png"),
              anchor="refs/anchor.png", write_refs=True, name="pack"):
    """A Style Pack on disk in the shape `create-style-pack` scaffolds: the anchor is
    ALSO listed in `refs`, which is exactly the de-dup case generate.py must handle."""
    pack_dir = Path(root) / name
    pack_dir.mkdir(parents=True, exist_ok=True)
    if write_refs:
        for i, rel in enumerate(refs):
            png(pack_dir / rel, extra=bytes([i]))
    manifest = {"id": name, "name": name, "styleLine": style_line,
                "rejectedPoles": list(rejected), "refs": list(refs)}
    if anchor is not None:
        manifest["anchor"] = anchor
    (pack_dir / "pack.json").write_text(json.dumps(manifest, indent=2))
    return str(pack_dir)


class Run:
    """What the provider WOULD have been called with, plus the recipe that was written."""

    def __init__(self, cmd, out):
        self.cmd = list(cmd)
        self.out = out

    def _after(self, flag):
        return self.cmd[self.cmd.index(flag) + 1]

    @property
    def prompt(self):
        return self._after("--prompt")

    @property
    def uploads(self):
        return [self.cmd[i + 1] for i, x in enumerate(self.cmd) if x == "--input-image"]

    @property
    def recipe(self):
        return json.loads(Path(self.out + ".recipe.json").read_text())

    @property
    def recipe_refs(self):
        return [r["path"] for r in self.recipe["refs"]]


class GenerateCase(unittest.TestCase):
    """Base: a temp workspace, and one driver that runs the real main() with the
    provider boundary stubbed."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.out = str(self.tmp / "out" / "image.png")
        self.calls = []

    def tearDown(self):
        self._tmp.cleanup()

    # --- the provider seam -------------------------------------------------
    def _fake_run(self, payload):
        def run(cmd, *a, **k):
            self.calls.append(list(cmd))
            # Prove we intercepted a real shell-out, not something already inert.
            assert cmd[0] == "uv", cmd
            fn = cmd[cmd.index("--filename") + 1]
            os.makedirs(os.path.dirname(fn), exist_ok=True)
            Path(fn).write_bytes(payload)
            return types.SimpleNamespace(returncode=0, args=cmd)
        return run

    def run_main(self, *args, out=None, payload=PNG_1x1, runner=None):
        out = out or self.out
        argv = ["generate.py", "--out", out, *[str(x) for x in args]]
        with mock.patch.object(gen.subprocess, "run", runner or self._fake_run(payload)), \
             mock.patch.object(gen, "provider_script",
                               lambda p: "/nonexistent/never-executed-provider.py"), \
             mock.patch.object(sys, "argv", argv), \
             contextlib.redirect_stdout(io.StringIO()):
            gen.main()
        return Run(self.calls[-1], out)

    def expect_exit(self, *args, out=None, runner=None):
        """Run and assert it REFUSED. Returns the exit message."""
        out = out or self.out
        with self.assertRaises(SystemExit) as ctx:
            self.run_main(*args, out=out, runner=runner)
        return str(ctx.exception)

    def base(self, *extra):
        return ("--prompt", "a lighthouse at dusk", "--ref-max-edge", "0", *extra)


# =====================================================================
# 1. --permit  (newest code, added 2026-07-30, zero coverage before this)
# =====================================================================
class TestPermit(GenerateCase):
    """--permit un-rejects ONE of a pack's standing poles for a single render.

    The load-bearing property is the loud refusal on a permit that matches nothing:
    a silent no-op reads to the operator as "text is allowed now" while the negative
    is still sitting in the prompt, so the render comes back wrong and the operator
    blames the model.
    """

    def test_permit_removes_exactly_the_matched_pole(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text", "3d render"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "any text"))
        clause = [l for l in r.prompt.split("\n\n") if l.startswith("Do NOT render")][0]
        self.assertNotIn("any text", clause)
        self.assertIn("photorealism", clause)
        self.assertIn("3d render", clause)

    def test_permit_leaves_the_other_poles_in_their_original_order(self):
        pack = make_pack(self.tmp, rejected=["a-pole", "b-pole", "c-pole"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "b-pole"))
        self.assertIn("Do NOT render it in any of these styles: a-pole, c-pole.", r.prompt)

    def test_permit_matches_a_substring_of_a_pole(self):
        pack = make_pack(self.tmp, rejected=["any text or lettering", "photorealism"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "text"))
        self.assertNotIn("lettering", r.prompt)
        self.assertIn("photorealism", r.prompt)

    def test_permit_matching_is_case_insensitive(self):
        pack = make_pack(self.tmp, rejected=["Any Text Or Lettering", "photorealism"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "TEXT"))
        self.assertNotIn("Lettering", r.prompt)

    def test_permit_is_repeatable(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text", "3d render"])
        r = self.run_main(*self.base("--style-pack", pack,
                                     "--permit", "text", "--permit", "3d"))
        self.assertIn("Do NOT render it in any of these styles: photorealism.", r.prompt)

    def test_one_permit_may_lift_several_poles(self):
        pack = make_pack(self.tmp, rejected=["text in the field", "text overlays", "neon"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "text"))
        self.assertIn("Do NOT render it in any of these styles: neon.", r.prompt)
        self.assertEqual(r.recipe["permitted"], ["text in the field", "text overlays"])

    def test_permitting_every_pole_drops_the_whole_negatives_clause(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        r = self.run_main(*self.base("--style-pack", pack,
                                     "--permit", "photorealism", "--permit", "text"))
        self.assertNotIn("Do NOT render", r.prompt)

    def test_permit_that_matches_nothing_refuses(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        msg = self.expect_exit(*self.base("--style-pack", pack, "--permit", "watercolour"))
        self.assertIn("--permit matched no rejected pole", msg)
        self.assertIn("watercolour", msg)

    def test_the_refusal_names_the_packs_actual_poles(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        msg = self.expect_exit(*self.base("--style-pack", pack, "--permit", "nope"))
        self.assertIn("the pack's poles are: photorealism, any text", msg)

    def test_a_refused_permit_generates_nothing_at_all(self):
        pack = make_pack(self.tmp, rejected=["photorealism"])
        self.expect_exit(*self.base("--style-pack", pack, "--permit", "typo"))
        self.assertEqual(self.calls, [], "refused, yet the provider was still invoked")
        self.assertFalse(os.path.exists(self.out))
        self.assertFalse(os.path.exists(self.out + ".recipe.json"))

    def test_one_bad_permit_refuses_even_when_another_matched(self):
        """Partial success is still a typo the operator needs to see."""
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        msg = self.expect_exit(*self.base("--style-pack", pack,
                                          "--permit", "text", "--permit", "typo"))
        self.assertIn("typo", msg)
        self.assertNotIn("matched no rejected pole in this pack: text", msg)

    def test_lifted_poles_are_recorded_in_the_recipe(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "text"))
        self.assertEqual(r.recipe["permitted"], ["any text"])

    def test_the_recipe_records_the_packs_wording_not_the_permit_string(self):
        """A render made under a permit must not be indistinguishable from one that
        never needed it, and the audit trail should read in the pack's own terms."""
        pack = make_pack(self.tmp, rejected=["Any Text Or Lettering"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "text"))
        self.assertEqual(r.recipe["permitted"], ["Any Text Or Lettering"])

    def test_no_permitted_key_when_nothing_was_lifted(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertIn("stylePack", r.recipe)
        self.assertNotIn("permitted", r.recipe)

    def test_no_permitted_key_on_a_pack_with_no_poles(self):
        pack = make_pack(self.tmp, rejected=[])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertNotIn("permitted", r.recipe)

    def test_permit_does_not_disturb_the_style_line(self):
        pack = make_pack(self.tmp, style_line="Impasto oil.", rejected=["any text"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "text"))
        self.assertEqual(r.prompt, "a lighthouse at dusk\n\nImpasto oil.")

    # --- the two silent no-ops these tests exposed, now fixed ------------
    # Both were found by this suite on the day --permit shipped, and both were the
    # exact failure the flag's own refusal was written to prevent: a permit that
    # neither lifts anything nor complains, leaving the caller believing a pole was
    # lifted while the negative sat in the prompt unchanged.
    def test_permit_without_a_pack_REFUSES(self):
        """A permit lifts a pole from a pack. With no pack there are no poles.

        Previously swallowed: every permit code path lives inside `if a.style_pack:`,
        so a permit passed without a pack fell through the branch entirely.
        """
        msg = self.expect_exit(*self.base("--permit", "any text"))
        self.assertIn("--permit needs --style-pack", msg)

    def test_an_empty_permit_REFUSES(self):
        """`--permit ""` must refuse rather than pass silently.

        The lift loop guards `t and t in r.lower()`, but the unmatched check did not,
        and "" is a substring of every pole. So an empty permit counted as matching
        everything, lifted nothing, and never tripped the refusal.
        """
        pack = make_pack(self.tmp, rejected=["photorealism"])
        msg = self.expect_exit(*self.base("--style-pack", pack, "--permit", ""))
        self.assertIn("empty value", msg)

    def test_a_real_permit_still_works_after_both_fixes(self):
        """The refusals must not have made the happy path stricter than intended."""
        pack = make_pack(self.tmp, rejected=["photorealism", "neon"])
        r = self.run_main(*self.base("--style-pack", pack, "--permit", "photoreal"))
        self.assertNotIn("photorealism", r.prompt)
        self.assertIn("neon", r.prompt)
        self.assertEqual(r.recipe.get("permitted"), ["photorealism"])


# =====================================================================
# 2. Style-pack compilation
# =====================================================================
class TestStylePackCompilation(GenerateCase):
    """A pack is the DEFINITION of the look. Before 2026-07-27 --style-pack wrote a
    label into the recipe and applied nothing, so the provenance asserted something
    untrue. These tests are that bug's headstone."""

    def test_style_line_is_appended_after_the_subject(self):
        pack = make_pack(self.tmp, style_line="Impasto oil.", rejected=[])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(r.prompt, "a lighthouse at dusk\n\nImpasto oil.")

    def test_rejected_poles_become_a_do_not_render_clause(self):
        pack = make_pack(self.tmp, style_line="", rejected=["photorealism", "3d render"])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(
            r.prompt,
            "a lighthouse at dusk\n\n"
            "Do NOT render it in any of these styles: photorealism, 3d render.")

    def test_a_pack_with_no_poles_produces_no_clause(self):
        pack = make_pack(self.tmp, rejected=[])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertNotIn("Do NOT render", r.prompt)

    def test_falsy_poles_are_dropped_from_the_clause(self):
        pack = make_pack(self.tmp, style_line="", rejected=["photorealism", "", None])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertIn("Do NOT render it in any of these styles: photorealism.", r.prompt)

    def test_the_compiled_order_is_subject_then_style_then_negatives(self):
        pack = make_pack(self.tmp, style_line="Impasto oil.", rejected=["photorealism"])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(r.prompt.split("\n\n"), [
            "a lighthouse at dusk",
            "Impasto oil.",
            "Do NOT render it in any of these styles: photorealism.",
        ])

    def test_a_missing_pack_json_refuses_and_names_the_path(self):
        missing = str(self.tmp / "no-such-pack")
        msg = self.expect_exit(*self.base("--style-pack", missing))
        self.assertIn("--style-pack has no pack.json", msg)
        self.assertIn(os.path.join(missing, "pack.json"), msg)

    def test_the_pack_may_be_named_by_its_json_file_directly(self):
        pack = make_pack(self.tmp, style_line="Impasto oil.", rejected=[])
        r = self.run_main(*self.base("--style-pack", os.path.join(pack, "pack.json")))
        self.assertIn("Impasto oil.", r.prompt)
        self.assertEqual(r.uploads[0], os.path.join(pack, "refs", "anchor.png"))

    def test_a_pack_resolving_zero_references_refuses(self):
        """The look IS the references. A pack-less render that still claims the pack
        in its recipe is worse than no render."""
        pack = make_pack(self.tmp, write_refs=False)
        msg = self.expect_exit(*self.base("--style-pack", pack))
        self.assertIn("resolved zero references", msg)
        self.assertEqual(self.calls, [])

    def test_the_pack_is_recorded_in_the_recipe_as_given(self):
        pack = make_pack(self.tmp)
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(r.recipe["stylePack"], pack)

    def test_no_style_pack_key_when_no_pack_was_used(self):
        r = self.run_main(*self.base("--ref", png(self.tmp / "a.png")))
        self.assertNotIn("stylePack", r.recipe)

    def test_a_pack_with_neither_style_line_nor_poles_leaves_the_prompt_alone(self):
        pack = make_pack(self.tmp, style_line="", rejected=[])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(r.prompt, "a lighthouse at dusk")


# =====================================================================
# 3. Ref ordering — load-bearing
# =====================================================================
class TestRefOrdering(GenerateCase):
    """A reference outranks words, so ORDER is meaning. The anchor is the pack's
    content-neutral reference and goes first; entity plates outrank even that,
    because a pack pulls hard toward its own faces and must not win an argument
    about who the subject is."""

    def test_the_anchor_comes_first(self):
        pack = make_pack(self.tmp, refs=["refs/b.png", "refs/anchor.png", "refs/c.png"],
                         anchor="refs/anchor.png")
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertTrue(r.uploads[0].endswith(os.path.join("refs", "anchor.png")))

    def test_pack_refs_follow_the_anchor_in_manifest_order(self):
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png", "refs/c.png"])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual([os.path.basename(p) for p in r.uploads],
                         ["anchor.png", "b.png", "c.png"])

    def test_caller_refs_come_last(self):
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png"])
        mine = png(self.tmp / "mine.png", extra=b"z")
        r = self.run_main(*self.base("--style-pack", pack, "--ref", mine))
        self.assertEqual([os.path.basename(p) for p in r.uploads],
                         ["anchor.png", "b.png", "mine.png"])

    def test_the_anchor_is_not_duplicated_when_it_is_also_listed_in_refs(self):
        """`create-style-pack` always writes the anchor into `refs` too."""
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png"],
                         anchor="refs/anchor.png")
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(len(r.uploads), 2)
        self.assertEqual(len(set(r.uploads)), 2)

    def test_a_caller_ref_that_repeats_a_pack_ref_is_not_duplicated(self):
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png"])
        again = os.path.join(pack, "refs", "b.png")
        r = self.run_main(*self.base("--style-pack", pack, "--ref", again))
        self.assertEqual(len(r.uploads), 2)

    def test_a_caller_ref_written_unnormalized_is_still_deduped(self):
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png"])
        again = os.path.join(pack, "refs", ".", "..", "refs", "b.png")
        r = self.run_main(*self.base("--style-pack", pack, "--ref", again))
        self.assertEqual(len(r.uploads), 2)

    def test_a_pack_ref_missing_from_disk_is_skipped_not_fatal(self):
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png"])
        os.remove(os.path.join(pack, "refs", "b.png"))
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual([os.path.basename(p) for p in r.uploads], ["anchor.png"])

    def test_a_pack_with_no_anchor_still_orders_its_refs(self):
        pack = make_pack(self.tmp, anchor=None, refs=["refs/b.png", "refs/c.png"])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual([os.path.basename(p) for p in r.uploads], ["b.png", "c.png"])

    def test_an_absolute_pack_ref_is_used_as_written(self):
        outside = png(self.tmp / "outside" / "x.png", extra=b"o")
        pack = make_pack(self.tmp, anchor=outside, refs=["refs/b.png"])
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(r.uploads[0], outside)

    def test_a_caller_ref_that_does_not_exist_refuses(self):
        msg = self.expect_exit(*self.base("--ref", str(self.tmp / "ghost.png")))
        self.assertIn("ref not found", msg)
        self.assertEqual(self.calls, [])

    def test_caller_ref_order_is_preserved(self):
        a = png(self.tmp / "a.png", extra=b"a")
        b = png(self.tmp / "b.png", extra=b"b")
        r = self.run_main(*self.base("--ref", b, "--ref", a))
        self.assertEqual([os.path.basename(p) for p in r.uploads], ["b.png", "a.png"])


# =====================================================================
# 4. The recipe is a SIDE EFFECT of generating and cannot be skipped
# =====================================================================
class TestRecipeIsUnskippable(GenerateCase):
    """This file's stated reason for existing: provenance is not a step you remember
    at lock time, it is a thing you cannot generate without."""

    BARE_KEYS = {"provider", "model", "prompt", "specVersion", "refs", "timestamp", "sha256", "size", "quality"}

    def test_the_recipe_lands_beside_the_output(self):
        r = self.run_main(*self.base())
        self.assertTrue(os.path.exists(self.out + ".recipe.json"))
        self.assertEqual(os.path.dirname(self.out + ".recipe.json"),
                         os.path.dirname(self.out))

    def test_a_bare_render_writes_exactly_the_documented_keys(self):
        r = self.run_main(*self.base())
        self.assertEqual(set(r.recipe), self.BARE_KEYS)

    def test_a_pack_render_adds_style_pack_and_nothing_else(self):
        pack = make_pack(self.tmp)
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(set(r.recipe), self.BARE_KEYS | {"stylePack"})

    def test_the_recipe_pins_the_prompt_actually_sent(self):
        pack = make_pack(self.tmp)
        r = self.run_main(*self.base("--style-pack", pack))
        self.assertEqual(r.recipe["prompt"], r.prompt.strip())

    def test_the_recipe_pins_the_model_as_both_provider_and_model(self):
        r = self.run_main(*self.base("--model", "nano-banana-pro"))
        self.assertEqual(r.recipe["provider"], "nano-banana-pro")
        self.assertEqual(r.recipe["model"], "nano-banana-pro")

    def test_the_recipe_pins_the_spec_version(self):
        r = self.run_main(*self.base("--spec-version", "0.17"))
        self.assertEqual(r.recipe["specVersion"], "0.17")

    def test_the_recipe_records_every_ref_in_render_order(self):
        pack = make_pack(self.tmp, refs=["refs/anchor.png", "refs/b.png"])
        mine = png(self.tmp / "mine.png", extra=b"m")
        r = self.run_main(*self.base("--style-pack", pack, "--ref", mine))
        self.assertEqual([os.path.basename(p) for p in r.recipe_refs],
                         ["anchor.png", "b.png", "mine.png"])
        self.assertEqual(r.recipe_refs, r.uploads)

    def test_sha256_matches_the_output_bytes(self):
        payload = PNG_1x1 + b"unique-bytes"
        r = self.run_main(*self.base(), payload=payload)
        self.assertEqual(r.recipe["sha256"], hashlib.sha256(payload).hexdigest())

    def test_sha256_distinguishes_a_regenerated_asset(self):
        first = self.run_main(*self.base(), payload=PNG_1x1 + b"one").recipe["sha256"]
        second = self.run_main(*self.base(), payload=PNG_1x1 + b"two").recipe["sha256"]
        self.assertNotEqual(first, second)

    def test_the_timestamp_is_utc_and_machine_neutral(self):
        r = self.run_main(*self.base())
        ts = datetime.datetime.fromisoformat(r.recipe["timestamp"])
        self.assertIsNotNone(ts.tzinfo)
        self.assertEqual(ts.utcoffset(), datetime.timedelta(0))

    def test_the_recipe_points_at_real_references_never_upload_temp_files(self):
        """Refs are downscaled FOR UPLOAD ONLY. A recipe pointing at a deleted temp
        copy is provenance that cannot be re-run."""
        big = real_png(self.tmp / "big.png", (900, 900))
        r = self.run_main("--prompt", "x", "--ref", big, "--ref-max-edge", "64")
        self.assertEqual(r.recipe_refs, [big])
        self.assertNotEqual(r.uploads, [big], "the reference was not shrunk at all")
        self.assertNotIn("agenticstory-refs-", json.dumps(r.recipe))

    def test_nothing_machine_specific_leaks_into_the_recipe(self):
        """A recipe is read by other people on other machines. It carries the render,
        not the box that ran it."""
        blob = json.dumps(self.run_main(*self.base()).recipe)
        self.assertNotIn(os.path.expanduser("~"), blob, "home directory leaked")
        self.assertNotIn(os.uname().nodename, blob, "hostname leaked")
        for junk in ("OPENAI", "API_KEY", "sk-", "agenticstory-refs-"):
            self.assertNotIn(junk, blob)

    def test_a_failed_generation_writes_no_image_and_no_recipe(self):
        def dead(cmd, *a, **k):
            self.calls.append(list(cmd))
            return types.SimpleNamespace(returncode=1, args=cmd)
        msg = self.expect_exit(*self.base(), runner=dead)
        self.assertIn("no image, no recipe", msg)
        self.assertFalse(os.path.exists(self.out + ".recipe.json"))

    def test_a_provider_that_returns_zero_but_writes_nothing_still_refuses(self):
        def liar(cmd, *a, **k):
            self.calls.append(list(cmd))
            return types.SimpleNamespace(returncode=0, args=cmd)
        msg = self.expect_exit(*self.base(), runner=liar)
        self.assertIn("generation FAILED", msg)
        self.assertFalse(os.path.exists(self.out + ".recipe.json"))

    def _lookbook(self, name="wardrobe", refs=6, **extra):
        """A real lookbook folder on disk. Until v0.28 these tests could not exist,
        because --lookbook never opened anything."""
        d = self.tmp / "books" / name
        names = [f"r{i}.png" for i in range(refs)]
        for n in names:
            png(d / "refs" / n, extra=n.encode())
        body = {"id": name, "kind": "lookbook", "name": name,
                "refs": [f"refs/{n}" for n in names],
                "aesthetic": "quiet luxury, one hero colour",
                "varietyRule": "dress each person differently, never a uniform",
                "gate": ["no two people dressed alike"], "minRefs": 3}
        body.update(extra)
        (d / "lookbook.json").write_text(json.dumps(body))
        return str(d)

    # A lookbook that is merely NAMED in the recipe steers nothing. Each of these
    # asserts one of the three behaviours SPEC 4.7.1 promised from v0.12 and that
    # nothing implemented until v0.28.

    def test_the_lookbooks_aesthetic_and_variety_rule_reach_the_prompt(self):
        r = self.run_main(*self.base("--lookbook", self._lookbook()))
        self.assertIn("quiet luxury, one hero colour", r.prompt)
        self.assertIn("dress each person differently", r.prompt)

    def test_the_lookbooks_negatives_reach_the_prompt(self):
        lb = self._lookbook(negatives=["no kaftans", "no beaded devotional strands"])
        r = self.run_main(*self.base("--lookbook", lb))
        self.assertIn("no kaftans", r.prompt)
        self.assertIn("no beaded devotional strands", r.prompt)

    def test_exemplars_are_actually_passed_as_references(self):
        r = self.run_main(*self.base("--lookbook", self._lookbook()))
        passed = [c for c in r.cmd if c.endswith(".png") and "/refs/" in c]
        self.assertEqual(len(passed), 3, r.cmd)

    def test_the_recipe_records_which_exemplars_were_SAMPLED(self):
        """The name alone does not make a render reproducible; the subset does."""
        r = self.run_main(*self.base("--lookbook", self._lookbook()))
        entry = r.recipe["lookbooks"][0]
        self.assertEqual(entry["id"], "wardrobe")
        self.assertEqual(len(entry["sampled"]), 3)
        self.assertEqual(entry["gate"], ["no two people dressed alike"])

    def test_the_sampled_subset_rotates_across_outputs(self):
        """Asserted over a RUN of outputs, not a single pair.

        Two seeds can legitimately land on the same 3-of-6 subset, and an earlier
        version of this test asserted that any two differ. It passed once and failed
        on the next run when the temp path changed. The honest property is that the
        sampler rotates rather than freezing on one subset; a lookbook that always
        hands over the same three refs is a Style Pack with extra steps.
        """
        lb = self._lookbook()
        seen = set()
        for i in range(8):
            r = self.run_main(*self.base("--lookbook", lb),
                              out=str(self.tmp / f"o/{i}.png"))
            seen.add(tuple(sorted(r.recipe["lookbooks"][0]["sampled"])))
        self.assertGreater(len(seen), 1, "the sampler never varied its subset")

    def test_one_output_path_always_replays_the_same_subset(self):
        """The other half: a recipe must be reproducible."""
        lb = self._lookbook()
        out = str(self.tmp / "o/fixed.png")
        first = self.run_main(*self.base("--lookbook", lb), out=out).recipe
        second = self.run_main(*self.base("--lookbook", lb), out=out).recipe
        self.assertEqual(first["lookbooks"][0]["sampled"],
                         second["lookbooks"][0]["sampled"])

    def test_two_lookbooks_both_apply(self):
        r = self.run_main(*self.base("--lookbook", self._lookbook("a"),
                                     "--lookbook", self._lookbook("b")))
        self.assertEqual({e["id"] for e in r.recipe["lookbooks"]}, {"a", "b"})

    def test_no_wardrobe_skips_it_entirely(self):
        r = self.run_main(*self.base("--lookbook", self._lookbook(), "--no-wardrobe"))
        self.assertNotIn("lookbooks", r.recipe)
        self.assertNotIn("quiet luxury", r.prompt)

    def test_no_lookbook_key_by_default(self):
        self.assertNotIn("lookbooks", self.run_main(*self.base()).recipe)

    def test_no_entities_key_when_no_entity_was_resolved(self):
        self.assertNotIn("entities", self.run_main(*self.base()).recipe)

    def test_the_recipe_is_valid_json_at_rest(self):
        self.run_main(*self.base())
        json.loads(Path(self.out + ".recipe.json").read_text())


# =====================================================================
# 5. resolve_entities refusal paths
# =====================================================================
def build_universe(root, *, entities, asset_root="."):
    """The minimum CanonStore will load: a manifest plus one entity file each."""
    root = Path(root)
    (root / "canon" / "entities").mkdir(parents=True, exist_ok=True)
    (root / "universe.json").write_text(json.dumps({"name": "T", "assetRoot": asset_root}))
    for e in entities:
        (root / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e, indent=2))
    return str(root)


def entity(eid, *, sheets=None, invariants=(), rules="", alt_looks=None, required=None):
    d = {"id": eid, "kind": "character", "status": "locked",
         "structured": {"sheets": dict(sheets or {}),
                        "requiredForRender": list(required if required is not None
                                                  else sorted((sheets or {}).keys())),
                        "invariants": list(invariants)}}
    if alt_looks:
        d["structured"]["altLooks"] = alt_looks
    if rules:
        d["prose"] = {"rules": rules}
    return d


class TestEntityRefusals(GenerateCase):
    """These refusals exist to prevent a plausible picture of the WRONG PERSON.

    A render that proceeds without the subject's locked plates is far more expensive
    than a hard stop, because it PASSES REVIEW. Every case here must refuse.
    """

    def universe(self, *entities, asset_root="."):
        return build_universe(self.tmp / "uni", entities=list(entities), asset_root=asset_root)

    def locked_chip(self):
        u = self.universe(entity(
            "chip",
            sheets={"face": "reference/chip/face.png", "body": "reference/chip/body.png"},
            invariants=["a gold visor", "left-handed"],
            rules="Chip never smiles."))
        png(Path(u) / "reference" / "chip" / "face.png", extra=b"f")
        png(Path(u) / "reference" / "chip" / "body.png", extra=b"b")
        return u

    def test_a_spec_without_a_colon_refuses(self):
        msg = self.expect_exit(*self.base("--entity", "chip"))
        self.assertIn("UNIVERSE:ID", msg)
        self.assertEqual(self.calls, [])

    def test_an_unknown_entity_id_refuses(self):
        u = self.locked_chip()
        msg = self.expect_exit(*self.base("--entity", f"{u}:nobody"))
        self.assertIn("no entity 'nobody'", msg)
        self.assertEqual(self.calls, [])

    def test_an_entity_with_zero_sheets_refuses(self):
        u = self.universe(entity("ghost", sheets={}))
        msg = self.expect_exit(*self.base("--entity", f"{u}:ghost"))
        self.assertIn("ZERO reference sheets", msg)
        self.assertIn("exactly the drift this flag exists to prevent", msg)

    def test_a_sheet_missing_from_disk_refuses_and_names_the_file(self):
        u = self.universe(entity("chip", sheets={"face": "reference/chip/face.png"}))
        msg = self.expect_exit(*self.base("--entity", f"{u}:chip"))
        self.assertIn("locked canon references are MISSING on disk", msg)
        self.assertIn("chip.face -> reference/chip/face.png", msg)
        self.assertIn("look fine and be off-canon", msg)

    def test_every_missing_sheet_is_named_not_just_the_first(self):
        u = self.universe(entity("chip", sheets={"face": "reference/chip/face.png",
                                                 "body": "reference/chip/body.png"}))
        msg = self.expect_exit(*self.base("--entity", f"{u}:chip"))
        self.assertIn("chip.face", msg)
        self.assertIn("chip.body", msg)

    def test_an_unknown_look_refuses(self):
        u = self.locked_chip()
        msg = self.expect_exit(*self.base("--entity", f"{u}:chip@spirit"))
        self.assertIn("has no altLook", msg)

    def test_a_universe_with_no_manifest_refuses_rather_than_rendering(self):
        empty = self.tmp / "not-a-universe"
        empty.mkdir()
        with self.assertRaises((SystemExit, FileNotFoundError)):
            self.run_main(*self.base("--entity", f"{empty}:chip"))
        self.assertEqual(self.calls, [])

    def test_a_resolvable_entity_prepends_its_sheets(self):
        u = self.locked_chip()
        r = self.run_main(*self.base("--entity", f"{u}:chip"))
        self.assertEqual([os.path.basename(p) for p in r.uploads],
                         ["body.png", "face.png"])

    def test_entity_plates_outrank_the_style_pack_anchor(self):
        u = self.locked_chip()
        pack = make_pack(self.tmp, refs=["refs/anchor.png"])
        r = self.run_main(*self.base("--style-pack", pack, "--entity", f"{u}:chip"))
        self.assertEqual([os.path.basename(p) for p in r.uploads],
                         ["body.png", "face.png", "anchor.png"])

    def test_invariants_are_baked_into_the_prompt_as_positives(self):
        u = self.locked_chip()
        r = self.run_main(*self.base("--entity", f"{u}:chip"))
        self.assertIn("These are LOCKED canonical traits", r.prompt)
        self.assertIn("a gold visor; left-handed", r.prompt)

    def test_prose_rules_are_appended(self):
        u = self.locked_chip()
        r = self.run_main(*self.base("--entity", f"{u}:chip"))
        self.assertIn("Chip never smiles.", r.prompt)

    def test_the_resolved_entity_is_recorded_in_the_recipe(self):
        u = self.locked_chip()
        r = self.run_main(*self.base("--entity", f"{u}:chip"))
        meta = r.recipe["entities"]
        self.assertEqual(len(meta), 1)
        self.assertEqual(meta[0]["id"], "chip")
        self.assertIsNone(meta[0]["look"])
        self.assertEqual(sorted(meta[0]["sheets"]), ["body", "face"])

    def test_a_shared_plate_is_passed_once(self):
        shared = "reference/shared/plate.png"
        u = self.universe(entity("a", sheets={"face": shared}),
                          entity("b", sheets={"face": shared}))
        png(Path(u) / shared)
        r = self.run_main(*self.base("--entity", f"{u}:a", "--entity", f"{u}:b"))
        self.assertEqual(len(r.uploads), 1)
        self.assertEqual(len(r.recipe["entities"]), 2)

    def test_a_caller_ref_already_passed_is_not_duplicated_by_canon(self):
        u = self.locked_chip()
        face = os.path.join(u, "reference", "chip", "face.png")
        r = self.run_main(*self.base("--entity", f"{u}:chip", "--ref", face))
        self.assertEqual(r.uploads.count(face), 1)


# =====================================================================
# 6. shrink_ref
# =====================================================================
class TestShrinkRef(unittest.TestCase):
    """An optimization that must never fail a render, and must never flatten alpha:
    a cut-out mark passed as a reference has a transparent background, and putting it
    on white teaches the model a box."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)
        self.dst = self.tmp / "shrunk"
        self.dst.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def test_alpha_is_preserved_as_png(self):
        from PIL import Image
        src = real_png(self.tmp / "mark.png", (800, 800), mode="RGBA")
        got = gen.shrink_ref(src, 64, str(self.dst))
        self.assertTrue(got.endswith(".png"), got)
        with Image.open(got) as im:
            self.assertIn(im.mode, ("RGBA", "LA", "P"))
            self.assertIn("A", im.getbands())

    def test_a_non_alpha_reference_becomes_jpeg(self):
        from PIL import Image
        src = real_png(self.tmp / "plate.png", (800, 800))
        got = gen.shrink_ref(src, 64, str(self.dst))
        self.assertTrue(got.endswith(".jpg"), got)
        with Image.open(got) as im:
            self.assertEqual(im.mode, "RGB")

    def test_the_result_respects_the_max_edge(self):
        from PIL import Image
        src = real_png(self.tmp / "wide.png", (900, 300))
        with Image.open(gen.shrink_ref(src, 100, str(self.dst))) as im:
            self.assertLessEqual(max(im.size), 100)

    def test_an_already_small_image_is_returned_untouched(self):
        src = real_png(self.tmp / "small.png", (32, 32))
        self.assertEqual(gen.shrink_ref(src, 1024, str(self.dst)), src)
        self.assertEqual(os.listdir(self.dst), [])

    def test_an_image_exactly_at_the_limit_is_untouched(self):
        src = real_png(self.tmp / "edge.png", (64, 64))
        self.assertEqual(gen.shrink_ref(src, 64, str(self.dst)), src)

    def test_shrinking_disabled_returns_the_path(self):
        src = real_png(self.tmp / "big.png", (800, 800))
        self.assertEqual(gen.shrink_ref(src, 0, str(self.dst)), src)
        self.assertEqual(gen.shrink_ref(src, 64, None), src)

    def test_missing_pillow_returns_the_path_rather_than_failing_the_render(self):
        src = real_png(self.tmp / "big.png", (800, 800))
        with mock.patch.dict(sys.modules, {"PIL": None, "PIL.Image": None}):
            self.assertEqual(gen.shrink_ref(src, 64, str(self.dst)), src)

    def test_an_undecodable_file_returns_the_path(self):
        junk = self.tmp / "junk.png"
        junk.write_bytes(b"not an image at all")
        self.assertEqual(gen.shrink_ref(str(junk), 64, str(self.dst)), str(junk))

    def test_shrunk_copies_do_not_collide_on_a_shared_stem(self):
        a = real_png(self.tmp / "one" / "plate.png", (800, 800))
        b = real_png(self.tmp / "two" / "plate.png", (700, 700))
        got = [gen.shrink_ref(a, 64, str(self.dst)), gen.shrink_ref(b, 64, str(self.dst))]
        self.assertEqual(len(set(got)), 2, "two references collapsed onto one upload")

    def test_the_original_is_never_modified(self):
        src = real_png(self.tmp / "big.png", (800, 800))
        before = Path(src).read_bytes()
        gen.shrink_ref(src, 64, str(self.dst))
        self.assertEqual(Path(src).read_bytes(), before)


# =====================================================================
# 7. _abu_root
# =====================================================================
class TestAbuRoot(unittest.TestCase):
    """It walks UP for engine/agenticstory instead of counting parents, because the
    script runs from a git clone AND from a plugin cache under ~/.claude/plugins.
    Counting worked in one and failed silently in the other."""

    def test_it_finds_the_root_from_the_scripts_own_location(self):
        root = gen._abu_root()
        self.assertTrue((root / "engine" / "agenticstory").is_dir())

    def test_it_finds_the_root_from_a_deeply_nested_path(self):
        deep = HERE / "a" / "b" / "c" / "d" / "nothing.py"
        self.assertEqual(gen._abu_root(str(deep)), gen._abu_root())

    def test_it_finds_the_root_from_the_root_itself(self):
        root = gen._abu_root()
        self.assertEqual(gen._abu_root(str(root / "README.md")), root)

    def test_it_does_not_count_parents(self):
        """Same answer from two different depths is the whole point of the walk."""
        root = gen._abu_root()
        self.assertEqual(gen._abu_root(str(root / "engine" / "agenticstory" / "x.py")),
                         gen._abu_root(str(root / "x.py")))

    def test_it_raises_a_helpful_systemexit_when_there_is_no_marker(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(SystemExit) as ctx:
                gen._abu_root(os.path.join(t, "deep", "nested", "file.py"))
        msg = str(ctx.exception)
        self.assertIn("cannot locate the ABU root", msg)
        self.assertIn("engine/agenticstory", msg)
        self.assertIn("/plugin marketplace add", msg)


# =====================================================================
# 8. The CLI boundary itself — real child process, no provider ever reached
# =====================================================================
class TestCliRefusals(unittest.TestCase):
    """Every case here exits BEFORE the provider is resolved, so running the real CLI
    costs nothing and touches no network. It proves the refusals are reachable through
    argparse and not merely through main() called in-process."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.tmp = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def cli(self, *args):
        env = dict(os.environ)
        env.pop("OPENAI_API_KEY", None)
        env.pop("GEMINI_API_KEY", None)
        return subprocess.run([sys.executable, str(GENERATE), *[str(a) for a in args]],
                              capture_output=True, text=True, env=env)

    def test_no_prompt_at_all_refuses(self):
        r = self.cli("--out", str(self.tmp / "o.png"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("need --prompt or --prompt-file", r.stderr)

    def test_a_missing_pack_refuses_at_the_cli(self):
        r = self.cli("--out", str(self.tmp / "o.png"), "--prompt", "x",
                     "--style-pack", str(self.tmp / "nope"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("has no pack.json", r.stderr)

    def test_a_bad_permit_refuses_at_the_cli(self):
        pack = make_pack(self.tmp, rejected=["photorealism", "any text"])
        r = self.cli("--out", str(self.tmp / "o.png"), "--prompt", "x",
                     "--style-pack", pack, "--permit", "watercolour")
        self.assertEqual(r.returncode, 1)
        self.assertIn("matched no rejected pole", r.stderr)
        self.assertIn("the pack's poles are: photorealism, any text", r.stderr)
        self.assertFalse(os.path.exists(str(self.tmp / "o.png")))

    def test_a_missing_ref_refuses_at_the_cli(self):
        r = self.cli("--out", str(self.tmp / "o.png"), "--prompt", "x",
                     "--ref", str(self.tmp / "ghost.png"))
        self.assertEqual(r.returncode, 1)
        self.assertIn("ref not found", r.stderr)

    def test_an_entity_without_a_colon_refuses_at_the_cli(self):
        r = self.cli("--out", str(self.tmp / "o.png"), "--prompt", "x", "--entity", "chip")
        self.assertEqual(r.returncode, 1)
        self.assertIn("UNIVERSE:ID", r.stderr)

    def test_the_prompt_file_is_read_from_disk(self):
        """Reaches the ref check, which proves the file was read and became the prompt."""
        pf = self.tmp / "p.txt"
        pf.write_text("a lighthouse at dusk")
        r = self.cli("--out", str(self.tmp / "o.png"), "--prompt-file", str(pf),
                     "--ref", str(self.tmp / "ghost.png"))
        self.assertIn("ref not found", r.stderr)


# =====================================================================
# 9. The stubbed provider boundary is real — a guard on this suite itself
# =====================================================================
class TestSuiteNeverCallsAProvider(GenerateCase):
    def test_the_command_would_have_shelled_out_and_did_not(self):
        r = self.run_main(*self.base())
        self.assertEqual(r.cmd[0], "uv")
        self.assertIn("/nonexistent/never-executed-provider.py", r.cmd)

    def test_the_gpt_path_passes_size_and_quality_and_OPENS_by_default(self):
        """A single render OPENS in Preview. Looking at it is the gate.

        This adapter used to append --no-open unconditionally, so an on-brand render
        finished silently and the operator had to go find the file. Gary: "on brand
        image, the image always opens up in preview... that should just be part of
        the skill." Batch callers opt out; a single render does not have to opt in.
        """
        r = self.run_main(*self.base())
        self.assertIn("--size", r.cmd)
        self.assertIn("--quality", r.cmd)
        self.assertNotIn("--no-open", r.cmd)

    def test_no_open_is_passed_through_when_asked(self):
        """Batch callers must still be able to suppress it, or N renders open N windows."""
        r = self.run_main(*self.base("--no-open"))
        self.assertIn("--no-open", r.cmd)

    def test_the_timeout_is_passed_through_only_when_set(self):
        self.assertNotIn("--timeout", self.run_main(*self.base()).cmd)
        r = self.run_main(*self.base("--timeout", "900"))
        self.assertEqual(r.cmd[r.cmd.index("--timeout") + 1], "900.0")

    def test_the_nano_path_takes_a_different_shape(self):
        r = self.run_main(*self.base("--model", "nano-banana-pro"))
        self.assertIn("--resolution", r.cmd)
        self.assertNotIn("--quality", r.cmd)

    def test_no_api_key_is_ever_read_by_this_module(self):
        """Credentials and HTTP belong to the provider script. This file is an adapter."""
        code = "\n".join(l.split("#", 1)[0] for l in GENERATE.read_text().splitlines())
        for name in ("API_KEY", "os.environ", "os.getenv",
                     "import requests", "import urllib", "http.client", "socket"):
            self.assertNotIn(name, code,
                             f"generate.py touches {name}; the provider script owns that")


if __name__ == "__main__":
    unittest.main(verbosity=1)
