"""scaffold.py writes textPolicy and refuses without it (gap G41, #44).

SPEC 4.7 made textPolicy REQUIRED on new packs in v0.12 and the scaffolder could not write it,
so every new pack silently fell back to 'diegetic', including one whose gate forbids every glyph.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

SCAFFOLD = pathlib.Path(__file__).resolve().parents[1] / "scripts" / "scaffold.py"
LINT = pathlib.Path(__file__).resolve().parents[2] / "lint-universe" / "scripts" / "lint.py"
PNG = b"\x89PNG\r\n\x1a\n"


class TestTextPolicy(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.src = pathlib.Path(self.t.name) / "src"
        self.src.mkdir()
        self.args = []
        for n in ("a", "b", "c"):
            (self.src / f"{n}.png").write_bytes(PNG + n.encode())
            self.args += ["--ref", str(self.src / f"{n}.png")]

    def tearDown(self):
        self.t.cleanup()

    def scaffold(self, *extra):
        out = pathlib.Path(self.t.name) / "pack"
        r = subprocess.run([sys.executable, str(SCAFFOLD), "--dir", str(out), "--id", "p",
                            "--name", "P", "--anchor", str(self.src / "a.png"), *self.args,
                            "--style-line", "x", "--gate", "no glyph anywhere", *extra],
                           capture_output=True, text=True)
        return r, out

    def test_refuses_without_a_text_policy(self):
        r, _ = self.scaffold()
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--text-policy", r.stderr)

    def test_writes_the_declared_policy(self):
        r, out = self.scaffold("--text-policy", "none")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads((out / "pack.json").read_text())["textPolicy"], "none")

    def test_an_unknown_policy_is_rejected(self):
        r, _ = self.scaffold("--text-policy", "some")
        self.assertNotEqual(r.returncode, 0)

    def test_lint_names_a_silent_pack(self):
        with tempfile.TemporaryDirectory() as t:
            u = pathlib.Path(t)
            (u / "canon" / "entities").mkdir(parents=True)
            d = u / "reference" / "style" / "old"
            (d / "refs").mkdir(parents=True)
            for n in ("a", "b", "c"):
                (d / "refs" / f"{n}.png").write_bytes(PNG)
            (d / "pack.json").write_text(json.dumps({
                "id": "old", "anchor": "refs/a.png", "refs": ["refs/a.png", "refs/b.png",
                                                               "refs/c.png"],
                "styleLine": "s", "gate": ["g"]}))
            (u / "universe.json").write_text(json.dumps({"name": "u"}))
            r = subprocess.run([sys.executable, str(LINT), str(u)], capture_output=True, text=True)
            self.assertIn("PACK-NO-TEXT-POLICY", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main()
