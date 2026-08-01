#!/usr/bin/env python3
"""Measure a render, and RECORD how it was measured.

`render-readback` can crop and it can zoom, so it can answer "does this look
right". It could not answer "is this 1:8 or 1:6.5", and several canon invariants
are numbers: a character's head-to-body proportion, a mark's height-to-width
ratio. Three consecutive sessions hand-rolled the same ruler to close that gap.

The re-work was not the worst of it. The worst of it was that the three
hand-rolled rulers disagreed, and nobody could tell whether a plate had improved
or the method had changed:

    session 1   "1:6.5 -> 1:7.6"     (landmarks unrecorded)
    session 2   "both plates 1:7.2"  (different crown/chin picks)
    session 3   "1:7.04 -> 1:7.26"   (different again; chin +-5px swings it +-0.2)

So a number alone is not a measurement. This module emits the LANDMARKS and the
METHOD alongside the ratio, and writes them beside the image as
`<image>.measure.json`, so the next pass compares like with like instead of
re-deriving a ruler from whatever survived in /tmp.

THREE FAILURES THIS ENCODES, all hit for real:

  1. A CONFIDENT WRONG NUMBER IS WORSE THAN A REFUSAL. One hand-rolled scanner
     used per-row background subtraction and returned crown=0, sole=1534 on a
     1536px plate: the full frame, silently, as if the figure filled it. Every
     detector here validates its own result and REFUSES rather than returning
     nonsense.
  2. THE CHIN RESISTS AUTOMATION. A luminance-minimum chin detector locks onto
     the shadow under the lower lip, not the chin base, and returns a confident
     1:8.8 to 1:9.2 on a figure that is really about 1:7.2. The chin is not
     auto-detected here. Pass `--chin Y`, or take the labelled overlay and read
     it, and the record says which you did.
  3. A RAW BBOX LIES ABOUT A PENDANT. The widest gold in a chest crop is the
     chain across the collarbones, not the mark; and the bail is another narrow
     gold column with nothing in the pixels marking where it ends and the top
     point begins. `star` isolates the compact component and measures from the
     CENTRE, which sidesteps both.

Usage:
    measure.py figure <image> [--chin Y] [--overlay OUT.png] [--no-record]
    measure.py star   <image> [--box x0,y0,x1,y1] [--overlay OUT.png] [--no-record]
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw

SCHEMA = 1

# North Star Cross fabrication spec (christofuture-church-os,
# static/brand/logos/north-star-cross-geometry.md). Top == side, bottom is long.
STAR_TARGET_HW = 1.24
STAR_TARGET_BOTTOM_OVER_SIDE = 1.48
STAR_DEFECT_HW = 1.5


class Unmeasurable(Exception):
    """The image does not support this measurement. Say so; never guess."""


# --------------------------------------------------------------------------- figure


def _dark_rows(a: np.ndarray, x0: float, x1: float, thresh: int) -> np.ndarray:
    """Count of dark pixels per row within a horizontal band of the frame."""
    w = a.shape[1]
    band = a[:, int(w * x0):int(w * x1)]
    return (band.sum(axis=2) / 3.0 < thresh).sum(axis=1)


def measure_figure(img: Image.Image, chin: int | None = None) -> dict:
    """Head-to-body ratio from crown, chin and sole.

    Crown and sole are found by silhouette scan against a light backdrop: dark
    hair in the centre columns, dark footwear low in the frame. Both are then
    sanity-checked, because the failure mode that matters is not "no answer", it
    is "the full frame, reported confidently".

    The chin is NOT detected. See the module docstring: automated chin detection
    is reliably wrong in a specific direction, and a wrong chin moves the ratio
    by more than the differences anyone is trying to measure.
    """
    a = np.asarray(img.convert("RGB")).astype(int)
    h, w = a.shape[0], a.shape[1]

    # A crown must PERSIST. Keying on the first row that clears the threshold
    # picks up a stray dark speck, a shadow or a stray hair and reports a crown
    # tens of pixels above the real one, which silently shrinks the head and
    # inflates the ratio. Require the run to hold for several consecutive rows.
    crown_runs = _dark_rows(a, 0.40, 0.60, 110)
    ok = crown_runs > 8
    persist = 6
    hit = np.nonzero(np.convolve(ok.astype(int), np.ones(persist, int), "valid") == persist)[0]
    if not len(hit):
        raise Unmeasurable(
            "no dark region in the centre columns, so the crown cannot be found. "
            "This scan assumes a dark-haired figure against a light backdrop.")
    crown = int(hit[0])

    sole_runs = _dark_rows(a, 0.28, 0.72, 105)
    lower0 = int(h * 0.80)
    low = np.nonzero(sole_runs[lower0:] > 6)[0]
    if not len(low):
        raise Unmeasurable(
            "no dark region in the bottom fifth of the frame, so the sole cannot "
            "be found. Is the figure cropped above the feet?")
    sole = lower0 + int(low.max())

    figure_px = sole - crown
    # The guard that the silently-broken scanner lacked. A figure filling ~100%
    # of the frame top to bottom means the scan locked onto the frame, not a body.
    if figure_px <= 0 or figure_px > h * 0.98:
        raise Unmeasurable(
            f"crown={crown} sole={sole} spans {figure_px / h:.0%} of the frame, "
            f"which is the signature of a failed scan rather than a tall figure.")

    out = {
        "schema": SCHEMA,
        "kind": "figure",
        "frame": {"w": w, "h": h},
        "landmarks": {"crown": crown, "sole": sole, "chin": chin},
        "figurePx": figure_px,
        "method": {
            "crown": "first row in centre 40-60% columns with >8 px of luminance<110",
            "sole": "lowest row in the bottom 20%, centre 28-72% columns, with >6 px of luminance<105",
            "chin": "operator-supplied" if chin is not None else "NOT MEASURED",
        },
    }

    if chin is None:
        out["headToBody"] = None
        out["note"] = (
            "No chin given, so no ratio. Pass --chin Y, or render --overlay and read "
            "the chin base off the ruler. Automated chin detection locks onto the "
            "shadow under the lower lip and reads roughly a full head too small.")
        return out

    head_px = chin - crown
    if head_px <= 0:
        raise Unmeasurable(f"chin={chin} is at or above crown={crown}.")
    ratio = figure_px / head_px
    out["headPx"] = head_px
    out["headToBody"] = round(ratio, 2)
    out["sensitivity"] = round(abs(figure_px / (head_px + 5) - ratio), 2)
    out["note"] = (
        f"1:{ratio:.2f}. A 5px error in the chin pick moves this by about "
        f"{out['sensitivity']:.2f}, so quote it to one decimal and compare only "
        f"against measurements whose landmarks are recorded.")
    return out


def overlay_figure(img: Image.Image, m: dict, step: int = 10) -> Image.Image:
    """A labelled ruler across the chin zone, for reading the one landmark that
    resists automation. Ticks every `step` px, majors every 50."""
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    w = im.size[0]
    crown, sole = m["landmarks"]["crown"], m["landmarks"]["sole"]
    for y, colour, label in ((crown, (0, 200, 90), "crown"), (sole, (0, 200, 90), "sole")):
        d.line([(0, y), (w, y)], fill=colour, width=3)
        d.text((6, max(0, y - 14)), f"{label} {y}", fill=colour)
    lo = crown + int((sole - crown) * 0.08)
    hi = crown + int((sole - crown) * 0.22)
    for y in range(lo, hi + 1, step):
        major = y % 50 == 0
        d.line([(int(w * 0.28), y), (int(w * 0.72), y)],
               fill=(220, 0, 0) if major else (0, 140, 255), width=2 if major else 1)
        d.text((int(w * 0.29), y - 9), str(y), fill=(255, 0, 0) if major else (0, 0, 180))
    return im


# --------------------------------------------------------------------------- star


def _gold_mask(a: np.ndarray) -> np.ndarray:
    """Saturated warm metal, NOT merely a warm pixel.

    The first cut was `r>120 and g>90 and b < r-35`, which a warm plaster or
    limewash backdrop passes easily. On a pendant shot against exactly that, the
    mask selected the ENTIRE FRAME (x 0-1023) and the measurement came back 0.93,
    a plausible-looking number derived from the background. Gold on a warm ground
    is separated by SATURATION and by channel ordering, not by warmth alone.
    """
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mx = np.maximum(np.maximum(r, g), b)
    mn = np.minimum(np.minimum(r, g), b)
    sat = (mx - mn) / np.maximum(mx, 1)
    return (r > 110) & (r > g + 12) & (g > b + 18) & (sat > 0.30)


def _components(mask: np.ndarray) -> list[np.ndarray]:
    """Connected components (8-way), iterative so a large blob cannot blow the stack."""
    h, w = mask.shape
    seen = np.zeros_like(mask, bool)
    out = []
    for y0, x0 in zip(*np.nonzero(mask)):
        if seen[y0, x0]:
            continue
        stack, pix = [(int(y0), int(x0))], []
        seen[y0, x0] = True
        while stack:
            y, x = stack.pop()
            pix.append((y, x))
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < h and 0 <= nx < w and mask[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True
                        stack.append((ny, nx))
        out.append(np.array(pix))
    return out


# --------------------------------------------------------------------------- star: WITHDRAWN
#
# `measure star` was REMOVED on 2026-08-01, the day it shipped, because it gave
# FALSE PRECISION: authoritative-looking numbers that were wrong five times out of
# five on real plates.
#
#   0.93   a mask that had selected the warm plaster backdrop, not the pendant
#   0.74   PASS, having locked onto a jacket button
#   6.11   the chain, connected to the pendant inside the crop
#   11.25  a crop that did not isolate the mark
#   PASS   on an obviously equilateral compass star the operator rejected on sight
#
# The last one is the disqualifying one. The function assumed "top arm == side
# arm, by spec" and therefore never measured the top arm, which is the single most
# important thing to check: a short top point is exactly what turns this mark from
# a cross into a compass star. It assumed away the defect it existed to catch, and
# each failure was patched rather than treated as evidence about the approach.
#
# THE LESSON, which is the framework's own thesis and was being worked against:
# a GOLDEN IS HUMAN JUDGEMENT, FROZEN. The right instrument for "does this mark
# look right" is a person's eye against a blessed reference plate, and then that
# blessed plate conditions every render after it. Gary, 2026-08-01: "I'm clearly
# going to need to just keep rerolling with you until it's good, then you just use
# those goldens. Reminds me of the importance of the human eye."
#
# Do not reintroduce a geometry checker here. Judge the mark against
# `reference/north-star-cross/turnaround.png` by eye, bless it, and condition on it.


# --------------------------------------------------------------------------- cli


def record_path(image: pathlib.Path) -> pathlib.Path:
    return image.parent / (image.name + ".measure.json")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("figure", help="head-to-body ratio from crown, chin and sole")
    f.add_argument("image")
    f.add_argument("--chin", type=int, help="chin-base y in pixels; the one landmark "
                                            "that must not be auto-detected")
    for p in (f,):
        p.add_argument("--overlay", help="write a labelled overlay here")
        p.add_argument("--no-record", action="store_true",
                       help="do not write <image>.measure.json")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.image)
    if not path.exists():
        print(f"measure: no such image: {path}", file=sys.stderr)
        return 2
    img = Image.open(path)

    try:
        m = measure_figure(img, args.chin)
    except Unmeasurable as e:
        # A refusal, not a number. This is the whole point of the module.
        print(f"measure: UNMEASURABLE: {e}", file=sys.stderr)
        return 2

    m["image"] = str(path)
    if not args.no_record:
        record_path(path).write_text(json.dumps(m, indent=2) + "\n")
        m["recordedAt"] = str(record_path(path))
    if args.overlay:
        ov = overlay_figure(img, m)
        ov.save(args.overlay)
        m["overlay"] = args.overlay
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
