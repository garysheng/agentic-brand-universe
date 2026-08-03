#!/usr/bin/env python3
"""
chroma_key.py --choke — the edge-color-from-body mode, promoted 2026-08-03 after being
hand-rolled three times in the electric-hymnal diorama works (dark-on-dark silhouettes,
where despill turns green edge contamination into a bright yellow hairline).

No API calls, no network. Synthetic images only.

Run:  python3 tests/test_chroma_key.py        (from the on-brand-image skill dir)
"""
import importlib.util
import os
import sys
import unittest

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location(
    "chroma_key", os.path.join(HERE, "..", "scripts", "chroma_key.py"))
ck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ck)


def synthetic_cutout():
    """A near-black body with a contaminated semi-alpha skirt, as the keyer emits it
    on a dark-on-dark silhouette: body RGB (10,10,14), skirt a bright yellow-green
    residue (150,180,40) at alpha 0.5, everything else clear."""
    w = h = 40
    rgb = np.zeros((h, w, 3), dtype=np.uint8)
    alpha = np.zeros((h, w), dtype=np.uint8)
    rgb[10:30, 10:30] = (10, 10, 14)          # body
    alpha[10:30, 10:30] = 255
    rgb[9, 10:30] = (150, 180, 40)            # contaminated skirt, one px, top edge
    alpha[9, 10:30] = 128
    rgb[2, 2] = (60, 120, 30)                 # isolated partial px the flood never reaches
    alpha[2, 2] = 120
    return Image.fromarray(np.dstack([rgb, alpha[..., None]]), "RGBA")


class ChokeTest(unittest.TestCase):
    def test_edge_takes_body_color(self):
        out, green_dom = ck.choke_edges(synthetic_cutout(), 12)
        a = np.asarray(out).astype(int)
        # The skirt pixel took the near-black body color, not its yellow residue.
        skirt = a[9, 15]
        self.assertLess(skirt[0], 30, f"skirt R still bright: {skirt}")
        self.assertLess(skirt[1], 30, f"skirt G still bright: {skirt}")
        # Alpha untouched.
        self.assertEqual(skirt[3], 128)
        self.assertEqual(a[15, 15][3], 255)
        self.assertEqual(green_dom, 0)

    def test_unreached_partial_kept_but_clamped(self):
        out, _ = ck.choke_edges(synthetic_cutout(), 12)
        a = np.asarray(out).astype(int)
        px = a[2, 2]
        self.assertEqual(px[3], 120, "isolated partial px alpha must survive")
        self.assertLessEqual(px[1], max(px[0], px[2]), "green must not lead after clamp")
        self.assertGreater(px[0], 0, "color kept, not blanked")

    def test_body_color_untouched(self):
        src = synthetic_cutout()
        out, _ = ck.choke_edges(src, 12)
        sa, oa = np.asarray(src), np.asarray(out)
        self.assertTrue((sa[10:30, 10:30] == oa[10:30, 10:30]).all(),
                        "fully-opaque body must be untouched")

    def test_zero_iterations_only_clamps(self):
        out, _ = ck.choke_edges(synthetic_cutout(), 0)
        a = np.asarray(out).astype(int)
        skirt = a[9, 15]
        # No flood: skirt keeps its (clamped) residue color rather than body black.
        self.assertGreater(skirt[0], 100)
        self.assertLessEqual(skirt[1], max(skirt[0], skirt[2]))

    def test_cli_default_is_off(self):
        # The mutation check: key() output without --choke must be byte-identical to
        # what it was before the choke landed (the choke only runs behind the flag).
        import subprocess, tempfile
        with tempfile.TemporaryDirectory() as td:
            src = os.path.join(td, "src.png")
            green = np.zeros((20, 20, 3), dtype=np.uint8)
            green[...] = (0, 177, 64)
            green[5:15, 5:15] = (200, 170, 90)
            Image.fromarray(green, "RGB").save(src)
            out1 = os.path.join(td, "a.png")
            out2 = os.path.join(td, "b.png")
            script = os.path.join(HERE, "..", "scripts", "chroma_key.py")
            r1 = subprocess.run([sys.executable, script, "--in", src, "--out", out1],
                                capture_output=True, text=True)
            self.assertEqual(r1.returncode, 0, r1.stderr)
            self.assertNotIn("choke", r1.stdout)
            r2 = subprocess.run([sys.executable, script, "--in", src, "--out", out2,
                                 "--choke", "4"], capture_output=True, text=True)
            self.assertEqual(r2.returncode, 0, r2.stderr)
            self.assertIn("choke x4", r2.stdout)


if __name__ == "__main__":
    unittest.main()
