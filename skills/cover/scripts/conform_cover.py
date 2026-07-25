#!/usr/bin/env python3
"""Conform a rendered cover to the platform aspect, and HARD-ASSERT the result.

The load-bearing half of the cover skill's conform contract: the transform and
the check live in one tested script, so the aspect step cannot be skipped or
hand-improvised (earned twice 2026-07-19: raw 2:3 renders shipped into 3:4
readers clipped the title and the mark).

Modes:
  crop  safe-margin center-crop (ONLY licensed when the generation prompt
        carried the compiler's SAFE MARGIN block; equal trim top+bottom)
  pad   self-bleed side panels (blurred edge extension) to widen to the aspect

`pad` (blurred self-bleed, no keyline) is the DEFAULT cover fill per SPEC v0.7
(§ producible-vs-surface aspect). A flat-color bar is BANNED: it passes the aspect
check but seams visibly against the art's textured, vignetted background. Do not
hand-roll a per-universe pad script; call this tool.

Exits non-zero unless the OUTPUT file's aspect equals --aspect exactly (±0.5%).

Usage:
  conform_cover.py <render.png> <out.png> --aspect 3:4 [--mode crop|pad]
"""
import argparse
import sys

from PIL import Image, ImageFilter


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--aspect", default="3:4")
    ap.add_argument("--mode", choices=["crop", "pad"], default="crop")
    args = ap.parse_args()

    aw, ah = (int(x) for x in args.aspect.split(":"))
    target = aw / ah
    im = Image.open(args.src).convert("RGB")
    w, h = im.size
    cur = w / h

    if abs(cur - target) / target < 0.005:
        out = im
    elif args.mode == "crop":
        if cur < target:  # too tall: equal trim top+bottom
            th = round(w / target)
            off = (h - th) // 2
            out = im.crop((0, off, w, off + th))
        else:  # too wide: equal trim left+right
            tw = round(h * target)
            off = (w - tw) // 2
            out = im.crop((off, 0, off + tw, h))
    else:  # pad with blurred self-bleed panels
        if cur < target:  # widen with side panels
            tw = round(h * target)
            panel = (tw - w) // 2
            canvas = im.resize((tw, h)).filter(ImageFilter.GaussianBlur(40))
            canvas.paste(im, (panel, 0))
            out = canvas
        else:  # heighten with top/bottom panels
            th = round(w / target)
            panel = (th - h) // 2
            canvas = im.resize((w, th)).filter(ImageFilter.GaussianBlur(40))
            canvas.paste(im, (0, panel))
            out = canvas

    out.save(args.out)
    ow, oh = out.size
    if abs((ow / oh) - target) / target >= 0.005:
        print(f"ASSERT FAIL: output {ow}x{oh} is not {args.aspect}", file=sys.stderr)
        return 1
    print(f"OK conform {w}x{h} -> {ow}x{oh} ({args.aspect}, {args.mode}): {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
