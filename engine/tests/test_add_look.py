"""`abu add-look` authors an alt-look correct by construction (G18, #23).

Every era used to be hand-edited JSON, and the one trap the spec spends four paragraphs on
(a look with no face source of its own renders a stranger) had no scaffolder to prevent it.
"""
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

ENGINE = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ENGINE))
from agenticstory.authoring import add_look, scaffold_entity  # noqa: E402

LINT = ENGINE.parent / "skills" / "lint-universe" / "scripts" / "lint.py"


def _josh():
    e = scaffold_entity("character", "josh", "Josh", photo_stack=["reference/josh/photos"])
    e["structured"]["sheets"]["face-neutral"] = "reference/josh/face-neutral.png"
    e["structured"]["invariants"] = ["salt-and-pepper-beard", "age-forty-three"]
    return e


class TestAddLook(unittest.TestCase):
    def test_refuses_a_look_with_no_face_source(self):
        with self.assertRaises(ValueError) as c:
            add_look(_josh(), "eighteen")
        self.assertIn("NO face source", str(c.exception))

    def test_photo_era_writes_the_spec_shape(self):
        e, md = add_look(_josh(), "eighteen", era=(1999, 2001),
                         photo_stack=["reference/josh/era-18/a.jpg"],
                         supersedes=["salt-and-pepper-beard", "age-forty-three"])
        look = e["structured"]["altLooks"]["eighteen"]
        self.assertEqual(look["photoStack"], ["reference/josh/era-18/a.jpg"])
        self.assertEqual(look["validFor"], {"from": 1999, "to": 2001})
        self.assertEqual(look["supersedes"], ["salt-and-pepper-beard", "age-forty-three"])
        self.assertIn("## face-neutral  -> reference/josh/eighteen/face-neutral.png", md)

    def test_chain_from_points_the_anchor_at_the_siblings_face(self):
        e, _ = add_look(_josh(), "eighteen", photo_stack=["p.jpg"])
        e, md = add_look(e, "sixteen", chain_from="eighteen")
        self.assertEqual(e["structured"]["altLooks"]["sixteen"]["anchorPhoto"],
                         "reference/josh/eighteen/face-neutral.png")
        self.assertIn("Shoot `eighteen` FIRST", md)

    def test_chain_from_an_undeclared_look_refuses(self):
        with self.assertRaises(ValueError):
            add_look(_josh(), "sixteen", chain_from="eighteen")

    def test_supersedes_must_match_an_invariant_exactly(self):
        with self.assertRaises(ValueError):
            add_look(_josh(), "eighteen", photo_stack=["p.jpg"], supersedes=["beard"])

    def test_keep_sheets_must_name_a_base_sheet(self):
        with self.assertRaises(ValueError):
            add_look(_josh(), "future", keep_sheets=["face-nuetral"])

    def test_a_duplicate_key_refuses(self):
        e, _ = add_look(_josh(), "eighteen", photo_stack=["p.jpg"])
        with self.assertRaises(ValueError):
            add_look(e, "eighteen", photo_stack=["p.jpg"])


class TestAddLookCliAndShootOrder(unittest.TestCase):
    def test_cli_writes_the_look_and_its_prompts_and_lint_names_the_order(self):
        with tempfile.TemporaryDirectory() as t:
            u = pathlib.Path(t)
            (u / "canon" / "entities").mkdir(parents=True)
            (u / "universe.json").write_text(json.dumps({"name": "u", "assetRoot": "."}))
            (u / "canon" / "entities" / "josh.json").write_text(json.dumps(_josh()))
            cli = [sys.executable, "-m", "agenticstory.cli"]
            r = subprocess.run(cli + ["add-look", str(u), "josh", "eighteen", "--era", "1999-2001",
                                      "--photo", "reference/josh/era-18/a.jpg"],
                               cwd=ENGINE, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            r = subprocess.run(cli + ["add-look", str(u), "josh", "sixteen",
                                      "--chain-from", "eighteen"],
                               cwd=ENGINE, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stderr)
            self.assertTrue((u / "reference/josh/sixteen/prompts.md").exists())
            ent = json.loads((u / "canon/entities/josh.json").read_text())
            self.assertIn("sixteen", ent["structured"]["altLooks"])
            lint = subprocess.run([sys.executable, str(LINT), str(u)],
                                  capture_output=True, text=True)
            self.assertIn("LOOK-CHAINED-BEFORE-SIBLING", lint.stdout + lint.stderr)

    def test_cli_refuses_a_faceless_look(self):
        with tempfile.TemporaryDirectory() as t:
            u = pathlib.Path(t)
            (u / "canon" / "entities").mkdir(parents=True)
            (u / "universe.json").write_text(json.dumps({"name": "u", "assetRoot": "."}))
            (u / "canon" / "entities" / "josh.json").write_text(json.dumps(_josh()))
            r = subprocess.run([sys.executable, "-m", "agenticstory.cli", "add-look", str(u),
                                "josh", "eighteen"], cwd=ENGINE, capture_output=True, text=True)
            self.assertEqual(r.returncode, 2)
            self.assertIn("NO face source", r.stderr)


if __name__ == "__main__":
    unittest.main()
