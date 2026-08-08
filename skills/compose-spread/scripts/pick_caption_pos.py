#!/usr/bin/env python3
"""Pick each spread's caption anchor by MEASURING the art, not by defaulting.

THE DEFECT THIS CLOSES. A picture-book caption is an opaque plate laid over the
finished painting, and until now nothing chose where it sat: the render-spec's
`pos` was hand-guessed by whoever authored the spec, and every spread that did not
carry one fell to the reader's `"bottom"` default. So a caption landed on a face,
a hand, a lit doorway or the one object the beat was about, over and over, and the
only way it got caught was Gary opening the book and seeing it (2026-08-08, three
spreads of the-introducer in one sitting: "the caption location needs to be
determined by the agent moving forward, seeing too many examples like this").

WHY MEASUREMENT AND NOT A PROMPT. The scene text already asks for a calm corner
("keep the lower-right of the frame calm"), and the model obeys that about as often
as it obeys any composition request, which is not always. The art on disk is the
ground truth, so the anchor should be read OFF the art after the fact. This costs
no model call and is deterministic.

WHERE THE CAPTION ACTUALLY SITS. In a `full-spread` book the reader paints ONE
landscape image across two pages and puts the caption on the RIGHT page only, at
`left:6% right:6%` of that page, `bottom:5%` or `top:5%` (reader.css). So the
region to score is the RIGHT HALF of the PNG, inset 6% on each side, and a band
roughly 26% of the page height. The corner variants (`bottom-right`, `top-left`, …)
cap their width at 44% of the page and anchor to one side, so they are scored as
narrower boxes. `center` is scored as a full-width band across the middle.

HOW A CANDIDATE IS SCORED. Busyness = mean gradient energy (Sobel-ish forward
difference on luminance) plus a luminance-variance term, both computed on a
downscaled copy. High energy means detail a plate would cover: faces, hands,
lettering, foliage, the glowing thing. Low energy means sky, wall, floor, bokeh.
Lowest score wins, with two deliberate tilts:

  * a small BOTTOM PREFERENCE, because bottom is the book's typographic norm and
    a caption that wanders to a different corner every page reads as restless;
  * a REJECT threshold: if even the best band is busier than `--max-energy`, the
    spread is reported as CROWDED so a human can decide (re-roll the art for a
    calm corner, or accept). It is never silently placed on a face.

USAGE
  pick_caption_pos.py <spread.png> [--layout full-spread|art-and-text]
  pick_caption_pos.py --spec <render-spec.json> --dir <spreads/> [--apply] [--json]

`--apply` writes the chosen `pos` back into the render-spec, which is the file the
book manifest is generated from, so the choice travels with the book.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# (name, x0, x1, y0, y1) as FRACTIONS OF THE CAPTION PAGE (the right half for a
# full-spread book). Mirrors reader.css: 6% side inset, 5% top/bottom offset, a
# plate about 26% of page height, corner variants capped at 44% width.
BANDS = [
    ("bottom",       0.06, 0.94, 0.69, 0.95),
    ("top",          0.06, 0.94, 0.05, 0.31),
    ("center",       0.06, 0.94, 0.37, 0.63),
    ("bottom-right", 0.50, 0.94, 0.69, 0.95),
    ("bottom-left",  0.06, 0.50, 0.69, 0.95),
    ("top-right",    0.50, 0.94, 0.05, 0.31),
    ("top-left",     0.06, 0.50, 0.05, 0.31),
]

# The book's typographic norm. A caption that moves every page reads as restless,
# so a band must be MEANINGFULLY calmer than bottom to displace it.
BOTTOM_BONUS = 0.82
DEFAULT_MAX_ENERGY = 34.0

# A SHORT VIEWPORT MOVES BOTTOM AND CENTER CAPTIONS TO THE TOP (reader.css: a phone
# or small window in landscape puts a fixed playback pill over the bottom band, so
# only bottom and center anchors relocate; corner and top anchors keep their place).
# That flip is invisible to anyone authoring on a laptop, and it is how a caption
# measured onto a calm floor ends up across a face on Gary's screen. So a band whose
# FLIP PARTNER is busy is penalised: the choice has to survive both viewports.
FLIP = {"bottom": "top", "center": "top"}
FLIP_WEIGHT = 0.45


def _load_gray(png: Path, max_w: int = 480):
    from PIL import Image

    im = Image.open(png).convert("L")
    if im.width > max_w:
        im = im.resize((max_w, max(1, round(im.height * max_w / im.width))))
    return im


def _energy(im, box) -> float:
    """Mean forward-difference gradient + luminance spread over a crop.

    Two terms because they catch different plate-killers: gradient catches DETAIL
    (a face, lettering, leaves), variance catches a strong TONAL SPLIT (a bright
    window against a dark wall) that is smooth but still terrible to lay a
    translucent plate across.
    """
    crop = im.crop(box)
    w, h = crop.size
    if w < 4 or h < 4:
        return 999.0
    px = list(crop.getdata())  # noqa: PIL deprecation is fine; get_flattened_data is 11+

    def at(x, y):
        return px[y * w + x]

    total, n = 0, 0
    step = 2  # sampling every other pixel is plenty at this scale and 4x faster
    for y in range(0, h - 1, step):
        for x in range(0, w - 1, step):
            v = at(x, y)
            total += abs(at(x + 1, y) - v) + abs(at(x, y + 1) - v)
            n += 1
    grad = total / max(1, n)

    vals = px[::7]
    mean = sum(vals) / len(vals)
    var = sum((v - mean) ** 2 for v in vals) / len(vals)
    return grad + (var ** 0.5) * 0.18


def caption_page_box(im, layout: str):
    """The region of the IMAGE that the caption page shows.

    full-spread: one landscape image spans two pages, caption on the RIGHT page,
    so the caption page is the right half. Anything else: the caption sits over
    the whole image.
    """
    w, h = im.size
    if layout == "full-spread":
        return (w // 2, 0, w, h)
    return (0, 0, w, h)


def pick(png: Path, layout: str = "full-spread", max_energy: float = DEFAULT_MAX_ENERGY):
    im = _load_gray(png)
    px0, py0, px1, py1 = caption_page_box(im, layout)
    pw, ph = px1 - px0, py1 - py0
    raw = {}
    for name, x0, x1, y0, y1 in BANDS:
        box = (round(px0 + x0 * pw), round(py0 + y0 * ph),
               round(px0 + x1 * pw), round(py0 + y1 * ph))
        raw[name] = _energy(im, box)

    scored = []
    for name in raw:
        w = raw[name] * (BOTTOM_BONUS if name == "bottom" else 1.0)
        partner = FLIP.get(name)
        if partner:
            w += FLIP_WEIGHT * raw[partner]   # must survive the short-viewport flip
        scored.append((w, raw[name], name))
    scored.sort()
    _, best_raw, best = scored[0]
    partner = FLIP.get(best)
    return {
        "file": png.name,
        "pos": best,
        "energy": round(best_raw, 2),
        "flipEnergy": round(raw[partner], 2) if partner else None,
        "crowded": best_raw > max_energy or (partner and raw[partner] > max_energy),
        "ranked": [{"pos": n, "energy": round(e, 2)} for _, e, n in scored],
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("png", nargs="?")
    ap.add_argument("--spec", help="render-spec.json to read spread ids from")
    ap.add_argument("--dir", help="directory holding spread-NN.png")
    ap.add_argument("--layout", default="full-spread",
                    choices=["full-spread", "art-and-text"])
    ap.add_argument("--max-energy", type=float, default=DEFAULT_MAX_ENERGY,
                    help="above this the best band is still busy; reported CROWDED")
    ap.add_argument("--apply", action="store_true",
                    help="write the chosen pos back into the render-spec")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if a.png:
        r = pick(Path(a.png), a.layout, a.max_energy)
        print(json.dumps(r, indent=1) if a.json else
              f"{r['file']}: pos={r['pos']} energy={r['energy']}"
              + ("  CROWDED" if r["crowded"] else ""))
        return 0

    if not (a.spec and a.dir):
        ap.error("pass a png, or both --spec and --dir")

    spec_path = Path(a.spec)
    spec = json.loads(spec_path.read_text())
    out, crowded = [], []
    for sp in spec.get("spreads", []):
        png = Path(a.dir) / f"{sp['id']}.png"
        if not png.exists():
            continue
        r = pick(png, a.layout, a.max_energy)
        r["id"] = sp["id"]
        r["was"] = sp.get("pos")
        out.append(r)
        if r["crowded"]:
            crowded.append(sp["id"])
        if a.apply:
            sp["pos"] = r["pos"]
    if a.apply:
        spec_path.write_text(json.dumps(spec, indent=2) + "\n")

    if a.json:
        print(json.dumps({"spreads": out, "crowded": crowded}, indent=1))
    else:
        for r in out:
            moved = "" if r["was"] == r["pos"] else f"   (was {r['was']})"
            print(f"  {r['id']}: {r['pos']:<13} energy={r['energy']:<6}"
                  + ("CROWDED " if r["crowded"] else "") + moved)
        print(f"\n{len(out)} spread(s) measured"
              + (f"; {len(crowded)} CROWDED: {', '.join(crowded)}" if crowded else "")
              + ("; render-spec updated" if a.apply else "; nothing written"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
