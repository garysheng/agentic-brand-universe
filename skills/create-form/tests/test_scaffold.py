#!/usr/bin/env python3
"""The create-form scaffolder's refusals must actually refuse, and its stamp must
match the evidence.

The evidence gate is the heart of the skill: a form with zero works is the retired
896-line composer all over again (SPEC 4.8, retired v0.17: 896 lines, 91 tests,
zero works). These tests pin the gate closed, pin the hypothesis warning to the
sub-three evidence base, and pin the integration with make-a-work's forms.py, so a
scaffolded form is discoverable the moment it lands and its STATUS line surfaces.

Every test here was proven to bite by mutating the scaffolder (dropping the refusal
or the stamp) and watching the test fail; see the SAVE-LOG entry that shipped it.
"""
import json, os, pathlib, subprocess, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
SCAFFOLD = HERE.parent / "scripts" / "scaffold.py"
FORMS_PY = HERE.parent.parent / "make-a-work" / "scripts" / "forms.py"


def make_universe(tmp):
    root = pathlib.Path(tmp) / "uni"
    root.mkdir()
    (root / "universe.json").write_text(json.dumps({"id": "test-universe"}))
    return root


def make_work(root, slug, declare_form=None):
    w = root / "works" / slug
    w.mkdir(parents=True)
    (w / "README.md").write_text("the work's own record")
    if declare_form:
        (w / "work.json").write_text(json.dumps({"id": slug, "form": declare_form}))
    return w


def run(*args, scaffold=SCAFFOLD):
    return subprocess.run([sys.executable, str(scaffold), *map(str, args)],
                          capture_output=True, text=True)


class TestEvidenceGate(unittest.TestCase):
    def test_zero_works_refuses_and_names_the_cautionary_tale(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            r = run(root, "poster")
            self.assertNotEqual(r.returncode, 0, "zero-works scaffold must refuse")
            self.assertIn("ZERO works", r.stderr)
            self.assertIn("896", r.stderr, "the retired composer stays named in the refusal")
            self.assertFalse((root / "forms" / "poster").exists(),
                             "a refusal must leave nothing behind")

    def test_missing_work_dir_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            r = run(root, "poster", "--work", root / "works" / "not-there")
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("not a directory on disk", r.stderr)
            self.assertFalse((root / "forms" / "poster").exists())


class TestIdAndClobber(unittest.TestCase):
    def test_bad_id_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x")
            for bad in ("Poster", "poster look", "poster-", "-poster"):
                r = run("--work", w, "--", root, bad)
                self.assertNotEqual(r.returncode, 0, f"id {bad!r} must refuse")
                self.assertIn("bad form id", r.stderr)

    def test_existing_form_is_not_clobbered(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x")
            fdir = root / "forms" / "poster"
            fdir.mkdir(parents=True)
            (fdir / "FORM.md").write_text("the live form")
            r = run(root, "poster", "--work", w)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn("Refusing to clobber", r.stderr)
            self.assertEqual((fdir / "FORM.md").read_text(), "the live form",
                             "the existing form was altered by a refused run")

    def test_retired_encoding_folder_is_kept_as_a_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x")
            fdir = root / "forms" / "poster"
            fdir.mkdir(parents=True)
            (fdir / "form.json").write_text("{}")
            r = run(root, "poster", "--work", w)
            self.assertNotEqual(r.returncode, 0)
            self.assertTrue((fdir / "form.json").exists())
            self.assertFalse((fdir / "FORM.md").exists())


class TestStamp(unittest.TestCase):
    def test_one_work_stamps_hypothesis_and_is_discoverable(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x", declare_form="poster")
            r = run(root, "poster", "--work", w, "--what", "A poster.")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

            form_md = (root / "forms" / "poster" / "FORM.md").read_text()
            self.assertIn("ONE finished work", form_md)
            self.assertIn("hypothesis", form_md.lower(),
                          "below three works the STATUS must carry the hypothesis warning")
            self.assertIn("works/2026-01-01-x", form_md, "the evidence work is listed")
            self.assertTrue((root / "forms" / "poster" / "PROMPT.md").exists())
            self.assertIn("HYPOTHESIS", r.stdout)

            # Integration: make-a-work's forms.py must see it as usable and surface STATUS.
            rr = subprocess.run([sys.executable, str(FORMS_PY), "resolve", str(root), "poster"],
                                capture_output=True, text=True)
            self.assertEqual(rr.returncode, 0, rr.stdout + rr.stderr)
            hit = json.loads(rr.stdout)
            self.assertTrue(hit["usable"])
            self.assertIn("STATUS", hit["status"] or "",
                          "the STATUS heading must surface through forms.py")

    def test_three_works_states_records_win_not_hypothesis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            ws = [make_work(root, f"2026-01-0{i}-x", declare_form="poster") for i in (1, 2, 3)]
            args = [root, "poster"]
            for w in ws:
                args += ["--work", w]
            r = run(*args)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            form_md = (root / "forms" / "poster" / "FORM.md").read_text()
            self.assertIn("THREE finished works", form_md)
            self.assertIn("the records win", form_md)
            self.assertNotIn("hypothesis", form_md.split("## Why this form exists")[0].lower(),
                             "at three works the STATUS section drops the hypothesis framing")
            self.assertNotIn("HYPOTHESIS", r.stdout)

    def test_evals_flag_creates_the_folder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x", declare_form="poster")
            r = run(root, "poster", "--work", w, "--evals")
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertTrue((root / "forms" / "poster" / "evals").is_dir())


class TestBackfillGuidance(unittest.TestCase):
    def test_undeclared_work_gets_backfill_guidance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x")           # no work.json at all
            r = run(root, "poster", "--work", w)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertIn("BACKFILL NEEDED", r.stdout)
            self.assertIn("NEVER rewrite", r.stdout,
                          "the guidance must state that historical records are not rewritten")
            self.assertFalse((w / "work.json").exists(),
                             "the scaffolder must not write work.json itself: the retrofit "
                             "note is an authored record, not boilerplate")

    def test_declared_work_gets_no_backfill_warning(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = make_universe(tmp)
            w = make_work(root, "2026-01-01-x", declare_form="poster")
            r = run(root, "poster", "--work", w)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertNotIn("BACKFILL NEEDED", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
