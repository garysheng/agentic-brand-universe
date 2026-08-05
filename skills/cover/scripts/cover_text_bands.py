#!/usr/bin/env python3
"""Build the EVIDENCE a vision judge needs to rule on a cover's lettering.

WHY THIS SHAPE. A cover is not done until somebody has confirmed that the lines it
was supposed to bake are actually drawn. Two ways of confirming that were tried on
2026-08-05 and both failed, in opposite directions:

  1. TRUSTING THE REQUEST. `render_cover.py` prints a BAKED TEXT block, which records
     what was ASKED FOR. A batch of twelve was reported as "all three lines present"
     off that block; four had no byline and no series mark. What you asked for is not
     evidence of what was drawn.

  2. OCR AS THE JUDGE. Tesseract over the same twelve produced THREE FALSE NEGATIVES:
     it read "LOOKE" for "LOOKED", and missed "DON'T FIX THE WORLD" and "WILL THERE BE
     ICE CREAM" outright. These titles are stylised painted display lettering, often
     light on dark, sometimes brush-drawn, and OCR is not good at them. A false negative
     is the expensive error here, because it re-rolls art that was already correct --
     the same class of mistake as over-flagging a canon pendant.

So this script DOES NOT RULE. It crops the two bands where cover lettering lives, scales
them up, stacks them per cover with the slug printed above, and writes one sheet. A
VISION-CAPABLE JUDGE then reads that sheet and states, per required line, present or
absent. That is the framework's `judge-slot` pattern: a ROLE, filled by whatever can
actually see -- a subagent, a fresh session, a human, or the composing agent's next turn.

The bands are 0 to 34% and 76 to 100% of frame height, which is where a compiled cover
puts its title/byline and its series mark. Full covers downscale to thumbnails in a
contact sheet and small lettering becomes unreadable; that is precisely how a missing
byline survived review.
"""
import argparse
import sys
from pathlib import Path

TOP = 0.34
BOT = 0.76
TILE_W = 760


def build(covers, out: Path, tile_w: int = TILE_W, cols: int = 3) -> Path:
    from PIL import Image, ImageDraw
    tiles = []
    for label, p in covers:
        im = Image.open(p).convert("RGB")
        W, H = im.size
        top = im.crop((0, 0, W, int(H * TOP)))
        bot = im.crop((0, int(H * BOT), W, H))
        top = top.resize((tile_w, max(1, int(top.height * tile_w / top.width))), Image.LANCZOS)
        bot = bot.resize((tile_w, max(1, int(bot.height * tile_w / bot.width))), Image.LANCZOS)
        t = Image.new("RGB", (tile_w, top.height + bot.height + 8), (255, 255, 255))
        t.paste(top, (0, 0))
        t.paste(bot, (0, top.height + 8))
        tiles.append((label, t))
    if not tiles:
        raise SystemExit("cover-text-bands: nothing to build")
    tw = max(t.width for _, t in tiles)
    th = max(t.height for _, t in tiles)
    rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw, rows * (th + 26)), (250, 250, 250))
    d = ImageDraw.Draw(sheet)
    for i, (label, t) in enumerate(tiles):
        x = (i % cols) * tw
        y = (i // cols) * (th + 26)
        d.text((x + 6, y + 7), label, fill=(0, 0, 0))
        sheet.paste(t, (x, y + 22))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("covers", nargs="+", help="cover image paths")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=3)
    ap.add_argument("--label", action="append", default=[],
                    help="label for each cover, in order; defaults to the parent-of-parent dir name")
    a = ap.parse_args()

    pairs = []
    for i, c in enumerate(a.covers):
        p = Path(c).expanduser()
        if not p.exists():
            print(f"REFUSE: no such cover: {p}", file=sys.stderr)
            return 2
        label = a.label[i] if i < len(a.label) else p.parent.parent.name
        pairs.append((label, p))

    out = build(pairs, Path(a.out).expanduser(), cols=a.cols)
    print(f"cover-text-bands: {len(pairs)} cover(s) -> {out}")
    print("NOT A VERDICT. Open this sheet and rule per cover, per required line: is the "
          "title drawn, is the byline drawn, is the series mark drawn? OCR is not reliable "
          "on this lettering and must not be the judge.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
