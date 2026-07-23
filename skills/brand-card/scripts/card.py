#!/usr/bin/env python3
"""
Deterministic emitter for two-panel brand cards (share cards, thank-you cards).

Exists because a slot typed `deterministic` with no emitter is not deterministic,
it is unspecified. Found by trying to execute the thank-you-card contract and
discovering nothing could lay out its text panel.

Composites a code-laid text panel beside a pre-generated art panel. The art is
NEVER cropped from a square: the spec requires it be generated at the panel's own
aspect, and this emitter refuses art whose ratio is too far off.
"""
import json, sys
from PIL import Image, ImageDraw, ImageFont

T = {"cream": (0xF5,0xF1,0xE9), "clay": (0xCC,0x78,0x5C),
     "ink": (0x1A,0x1A,0x17), "mute": (0x73,0x6E,0x63)}
SERIF = "/System/Library/Fonts/Supplemental/Georgia.ttf"
SANS  = "/System/Library/Fonts/Supplemental/Arial.ttf"
SANSB = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"

def wrap(draw, text, font, max_w):
    out, line = [], ""
    for word in text.split():
        t = (line + " " + word).strip()
        if draw.textlength(t, font=font) <= max_w: line = t
        else: out.append(line); line = word
    if line: out.append(line)
    return out

def tracked(draw, xy, text, font, fill, track):
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill); x += draw.textlength(ch, font=font) + track

def emit(spec):
    W, H = spec["width"], spec["height"]
    split = spec.get("split", int(W * 0.66))
    card = Image.new("RGB", (W, H), T["cream"])
    d = ImageDraw.Draw(card)

    # --- art panel: generated AT this aspect, never cropped from a square
    art = Image.open(spec["art"]).convert("RGB")
    pw, ph = W - split, H
    want, got = pw / ph, art.width / art.height
    if abs(want - got) / want > 0.25:
        raise SystemExit(f"GATE FAIL: art aspect {got:.3f} vs panel {want:.3f}. "
                         "Generate the art at the panel's aspect; do not crop a square into it.")
    sc = max(pw / art.width, ph / art.height)
    r = art.resize((round(art.width*sc), round(art.height*sc)), Image.LANCZOS)
    card.paste(r.crop(((r.width-pw)//2, (r.height-ph)//2, (r.width-pw)//2+pw, (r.height-ph)//2+ph)), (split, 0))

    L, y = spec.get("pad", 64), spec.get("pad", 64) + 8
    inner = split - L*2
    if spec.get("eyebrow"):
        tracked(d, (L, y), spec["eyebrow"].upper(), ImageFont.truetype(SANSB, 20), T["clay"], 4.2); y += 74

    f_head = ImageFont.truetype(SERIF, spec.get("headlineSize", 58))
    for line in wrap(d, spec["headline"], f_head, inner):
        d.text((L, y), line, font=f_head, fill=T["ink"]); y += spec.get("headlineSize", 58) + 18

    if spec.get("body"):
        y += 18; f_body = ImageFont.truetype(SANS, 25)
        for line in wrap(d, spec["body"], f_body, inner):
            d.text((L, y), line, font=f_body, fill=T["mute"]); y += 38

    if spec.get("signoff"):
        d.rectangle([L, H-150, L+140, H-145], fill=T["clay"])
        d.text((L, H-118), spec["signoff"], font=ImageFont.truetype(SANS, 25), fill=T["mute"])

    # --- computed gate
    errs = []
    if (card.width, card.height) != (W, H): errs.append("geometry drifted")
    if y > H - 160: errs.append(f"text overflows its panel (ends at y={y}, floor {H-160})")
    if errs:
        print("GATE FAIL:"); [print("  -", e) for e in errs]; return 1
    card.save(spec["out"], optimize=True)
    print(f"  wrote {spec['out']}  ({W}x{H})  text ends y={y}")
    return 0

if __name__ == "__main__":
    sys.exit(emit(json.load(open(sys.argv[1]))))
