"""A REGISTER-NEUTRAL matrix (SPEC v0.37 §12) — tests.

The deadlock these cover: a photoreal identity master cannot be shot before a register
exists, and it must be, because every register rendition is derived FROM it. Four
behaviours, in the order they bite:

  1. a declared register-neutral entity PLANS AND SHOOTS with a null universe anchor,
     where the shooter previously refused unconditionally
  2. NO ANCHOR IS PASSED, and that stays true after the universe blesses a register
     (the silent re-shoot is the failure mode; a plate cannot be un-baked)
  3. `--register` / `--no-style-pack` are REFUSED here, because both name WHICH anchor
     and neither can name none
  4. the refusal on a null anchor with NO declaration teaches the route

Run:  python3 -m unittest discover -s tests   (from the shoot-references skill dir)
"""
import argparse as _ap
import importlib.util
import json
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path

from PIL import Image

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
CHAIN = SCRIPTS / "chain_matrix.py"

MEDIUM = "hyper-realistic documentary photography"
WHY = "one photoreal master; every register is a conversion of it"


def png(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (8, 8), (180, 160, 120)).save(path)


def build(root: Path, neutral=True, anchor=None):
    """A universe with NO blessed register (anchor=None), and one character whose
    matrix is the identity master. `anchor` set makes it a universe that HAS since
    blessed a register, which is case 2."""
    (root / "canon" / "entities").mkdir(parents=True)
    register = {"name": "field-log editorial", "anchor": anchor,
                "rejectedPoles": ["posed stock-photo", "AI-glossy airbrush"]}
    if anchor:
        png(root / anchor)
    (root / "universe.json").write_text(json.dumps({
        "name": "testverse", "assetRoot": ".", "identity": {"register": register}}))
    structured = {"sheets": {}, "invariants": []}
    if neutral:
        structured["registerNeutral"] = {"medium": MEDIUM, "why": WHY}
    (root / "canon" / "entities" / "russ.json").write_text(json.dumps({
        "id": "russ", "kind": "character", "structured": structured}))
    md = "# russ prompts\n\n"
    for s in ("face-neutral", "face-3q", "forward-fullbody"):
        md += f"## {s} → `reference/russ/{s}.png`\nA photographic {s} plate of the man.\n\n"
    (root / "reference" / "russ").mkdir(parents=True, exist_ok=True)
    (root / "reference" / "russ" / "prompts.md").write_text(md)
    return root


def run(root: Path, *extra):
    return subprocess.run([sys.executable, str(CHAIN), str(root), "russ", *extra],
                          capture_output=True, text=True)


def load_module():
    spec = importlib.util.spec_from_file_location("cm_rn", CHAIN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestRegisterNeutralPlan(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = build(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_it_plans_at_all_with_a_null_register_anchor(self):
        """The whole deadlock. Before v0.37 this returned 2 with 'the universe style is
        not locked; do not generate' and there was no way through it."""
        r = run(self.root, "--print-plan")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("REGISTER-NEUTRAL", r.stdout)
        self.assertIn(MEDIUM, r.stdout)
        self.assertIn(WHY, r.stdout)
        self.assertIn("seed (hero) = forward-fullbody", r.stdout)

    def test_the_plan_never_advertises_an_anchor_it_will_not_pass(self):
        r = run(self.root, "--print-plan")
        line = [l for l in r.stdout.splitlines() if "2. face-neutral" in l][0]
        self.assertIn("no anchor (register-neutral)", line)

    def test_the_register_poles_are_not_baked_as_negatives(self):
        """A pole is the opposite of a medium this matrix is not being shot in. On POV
        the top pole would be the register's own documentary photography, which is what
        the master IS."""
        m = load_module()
        plan = m.build_plan(self.root, "russ")
        self.assertIsNone(plan["anchor"])
        self.assertEqual(plan["poles"], [])
        self.assertEqual(plan["negatives"], [])
        self.assertEqual(plan["registerNeutral"]["medium"], MEDIUM)
        self.assertIn(MEDIUM, plan["styleLine"])
        self.assertIn("REGISTER-NEUTRAL", plan["styleLine"])


class TestNoAnchorIsPassed(unittest.TestCase):
    """The non-obvious half: neutral means no anchor is PASSED, not 'not required'."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def _shoot_and_capture(self, root):
        m = load_module()
        m._provider_script = lambda provider="gpt-image-2": "/dev/null/fake-provider.py"
        seen = {}

        def fake_run(cmd, *a, **kw):
            seen["inputs"] = [cmd[i + 1] for i, c in enumerate(cmd) if c == "--input-image"]
            seen["prompt"] = cmd[cmd.index("--prompt") + 1]
            out = Path(cmd[cmd.index("--filename") + 1])
            Image.new("RGB", (8, 8), (10, 20, 30)).save(out)
            return types.SimpleNamespace(returncode=0)

        m.subprocess = types.SimpleNamespace(run=fake_run)
        plan = m.build_plan(root, "russ")
        args = _ap.Namespace(size="1024x1024", max_conditioning=4, star=False)
        anchor_abs = str((root / plan["anchor"]).resolve()) if plan["anchor"] else None
        rc = m._shoot(plan, "face-neutral", [], args, anchor_abs, "", plan["refdir"], root)
        self.assertEqual(rc, 0)
        return seen, plan

    def test_the_provider_receives_no_anchor_image(self):
        root = build(Path(self.tmp.name))
        seen, _ = self._shoot_and_capture(root)
        self.assertEqual(seen["inputs"], [],
                         "a register-neutral shoot passes no style anchor at all")
        self.assertIn(MEDIUM, seen["prompt"])
        self.assertNotIn("field-log editorial", seen["prompt"])

    def test_it_still_passes_none_after_the_universe_blesses_a_register(self):
        """THE RE-SHOOT. This is why the declaration is canon and not a flag: months
        later the universe HAS an anchor, and a re-shoot must still refuse to bake it
        into the master."""
        root = build(Path(self.tmp.name), anchor="reference/register/anchor.png")
        seen, plan = self._shoot_and_capture(root)
        self.assertIsNone(plan["anchor"])
        self.assertEqual(seen["inputs"], [])

    def test_the_recipe_states_the_absence_rather_than_omitting_it(self):
        root = build(Path(self.tmp.name))
        _, plan = self._shoot_and_capture(root)
        rec = json.loads((plan["refdir"] / "face-neutral.png.recipe.json").read_text())
        self.assertIsNone(rec["anchor"])
        self.assertEqual(rec["registerNeutral"]["medium"], MEDIUM)
        self.assertEqual(rec["registerNeutral"]["why"], WHY)


class TestRefusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def test_register_override_is_refused(self):
        root = build(Path(self.tmp.name))
        r = run(root, "--register", "some-pack", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("REGISTER-NEUTRAL", r.stderr)
        self.assertIn("--register", r.stderr)

    def test_no_style_pack_is_refused(self):
        root = build(Path(self.tmp.name))
        r = run(root, "--no-style-pack", "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("--no-style-pack", r.stderr)

    def test_a_malformed_declaration_refuses_rather_than_shooting_in_register(self):
        """FAIL CLOSED. Falling back to None here would silently shoot the master
        against the register anchor, which is the outcome the field exists to forbid."""
        root = build(Path(self.tmp.name), anchor="reference/register/anchor.png")
        p = root / "canon" / "entities" / "russ.json"
        e = json.loads(p.read_text())
        e["structured"]["registerNeutral"] = True
        p.write_text(json.dumps(e))
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("must be an OBJECT", r.stderr)

    def test_a_declaration_with_no_medium_refuses(self):
        root = build(Path(self.tmp.name))
        p = root / "canon" / "entities" / "russ.json"
        e = json.loads(p.read_text())
        e["structured"]["registerNeutral"] = {"why": WHY}
        p.write_text(json.dumps(e))
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("declares no `medium`", r.stderr)

    def test_the_null_anchor_refusal_teaches_the_route(self):
        """An undeclared entity in a register-less universe still refuses, and the
        refusal must name the way out the same way its sibling names --register."""
        root = build(Path(self.tmp.name), neutral=False)
        r = run(root, "--print-plan")
        self.assertEqual(r.returncode, 2)
        self.assertIn("registerNeutral", r.stderr)
        self.assertIn("medium", r.stderr)

    def test_an_undeclared_entity_is_unaffected(self):
        """Backward compatibility, stated as a test: no declaration, no change."""
        root = build(Path(self.tmp.name), neutral=False,
                     anchor="reference/register/anchor.png")
        m = load_module()
        plan = m.build_plan(root, "russ")
        self.assertEqual(plan["anchor"], "reference/register/anchor.png")
        self.assertIsNone(plan["registerNeutral"])
        self.assertEqual(plan["poles"], ["posed stock-photo", "AI-glossy airbrush"])


if __name__ == "__main__":
    unittest.main()
