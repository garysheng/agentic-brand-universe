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

from PIL import Image, ImageDraw, ImageFilter


def _bleed(im, cw, ch, blur):
    """A blurred SELF-BLEED backdrop at (cw, ch): scale the art to COVER the
    canvas, center-crop, blur. Cover-crop (not a stretch) keeps the matte's
    colors true and never distorts the art's own palette into the panels."""
    w, h = im.size
    scale = max(cw / w, ch / h)
    bw, bh = round(w * scale), round(h * scale)
    ox, oy = (bw - cw) // 2, (bh - ch) // 2
    bg = im.resize((bw, bh)).crop((ox, oy, ox + cw, oy + ch))
    return bg.filter(ImageFilter.GaussianBlur(blur))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--aspect", default="3:4")
    ap.add_argument("--mode", choices=["crop", "pad"], default="crop")
    ap.add_argument("--keyline", default=None,
                    help="hex color (e.g. '#BF9540') for a crisp line framing the "
                         "sharp art in pad mode; DEFAULT none (self-bleed, no line, "
                         "SPEC v0.7). A keyline is a per-universe stylistic opt-in.")
    ap.add_argument("--inset", type=float, default=1.0,
                    help="pad mode: inset the sharp art to this fraction of the canvas "
                         "(1.0 = fill, art bleeds to the long edges; e.g. 0.99 leaves a "
                         "hair of matte all around so a keyline never kisses the edge).")
    ap.add_argument("--blur", type=int, default=40, help="self-bleed matte blur radius.")
    args = ap.parse_args()

    aw, ah = (int(x) for x in args.aspect.split(":"))
    target = aw / ah
    im = Image.open(args.src).convert("RGB")
    w, h = im.size
    cur = w / h

    if abs(cur - target) / target < 0.005 and args.inset >= 1.0 and not args.keyline:
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
    else:  # pad with blurred self-bleed panels (+ optional inset/keyline)
        cw = round(h * target) if cur < target else w
        ch = h if cur < target else round(w / target)
        canvas = _bleed(im, cw, ch, args.blur)
        # sharp art, inset, centered
        fh = round(ch * args.inset)
        fw = round(fh * w / h)
        if fw > cw:  # inset limited by width for very small aspect gaps
            fw = round(cw * args.inset)
            fh = round(fw * h / w)
        ox, oy = (cw - fw) // 2, (ch - fh) // 2
        canvas.paste(im.resize((fw, fh)), (ox, oy))
        if args.keyline:
            stroke = max(3, round(cw * 0.004))
            ImageDraw.Draw(canvas).rectangle(
                [ox, oy, ox + fw - 1, oy + fh - 1], outline=args.keyline, width=stroke)
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
