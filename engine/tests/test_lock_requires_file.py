"""Locking cannot approve art that is not on disk (SPEC 4.6.1-adjacent, v1.11.2).

validate and assert-story both check that a required sheet has a VALUE, never that the
value resolves, so a dangling sheet survives every downstream gate until a story casts it.
"""
import pathlib
import tempfile
import unittest

from agenticstory.authoring import lock_shot


def _entity():
    return {"id": "the-wingman", "kind": "character",
            "structured": {"sheets": {"master": None}, "requiredForRender": []},
            "authority": {"lockedBy": "someone"}}


class LockRequiresFileTest(unittest.TestCase):
    def test_refuses_a_path_with_no_file(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(ValueError) as cm:
                lock_shot(_entity(), "master", "reference/x/master.png", root=root)
            msg = str(cm.exception)
            self.assertIn("no file at", msg)
            # The message must say WHY nothing else would catch it, or the next person
            # assumes a downstream gate will.
            self.assertIn("validate", msg)

    def test_accepts_a_path_with_a_file(self):
        with tempfile.TemporaryDirectory() as root:
            p = pathlib.Path(root) / "reference" / "x"
            p.mkdir(parents=True)
            (p / "master.png").write_bytes(b"\x89PNG")
            ent = lock_shot(_entity(), "master", "reference/x/master.png", root=root)
            self.assertEqual(ent["structured"]["sheets"]["master"], "reference/x/master.png")

    def test_absolute_paths_are_checked_too(self):
        with tempfile.TemporaryDirectory() as root:
            missing = str(pathlib.Path(root) / "nope.png")
            with self.assertRaises(ValueError):
                lock_shot(_entity(), "master", missing, root=root)


if __name__ == "__main__":
    unittest.main()
