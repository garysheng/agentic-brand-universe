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

`periodic` and `patch` are the two rulers a MEDIUM needs, as opposed to the one a
BODY needs. Both take a patch in FRACTIONAL frame coordinates, and both record it,
because the number is meaningless without the region it came from. See their own
docstrings for the failures each encodes.
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
    for p in (f, per, pat):
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
        ov = overlay_figure(img, m) if args.cmd == "figure" else overlay_patch(img, m)
        ov.save(args.overlay)
        m["overlay"] = args.overlay
    print(json.dumps(m, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
