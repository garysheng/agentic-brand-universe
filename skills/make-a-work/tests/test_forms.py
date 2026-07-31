#!/usr/bin/env python3
"""Forms are DATA, so form discovery is the thing that must not lie.

The failure that matters is not a crash. It is offering a form that cannot be made
from, which sends an agent looking for a method that does not exist and invites it to
improvise one. So every test here is about refusing.
"""
import importlib.util, io, contextlib, json, pathlib, sys, tempfile, unittest

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("forms", HERE.parent / "scripts" / "forms.py")
forms = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(forms)


def universe(root, name="u"):
    d = pathlib.Path(root) / name
    (d / "forms").mkdir(parents=True, exist_ok=True)
    (d / "universe.json").write_text(json.dumps({"name": name, "assetRoot": "."}))
    return d


def form(u, fid, *, form_md=True, prompt_md=True, form_json=False, evals=(), status=None):
    d = u / "forms" / fid
    (d).mkdir(parents=True, exist_ok=True)
    if form_md:
        body = "# f\n"
        if status:
            body += f"\n> ## {status}\n"
        (d / "FORM.md").write_text(body)
    if prompt_md:
        (d / "PROMPT.md").write_text("# method\n")
    if form_json:
        (d / "form.json").write_text("{}")
    for e in evals:
        (d / "evals").mkdir(exist_ok=True)
        (d / "evals" / e).write_text("")
    return d


class TestSurvey(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory(); self.tmp = self._t.name
        self.u = universe(self.tmp)

    def tearDown(self):
        self._t.cleanup()

    def test_a_complete_form_is_usable(self):
        form(self.u, "flyer", evals=["thumbnail.py"])
        f = forms.survey(self.u)[0]
        self.assertTrue(f["usable"]); self.assertEqual(f["evals"], ["thumbnail.py"])

    def test_a_form_with_no_PROMPT_is_NOT_usable(self):
        """No method means nothing can be made. This is the whole point."""
        form(self.u, "flyer", prompt_md=False)
        f = forms.survey(self.u)[0]
        self.assertFalse(f["usable"]); self.assertIn("PROMPT.md", f["missing"])

    def test_a_form_with_no_FORM_is_NOT_usable(self):
        form(self.u, "flyer", form_md=False)
        self.assertFalse(forms.survey(self.u)[0]["usable"])

    def test_a_retired_form_json_folder_is_flagged_not_offered(self):
        form(self.u, "diorama", form_md=False, prompt_md=False, form_json=True)
        f = forms.survey(self.u)[0]
        self.assertFalse(f["usable"]); self.assertTrue(f["retiredEncodingOnly"])

    def test_a_bare_folder_is_not_mistaken_for_the_retired_encoding(self):
        form(self.u, "empty", form_md=False, prompt_md=False)
        self.assertFalse(forms.survey(self.u)[0]["retiredEncodingOnly"])

    def test_the_status_warning_is_surfaced(self):
        """A one-instance form is a hypothesis; an agent reading only the method
        would follow it with unearned confidence."""
        form(self.u, "flyer", status="STATUS: ONE-INSTANCE-DERIVED. Expect correction.")
        self.assertIn("ONE-INSTANCE-DERIVED", forms.survey(self.u)[0]["status"])

    def test_no_status_is_None_not_a_crash(self):
        form(self.u, "flyer")
        self.assertIsNone(forms.survey(self.u)[0]["status"])

    def test_a_universe_with_no_forms_dir_surveys_empty(self):
        u2 = universe(self.tmp, "bare")
        (u2 / "forms").rmdir()
        self.assertEqual(forms.survey(u2), [])

    def test_forms_are_listed_in_a_stable_order(self):
        for fid in ("zebra", "apple", "moose"):
            form(self.u, fid)
        self.assertEqual([f["id"] for f in forms.survey(self.u)], ["apple", "moose", "zebra"])


class TestRefusals(unittest.TestCase):
    def setUp(self):
        self._t = tempfile.TemporaryDirectory(); self.tmp = self._t.name
        self.u = universe(self.tmp)

    def tearDown(self):
        self._t.cleanup()

    def _resolve(self, fid):
        ns = type("N", (), {"universe": str(self.u), "form": fid})
        with contextlib.redirect_stdout(io.StringIO()):
            return forms.cmd_resolve(ns)

    def test_resolving_an_unknown_form_REFUSES(self):
        form(self.u, "flyer")
        with self.assertRaises(SystemExit) as c:
            self._resolve("poster")
        self.assertIn("no form", str(c.exception))

    def test_the_refusal_names_what_IS_declared(self):
        """A bare refusal makes the next move a guess."""
        form(self.u, "flyer")
        with self.assertRaises(SystemExit) as c:
            self._resolve("poster")
        self.assertIn("flyer", str(c.exception))

    def test_resolving_an_unusable_form_REFUSES(self):
        form(self.u, "flyer", prompt_md=False)
        with self.assertRaises(SystemExit) as c:
            self._resolve("flyer")
        self.assertIn("not usable", str(c.exception))

    def test_a_non_universe_path_REFUSES(self):
        with self.assertRaises(SystemExit) as c:
            forms._universe(self.tmp)
        self.assertIn("not a universe", str(c.exception))

    def test_resolving_a_good_form_returns_zero(self):
        form(self.u, "flyer")
        self.assertEqual(self._resolve("flyer"), 0)


if __name__ == "__main__":
    unittest.main()
