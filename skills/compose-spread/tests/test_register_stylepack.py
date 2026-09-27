"""A register declaring ONLY a stylePack can be RENDERED, not just shot (gap G22, #16).

Before: assemble_prompt refused "no anchor: identity.register.anchor is null" while
chain_matrix shot the same universe happily from its pack. Both ends of the cover
path are covered too, since compile_cover had the same refusal.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_assemble_prompt import ASSEMBLE, build_universe, png, run, write_spec  # noqa: E402

COMPILE_COVER = Path(__file__).resolve().parents[2] / "cover" / "scripts" / "compile_cover.py"


def pack_only(root: Path):
    d = root / "reference" / "style" / "soft"
    png(d / "swatch.png")
    (d / "pack.json").write_text(json.dumps({
        "id": "soft", "anchor": "swatch.png", "styleLine": "soft pack gouache",
        "rejectedPoles": ["pack-pole-photoreal"], "anchorSubject": "a clay jar"}))
    uni = json.loads((root / "universe.json").read_text())
    uni["identity"]["register"] = {"stylePack": "soft"}
    (root / "universe.json").write_text(json.dumps(uni))


class TestStylePackOnlyRegister(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)
        build_universe(self.root)
        pack_only(self.root)

    def tearDown(self):
        self.t.cleanup()

    def test_spread_renders_from_the_pack_anchor(self):
        spec = write_spec(self.root, [{"id": "clean"}])
        r = run(self.root, spec)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertTrue(out["refs"][0].endswith("reference/style/soft/swatch.png"), out["refs"])
        self.assertIn("pack-pole-photoreal", out["prompt"])
        self.assertIn("a clay jar", out["prompt"])

    def test_no_anchor_and_no_pack_still_refuses(self):
        uni = json.loads((self.root / "universe.json").read_text())
        uni["identity"]["register"] = {}
        (self.root / "universe.json").write_text(json.dumps(uni))
        spec = write_spec(self.root, [{"id": "clean"}])
        r = run(self.root, spec)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no anchor", r.stderr + r.stdout)

    def test_cover_compiles_from_the_pack_anchor(self):
        (self.root / "stories").mkdir(exist_ok=True)
        (self.root / "stories" / "tale.json").write_text(json.dumps(
            {"id": "tale", "features": ["clean"]}))
        r = subprocess.run([sys.executable, str(COMPILE_COVER), str(self.root), "tale",
                            "--title", "T"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        job = json.loads(r.stdout)
        self.assertTrue(job["refs"][0].endswith("reference/style/soft/swatch.png"), job["refs"])
        self.assertIn("pack-pole-photoreal", job["prompt"])


if __name__ == "__main__":
    unittest.main()
