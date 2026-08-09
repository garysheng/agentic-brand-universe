#!/usr/bin/env -S uv run --with pillow --script
# /// script
# dependencies = ["pillow"]
# ///
# ^ PEP 723 inline metadata, so `uv run <this script>` resolves Pillow itself.
#   Before this, every invocation needed `uv run --with pillow` typed from memory,
#   and the takeoff-thursdays run (2026-08) paid that tax on every single readback.
"""
Crop-zoom one or more regions of a render, for INVARIANT READ-BACK.

`contact_sheet.py` is the wide pass: it catches composition, wrong character,
invented people, panel drift and gross canon breaches. This is the narrow pass
that has to follow it, because most canon invariants are DETAILS: a pendant that
must be a four-point star and not a crucifix, two gold incisors, a patch on the
correct side, a face-down phone, a flap that must not have changed size.

Earned on the-little-door, 2026-07-30. Four separate fractional-crop PIL snippets
were hand-written in one run (pendant twice, a flap at wide scale, two back
shots), two of them with mis-guessed boxes that returned a rectangle of empty
shadow and had to be redone. The skill has said "crop-zoom every invariant" since
it was written and shipped no way to do it, so every book re-invented this.

Usage:
  crop_zoom.py OUT.png IMG --box X0,Y0,X1,Y1 [--box ...] [--label NAME] ...
  crop_zoom.py OUT.png IMG --grid 3x3            # locate a region first

Boxes are FRACTIONS of the image (0..1), because a render's pixel size varies by
aspect and a fractional box survives a re-render at another size.

--grid overlays a labelled fraction grid on the whole image and writes that
instead of cropping. Reach for it FIRST when you do not already know where the
detail is: guessing a box, getting shadow, and guessing again costs two round
trips, and the grid costs one.
"""
import sys
from PIL import Image, ImageDraw, ImageFont

PAPER, INK, RULE = (240, 238, 232), (30, 34, 42), (198, 92, 74)


def font(sz):
    for p in ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
              "/System/Library/Fonts/Menlo.ttc"):
        try:
            return ImageFont.truetype(p, sz)
        except Exception:
            pass
    return ImageFont.load_default()


def parse_box(s):
    try:
        v = [float(x) for x in s.split(",")]
    except ValueError:
        sys.exit(f"bad --box {s!r}: want four comma-separated numbers")
    if len(v) != 4:
        sys.exit(f"bad --box {s!r}: want X0,Y0,X1,Y1")
    if not all(0.0 <= x <= 1.0 for x in v):
        sys.exit(f"bad --box {s!r}: fractions must be 0..1")
    if v[0] >= v[2] or v[1] >= v[3]:
        sys.exit(f"bad --box {s!r}: need X0<X1 and Y0<Y1")
    return v


def main():
    args = sys.argv[1:]
    if len(args) < 2:
        sys.exit(__doc__.strip().split("Usage:")[1].strip())
    out_path, src = args[0], args[1]
    boxes, labels, grid, width = [], [], None, 900
    i = 2
    while i < len(args):
        a = args[i]
        if a == "--box":
            boxes.append(parse_box(args[i + 1])); i += 2
        elif a == "--label":
            labels.append(args[i + 1]); i += 2
        elif a == "--grid":
            grid = args[i + 1]; i += 2
        elif a == "--width":
            width = int(args[i + 1]); i += 2
        else:
            sys.exit(f"unknown arg {a!r}")

    im = Image.open(src).convert("RGB")
    W, H = im.size

    if grid:
        try:
            gx, gy = (int(v) for v in grid.lower().split("x"))
        except ValueError:
            sys.exit(f"bad --grid {grid!r}: want NxM, e.g. 3x3")
        sheet = im.copy()
        d = ImageDraw.Draw(sheet)
        f = font(max(14, W // 70))
        for c in range(1, gx):
            x = W * c / gx
            d.line([(x, 0), (x, H)], fill=RULE, width=max(2, W // 700))
        for r in range(1, gy):
            y = H * r / gy
            d.line([(0, y), (W, y)], fill=RULE, width=max(2, W // 700))
        for c in range(gx):
            for r in range(gy):
                x0, y0 = c / gx, r / gy
                d.text((W * x0 + 8, H * y0 + 6), f"{x0:.2f},{y0:.2f}", font=f, fill=RULE)
        sheet.save(out_path)
        print(f"wrote {out_path}  grid {gx}x{gy} over {W}x{H} "
              f"(labels are the TOP-LEFT fraction of each cell)")
        return 0

    if not boxes:
        sys.exit("no --box given (and no --grid); nothing to crop")

    tiles = []
    for n, b in enumerate(boxes):
        px = (int(W * b[0]), int(H * b[1]), int(W * b[2]), int(H * b[3]))
        crop = im.crop(px)
        scale = width / crop.width
        crop = crop.resize((width, max(1, int(crop.height * scale))), Image.LANCZOS)
        name = labels[n] if n < len(labels) else f"{b[0]:.2f},{b[1]:.2f}-{b[2]:.2f},{b[3]:.2f}"
        tiles.append((name, crop))

    CAP, PAD = 34, 16
    sheet_w = sum(t[1].width for t in tiles) + PAD * (len(tiles) + 1)
    sheet_h = max(t[1].height for t in tiles) + CAP + PAD * 2
    sheet = Image.new("RGB", (sheet_w, sheet_h), PAPER)
    d = ImageDraw.Draw(sheet)
    f = font(24)
    x = PAD
    for name, c in tiles:
        d.text((x, PAD), name, font=f, fill=INK)
        sheet.paste(c, (x, PAD + CAP))
        x += c.width + PAD
    sheet.save(out_path)
    print(f"wrote {out_path}  {len(tiles)} crop(s) from {src} ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
