#!/usr/bin/env python3
"""strip.py: a strip is a spec, panels are judged one roll at a time, and the composite's recipe
passes a wiki's provenance gate by construction (SPEC v0.53, §4.15).

What is load-bearing:

  * a spec is refused before any render when it cannot make an honest strip: 2 to 4 panels, a
    beat and a scene and entities on every panel, refs that resolve, widths that fill the canvas;
  * a roll is judged before the next one starts, a DEFECT needs a reason, the reject is MOVED
    (never deleted) into panels/rejected/ with a `.reject.json`, and its counter binds every
    later roll of that panel;
  * the cap holds: the first roll plus `maxRerolls`, then a refusal, never a silent extra roll;
  * a PASS is refused while the binding check reports anything, including an unjudged guard;
  * compose refuses until every panel is kept, draws gutters and no borders, and writes ONE
    recipe that the wiki gate's rules accept, with every panel's exact prompt and every ref at
    the top level; each required field is MUTATION-CHECKED: delete it and the recipe is refused;
  * the exported WebP carries the recipe restated for where it will sit in the wiki;
  * when the real wiki gate is on this machine, it is run against the export too.

No network, no API key, no image model: generate.py is replaced by a runner that paints a flat
PNG and writes a recipe in the adapter's shape, and the binding check is stubbed per test.
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from PIL import Image

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "strip.py"
spec_ = importlib.util.spec_from_file_location("strip", SCRIPT)
strip = importlib.util.module_from_spec(spec_)
spec_.loader.exec_module(strip)

COLOURS = {"p1": (200, 40, 40), "p2": (40, 200, 40), "p3": (40, 40, 200), "p4": (200, 200, 40)}


def fake_generate(cmd):
    """Stand-in for generate.py: a flat 1024x1536 PNG and an adapter-shaped recipe."""
    out = Path(cmd[cmd.index("--out") + 1])
    prompt = Path(cmd[cmd.index("--prompt-file") + 1]).read_text().strip()
    pid = out.name.split(".")[0]
    Image.new("RGB", (1024, 1536), COLOURS.get(pid, (90, 90, 90))).save(out)
    refs = [{"path": cmd[i + 1]} for i, a in enumerate(cmd) if a == "--ref"]
    ents = [cmd[i + 1] for i, a in enumerate(cmd) if a == "--entity"]
    Path(str(out) + ".recipe.json").write_text(json.dumps({
        "provider": "gpt-image-2.5-sunburst", "model": "gpt-image-2.5-sunburst",
        "prompt": prompt, "specVersion": "0.6",
        "refs": refs + [{"path": f"/u/reference/{e.split(':')[-1]}/hero.png"} for e in ents],
        "timestamp": "2026-09-25T00:00:00+00:00", "sha256": "x", "entities": ents}))
    return SimpleNamespace(returncode=0)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.uni = self.tmp / "uni"
        (self.uni / "reference" / "lens").mkdir(parents=True)
        (self.uni / "universe.json").write_text('{"name": "test"}')
        Image.new("RGB", (8, 8)).save(self.uni / "reference" / "lens" / "hero.png")
        self.work = self.uni / "works" / "2026-09-25-wiki-hero-x"
        self.work.mkdir(parents=True)
        self.verify_result = (True, [])
        self._verify = strip.verify
        strip.verify = lambda spec, p, png, guards=None: self.verify_result

    def tearDown(self):
        strip.verify = self._verify
        shutil.rmtree(self.tmp)

    def write_spec(self, **over):
        doc = {
            "id": "x", "universe": "../..", "out": "x.png",
            "promptBlocks": {"medium": "MEDIUM: film.", "clean": "No text."},
            "maxRerolls": 2,
            "panels": [
                {"id": f"p{i}", "beat": f"beat {i}", "world": "real-room" if i == 1 else "agentspace",
                 "blocks": ["medium", "scene", "clean"], "entities": ["witney"],
                 "refs": ["reference/lens/hero.png"], "scene": f"scene {i}"}
                for i in (1, 2, 3)],
        }
        doc.update(over)
        p = self.work / "strip.json"
        p.write_text(json.dumps(doc))
        return p

    def spec(self, **over):
        return strip.load_spec(self.write_spec(**over))

    def keep_all(self, s):
        for p in s["panels"]:
            strip.cmd_render(s, p["id"], runner=fake_generate)
            strip.cmd_judge(s, p["id"], 1, "pass")


class SpecTest(Base):
    def test_panel_count_is_two_to_four(self):
        panels = json.loads(self.write_spec().read_text())["panels"]
        for n in (1, 5):
            with self.assertRaisesRegex(strip.StripError, "2 to 4 panels"):
                self.spec(panels=(panels * 2)[:n])

    def test_every_panel_needs_beat_scene_entities(self):
        for key in ("beat", "scene", "entities"):
            panels = json.loads(self.write_spec().read_text())["panels"]
            del panels[1][key]
            with self.assertRaisesRegex(strip.StripError, key):
                self.spec(panels=panels)

    def test_missing_ref_and_unknown_block_refused(self):
        panels = json.loads(self.write_spec().read_text())["panels"]
        panels[0]["refs"] = ["reference/nope.png"]
        with self.assertRaisesRegex(strip.StripError, "does not resolve"):
            self.spec(panels=panels)
        panels[0]["refs"] = []
        panels[0]["blocks"] = ["medium", "vibes"]
        with self.assertRaisesRegex(strip.StripError, "vibes"):
            self.spec(panels=panels)

    def test_widths_must_fill_the_canvas(self):
        panels = json.loads(self.write_spec().read_text())["panels"]
        for p, w in zip(panels, (450, 500, 500)):
            p["width"] = w
        with self.assertRaisesRegex(strip.StripError, "sum to 1450"):
            self.spec(panels=panels)
        panels[2]["width"] = 522
        self.assertEqual(strip.panel_widths(self.spec(panels=panels)), [450, 500, 522])

    def test_equal_split_fills_exactly(self):
        s = self.spec()
        self.assertEqual(sum(strip.panel_widths(s)), 1536 - 32 - 32)


class PromptTest(Base):
    def test_blocks_in_order_scene_where_declared_counters_last(self):
        s = self.spec()
        text = strip.assemble_prompt(s, s["panels"][1], ["Her watch is on the LEFT wrist."])
        order = [text.index(x) for x in ("MEDIUM: film.", "PANEL 2 OF A 3-PANEL STRIP: beat 2",
                                          "SCENE: scene 2", "No text.", "LEFT wrist")]
        self.assertEqual(order, sorted(order))

    def test_generate_cmd_uses_the_entity_route(self):
        s = self.spec()
        cmd = strip.generate_cmd(s, s["panels"][0], Path("/o.png"), Path("/o.txt"))
        self.assertIn(f"{s['_universe']}:witney", cmd)
        self.assertIn("--no-wardrobe", cmd)
        self.assertIn(str(s["_universe"] / "reference/lens/hero.png"), cmd)


class RollTest(Base):
    def test_defect_moves_reject_with_reason_and_counter_binds_next_roll(self):
        s = self.spec()
        strip.cmd_render(s, "p1", runner=fake_generate)
        with self.assertRaisesRegex(strip.StripError, "needs --reason"):
            strip.cmd_judge(s, "p1", 1, "defect")
        strip.cmd_judge(s, "p1", 1, "defect", "watch on right wrist", "The watch is on her LEFT wrist.")
        rej = self.work / "panels" / "rejected"
        self.assertTrue((rej / "p1.r1.png").exists())
        self.assertTrue((rej / "p1.r1.png.recipe.json").exists())
        self.assertEqual(json.loads((rej / "p1.r1.png.reject.json").read_text())["reason"],
                         "watch on right wrist")
        self.assertFalse((self.work / "panels" / "p1.r1.png").exists())
        strip.cmd_render(s, "p1", runner=fake_generate)
        self.assertIn("LEFT wrist", (self.work / "panels" / "p1.r2.prompt.txt").read_text())

    def test_unjudged_roll_blocks_the_next(self):
        s = self.spec()
        strip.cmd_render(s, "p1", runner=fake_generate)
        with self.assertRaisesRegex(strip.StripError, "has not been judged"):
            strip.cmd_render(s, "p1", runner=fake_generate)

    def test_cap_is_first_roll_plus_max_rerolls(self):
        s = self.spec()  # maxRerolls 2 -> 3 rolls
        for n in (1, 2, 3):
            strip.cmd_render(s, "p1", runner=fake_generate)
            strip.cmd_judge(s, "p1", n, "defect", f"bad {n}")
        with self.assertRaisesRegex(strip.StripError, "used all 3 rolls"):
            strip.cmd_render(s, "p1", runner=fake_generate)
        self.assertIn("EXHAUSTED", strip.cmd_plan(s)["panels"][0]["next"])

    def test_pass_refused_while_verify_reports_anything(self):
        s = self.spec()
        strip.cmd_render(s, "p1", runner=fake_generate)
        self.verify_result = (True, ["guard 'device-anatomy' FIRED on this render and has no recorded verdict"])
        with self.assertRaisesRegex(strip.StripError, "cannot PASS"):
            strip.cmd_judge(s, "p1", 1, "pass")
        self.verify_result = (True, [])
        strip.cmd_judge(s, "p1", 1, "pass")
        with self.assertRaisesRegex(strip.StripError, "already kept"):
            strip.cmd_render(s, "p1", runner=fake_generate)

    def test_reopen_rejects_the_kept_roll_and_restarts_the_cap(self):
        s = self.spec()
        for n in (1, 2):
            strip.cmd_render(s, "p1", runner=fake_generate)
            strip.cmd_judge(s, "p1", n, "defect" if n == 1 else "pass", "bad" if n == 1 else "")
        strip.cmd_reopen(s, "p1", "Gary: her face is too dark")
        self.assertTrue((self.work / "panels" / "rejected" / "p1.r2.png").exists())
        for n in (3, 4, 5):  # three fresh rolls after a person's reopen
            strip.cmd_render(s, "p1", runner=fake_generate)
            strip.cmd_judge(s, "p1", n, "defect", "bad")
        with self.assertRaisesRegex(strip.StripError, "used all"):
            strip.cmd_render(s, "p1", runner=fake_generate)

    def test_binding_pending_guard_is_not_broken(self):
        strip.verify = self._verify
        s = self.spec()
        calls = []

        def fake_run(cmd, capture_output, text):
            calls.append(cmd)
            return SimpleNamespace(returncode=1, stderr=(
                "verify-render: 1 problem(s):\n  - x.png: guard 'no-ui-chrome' FIRED on this "
                "render and has no recorded verdict. Look\n"))
        orig = strip.subprocess.run
        strip.subprocess.run = fake_run
        try:
            ok, problems = strip.verify(s, s["panels"][0], Path("x.png"))
        finally:
            strip.subprocess.run = orig
        self.assertTrue(ok)
        self.assertEqual(len(problems), 1)
        self.assertIn("--expect", calls[0])


class ComposeTest(Base):
    def test_refuses_until_every_panel_is_kept(self):
        s = self.spec()
        strip.cmd_render(s, "p1", runner=fake_generate)
        strip.cmd_judge(s, "p1", 1, "pass")
        with self.assertRaisesRegex(strip.StripError, "p2, p3"):
            strip.cmd_compose(s)

    def test_canvas_gutters_and_panels(self):
        s = self.spec()
        self.keep_all(s)
        res = strip.cmd_compose(s)
        im = Image.open(res["out"]).convert("RGB")
        self.assertEqual(im.size, (1536, 1024))
        cream = (0xF0, 0xEC, 0xE5)
        w = strip.panel_widths(s)
        self.assertEqual(im.getpixel((5, 500)), cream)                 # outer margin
        self.assertEqual(im.getpixel((16 + w[0] + 8, 500)), cream)     # first gutter
        self.assertEqual(im.getpixel((16 + 10, 500)), COLOURS["p1"])   # panel 1, no border
        self.assertEqual(im.getpixel((1536 - 30, 500)), COLOURS["p3"])

    def test_recipe_passes_the_gate_rules_and_carries_everything(self):
        s = self.spec()
        self.keep_all(s)
        res = strip.cmd_compose(s)
        r = json.loads(Path(res["recipe"]).read_text())
        self.assertEqual(r["asset"], "works/2026-09-25-wiki-hero-x/x.png")
        self.assertEqual(strip.validate_recipe(r, "x.png"), [])
        self.assertEqual(strip.completeness(r), [])
        for pid in ("p1", "p2", "p3"):
            self.assertIn(r["panelRecipes"][pid]["prompt"], r["prompt"])
        self.assertEqual(r["panels"][0]["rolls"], 1)
        self.assertIsNone(r["compose"]["borders"])

    def test_every_required_field_is_mutation_checked(self):
        s = self.spec()
        self.keep_all(s)
        good = json.loads(Path(strip.cmd_compose(s)["recipe"]).read_text())

        def refused(r):
            return strip.validate_recipe(r, "x.png") + strip.completeness(r)

        self.assertEqual(refused(good), [])
        for k in ("asset", "prompt", "model", "provider", "timestamp", "compositor", "sha256",
                  "refs", "panelRecipes"):
            r = json.loads(json.dumps(good))
            del r[k]
            self.assertTrue(refused(r), f"deleting `{k}` was not refused")
        r = json.loads(json.dumps(good))
        r["prompt"] = r["prompt"].replace(r["panelRecipes"]["p2"]["prompt"], "")
        self.assertTrue(any("p2" in x for x in refused(r)), "a dropped panel prompt passed")
        r = json.loads(json.dumps(good))
        r["refs"] = []
        for part in r["panelRecipes"].values():
            part["refs"] = []
        self.assertTrue(refused(r), "an empty top-level refs list passed")
        r = json.loads(json.dumps(good))
        r["refs"] = r["refs"][:1]
        self.assertTrue(any("missing from the top-level" in x for x in refused(r)))
        for k in ("model", "prompt", "timestamp"):
            r = json.loads(json.dumps(good))
            del r["panelRecipes"]["p1"][k]
            if k == "model":
                del r["panelRecipes"]["p1"]["provider"]
            self.assertTrue(any(x.startswith("part p1") for x in refused(r)), f"part without {k} passed")
        r = json.loads(json.dumps(good))
        r["asset"] = "works/other.png"
        self.assertTrue(any("claims asset" in x for x in refused(r)))

    def test_export_restates_the_recipe_for_the_wiki(self):
        s = self.spec()
        self.keep_all(s)
        dest = self.tmp / "wiki" / "static" / "img" / "illustrations" / "x.webp"
        res = strip.cmd_compose(s, str(dest), "static/img/illustrations/x.webp")
        r = json.loads(Path(res["export"]["recipe"]).read_text())
        self.assertEqual(r["asset"], "static/img/illustrations/x.webp")
        self.assertEqual(r["sha256"], strip._sha(dest))
        self.assertIn("webp q82", r["derived"]["op"])
        self.assertEqual(strip.validate_recipe(r, "static/img/illustrations/x.webp"), [])
        with Image.open(dest) as im:
            self.assertEqual(max(im.size), 1536)

    def test_real_wiki_gate_when_present(self):
        # Point ABU_WIKI_PROVENANCE_GATE at a wiki's check-image-provenance.mjs (it ships in
        # @supersuit/docusaurus-preset-wiki under src/cli/) to run the real gate here.
        gate = os.environ.get("ABU_WIKI_PROVENANCE_GATE")
        if not gate or not Path(gate).exists() or not shutil.which("node"):
            self.skipTest("set ABU_WIKI_PROVENANCE_GATE to run the real wiki gate")
        s = self.spec()
        self.keep_all(s)
        wiki = self.tmp / "wiki"
        dest = wiki / "static" / "img" / "illustrations" / "x.webp"
        strip.cmd_compose(s, str(dest), "static/img/illustrations/x.webp")
        r = subprocess.run(["node", gate, str(wiki)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rec = Path(str(dest) + ".recipe.json")
        bad = json.loads(rec.read_text())
        del bad["panelRecipes"]["p1"]["prompt"]
        rec.write_text(json.dumps(bad))
        r = subprocess.run(["node", gate, str(wiki)], capture_output=True, text=True)
        self.assertEqual(r.returncode, 1, "the real gate accepted a panel with no prompt")


class StageTest(Base):
    def test_stage_writes_the_manifest_and_opens_the_board(self):
        s = self.spec(title="X", argues="the argument")
        self.keep_all(s)
        strip.cmd_compose(s)
        seen = []

        def runner(cmd, capture_output, text):
            seen.append(cmd)
            return SimpleNamespace(returncode=0, stdout='{"phone": "https://x"}', stderr="")
        man = self.work / "heroes.json"
        res = strip.cmd_stage(s, man, "wiki-heroes", "Wiki heroes", None, mount=False, runner=runner)
        items = json.loads(man.read_text())["items"]
        self.assertEqual(items[0]["context"], "the argument")
        self.assertEqual(items[0]["kind"], "strip")
        self.assertIn("--no-mount", seen[0])
        self.assertEqual(res["board"]["phone"], "https://x")
        strip.cmd_stage(s, man, "wiki-heroes", "Wiki heroes", "new line", mount=False, runner=runner)
        items = json.loads(man.read_text())["items"]
        self.assertEqual(len(items), 1, "restaging duplicated the item")
        self.assertEqual(items[0]["context"], "new line")


if __name__ == "__main__":
    unittest.main()
