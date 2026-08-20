#!/usr/bin/env python3
"""Tests for bless_ref.py — per-ref human blessing on a Style Pack (SPEC §4.7)."""
import json, os, pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "bless_ref.py"
SCAFFOLD = HERE.parent / "scripts" / "scaffold.py"

PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d494844520000000100000001080600000"
    "01f15c4890000000a49444154789c6360000002000100ffff03000006"
    "0005574bd0e60000000049454e44ae426082"
)


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args],
                          capture_output=True, text=True)


class BlessRefTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.pack = pathlib.Path(self.tmp.name) / "pack"
        (self.pack / "refs").mkdir(parents=True)
        self.refs = []
        for n in ("anchor", "b", "c"):
            p = self.pack / "refs" / f"{n}.png"
            p.write_bytes(PNG + n.encode())
            self.refs.append(f"refs/{n}.png")
        (self.pack / "pack.json").write_text(json.dumps({
            "id": "t", "name": "T", "anchor": "refs/anchor.png", "refs": self.refs,
            "styleLine": "x", "gate": ["y"],
        }))

    def tearDown(self):
        self.tmp.cleanup()

    def marker(self, name):
        return self.pack / "refs" / f"{name}.png.blessed.json"

    # --- the happy path -------------------------------------------------
    def test_blessing_writes_a_hash_bound_marker_beside_the_ref(self):
        r = run(str(self.pack), "--ref", "b", "--by", "Gary Sheng, 2026-08-20")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertTrue(self.marker("b").exists())
        m = json.loads(self.marker("b").read_text())
        self.assertEqual(m["ref"], "refs/b.png")
        self.assertEqual(m["blessedBy"], "Gary Sheng, 2026-08-20")
        self.assertEqual(len(m["sha256"]), 64)
        self.assertIn("blessedOn", m)

    def test_a_ref_resolves_by_bare_stem_basename_or_relpath(self):
        for arg in ("b", "b.png", "refs/b.png"):
            for f in (self.pack / "refs").glob("*.blessed.json"):
                f.unlink()
            r = run(str(self.pack), "--ref", arg, "--by", "G")
            self.assertEqual(r.returncode, 0, f"{arg}: {r.stderr}")

    # --- the refusals ---------------------------------------------------
    def test_by_is_required_and_never_defaulted_to_human(self):
        r = run(str(self.pack), "--ref", "b")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--by is REQUIRED", r.stderr)
        self.assertFalse(self.marker("b").exists())

    def test_blessing_a_ref_the_pack_does_not_list_is_refused(self):
        (self.pack / "refs" / "stranger.png").write_bytes(PNG)
        r = run(str(self.pack), "--ref", "stranger", "--by", "G")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("blessing of nothing", r.stderr)
        self.assertFalse((self.pack / "refs" / "stranger.png.blessed.json").exists())

    def test_a_listed_ref_missing_from_disk_is_refused(self):
        (self.pack / "refs" / "c.png").unlink()
        r = run(str(self.pack), "--ref", "c", "--by", "G")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not on disk", r.stderr)

    def test_no_packjson_is_refused(self):
        (self.pack / "pack.json").unlink()
        r = run(str(self.pack), "--status")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no pack.json", r.stderr)

    def test_overwriting_an_existing_blessing_needs_rebless(self):
        self.assertEqual(run(str(self.pack), "--ref", "b", "--by", "Russ").returncode, 0)
        r = run(str(self.pack), "--ref", "b", "--by", "Somebody Else")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("--rebless", r.stderr)
        self.assertEqual(json.loads(self.marker("b").read_text())["blessedBy"], "Russ")

    def test_rebless_keeps_who_it_replaced(self):
        run(str(self.pack), "--ref", "b", "--by", "Russ")
        r = run(str(self.pack), "--ref", "b", "--by", "Gary", "--rebless")
        self.assertEqual(r.returncode, 0, r.stderr)
        m = json.loads(self.marker("b").read_text())
        self.assertEqual(m["blessedBy"], "Gary")
        self.assertEqual(m["replaced"]["blessedBy"], "Russ")

    # --- the point of the hash ------------------------------------------
    def test_a_blessing_goes_STALE_when_the_bytes_change(self):
        run(str(self.pack), "--ref", "b", "--by", "Gary")
        self.assertIn("blessed   refs/b.png", run(str(self.pack), "--status").stdout)
        (self.pack / "refs" / "b.png").write_bytes(PNG + b"a different roll")
        out = run(str(self.pack), "--status").stdout
        self.assertIn("STALE", out)
        self.assertIn("nobody saw", out)
        self.assertIn("0 of 3 refs individually blessed", out)

    # --- status ---------------------------------------------------------
    def test_status_counts_and_names_the_candidates(self):
        run(str(self.pack), "--ref", "b", "--by", "Gary")
        out = run(str(self.pack), "--status").stdout
        self.assertIn("1 of 3 refs individually blessed", out)
        self.assertIn("CANDIDATES", out)
        self.assertIn("unblessed", out)

    def test_status_warns_loudly_when_the_ANCHOR_is_unblessed(self):
        run(str(self.pack), "--ref", "b", "--by", "Gary")
        out = run(str(self.pack), "--status").stdout
        self.assertIn("WARNING: the ANCHOR", out)
        self.assertIn("passed FIRST", out)

    def test_status_is_quiet_about_the_anchor_once_it_is_blessed(self):
        for n in ("anchor", "b", "c"):
            run(str(self.pack), "--ref", n, "--by", "Gary")
        out = run(str(self.pack), "--status").stdout
        self.assertNotIn("WARNING", out)
        self.assertIn("3 of 3 refs individually blessed", out)
        self.assertNotIn("CANDIDATES", out)

    def test_status_flags_a_ref_listed_but_missing(self):
        (self.pack / "refs" / "c.png").unlink()
        out = run(str(self.pack), "--status").stdout
        self.assertIn("MISSING", out)

    def test_bare_pack_path_defaults_to_status(self):
        self.assertIn("refs individually blessed", run(str(self.pack)).stdout)

    # --- it survives the scaffolder -------------------------------------
    def test_scaffold_reports_blessing_coverage_and_names_the_verb(self):
        src = pathlib.Path(self.tmp.name) / "src"
        src.mkdir()
        args = []
        for n in ("a", "b", "c"):
            p = src / f"{n}.png"
            p.write_bytes(PNG + n.encode())
            args += ["--ref", str(p)]
        out = pathlib.Path(self.tmp.name) / "newpack"
        r = subprocess.run([sys.executable, str(SCAFFOLD), "--dir", str(out),
                            "--id", "np", "--name", "NP", "--anchor", str(src / "a.png"),
                            *args, "--style-line", "x", "--gate", "y"],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("0 of 3", r.stdout)
        self.assertIn("bless_ref.py", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
