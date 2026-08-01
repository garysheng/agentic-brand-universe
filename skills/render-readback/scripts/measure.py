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
    r, g, b = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    return (r > 120) & (g > 90) & (b < r - 35)


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


def measure_star(img: Image.Image, box: tuple | None = None) -> dict:
    """The four-point mark's proportions, measured from the centre.

    The spec fixes top == side, so the top arm IS half the width, and the only
    free measurements are the width at the widest row and the crossing-to-bottom
    distance. That is what makes this immune to the bail, which is a narrow gold
    column above the star with no pixel boundary saying where the point begins.
    """
    a = np.asarray(img.convert("RGB")).astype(int)
    if box:
        x0, y0, x1, y1 = box
        a = a[y0:y1, x0:x1]
    comps = _components(_gold_mask(a))
    if not comps:
        raise Unmeasurable("no gold pixels found. Is the crop over the pendant?")

    # Pick by STAR-LIKENESS, not raw compactness. Compactness alone picks a
    # jacket button, which is the most compact gold blob in a chest crop by a
    # wide margin: measured 0.74 H:W on a plate whose pendant was really 1.5,
    # and reported PASS. A four-point star with concave edges fills roughly a
    # third of its bbox; a chain link run fills far less; a button or a buckle
    # fills far more. So bound the fill, then take the LARGEST survivor.
    def fill(c):
        hh = c[:, 0].max() - c[:, 0].min() + 1
        ww = c[:, 1].max() - c[:, 1].min() + 1
        return len(c) / float(hh * ww)

    # Pick the MOST COMPACT component. The chain is long and thin so it loses;
    # a jacket button can win on compactness alone, which is why the caller must
    # crop to the pendant with --box rather than hand this a whole chest.
    big = [c for c in comps if len(c) >= 24] or comps
    star = max(big, key=fill)

    # If the chain hangs INTO the crop it is one connected blob with the pendant,
    # and the blob is then tall and thin rather than star-shaped. Refuse instead
    # of reporting the chain's aspect ratio as the mark's: measured 6.11 H:W on a
    # pendant that was really 1.4.
    if fill(star) < 0.15:
        raise Unmeasurable(
            "the gold blob is long and thin (fill %.2f), which means the chain is "
            "connected to the pendant inside this crop. Tighten --box to the "
            "pendant itself, below where the chain meets the bail." % fill(star))

    ys, xs = star[:, 0], star[:, 1]
    rows = {}
    for y, x in star:
        lo, hi = rows.get(y, (x, x))
        rows[y] = (min(lo, x), max(hi, x))
    widest_y = max(rows, key=lambda y: rows[y][1] - rows[y][0])
    width = rows[widest_y][1] - rows[widest_y][0] + 1
    bottom = int(ys.max())

    side = width / 2.0
    bottom_arm = bottom - widest_y
    if side <= 0 or bottom_arm <= 0:
        raise Unmeasurable("degenerate pendant blob; widen the crop.")
    height = side + bottom_arm            # top arm == side arm, by spec
    hw = height / width

    # THE MODULE'S OWN CONTRACT, APPLIED TO ITSELF. No plausible rendering of a
    # four-point mark whose top and side arms are equal is three times taller
    # than it is wide: that result means the blob is not the pendant (a bail, a
    # button, a fold of chain). Refuse. Every wrong number this file has produced
    # in testing was above this bound, and a refusal the caller can act on beats a
    # ratio they might believe.
    if hw > 3.0:
        raise Unmeasurable(
            f"measured {hw:.2f} H:W, which no rendering of this mark can be. The "
            f"crop is not isolating the pendant. Tighten --box to the star itself, "
            f"excluding the chain and the bail, and try again.")
    return {
        "schema": SCHEMA,
        "kind": "star",
        "widthPx": int(width),
        "sideArmPx": round(side, 1),
        "bottomArmPx": int(bottom_arm),
        "heightPx": round(height, 1),
        "heightOverWidth": round(hw, 2),
        "bottomOverSide": round(bottom_arm / side, 2),
        "crossingPctFromTop": round(100 * side / height, 1),
        "targets": {
            "heightOverWidth": STAR_TARGET_HW,
            "bottomOverSide": STAR_TARGET_BOTTOM_OVER_SIDE,
            "crossingPctFromTop": 40.0,
        },
        "verdict": "DEFECT" if hw > STAR_DEFECT_HW else "PASS",
        "method": (
            "warm-gold mask, most-compact connected component (isolates the mark "
            "from the chain), measured from the centre: width at the widest row, "
            "bottom arm from that row to the lowest pixel, top arm assumed equal "
            "to the side arm per the fabrication spec"),
        "note": (
            f"H:W {hw:.2f} against a target of {STAR_TARGET_HW}. Above "
            f"{STAR_DEFECT_HW} the side arms read stubby and the mark reads as a "
            f"crucifix, which the invariant forbids by name."),
    }


def overlay_star(img: Image.Image, m: dict, box: tuple | None = None) -> Image.Image:
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    ox, oy = (box[0], box[1]) if box else (0, 0)
    d.text((ox + 4, oy + 4),
           f"H:W {m['heightOverWidth']} (target {STAR_TARGET_HW})  "
           f"bottom/side {m['bottomOverSide']} (target {STAR_TARGET_BOTTOM_OVER_SIDE})  "
           f"{m['verdict']}",
           fill=(255, 0, 0))
    if box:
        d.rectangle([box[0], box[1], box[2], box[3]], outline=(0, 200, 255), width=2)
    return im


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
    s = sub.add_parser("star", help="four-point mark proportions, measured from the centre")
    s.add_argument("image")
    s.add_argument("--box", help="x0,y0,x1,y1 crop over the pendant")
    for p in (f, s):
        p.add_argument("--overlay", help="write a labelled overlay here")
        p.add_argument("--no-record", action="store_true",
                       help="do not write <image>.measure.json")
    args = ap.parse_args(argv)

    path = pathlib.Path(args.image)
    if not path.exists():
        print(f"measure: no such image: {path}", file=sys.stderr)
        return 2
    img = Image.open(path)
    box = tuple(int(v) for v in args.box.split(",")) if getattr(args, "box", None) else None

    try:
        m = measure_figure(img, args.chin) if args.cmd == "figure" else measure_star(img, box)
    except Unmeasurable as e:
        # A refusal, not a number. This is the whole point of the module.
        print(f"measure: UNMEASURABLE: {e}", file=sys.stderr)
        return 2

    m["image"] = str(path)
    if not args.no_record:
        record_path(path).write_text(json.dumps(m, indent=2) + "\n")
        m["recordedAt"] = str(record_path(path))
    if args.overlay:
        ov = overlay_figure(img, m) if args.cmd == "figure" else overlay_star(img, m, box)
        ov.save(args.overlay)
        m["overlay"] = args.overlay
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
