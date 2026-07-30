#!/usr/bin/env python3
"""Scaffolding a lookbook twice must not fork the manifest off its provenance.

A lookbook GROWS: you scaffold four exemplars, shoot four more, and re-run with all
eight. Before 2026-07-30 that re-run renamed every already-present exemplar to
`<stem>-1.png` (the collision guard could not tell "a different file with the same
name" from "this same file again"), pointed the manifest at the renamed copy, and
left `<stem>.png.recipe.json` beside the original. Result: the refs folder doubled
and every re-scaffolded exemplar silently lost its provenance. Caught in
christofuturism on 8 of 12 women's plates, and only by a manual audit, because
nothing downstream checks this.

The second failure this locks down: the scaffolder copied the image without its
`.recipe.json` sidecar at all, so callers hand-copied provenance after every run.
"""
import json, os, subprocess, sys, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCAFFOLD = os.path.join(os.path.dirname(HERE), "scripts", "scaffold.py")

PNG_1x1 = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010802000000907753"
    "de0000000c4944415408d763f8cfc0000003010100b5e2e8250000000049454e44ae426082"
)


def _plate(d, name, tint):
    """A tiny unique PNG plus the recipe sidecar generate.py would have written."""
    with open(os.path.join(d, name + ".png"), "wb") as f:
        f.write(PNG_1x1 + bytes([tint]))
    json.dump({"provider": "gpt-image-2", "prompt": name},
              open(os.path.join(d, name + ".png.recipe.json"), "w"))


class TestLookbookScaffoldRerun(unittest.TestCase):
    def _run(self, out, src, names):
        cmd = [sys.executable, SCAFFOLD, "--dir", out, "--id", "t", "--name", "T",
               "--aesthetic", "a", "--variety-rule", "v", "--gate", "g"]
        for n in names:
            cmd += ["--ref", os.path.join(src, n + ".png")]
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        return r

    def test_rerun_keeps_names_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = os.path.join(tmp, "src"); os.makedirs(src)
            out = os.path.join(tmp, "lb")
            names = ["plate-%s" % c for c in "abcdef"]
            for i, n in enumerate(names):
                _plate(src, n, i)

            self._run(out, src, names[:4])
            self._run(out, src, names)          # the re-run

            manifest = json.load(open(os.path.join(out, "lookbook.json")))
            self.assertEqual(sorted(manifest["refs"]),
                             sorted("refs/%s.png" % n for n in names),
                             "re-run forked the manifest onto renamed copies")

            pngs = [f for f in os.listdir(os.path.join(out, "refs")) if f.endswith(".png")]
            self.assertEqual(len(pngs), 6, "re-run duplicated exemplars: %s" % sorted(pngs))

            for r in manifest["refs"]:
                self.assertTrue(os.path.exists(os.path.join(out, r + ".recipe.json")),
                                "%s landed with no provenance sidecar" % r)

    def test_distinct_files_sharing_a_basename_still_get_unique_names(self):
        """The collision guard must survive the fix: DIFFERENT content keeps renaming."""
        with tempfile.TemporaryDirectory() as tmp:
            a = os.path.join(tmp, "a"); b = os.path.join(tmp, "b")
            os.makedirs(a); os.makedirs(b)
            out = os.path.join(tmp, "lb")
            for i, n in enumerate(["p1", "p2", "p3", "p4"]):
                _plate(a, n, i)
            _plate(b, "p1", 99)                 # same basename, different bytes

            cmd = [sys.executable, SCAFFOLD, "--dir", out, "--id", "t", "--name", "T",
                   "--aesthetic", "a", "--variety-rule", "v", "--gate", "g"]
            for n in ["p1", "p2", "p3", "p4"]:
                cmd += ["--ref", os.path.join(a, n + ".png")]
            cmd += ["--ref", os.path.join(b, "p1.png")]
            r = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

            manifest = json.load(open(os.path.join(out, "lookbook.json")))
            self.assertEqual(len(manifest["refs"]), 5)
            self.assertEqual(len(set(manifest["refs"])), 5, "a distinct ref was clobbered")
            self.assertIn("refs/p1-1.png", manifest["refs"],
                          "different content sharing a basename must still be renamed")


if __name__ == "__main__":
    unittest.main(verbosity=2)
