"""verify_render — the readback that used to be two pasted one-liners.

Every check here corresponds to a silent failure that reached a human's eyes: a bypassed
binding (four times), a pure-black frame (twice), and a "binding test" whose scene text
named the garment, which proves nothing at all.
"""
import importlib.util
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_SCRIPT = _HERE.parent / "scripts" / "verify_render.py"
_spec = importlib.util.spec_from_file_location("verify_render", _SCRIPT)
vr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vr)


def png(path: Path, *, black=False):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (4, 4), (0, 0, 0) if black else (200, 180, 160)).save(path)
    return str(path)


def recipe(path: Path, *, entities=None, prompt=None):
    if prompt is None:
        prompt = ("A scene. These are LOCKED canonical traits: a gold visor."
                  if entities else "A scene with nobody in it.")
    body = {"prompt": prompt}
    if entities is not None:
        body["entities"] = entities
    Path(str(path) + ".recipe.json").write_text(json.dumps(body))


def ent(eid, look=None, sheets=2, photos=0):
    return {"id": eid, "look": look,
            "sheets": {f"s{i}": f"{i}.png" for i in range(sheets)},
            "photoStackDeclared": [], "photoStackPassed": ["p.png"] * photos}


class VerifyRender(unittest.TestCase):
    def setUp(self):
        self.d = Path(tempfile.mkdtemp(prefix="abu-vr-"))
        self.addCleanup(shutil.rmtree, self.d, True)

    def run_it(self, *args):
        """Returns (exit_code, stderr_text)."""
        import io
        from contextlib import redirect_stderr, redirect_stdout
        err, out = io.StringIO(), io.StringIO()
        with redirect_stderr(err), redirect_stdout(out):
            code = vr.main(list(args))
        return code, err.getvalue()

    def good(self, name="a.png", **kw):
        p = Path(png(self.d / name))
        recipe(p, entities=[ent("selah", "wedding-dress")], **kw)
        return str(p)

    # --- the happy path must actually pass, or the gate gets disabled ------
    def test_a_correct_render_passes(self):
        code, _ = self.run_it(self.good())
        self.assertEqual(code, 0)

    def test_several_files_at_once(self):
        code, _ = self.run_it(self.good("a.png"), self.good("b.png"))
        self.assertEqual(code, 0)

    # --- recipe --------------------------------------------------------
    def test_a_missing_recipe_fails_and_names_the_cause(self):
        p = png(self.d / "orphan.png")
        code, err = self.run_it(p)
        self.assertEqual(code, 1)
        self.assertIn("NO RECIPE", err)
        self.assertIn("Never call a provider directly", err)

    def test_a_missing_file_fails(self):
        code, err = self.run_it(str(self.d / "nope.png"))
        self.assertEqual(code, 1)
        self.assertIn("NOT ON DISK", err)

    # --- invariants ----------------------------------------------------
    def test_entities_without_the_invariant_block_fail(self):
        """The signature of a hand-assembled prompt: it looks fine and is off-canon."""
        p = Path(png(self.d / "a.png"))
        recipe(p, entities=[ent("selah")], prompt="A scene, hand written, no canon.")
        code, err = self.run_it(str(p))
        self.assertEqual(code, 1)
        self.assertIn("invariant block is MISSING", err)

    def test_no_entities_means_the_invariant_check_does_not_apply(self):
        """A render with no people in it is not required to carry an entity block."""
        p = Path(png(self.d / "a.png"))
        recipe(p, entities=[], prompt="An empty room.")
        self.assertEqual(self.run_it(str(p))[0], 0)

    # --- binding -------------------------------------------------------
    def test_expecting_a_look_that_is_bound_passes(self):
        code, _ = self.run_it(self.good(), "--expect", "selah@wedding-dress")
        self.assertEqual(code, 0)

    def test_a_BARE_entity_does_not_satisfy_an_expected_LOOK(self):
        """THE FOUR-TIME BUG. `--entity selah` where `selah@wedding-dress` was meant is
        silent, and produced a fitted trumpet where an A-line was blessed. Matching on the
        id alone would let exactly that through."""
        p = Path(png(self.d / "a.png"))
        recipe(p, entities=[ent("selah", None)])
        code, err = self.run_it(str(p), "--expect", "selah@wedding-dress")
        self.assertEqual(code, 1)
        self.assertIn("expected entity 'selah@wedding-dress'", err)

    def test_the_wrong_look_fails(self):
        code, err = self.run_it(self.good(), "--expect", "selah@usa-flag-dress")
        self.assertEqual(code, 1)
        self.assertIn("usa-flag-dress", err)

    def test_a_missing_second_entity_fails(self):
        code, err = self.run_it(self.good(), "--expect", "selah@wedding-dress",
                                "--expect", "gary@wedding-suit")
        self.assertEqual(code, 1)
        self.assertIn("gary@wedding-suit", err)

    # --- dead frame ----------------------------------------------------
    def test_a_pure_black_render_fails(self):
        p = Path(png(self.d / "dead.png", black=True))
        recipe(p, entities=[ent("selah")])
        code, err = self.run_it(str(p))
        self.assertEqual(code, 1)
        self.assertIn("DEAD FRAME", err)

    def test_a_dead_frame_is_caught_even_with_no_recipe(self):
        """It is a fact about the image and does not depend on provenance."""
        code, err = self.run_it(png(self.d / "dead.png", black=True))
        self.assertEqual(code, 1)
        self.assertIn("DEAD FRAME", err)
        self.assertIn("NO RECIPE", err)

    # --- the binding test ----------------------------------------------
    def test_a_scene_naming_a_garment_fails(self):
        code, err = self.run_it(self.good(), "--scene",
                                "She stands on the steps in an ivory lace gown, laughing.")
        self.assertEqual(code, 1)
        self.assertIn("cannot prove the look is BOUND", err)
        for w in ("gown", "lace"):
            self.assertIn(w, err)

    def test_a_clean_scene_passes(self):
        code, _ = self.run_it(self.good(), "--scene",
                              "She stands at the top of a sunlit stone staircase, laughing.")
        self.assertEqual(code, 0)

    def test_forbid_overrides_the_default_vocabulary(self):
        """Only the caller knows this look's hero words, so the list must be replaceable."""
        code, err = self.run_it(self.good(), "--scene", "A quiet room with a cummerbund.",
                                "--forbid", "cummerbund,capelet")
        self.assertEqual(code, 1)
        self.assertIn("cummerbund", err)

    def test_the_scene_check_is_case_insensitive(self):
        code, err = self.run_it(self.good(), "--scene", "She wears a GOWN.")
        self.assertEqual(code, 1)
        self.assertIn("gown", err)

    def test_the_scene_is_reported_once_not_once_per_file(self):
        """A batch shares one scene; reporting it N times buries the other problems."""
        code, err = self.run_it(self.good("a.png"), self.good("b.png"),
                                "--scene", "in a lace gown")
        self.assertEqual(code, 1)
        self.assertEqual(err.count("cannot prove the look is BOUND"), 1)


if __name__ == "__main__":
    unittest.main()
