"""agenticstory.register: the ONE register resolver (gap G22, issue #16).

The shooter could resolve a stylePack-only register and the spread and cover
compilers could not, so a universe could shoot its matrix and render nothing.
"""
import json
import tempfile
import unittest
from pathlib import Path

from agenticstory.register import RegisterError, load_style_pack, render_register


def _pack(root: Path, pid="soft", anchor="anchor.png", **extra):
    d = root / "reference" / "style" / pid
    d.mkdir(parents=True)
    (d / anchor).write_bytes(b"png")
    (d / "pack.json").write_text(json.dumps({"id": pid, "anchor": anchor, **extra}))
    return d


class TestRenderRegister(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.root = Path(self.t.name)

    def tearDown(self):
        self.t.cleanup()

    def test_inline_anchor_wins(self):
        uni = {"identity": {"register": {"anchor": "a.png", "rejectedPoles": ["x"],
                                         "stylePack": "soft"}}}
        got = render_register(self.root, uni)
        self.assertEqual(got["anchor"], "a.png")
        self.assertEqual(got["rejectedPoles"], ["x"])
        self.assertIsNone(got["pack"])

    def test_stylepack_only_register_resolves_from_the_pack(self):
        _pack(self.root, rejectedPoles=["photoreal"], anchorSubject="an oil lamp",
              styleLine="soft painterly gouache")
        uni = {"identity": {"register": {"stylePack": "soft"}}}
        got = render_register(self.root, uni)
        self.assertEqual(got["anchor"], "reference/style/soft/anchor.png")
        self.assertEqual(got["rejectedPoles"], ["photoreal"])
        self.assertEqual(got["anchorSubject"], "an oil lamp")
        self.assertEqual(got["name"], "soft painterly gouache")

    def test_path_form_pack_spec(self):
        _pack(self.root)
        uni = {"identity": {"register": {"stylePack": "reference/style/soft"}}}
        self.assertEqual(render_register(self.root, uni)["anchor"],
                         "reference/style/soft/anchor.png")

    def test_inline_poles_override_the_packs(self):
        _pack(self.root, rejectedPoles=["pack-pole"])
        uni = {"identity": {"register": {"stylePack": "soft", "rejectedPoles": ["mine"]}}}
        self.assertEqual(render_register(self.root, uni)["rejectedPoles"], ["mine"])

    def test_neither_refuses(self):
        with self.assertRaises(RegisterError):
            render_register(self.root, {"identity": {"register": {}}})

    def test_missing_pack_refuses(self):
        with self.assertRaises(RegisterError):
            render_register(self.root, {"identity": {"register": {"stylePack": "nope"}}})

    def test_pack_anchor_off_disk_refuses(self):
        d = _pack(self.root)
        (d / "anchor.png").unlink()
        with self.assertRaises(RegisterError):
            load_style_pack(self.root, "soft", "why")


if __name__ == "__main__":
    unittest.main()
