#!/usr/bin/env python3
# /// script
# dependencies = ["pillow", "numpy"]
# ///
# ^ PEP 723 inline metadata, so `uv run <this script>` resolves Pillow itself.
#   NUMPY WAS MISSING FROM THIS LIST until 2026-08-20, and this module has imported
#   it since the day it shipped, so `uv run measure.py` — the invocation the block
#   exists to make work — died on ModuleNotFoundError every time. It only ever ran
#   for people who happened to have numpy on the ambient env. A declaration that is
#   not exercised is a declaration that is wrong.
#   Before this, every invocation needed `uv run --with pillow` typed from memory,
#   and the takeoff-thursdays run (2026-08) paid that tax on every single readback.
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
    measure.py figure   <image> [--chin Y] [--overlay OUT.png] [--no-record]
    measure.py periodic <image> --patch x0,y0,x1,y1 [--overlay OUT.png] [--no-record]
    measure.py patch    <image> --patch x0,y0,x1,y1 [--target '#RRGGBB'] [--no-record]
    measure.py extent   <image> --feature warm-chroma [--min-chroma N] [--blur PX]
                                [--bridge PX] [--allow-clipped] [--no-record]

`periodic` and `patch` are the two rulers a MEDIUM needs, as opposed to the one a
BODY needs. Both take a patch in FRACTIONAL frame coordinates, and both record it,
because the number is meaningless without the region it came from.

`extent` is the ruler a FEATURE needs: not what the sheet is made of, but how far
one thing on it runs, how continuous it is, and how many of them there are. Any
gate phrased as "short", "one place only", "does not reach the edge" is an extent
claim, and every one of them was vibes until this existed. It takes a PREDICATE
rather than a patch, and records that instead. See their own docstrings for the
failures each encodes.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

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


# --------------------------------------------------------------------------- patches
#
# THE OTHER KIND OF MEASUREMENT. `figure` measures a BODY; these two measure a
# MEDIUM. A register whose whole argument is "this is a printed sheet" has
# properties that are numbers — how coarse the screen is, how pale the ink is —
# and neither is a thing an eye can hold steady across a batch or across weeks.
#
# EARNED TWICE IN ONE DAY. proof-of-vibes' cloud exploration (2026-08-20) asked a
# halftone plate for a COARSE screen three rounds running and got a fine one every
# time, and nobody could tell, because "coarse" is a word. Round 3 hand-rolled an
# autocorrelation dot-pitch ruler plus a patch-mean colour ruler over nine plates,
# reported the misses as numbers for the first time, and threw both scripts away;
# round 4 needed the identical method hours later to stay comparable to round 3.
# That is the same three-hand-rolled-rulers-that-disagree story this module was
# built for, replayed on the medium instead of on the figure.
#
# THE PATCH IS REQUIRED AND IS RECORDED, for exactly the reason the figure's
# landmarks are. A dot pitch read over a cloud is not a dot pitch read over open
# sky, and a mean colour is entirely a statement about which pixels were averaged.
# There is no default patch: a default would silently make two runs incomparable
# while looking like one method.


def parse_patch(s: str) -> tuple[float, float, float, float]:
    """`x0,y0,x1,y1` in FRACTIONS of the frame, so it ports across sizes."""
    try:
        x0, y0, x1, y1 = (float(v) for v in s.split(","))
    except ValueError:
        raise Unmeasurable(f"--patch wants four comma-separated fractions, got {s!r}")
    if not (0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1):
        raise Unmeasurable(
            f"--patch {s!r} is not a fractional box inside the frame "
            f"(want 0 <= x0 < x1 <= 1 and 0 <= y0 < y1 <= 1). These are FRACTIONS, "
            f"not pixels.")
    return x0, y0, x1, y1


def _crop(a: np.ndarray, patch: tuple[float, float, float, float]) -> np.ndarray:
    h, w = a.shape[0], a.shape[1]
    x0, y0, x1, y1 = patch
    return a[int(h * y0):int(h * y1), int(w * x0):int(w * x1)]


def _autocorr(rows: np.ndarray) -> np.ndarray:
    """Mean 1-D autocorrelation of a stack of detrended rows, normalised to r[0]=1."""
    n = rows.shape[1]
    f = np.fft.rfft(rows, n=2 * n, axis=1)
    r = np.fft.irfft(f * np.conj(f), n=2 * n, axis=1)[:, :n].real
    r = r.mean(axis=0)
    return r / r[0] if r[0] > 0 else r


def _detrend(g: np.ndarray, axis: int) -> np.ndarray:
    """Strip the TONAL RAMP so only the screen is left.

    A halftone sky is a slow density gradient with a fast dot grid on top. The
    gradient is by far the larger signal, and an autocorrelation run against it
    returns the size of the PICTURE, not the size of the DOT: on a cloud plate it
    reports a period of hundreds of pixels and a confident, wrong dots-per-width
    in the single digits. Subtracting a running mean roughly a dozen dots wide
    removes the picture and leaves the screen.
    """
    lines = g if axis == 1 else g.T
    k = max(9, (lines.shape[1] // 24) | 1)
    pad = k // 2
    padded = np.pad(lines, ((0, 0), (pad, pad)), mode="edge")
    kern = np.ones(k) / k
    smooth = np.apply_along_axis(lambda v: np.convolve(v, kern, "valid"), 1, padded)
    return lines - smooth[:, : lines.shape[1]]


FLOOR = 0.10  # below this a "repeat" is noise wearing a number


def _fundamental(r: np.ndarray, span: int) -> tuple[int, float, list]:
    """The FUNDAMENTAL period, its confidence, and the whole harmonic ladder.

    THE TRAP, and it cost a factor of two on real plates before it was caught. A
    screen repeats at p, so its autocorrelation peaks at p, 2p, 3p — and on a
    rotated (45-degree) screen the harmonic is routinely LOUDER than the
    fundamental, because two lattice directions reinforce there. Taking the
    STRONGEST local maximum therefore reports 2p and halves the dot count. Taking
    the FIRST local maximum has the opposite failure, latching onto a single-pixel
    resampling artefact. Both were tried and both were wrong.

    So the pick is the textbook one and not a threshold anybody tuned: a lag is
    the fundamental if IT HAS A HARMONIC — another peak near twice itself — and
    the smallest such lag wins. A ladder with no harmonic anywhere in it is not a
    screen this method can read, and that REFUSES. A confident wrong pitch is
    worse than no pitch, and a factor-of-two error is the confident wrong pitch
    this measurement is most prone to.

    The full ladder is returned and recorded either way, because it is the
    evidence that reconciles two measurements disagreeing by an integer factor —
    exactly how a hand-rolled ruler and this one differed, with neither able to
    show its work.
    """
    hi = max(4, span // 4)
    maxima = [(lag, float(r[lag])) for lag in range(2, min(hi, len(r) - 1))
              if r[lag] > r[lag - 1] and r[lag] >= r[lag + 1]]
    ladder = [{"lagPx": l, "r": round(v, 3)} for l, v in maxima]
    if not maxima:
        raise Unmeasurable(
            "no local maximum in the autocorrelation, so this patch has no "
            "repeating structure to measure. Is it flat, or is the screen finer "
            "than the pixel grid?")
    loudest = max(v for _, v in maxima)
    if loudest < FLOOR:
        raise Unmeasurable(
            f"the strongest repeat in this patch is only {loudest:.3f} correlation, "
            f"which is noise rather than a screen. Two innocent causes: the patch "
            f"is at or near FULL INK COVERAGE, where a halftone has no dots left to "
            f"measure, or the screen is finer than the pixel grid. A REFUSAL HERE IS "
            f"THE POINT: a confident wrong pitch is worse than no pitch.")

    lags = [l for l, v in maxima if v >= FLOOR]
    if len(lags) == 1:
        # ONE rung is not a ladder. The refusal below exists to stop the wrong rung
        # being picked, and a single peak offers no wrong rung to pick.
        return lags[0], float(dict(maxima)[lags[0]]), ladder
    for lag in lags:
        # Peaks land off-integer on a real screen (a 7.2px pitch shows up at 8 and
        # 14), so the window must be proportional. +-1 was tried and refused half
        # of a set of plates whose screens were perfectly legible.
        tol = max(2, round(0.20 * lag))
        if any(abs(other - 2 * lag) <= tol for other in lags):
            return lag, float(dict(maxima)[lag]), ladder
    raise Unmeasurable(
        f"peaks at lags {lags} and not one of them has a harmonic near twice "
        f"itself, so there is no fundamental to report and any single number here "
        f"would be a guess with a factor-of-two error in it. On a printed plate the "
        f"usual innocent cause is that the screen is DAMAGED — plugged shadows or a "
        f"broken dot — so there is no clean pitch left. Read harmonicLadder and pick "
        f"by eye, or measure a patch with more intact screen in it.")


def measure_periodic(img: Image.Image, patch: tuple[float, float, float, float]) -> dict:
    """Fundamental spatial period of a repeating screen, over a declared patch.

    Answers "how coarse is this halftone", "is this weave the same weave", "did
    the grid pitch drift" — the class of question a register can regress on
    silently, because a look is judged by eye and a pitch is not visible by eye at
    any size a person reviews at.

    Reported as `dotsAcrossWidth` (frame width / horizontal repeat), which is how
    a prompt should ASK for a screen too: a count across the frame is measurable
    on read-back, where "coarse" and "fine" are not.
    """
    a = np.asarray(img.convert("RGB")).astype(float)
    h, w = a.shape[0], a.shape[1]
    box = _crop(a, patch)
    if box.shape[0] < 32 or box.shape[1] < 32:
        raise Unmeasurable(
            f"patch is {box.shape[1]}x{box.shape[0]}px, too small to hold enough "
            f"cycles to measure. Give it at least 32px on each side.")
    g = box.mean(axis=2)

    out = {
        "schema": SCHEMA,
        "kind": "periodic",
        "frame": {"w": w, "h": h},
        "patch": {"fractional": list(patch),
                  "px": {"w": int(box.shape[1]), "h": int(box.shape[0])}},
        "method": {
            "detrend": "subtract a running mean ~1/24 of the patch, to strip the tonal ramp",
            "estimator": "FFT autocorrelation per line, averaged across lines, normalised to r[0]=1",
            "pick": ("SMALLEST local maximum that HAS A HARMONIC (another peak within "
                     "20% of twice its lag), searched within a quarter of the line "
                     "length, so a louder harmonic cannot be mistaken for the "
                     "fundamental. A ladder with only ONE peak is taken as-is."),
            "refusesWhen": (f"no local maximum, or the loudest peak < {FLOOR:g}, or no "
                            f"peak in the ladder has a harmonic"),
        },
        "axes": {},
    }

    for name, axis in (("x", 1), ("y", 0)):
        lines = _detrend(g, axis)
        r = _autocorr(lines)
        lag, peak, ladder = _fundamental(r, lines.shape[1])
        out["axes"][name] = {"periodPx": lag, "confidence": round(peak, 3),
                             "harmonicLadder": ladder}

    px = out["axes"]["x"]["periodPx"]
    out["dotsAcrossWidth"] = int(round(w / px))
    out["note"] = (
        f"{out['dotsAcrossWidth']} dots across the frame width "
        f"(horizontal repeat {px}px, confidence {out['axes']['x']['confidence']:.2f}). "
        f"Compare only against measurements over the SAME fractional patch; a pitch "
        f"read over a cloud is not a pitch read over open sky. If another measurement "
        f"disagrees by an integer factor, check it against harmonicLadder before "
        f"believing either.")
    return out


def overlay_patch(img: Image.Image, m: dict) -> Image.Image:
    """Draw the measured box, so the record and the region can be checked together."""
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    w, h = im.size
    x0, y0, x1, y1 = m["patch"]["fractional"]
    d.rectangle([int(w * x0), int(h * y0), int(w * x1), int(h * y1)],
                outline=(220, 0, 0), width=4)
    d.text((int(w * x0) + 8, max(0, int(h * y0) - 14)),
           m.get("note", "").split(".")[0], fill=(220, 0, 0))
    return im


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(int(round(v)) for v in rgb)


def measure_patch(img: Image.Image, patch: tuple[float, float, float, float],
                  target: str | None = None) -> dict:
    """Mean colour over a declared patch, and its distance from a target.

    The colour half of the same problem. "The blue is too deep" is a judgement
    nobody can hold across three rounds and six weeks; `dHex` is 107 on one plate
    and 19 on another and the correction is then a fact rather than an argument.

    `dHex` is the MAX PER-CHANNEL distance, not a Euclidean one, deliberately: a
    single channel drifting 60 while the other two hold is exactly the failure a
    mean distance hides.
    """
    a = np.asarray(img.convert("RGB")).astype(float)
    h, w = a.shape[0], a.shape[1]
    box = _crop(a, patch)
    if box.size == 0:
        raise Unmeasurable("patch selects zero pixels.")
    mean = box.reshape(-1, 3).mean(axis=0)

    out = {
        "schema": SCHEMA,
        "kind": "patch",
        "frame": {"w": w, "h": h},
        "patch": {"fractional": list(patch),
                  "px": {"w": int(box.shape[1]), "h": int(box.shape[0])}},
        "mean": {"rgb": [round(v, 1) for v in mean], "hex": _hex(mean)},
        "method": {"estimator": "arithmetic mean of sRGB channels over the patch",
                   "distance": "max per-channel absolute difference from the target"},
    }
    if target:
        t = target.lstrip("#")
        if len(t) != 6:
            raise Unmeasurable(f"--target wants #RRGGBB, got {target!r}")
        tr = [int(t[i:i + 2], 16) for i in (0, 2, 4)]
        d = max(abs(mean[i] - tr[i]) for i in range(3))
        out["target"] = {"hex": "#" + t.upper(), "rgb": tr}
        out["dHex"] = int(round(d))
        out["note"] = (f"{out['mean']['hex']} against {out['target']['hex']}, "
                       f"max per-channel distance {out['dHex']}.")
    else:
        out["note"] = f"{out['mean']['hex']}. No --target, so no distance."
    return out


# --------------------------------------------------------------------------- extent


def _lab(a: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """CIELAB (D65) from sRGB. Computed here rather than via ImageCms because
    PIL's LAB mode packs a* and b* into unsigned bytes and clips them, which
    reports every plate's warm peak as the same saturated 127."""
    x = a / 255.0
    x = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    m = np.array([[0.4124, 0.3576, 0.1805],
                  [0.2126, 0.7152, 0.0722],
                  [0.0193, 0.1192, 0.9505]])
    xyz = (x @ m.T) / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 0.008856, np.cbrt(xyz), 7.787 * xyz + 16 / 116)
    return (116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]),
            200 * (f[..., 1] - f[..., 2]))


#: Above this the mask is describing the SHEET, not a feature on it.
MAX_MASK_FRACTION = 0.25

FEATURES = ("warm-chroma",)


def _dilate(mask: np.ndarray, r: int) -> np.ndarray:
    """Square dilation by r, via the max over shifted copies. No scipy."""
    out = mask.copy()
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            out |= np.roll(np.roll(mask, dy, axis=0), dx, axis=1)
    return out


def measure_extent(img: Image.Image, feature: str, min_chroma: float = 6.0,
                   blur: float = 3.0, min_region_frac: float = 0.0002,
                   allow_clipped: bool = False, bridge: int = 0) -> dict:
    """How far a feature RUNS, how continuous it is, and how many there are.

    `periodic` measures a repeat and `patch` measures a colour, so a gate that
    says "coarse" or "too blue" became a number. A gate that says "no longer than
    about a sixth of the frame width, broken, fading at both ends" did not, and a
    length judged by eye is the same class of claim "coarse" was before v0.40.

    Earned by `pov-fine-screen-halftone`, whose prismatic-fringe assertion failed
    its own pack round-trip TWICE on two different ref sets, both times called in
    prose, and the two calls were not comparable because no method was recorded
    (docs/GAPS.md G38).

    THE PREDICATE IS THE PRODUCT, and it is stated by the caller, never guessed.
    `warm-chroma` scores each pixel by how far it lies on the WARM side in
    CIELAB, `max(a*, b*, 0)`: gold is +b*, rose is +a*, and a cool blue ink is
    negative in both, so an accent ink separates from the ground without any
    per-plate fitting. THREE EARLIER PREDICATES WERE TRIED AND ALL THREE FAILED,
    which is why this one is written down rather than re-derived:

      1. distance off the canonical paper->ink axis. The saturated plates put
         12-16% of their pixels off it, because their own ink is not the
         canonical ink, so the deepest-fringed plate scored LOWEST.
      2. the same, with the axis fitted per plate. Halftone dot edges are
         partial coverage, which does not travel that axis in sRGB.
      3. the same again in linear light, where partial coverage IS linear. Still
         useless, because these sheets are not one ink: the blue itself drifts
         in hue across the frame.

    BLUR IS NOT COSMETIC AND IS RECORDED. On a halftone the accent inks arrive as
    separated dots, so an unblurred mask has thousands of one-dot components and
    "how far does it run" is answered per DOT, which is the wrong question. The
    blur merges the screen into the region the eye actually reads.

    `occupancy` is the answer to the half of the gate that is not length. Bin the
    region along its own principal axis and report the fraction of bins that
    carry pixels: a continuous drawn line approaches 1.0, a broken dotty stretch
    fades well below it. Length was never the only way a fringe fails, and this
    is the number that says which failure it is.
    """
    if feature not in FEATURES:
        raise Unmeasurable(
            f"unknown --feature {feature!r}. Known: {', '.join(FEATURES)}. "
            f"The predicate is never guessed: a feature nobody named is a "
            f"measurement of whatever happened to be bright.")

    rgb = img.convert("RGB")
    if blur > 0:
        rgb = rgb.filter(ImageFilter.GaussianBlur(blur))
    a = np.asarray(rgb).astype(float)
    h, w = a.shape[0], a.shape[1]
    _, a_star, b_star = _lab(a)

    # REFUSAL 1: no cool ground for a warm feature to be a departure FROM.
    coolest = float(b_star.min())
    if coolest > -5.0:
        raise Unmeasurable(
            f"this frame has no cool ground (min b* {coolest:.1f}), so "
            f"'warm-chroma' has nothing to be a departure from. On a warm or "
            f"neutral sheet every pixel is the feature.")

    score = np.maximum(np.maximum(a_star, b_star), 0.0)
    mask = score >= min_chroma

    # REFUSAL 2: the mask is describing the sheet rather than a feature on it.
    frac = float(mask.mean())
    if frac > MAX_MASK_FRACTION:
        raise Unmeasurable(
            f"'warm-chroma' at min-chroma {min_chroma} selects {100 * frac:.1f}% "
            f"of the frame, over the {100 * MAX_MASK_FRACTION:.0f}% ceiling. That "
            f"is a description of the ground, not of a feature on it. Raise "
            f"--min-chroma, or this is the wrong predicate for this image.")

    # BRIDGING answers a different question from connectivity, and the gate asks
    # both. A dotty fringe running down one cloud edge arrives as several
    # separated stretches; unbridged, "how long is it" is answered per STRETCH,
    # which understates a feature the eye plainly reads as one line. Bridged, the
    # stretches merge and the answer is how far the fringe RUNS. The radius is
    # stated by the caller and recorded, because the two numbers are different
    # claims and a reader must be able to tell which one they are holding. Area
    # and occupancy are always computed from the ORIGINAL mask, so bridging can
    # never inflate how much ink is actually there.
    grouped = _dilate(mask, bridge) if bridge > 0 else mask

    min_px = max(1, int(min_region_frac * h * w))
    regions = []
    for group in _components(grouped):
        if bridge > 0:
            sel = mask[group[:, 0], group[:, 1]]
            pix = group[sel]
            if len(pix) == 0:
                continue
        else:
            pix = group
        if len(pix) < min_px:
            continue
        ys, xs = pix[:, 0].astype(float), pix[:, 1].astype(float)
        pts = np.stack([xs, ys], 1)
        centred = pts - pts.mean(0)
        # Principal axis: a fringe running down a cloud edge is diagonal, so a
        # bbox width alone understates it and a bbox diagonal overstates it.
        _, _, vt = np.linalg.svd(centred, full_matrices=False)
        along = centred @ vt[0]
        ext = float(np.ptp(along))
        nbins = max(1, int(round(ext / 8.0)))
        hist, _ = np.histogram(along, bins=nbins)
        regions.append({
            "areaPx": int(len(pix)),
            "areaFrac": round(len(pix) / (h * w), 6),
            "bboxFrac": {"x0": round(xs.min() / w, 4), "x1": round(xs.max() / w, 4),
                         "y0": round(ys.min() / h, 4), "y1": round(ys.max() / h, 4)},
            "axisExtentFracW": round(ext / w, 4),
            "axisExtentFracH": round(ext / h, 4),
            "occupancy": round(float((hist > 0).mean()), 3),
            "peakChroma": round(float(score[pix[:, 0], pix[:, 1]].max()), 1),
            "touchesFrameEdge": bool(xs.min() <= 1 or ys.min() <= 1
                                     or xs.max() >= w - 2 or ys.max() >= h - 2),
        })
    regions.sort(key=lambda r: r["axisExtentFracW"], reverse=True)

    out = {
        "schema": SCHEMA,
        "kind": "extent",
        "frame": {"w": w, "h": h},
        "feature": feature,
        "method": {
            "predicate": "max(a*, b*, 0) in CIELAB D65, the WARM side",
            "minChroma": min_chroma,
            "blurPx": blur,
            "minRegionFrac": min_region_frac,
            "connectivity": "8-way",
            "bridgePx": bridge,
            "extent": "peak-to-peak along the region's own principal axis",
            "occupancy": "fraction of 8px bins along that axis carrying pixels",
        },
        "maskFrac": round(frac, 5),
        "regions": len(regions),
        "detail": regions,
    }
    if not regions:
        out["note"] = (f"no region of {feature} survives min-chroma {min_chroma} "
                       f"at {min_region_frac} of frame area. That is a MEASUREMENT, "
                       f"not a refusal: a plate with no such feature has no extent.")
        return out

    big = regions[0]
    # REFUSAL 3: a clipped feature's extent is a lower bound, not a measurement.
    if big["touchesFrameEdge"] and not allow_clipped:
        raise Unmeasurable(
            f"the largest region touches the frame edge, so its true extent runs "
            f"off the sheet and {big['axisExtentFracW']} of frame width is a LOWER "
            f"BOUND rather than a measurement. Re-run with --allow-clipped to "
            f"record it as one.")
    out["longestRunFracW"] = big["axisExtentFracW"]
    out["longestRunOccupancy"] = big["occupancy"]
    out["extentIsLowerBound"] = big["touchesFrameEdge"]
    out["note"] = (
        f"{len(regions)} region(s); the longest runs {big['axisExtentFracW']} of "
        f"frame width ({big['axisExtentFracH']} of height) at occupancy "
        f"{big['occupancy']}"
        + (" (LOWER BOUND: it is clipped by the frame)." if big["touchesFrameEdge"]
           else "."))
    return out


def overlay_extent(img: Image.Image, m: dict) -> Image.Image:
    """Box every region found, so a human can see WHAT was measured before
    trusting the number. The same discipline `star` was withdrawn for lacking."""
    im = img.convert("RGB").copy()
    d = ImageDraw.Draw(im)
    w, h = im.size
    for i, r in enumerate(m.get("detail", [])):
        bb = r["bboxFrac"]
        box = [int(w * bb["x0"]), int(h * bb["y0"]), int(w * bb["x1"]), int(h * bb["y1"])]
        colour = (220, 0, 0) if i == 0 else (0, 130, 220)
        d.rectangle(box, outline=colour, width=3)
        d.text((box[0] + 6, max(0, box[1] - 14)),
               f"{r['axisExtentFracW']}W occ {r['occupancy']}", fill=colour)
    return im


# --------------------------------------------------------------------------- cli


def record_path(image: pathlib.Path) -> pathlib.Path:
    return image.parent / (image.name + ".measure.json")


def write_record(image: pathlib.Path, m: dict) -> pathlib.Path:
    """MERGE by kind, never clobber.

    One plate legitimately carries several measurements at once — a cloud plate
    has both a dot pitch and a sky colour — and the first shape of this file was a
    single flat record, so measuring a second thing DELETED the first without
    saying so. The record is now `{"<kind>": {...}}`. A legacy flat record is
    folded under its own kind rather than discarded, because a measurement already
    taken is exactly the thing this module exists to stop people re-deriving.
    """
    p = record_path(image)
    doc = {}
    if p.exists():
        try:
            prev = json.loads(p.read_text())
            doc = {prev["kind"]: prev} if "kind" in prev else prev
        except (ValueError, KeyError):
            doc = {}
    doc[m["kind"]] = m
    p.write_text(json.dumps(doc, indent=2) + "\n")
    return p


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("figure", help="head-to-body ratio from crown, chin and sole")
    f.add_argument("--chin", type=int, help="chin-base y in pixels; the one landmark "
                                            "that must not be auto-detected")
    per = sub.add_parser("periodic", help="dot pitch / weave / grid period over a patch")
    pat = sub.add_parser("patch", help="mean colour over a patch, and its distance from a target")
    pat.add_argument("--target", help="#RRGGBB the patch is being compared against")
    for p in (per, pat):
        p.add_argument("--patch", required=True, metavar="x0,y0,x1,y1",
                       help="the measured region, in FRACTIONS of the frame. Required, "
                            "and recorded: a pitch or a colour is a statement about a "
                            "region, and two runs over different regions are not "
                            "comparable however alike the numbers look.")
    ext = sub.add_parser("extent", help="how far a feature RUNS, how continuous, how many")
    ext.add_argument("--feature", required=True, choices=FEATURES,
                     help="the predicate that DEFINES the feature. Required and "
                          "recorded: an extent is a statement about a predicate, and "
                          "two runs under different predicates are not comparable.")
    ext.add_argument("--min-chroma", type=float, default=6.0,
                     help="CIELAB units on the warm side (default 6)")
    ext.add_argument("--blur", type=float, default=3.0,
                     help="px; merges a halftone screen into the region the eye reads "
                          "(default 3). 0 measures individual dots, which is the wrong "
                          "question.")
    ext.add_argument("--min-region-frac", type=float, default=0.0002,
                     help="ignore regions smaller than this fraction of frame area")
    ext.add_argument("--bridge", type=int, default=0, metavar="PX",
                     help="merge separated stretches within PX into ONE region before "
                          "measuring, so a dotty fringe the eye reads as one line is "
                          "measured as one line. Recorded. Area and occupancy still "
                          "come from the unbridged mask.")
    ext.add_argument("--allow-clipped", action="store_true",
                     help="record a frame-clipped extent as an explicit LOWER BOUND "
                          "instead of refusing")
    for p in (f, per, pat, ext):
        p.add_argument("image")
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
        if args.cmd == "figure":
            m = measure_figure(img, args.chin)
        elif args.cmd == "periodic":
            m = measure_periodic(img, parse_patch(args.patch))
        elif args.cmd == "extent":
            m = measure_extent(img, args.feature, args.min_chroma, args.blur,
                               args.min_region_frac, args.allow_clipped,
                               args.bridge)
        else:
            m = measure_patch(img, parse_patch(args.patch), args.target)
    except Unmeasurable as e:
        # A refusal, not a number. This is the whole point of the module.
        print(f"measure: UNMEASURABLE: {e}", file=sys.stderr)
        return 2

    m["image"] = str(path)
    if not args.no_record:
        m["recordedAt"] = str(write_record(path, m))
    if args.overlay:
        if args.cmd == "figure":
            ov = overlay_figure(img, m)
        elif args.cmd == "extent":
            ov = overlay_extent(img, m)
        else:
            ov = overlay_patch(img, m)
        ov.save(args.overlay)
        m["overlay"] = args.overlay
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
