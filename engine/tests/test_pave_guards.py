"""Two guards paved 2026-08-01 after will-there-be-ice-cream.

Both failure modes were SILENT and both exited 0, which is why they needed to
become refusals rather than notes in a skill file.
"""
import sys, json, pathlib, tempfile, unittest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "skills/compose-spread/scripts"))
sys.path.insert(0, str(ROOT / "skills/book-doctor/scripts"))
import book_doctor


class TestOutMustBeAFile(unittest.TestCase):
    """`--out` handed a DIRECTORY made --skip-existing skip all 72 spreads."""

    def test_render_spread_refuses_a_directory_for_out(self):
        src = (ROOT / "skills/compose-spread/scripts/render_spread.py").read_text()
        self.assertIn("out.is_dir()", src,
                      "a directory passed to --out must be refused, not silently skipped")
        i_guard = src.index("out.is_dir()")
        i_skip = src.index("args.skip_existing and out.exists()")
        self.assertLess(i_guard, i_skip,
                        "the directory guard must run BEFORE --skip-existing, "
                        "or the skip still swallows the whole batch")


class TestStaleCaptions(unittest.TestCase):
    """A `_caption` that drifted from its beat ships the wrong words."""

    def _book(self, tmp, caption, beat_text):
        book = pathlib.Path(tmp) / "b-book"
        (book / "spreads").mkdir(parents=True)
        (book / "render-spec.json").write_text(json.dumps({
            "book": "b-book", "story": "s", "size": "1536x1024",
            "spreads": [{"id": "spread-01", "_caption": caption, "cast": []}]}))
        uni = pathlib.Path(tmp) / "u"
        (uni / "stories").mkdir(parents=True)
        (uni / "canon" / "entities").mkdir(parents=True)
        (uni / "stories" / "s.json").write_text(json.dumps(
            {"id": "s", "beats": [{"n": 1, "text": beat_text}]}))
        return str(book), str(uni)

    def _caption_rows(self, res):
        rows = res.get("rows") or res.get("checks") or []
        return [r for r in rows if "caption" in str(r).lower()]

    def test_drifted_caption_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            book, uni = self._book(tmp, "a small creamery on a warm evening",
                                   "a quiet park on a warm afternoon")
            res = book_doctor.diagnose(book, uni)
            rows = self._caption_rows(res)
            self.assertTrue(rows, "book_doctor must report on captions when given a universe")
            self.assertTrue(any(not r.get("ok", True) for r in rows),
                            "a caption that disagrees with its beat must FAIL")

    def test_matching_caption_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            same = "a quiet park on a warm afternoon"
            book, uni = self._book(tmp, same, same)
            res = book_doctor.diagnose(book, uni)
            rows = self._caption_rows(res)
            self.assertTrue(rows)
            self.assertTrue(all(r.get("ok", False) for r in rows),
                            "verbatim captions must pass")


if __name__ == "__main__":
    unittest.main()
