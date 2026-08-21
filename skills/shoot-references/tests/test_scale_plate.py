#!/usr/bin/env python3
"""Tests for scale_plate: the scene is DERIVED from canon, and refusals fire pre-spend.

Every refusal here corresponds to a way a scale plate can waste a paid render or,
worse, ship a picture that contradicts the records it exists to depict.
"""
import importlib.util
import json
import pathlib
import subprocess
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "scale_plate.py"
spec = importlib.util.spec_from_file_location("scale_plate", SCRIPT)
scale_plate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scale_plate)


def _ent(eid, height=None, rel=None, sheets=("face-neutral",), kind="character",
         poses=("default",)):
    return {
        "id": eid,
        "kind": kind,
        "structured": {
            "sheets": {s: f"reference/{eid}/{s}.png" for s in sheets},
            "scale": {**({"height": height} if height else {}),
                      **({"relativeTo": rel} if rel else {})},
            "render": {"poses": {p: {} for p in poses}},
        },
    }


class ScalePlateRefusals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name) / "u"
        (self.root / "canon" / "entities").mkdir(parents=True)
        (self.root / "universe.json").write_text("{}")

    def tearDown(self):
        self.tmp.cleanup()

    def _write(self, *ents):
        for e in ents:
            (self.root / "canon" / "entities" / f"{e['id']}.json").write_text(json.dumps(e))

    def _run(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), str(self.root), *args],
                              capture_output=True, text=True)

    def test_refuses_a_single_character(self):
        self._write(_ent("a"))
        r = self._run("a")
        self.assertNotEqual(r.returncode, 0)
        # The refusal must teach WHY two, not merely that two are required.
        self.assertIn("at least TWO", r.stderr)
        self.assertIn("numbers do not survive", r.stderr)

    def test_refuses_a_duplicate(self):
        self._write(_ent("a"), _ent("b"))
        r = self._run("a", "a")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("twice", r.stderr)

    def test_refuses_an_unlocked_character(self):
        """No locked sheets means no likeness to place: refuse BEFORE spending."""
        self._write(_ent("a"), _ent("b", sheets=()))
        r = self._run("a", "b")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("no locked sheets", r.stderr)
        self.assertIn("shoot-references", r.stderr)

    def test_refuses_a_non_character(self):
        self._write(_ent("a"), _ent("room", kind="setting"))
        r = self._run("a", "room")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("not a character", r.stderr)


class ScalePlateScene(unittest.TestCase):
    def test_uses_the_declared_relation_not_the_caller(self):
        tall = _ent("tall", height="Six feet three.", rel={"short": "a few inches TALLER than"})
        short = _ent("short", height="Six feet.")
        scene, negs = scale_plate.build_scene([("tall", tall), ("short", short)])
        self.assertIn("tall is a few inches TALLER than short", scene)
        self.assertIn("LEFT TO RIGHT THE ORDER IS: tall, then short", scene)
        self.assertIn("Six feet three.", scene)
        self.assertIn("Six feet.", scene)
        self.assertIn("no numbers", negs)
        self.assertIn("same height", negs)

    def test_reads_the_relation_from_either_side(self):
        """Only one of the two entities needs to carry the phrase."""
        a, b = _ent("a"), _ent("b", rel={"a": "shorter than"})
        scene, _ = scale_plate.build_scene([("a", a), ("b", b)])
        self.assertIn("b is shorter than a", scene)

    def test_missing_relation_says_so_instead_of_inventing_one(self):
        a, b = _ent("a"), _ent("b")
        scene, _ = scale_plate.build_scene([("a", a), ("b", b)])
        self.assertIn("NO declared relative scale", scene)
        self.assertIn("do not invent a dramatic difference", scene)

    def test_three_characters_state_two_relations(self):
        a = _ent("a", rel={"b": "taller than"})
        b = _ent("b", rel={"c": "taller than"})
        c = _ent("c")
        scene, _ = scale_plate.build_scene([("a", a), ("b", b), ("c", c)])
        self.assertIn("a is taller than b", scene)
        self.assertIn("b is taller than c", scene)
        self.assertIn("A 3-PERSON HEIGHT COMPARISON", scene)


if __name__ == "__main__":
    unittest.main()
