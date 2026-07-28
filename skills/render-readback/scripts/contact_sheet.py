#!/usr/bin/env -S uv run --with pillow --script
"""
Build a labelled contact sheet from a list of images, for READ-BACK.

A contact sheet of four is the right read-back unit for a long book (earned on
he-didnt-know, 40 spreads): it catches composition, wrong character, invented
people, panel drift, photoreal drift and gross canon breaches in one look, and
you then crop-zoom only what a beat actually depends on.

Usage:
  contact_sheet.py OUT.png [--cols N] [--width PX] IMG [IMG ...]

Labels are the input filenames (stem), so a defect is reportable by name.
"""
import os
import sys
from PIL import Image, ImageDraw, ImageFont

args = sys.argv[1:]
if not args:
    sys.exit("usage: contact_sheet.py OUT.png [--cols N] [--width PX] IMG [IMG ...]")

out_path = args.pop(0)
cols, cell_w = 2, 760
rest = []
i = 0
while i < len(args):
    if args[i] == "--cols":
        cols = int(args[i + 1]); i += 2
    elif args[i] == "--width":
        cell_w = int(args[i + 1]); i += 2
    else:
        rest.append(args[i]); i += 1

if not rest:
    sys.exit("no input images")

PAD, CAP, PAPER, INK = 18, 34, (240, 238, 232), (30, 34, 42)


def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            continue
    return ImageFont.load_default()


F = font(20)

tiles = []
for p in rest:
    im = Image.open(p).convert("RGB")
    h = round(im.height * cell_w / im.width)
    tiles.append((os.path.splitext(os.path.basename(p))[0], im.resize((cell_w, h), Image.LANCZOS)))

rows = (len(tiles) + cols - 1) // cols
row_h = [max(t[1].height for t in tiles[r * cols:(r + 1) * cols]) for r in range(rows)]

W = PAD + cols * (cell_w + PAD)
H = PAD + sum(h + CAP + PAD for h in row_h)
sheet = Image.new("RGB", (W, H), PAPER)
d = ImageDraw.Draw(sheet)

y = PAD
for r in range(rows):
    x = PAD
    for name, im in tiles[r * cols:(r + 1) * cols]:
        sheet.paste(im, (x, y))
        d.rectangle([x, y, x + cell_w, y + im.height], outline=INK, width=2)
        d.text((x + 2, y + im.height + 8), name, font=F, fill=INK, anchor="lt")
        x += cell_w + PAD
    y += row_h[r] + CAP + PAD

sheet.save(out_path)
print("wrote", out_path, sheet.size, f"({len(tiles)} tiles)")
