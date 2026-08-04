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
import hashlib
import json
import pathlib
import sys

from PIL import Image, ImageDraw, ImageFilter


def _sha16(p: "pathlib.Path") -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def _write_derivative_recipe(args, src_size, out_size) -> "pathlib.Path | None":
    """Write `<out>.recipe.json` recording this conform as a DERIVATIVE.

    EVERY GENERATED ASSET CARRIES ITS PROVENANCE RECIPE is a framework-wide rule, and
    this script was breaking it for the one asset a reader actually sees. `cover.png` is
    what the platform ships; `cover-raw.png` is the model output nobody looks at. Only
    the raw got a recipe, from the provider adapter, so `book-doctor` reported
    "provenance cover.png: no recipe.json beside the asset" and FAILED every book that
    conformed a cover. Two separate book runs hand-wrote the missing file rather than
    fixing the tool (Why We Are the Luckiest Generation, 2026-08-04, wrote it twice in
    one session because the cover was re-rolled), and at least one shipped book has the
    hole still open.

    The recipe is honest about being a derivative rather than a generation: model is
    explicitly none, prompt is null, and `derivedFrom` names the source plus its own
    recipe and hash. It carries `spec`/`universe`/`story` forward from the source recipe
    when there is one, so the chain back to the canon that made the art is unbroken.
    """
    out = pathlib.Path(args.out)
    src = pathlib.Path(args.src)
    src_recipe = src.with_name(src.name + ".recipe.json")
    carried = {}
    if src_recipe.exists():
        try:
            s = json.loads(src_recipe.read_text())
            carried = {k: s[k] for k in ("spec", "universe", "story") if k in s}
        except (json.JSONDecodeError, OSError):
            carried = {}
    rec = {
        "asset": str(out),
        "model": "none (deterministic image transform, no model call)",
        "mode": "derive",
        "tool": "abu:cover/scripts/conform_cover.py",
        "args": {"aspect": args.aspect, "mode": args.mode, "inset": args.inset,
                 "blur": args.blur, "keyline": args.keyline},
        "prompt": None,
        "transform": f"{src_size[0]}x{src_size[1]} -> {out_size[0]}x{out_size[1]}",
        "inputs": [{"path": str(src), "sha256_16": _sha16(src), "role": "source render"}],
        "sha256_16": _sha16(out),
        "derivedFrom": {
            "path": str(src),
            "recipe": str(src_recipe) if src_recipe.exists() else None,
            "sha256_16": _sha16(src),
        },
        "note": ("DERIVATIVE, not a generation. The cover was conformed to the reader "
                 "platform's page aspect by conform_cover.py. No image model was called "
                 "and no pixels of the sharp art were repainted; see derivedFrom for the "
                 "recipe of the render this came from."),
        **carried,
    }
    try:
        out.with_name(out.name + ".recipe.json").write_text(
            json.dumps(rec, indent=2) + "\n")
    except OSError as e:
        print(f"WARNING: could not write provenance beside {out}: {e}", file=sys.stderr)
        return None
    return out.with_name(out.name + ".recipe.json")


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
    recipe = _write_derivative_recipe(args, (w, h), (ow, oh))
    print(f"OK conform {w}x{h} -> {ow}x{oh} ({args.aspect}, {args.mode}): {args.out}")
    if recipe:
        print(f"   provenance: {recipe}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
