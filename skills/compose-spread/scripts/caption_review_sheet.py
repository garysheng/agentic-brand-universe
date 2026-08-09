#!/usr/bin/env python3
"""Draw every legal caption plate at its REAL footprint so the AGENT can look and choose.

THE AGENT IS THE VISION MODEL. This is the no-API-key path for the mandatory caption pass
(make-a-book step 4b). The operator's agent already has vision and is already running on
their subscription, so a caption decision does not need a second model behind a second
credential. It needs the agent to see the plate sitting on the painting. Same division of
labour as render-readback, where scripts build the crop and the agent supplies the eyes.

The other path is the platform's `caption-vision.ts`, which asks Claude over the API and
caches to `<slug>.protect.json`. Use that for an unattended run. Use THIS inside a normal
book chain, where an agent is already in the loop and blocking on a key is silly.

WHAT CODE OWNS AND WHAT THE EYES OWN. Code computes each anchor's real footprint from the
real caption text at the real line count, and draws it in place. Geometry is arithmetic.
"That is the hero's face" is not, and no gradient map has ever been able to see it: skin is
smooth, so a face scores CALM to a busyness metric and reads as an excellent place for a
plate. That is why this exists.

The rectangles mirror reader.css: a caption sits on the RIGHT PAGE only of a full-spread
book, inset 6% each side, 5% from the top or bottom edge, and the CORNER variants cap their
width at 44% and anchor to one side. A corner is therefore a different SHAPE, not just a
different place, which is why they are drawn in a different colour.

USAGE
  caption_review_sheet.py --spec <render-spec.json> --dir <spreads/> --out <dir/>
  caption_review_sheet.py <spread.png> --out sheet.png --lines 3
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("needs Pillow:  uv run --with pillow caption_review_sheet.py ...")

# (name, x0, x1, y0_anchor, corner) as fractions of the CAPTION PAGE. Height is computed
# from the caption's real line count rather than assumed, because a four-line caption is a
# very different box from a one-line one and the difference decides what it covers.
ANCHORS = [
    ("bottom",       0.06, 0.94, "bottom"),
    ("top",          0.06, 0.94, "top"),
    ("center",       0.06, 0.94, "center"),
    ("bottom-right", 0.50, 0.94, "bottom"),
    ("bottom-left",  0.06, 0.50, "bottom"),
    ("top-right",    0.50, 0.94, "top"),
    ("top-left",     0.06, 0.50, "top"),
]
FULL_WIDTH = {"bottom", "top", "center"}
GOLD = (255, 206, 84)     # full-width band
CYAN = (110, 214, 255)    # corner plate, 44% wide: a different SHAPE


def _font(size: int):
    for p in ("/System/Library/Fonts/Supplemental/Arial Bold.ttf",
              "/System/Library/Fonts/Helvetica.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def plate_height(n_lines: int, corner: bool) -> float:
    """Plate height as a fraction of page height.

    A corner plate is 44% of the page wide, so the same words wrap to roughly twice the
    lines and the box is roughly twice as tall. Ignoring that is how a corner looks like a
    tidy little card in a diagram and covers a face in the book.
    """
    per_line = 0.052 if not corner else 0.052
    wrap = 1.0 if not corner else 2.0
    return min(0.62, 0.045 + per_line * max(1, round(n_lines * wrap)))


def annotate(png: Path, n_lines: int, layout: str = "full-spread") -> Image.Image:
    im = Image.open(png).convert("RGB")
    w, h = im.size
    px0 = w // 2 if layout == "full-spread" else 0
    pw, ph = w - px0, h
    d = ImageDraw.Draw(im, "RGBA")
    f = _font(max(15, w // 70))

    d.line([(px0, 0), (px0, h)], fill=(255, 255, 255, 130), width=2)

    for name, x0, x1, vert in ANCHORS:
        corner = name not in FULL_WIDTH
        bh = plate_height(n_lines, corner) * ph
        if vert == "top":
            y0 = 0.05 * ph
        elif vert == "bottom":
            y0 = ph - 0.05 * ph - bh
        else:
            y0 = (ph - bh) / 2
        box = (round(px0 + x0 * pw), round(y0), round(px0 + x1 * pw), round(y0 + bh))
        c = GOLD if not corner else CYAN
        d.rectangle(box, fill=c + (52,), outline=c + (255,), width=3)
        bb = d.textbbox((0, 0), name, font=f)
        d.rectangle((box[0], box[1], box[0] + bb[2] + 12, box[1] + bb[3] + 9),
                    fill=(0, 0, 0, 200))
        d.text((box[0] + 6, box[1] + 3), name, font=f, fill=c + (255,))

    tag = f"{png.stem}   ({n_lines} caption line{'s' if n_lines != 1 else ''})"
    bb = d.textbbox((0, 0), tag, font=f)
    d.rectangle((0, 0, bb[2] + 14, bb[3] + 11), fill=(0, 0, 0, 225))
    d.text((7, 4), tag, font=f, fill=(255, 255, 255, 255))
    return im


def tile(images, cols: int, width: int = 1400) -> Image.Image:
    cell = width // cols
    scaled = [im.resize((cell, max(1, round(im.height * cell / im.width)))) for im in images]
    rows = (len(scaled) + cols - 1) // cols
    heights = [max(s.height for s in scaled[r * cols:(r + 1) * cols]) for r in range(rows)]
    out = Image.new("RGB", (width, sum(heights)), (22, 20, 18))
    y = 0
    for r in range(rows):
        x = 0
        for s in scaled[r * cols:(r + 1) * cols]:
            out.paste(s, (x, y))
            x += cell
        y += heights[r]
    return out


def caption_lines(spread: dict) -> int:
    cap = spread.get("_caption") or ""
    return max(1, len([p for p in cap.split("\n") if p.strip()]))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("png", nargs="?")
    ap.add_argument("--spec")
    ap.add_argument("--dir")
    ap.add_argument("--out", required=True)
    ap.add_argument("--lines", type=int, default=3)
    ap.add_argument("--layout", default="full-spread", choices=["full-spread", "art-and-text"])
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--per-sheet", type=int, default=4)
    a = ap.parse_args()

    if a.png:
        annotate(Path(a.png), a.lines, a.layout).save(a.out)
        print(f"wrote {a.out}")
        return 0
    if not (a.spec and a.dir):
        ap.error("pass a PNG, or --spec and --dir")

    spec = json.loads(Path(a.spec).read_text())
    rows = [(s["id"], caption_lines(s)) for s in spec["spreads"]
            if (Path(a.dir) / f"{s['id']}.png").exists()]
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    for i in range(0, len(rows), a.per_sheet):
        chunk = rows[i:i + a.per_sheet]
        imgs = [annotate(Path(a.dir) / f"{sid}.png", n, a.layout) for sid, n in chunk]
        p = out / f"caption-review-{i // a.per_sheet + 1:02d}.png"
        tile(imgs, a.cols).save(p)
        print(f"{p}  <- {', '.join(s for s, _ in chunk)}")
    print(f"{len(rows)} spread(s). LOOK at every sheet and choose per spread. "
          "Gold = full-width band. Cyan = 44% corner card, a different SHAPE.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
