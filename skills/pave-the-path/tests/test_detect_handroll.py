"""pave-the-path detect_handroll.py — tests. Stdlib unittest, no network.

Every case writes a scratchpad file that reproduces a REAL hand-roll from a real
run, and asserts the detector both catches it and NAMES THE VERB that owns it.

Naming the verb is the point. `contact_sheet.py` was promoted into
`render-readback` on 2026-07-30 with a docstring recording that the same PIL
montage had been hand-rolled ten times in one session, and it was hand-rolled
again the next day in a session that had the tool installed. Reporting the fact
of a hand-roll is not enough; a tool nobody can find is a tool nobody has.

The counterweight is `test_a_legitimate_driver_is_not_flagged`: a detector that
cries wolf gets ignored, which is the same failure as a doctor that always fails.

Run:  python3 tests/test_detect_handroll.py
"""
import importlib.util
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
_s = importlib.util.spec_from_file_location(
    "detect_handroll", HERE.parent / "scripts" / "detect_handroll.py")
det = importlib.util.module_from_spec(_s)
_s.loader.exec_module(det)


def scan(**files):
    with tempfile.TemporaryDirectory() as t:
        for name, body in files.items():
            (Path(t) / name).write_text(body)
        return "\n".join(det.scan_scratchpad(Path(t)))


class TestSignatures(unittest.TestCase):

    def test_provider_call_names_shoot_references(self):
        """shoot_hagin.py / shoot_places.py / shoot_people.py, 2026-07-31."""
        out = scan(**{"shoot.py": 'cmd = ["uv","run", GEN/"generate_image.py"]'})
        self.assertIn("provider generate script", out)
        self.assertIn("shoot-references", out)

    def test_hardcoded_register_names_canon(self):
        out = scan(**{"s.py": 'R = "SOFT PAINTERLY STORYBOOK REALISM: ..."'})
        self.assertIn("register/style line", out)
        self.assertIn("identity.register", out)

    def test_hand_written_render_spec_names_compose_spec(self):
        """build_spec.py, 2026-07-31: 48KB of hand-written render-spec, while
        abu:compose-spec already did exactly this and was simply not reached for."""
        out = scan(**{"build_spec.py":
                      'OUT = B / "render-spec.json"\n'
                      'OUT.write_text(json.dumps(spec, indent=2))'})
        self.assertIn("render-spec.json by hand", out)
        self.assertIn("compose-spec", out)

    def test_pil_contact_sheet_names_the_tool_that_already_exists(self):
        """contact.py, 2026-07-31, one day after contact_sheet.py was promoted."""
        out = scan(**{"contact.py":
                      "from PIL import Image, ImageDraw\n"
                      "def build(names, out):\n"
                      "    sheet = Image.new('RGB', (w, h))\n"})
        self.assertIn("contact sheet", out)
        self.assertIn("contact_sheet.py", out)

    def test_render_spread_driver_names_the_batch_mode(self):
        """render.py, 2026-07-31, and the same driver one book earlier."""
        out = scan(**{"render.py":
                      'RS = ABU / "skills/compose-spread/scripts/render_spread.py"\n'
                      'subprocess.run([sys.executable, str(RS), U, SPEC, sid])'})
        self.assertIn("drives render_spread.py", out)
        self.assertIn("--jobs", out)

    def test_inline_massing_spec_names_the_scaffolder(self):
        """make_massing.py, 2026-07-31: four rooms, the same boilerplate each time."""
        out = scan(**{"make_massing.py":
                      "def room(w,d,h):\n    return [quad(...)]\n"
                      'spec = {"solids": room(3,3,2.4), "cameras": [{"id":"c1"}]}'})
        self.assertIn("massing spec inline", out)
        self.assertIn("massing-scaffold", out)

    # ── the counterweight ────────────────────────────────────────────────────

    def test_a_legitimate_driver_is_not_flagged(self):
        """Merely READING a render-spec is what every legitimate consumer does.
        Only WRITING one is the hand-roll compose-spec owns."""
        out = scan(**{"ok.py": 'spec = json.load(open(BOOK / "render-spec.json"))'})
        self.assertNotIn("render-spec.json by hand", out)

    def test_a_clean_scratchpad_is_silent(self):
        self.assertEqual(scan(**{"notes.py": "print('hello')"}), "")

    def test_the_detector_does_not_flag_itself(self):
        """It quotes every signature it looks for, so without the guard it is its
        own worst offender."""
        with tempfile.TemporaryDirectory() as t:
            body = (HERE.parent / "scripts" / "detect_handroll.py").read_text()
            (Path(t) / "detect_handroll.py").write_text(body)
            self.assertEqual(det.scan_scratchpad(Path(t)), [])


class TestUniverseScan(unittest.TestCase):
    def universe(self, tmp, *, art=True, recipe=True, todo=True):
        d = Path(tmp) / "reference" / "someone"
        d.mkdir(parents=True)
        (d / "prompts.md").write_text(
            "# someone\n\n## face-3q\n"
            + ("TODO(author): the prompt for this shot." if todo else "a real prompt."))
        if art:
            (d / "face-3q.png").write_bytes(b"\x89PNG")
            if recipe:
                (d / "face-3q.png.recipe.json").write_text('{"prompt": "the real one"}')
        return Path(tmp)

    def test_art_beside_an_unfilled_prompts_md_is_reported(self):
        with tempfile.TemporaryDirectory() as t:
            out = "\n".join(det.scan_universe(self.universe(t)))
            self.assertIn("recorded nowhere", out)

    def test_a_recoverable_finding_names_the_backfill_tool(self):
        """The prompt is not lost: it is in the plate's own recipe."""
        with tempfile.TemporaryDirectory() as t:
            out = "\n".join(det.scan_universe(self.universe(t)))
            self.assertIn("backfill_prompts.py", out)
            self.assertIn("1/1 recoverable", out)

    def test_an_unrecoverable_finding_says_so_plainly(self):
        with tempfile.TemporaryDirectory() as t:
            out = "\n".join(det.scan_universe(self.universe(t, recipe=False)))
            self.assertIn("UNRECOVERABLE", out)

    def test_a_filled_prompts_md_is_silent(self):
        with tempfile.TemporaryDirectory() as t:
            self.assertEqual(det.scan_universe(self.universe(t, todo=False)), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
