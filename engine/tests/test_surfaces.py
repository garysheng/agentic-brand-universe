"""identity.surfaces (SPEC §11, v0.59): a renderer outside the universe reads these roles, so
`validate` must refuse a declaration that no longer resolves. Earned by freedom#163, where the
two first universes keep their colors in different files under names that mean opposite things.
"""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from agenticstory.store import CanonStore

CHROME = {"ground": "#0a1030", "ink": "#EDEAE2", "gold": "#C2A15C"}


class SurfacesTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-surfaces-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        (self.dir / "canon" / "craft").mkdir(parents=True)
        (self.dir / "canon" / "craft" / "palette.json").write_text(json.dumps(
            {"id": "p", "kind": "register-rule", "name": "P", "summary": "s", "rules": ["r"],
             "tokens": {"ink": {"hex": "#1E1B19"}, "cream": {"hex": "#F0ECE5"}, "live": {"hex": "#007AFF"}}}))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def problems(self, surfaces):
        (self.dir / "universe.json").write_text(json.dumps({
            "id": "t", "name": "T", "assetRoot": ".", "brand": {"chrome": CHROME},
            "identity": {"register": "photoreal", "surfaces": surfaces}}))
        return [p for p in CanonStore(self.dir).validate_canon() if "identity.surfaces" in p]

    def test_both_real_token_shapes_validate(self):
        self.assertEqual(self.problems({
            "default": {"tokens": "universe.json#brand.chrome", "roles": {"ground": "ground", "text": "ink", "accent": "gold"}, "display": "Fraunces"},
            "deck": {"tokens": "canon/craft/palette.json#tokens", "roles": {"ground": "ink", "text": "cream", "accent": "live"}},
        }), [])

    def test_absent_is_fine(self):
        (self.dir / "universe.json").write_text(json.dumps({"id": "t", "name": "T", "assetRoot": ".", "identity": {}}))
        self.assertEqual([p for p in CanonStore(self.dir).validate_canon() if "surfaces" in p], [])

    def test_every_defect_is_named(self):
        got = "\n".join(self.problems({
            "deck": {"tokens": "canon/craft/palette.json#tokens", "roles": {"ground": "ink", "text": "cream", "accent": "glow"}},
            "artifact": {"tokens": "canon/craft/gone.json#tokens", "roles": {"ground": "a", "text": "b", "accent": "c"}},
            "share": {"tokens": "universe.json#brand.chrome", "roles": {"ground": "ground", "text": "ink"}},
        }))
        self.assertIn("has no 'default'", got)
        self.assertIn("accent names token 'glow'", got)
        self.assertIn("gone.json does not exist", got)
        self.assertIn("share: roles.accent is missing", got)

    def test_a_token_that_is_not_a_hex_is_refused(self):
        bad = dict(CHROME, gold="golden")
        (self.dir / "x.json").write_text(json.dumps({"t": bad}))
        got = self.problems({"default": {"tokens": "x.json#t", "roles": {"ground": "ground", "text": "ink", "accent": "gold"}}})
        self.assertEqual(len(got), 1)
        self.assertIn("is not a hex color", got[0])


if __name__ == "__main__":
    unittest.main()
