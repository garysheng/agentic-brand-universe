#!/usr/bin/env python3
"""
chroma_key.py — turn a green-screen render into a clean cutout with a vanishing edge.

The framework has told people to render cutouts on chroma green for a while, and then left
them to hand-roll the key every time. This is that step, once, correctly.

Why green and not a "nice" ground
---------------------------------
A warm or bone background bakes a contact shadow and a floor reflection into the render,
and on a gold subject those read as high-chroma gold that no heuristic can separate from
the subject. Flat green is separable by construction. Render the subject FLOATING on
`#00B140` with no shadow, no reflection and no surface.

The three defects this handles, which are independent
-----------------------------------------------------
1. COVERAGE. Where the subject is. Computed from `greenness = G - max(R, B)` rather than
   distance to a green colour, because greenness survives the wide luminance range of a lit
   subject while a colour distance does not.

2. CONTAMINATED COLOUR (spill). Every partly transparent pixel holds a blend of subject and
   background, so a keyed edge carries a green rim onto any new ground. Despill clamps the
   green channel toward the other two ONLY where green leads, which removes the rim without
   touching hue anywhere else.

3. EXCESS COVERAGE. A generous matte leaves a broad veil of faint alpha that is invisible on
   a light ground and reads as a glow on a dark one. `--floor` collapses the faint half of
   the falloff and keeps the strong half.

4. EDGE COLOR ON DARK-ON-DARK SILHOUETTES (`--choke N`). Despill turns green edge
   contamination into a bright yellow hairline exactly where the subject is near-black,
   because clamping G toward max(R, B) on a dark pixel leaves the residue lighter than the
   body it borders. The choke replaces each semi-alpha edge pixel's COLOR with the color of
   the nearest fully-opaque body pixel, flooding outward from the body for N iterations
   (alpha is untouched), so a gold rim survives where the body is gold and a black
   silhouette gets a black skirt. Partial pixels the flood never reaches (isolated thin
   detail like grass blades) keep their color but get green-dominance clamped, so nothing
   legitimate is lost. OFF by default; 12 is the proven value. Promoted 2026-08-03 after
   the same step was hand-rolled three times in the electric-hymnal diorama works.

See userexperience.wiki/concepts/the-vanishing-edge: halo is two different defects wearing
one face, and the diagnostic is the background you inspect on. Always proof a cutout on BOTH
a light and a dark ground before accepting it.

Usage:
  python3 chroma_key.py --in render.png --out layer.png [--key 00B140]
                        [--low 0.12] [--high 0.34] [--floor 0.06] [--despill 1.0]
                        [--feather 1.0] [--choke 12] [--proof proof.png]
"""
import argparse, os, sys

import numpy as np
from PIL import Image, ImageFilter


def key(img, low, high, floor, despill, feather):
    """Return an RGBA image with the chroma background removed."""
    a = np.asarray(img.convert("RGB")).astype(np.float32) / 255.0
    r, g, b = a[..., 0], a[..., 1], a[..., 2]

    # 1. COVERAGE. Greenness, not colour distance: a lit subject spans a wide luminance
    #    range and a distance metric keys the shadows as background.
    greenness = g - np.maximum(r, b)
    alpha = 1.0 - np.clip((greenness - low) / max(1e-6, (high - low)), 0.0, 1.0)

    # 3. EXCESS COVERAGE. Collapse the faint half of the falloff, keep the strong half, so
    #    the veil that is invisible on white stops glowing on a dark ground.
    alpha = np.clip((alpha - floor) / max(1e-6, 1.0 - floor), 0.0, 1.0)
    alpha = alpha * alpha * (3 - 2 * alpha)                    # smoothstep, no knee

    # 2. CONTAMINATED COLOUR. Clamp green toward the other channels only where it leads.
    if despill > 0:
        lead = np.maximum(r, b)
        over = np.maximum(g - lead, 0.0)
        g = g - over * despill
        a = np.stack([r, g, b], axis=-1)

    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8), "RGB").convert("RGBA")
    am = Image.fromarray((alpha * 255).astype(np.uint8), "L")
    if feather > 0:
        am = am.filter(ImageFilter.GaussianBlur(feather))
    out.putalpha(am)
    return out


def choke_edges(cut, iterations, body_thresh=0.98, partial_thresh=0.02):
    """Give every semi-alpha edge pixel the color of the nearest fully-opaque body pixel.

    Floods body color outward for `iterations` steps (8-connected, mean of reached
    neighbors). Alpha is never modified. Partial pixels the flood does not reach keep
    their own color; ALL partial pixels get green-dominance clamped (G <= max(R, B)),
    so residual key contamination cannot survive as a hairline. Returns the new image
    and the count of green-dominant partial pixels remaining (should be 0)."""
    arr = np.asarray(cut.convert("RGBA")).astype(np.float32) / 255.0
    rgb, alpha = arr[..., :3].copy(), arr[..., 3]
    filled = alpha >= body_thresh
    partial = (alpha > partial_thresh) & ~filled

    def shifts(m):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dy == 0 and dx == 0:
                    continue
                yield np.roll(np.roll(m, dy, axis=0), dx, axis=1)

    for _ in range(max(0, iterations)):
        remaining = partial & ~filled
        if not remaining.any():
            break
        color_sum = np.zeros_like(rgb)
        count = np.zeros(alpha.shape, dtype=np.float32)
        for sm, sc in zip(shifts(filled), shifts(rgb)):
            color_sum += sc * sm[..., None]
            count += sm
        reach = remaining & (count > 0)
        rgb[reach] = color_sum[reach] / count[reach][..., None]
        filled = filled | reach

    # Green-dominance clamp on every partial pixel, reached or not.
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    lead = np.maximum(r, b)
    clamp = partial & (g > lead)
    g2 = np.where(clamp, lead, g)
    rgb = np.stack([r, g2, b], axis=-1)

    out = np.dstack([np.clip(rgb, 0, 1), alpha[..., None]])
    img = Image.fromarray((out * 255).astype(np.uint8), "RGBA")
    green_dom = int(((np.asarray(img).astype(np.float32)[..., 1]
                      > np.maximum(np.asarray(img).astype(np.float32)[..., 0],
                                   np.asarray(img).astype(np.float32)[..., 2]))
                     & (alpha > partial_thresh)).sum())
    return img, green_dom


def proof_sheet(cut, path):
    """The cutout on a light AND a dark ground. Checking one hides half the defects:
    a light ground hides excess coverage, a dark ground hides dark contamination."""
    w, h = cut.size
    sheet = Image.new("RGB", (w * 2, h), "#0a1030")
    sheet.paste(Image.new("RGB", (w, h), "#F2EFE7"), (0, 0))
    sheet.paste(cut, (0, 0), cut)
    sheet.paste(cut, (w, 0), cut)
    sheet.thumbnail((1800, 1800), Image.LANCZOS)
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="src", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--low", type=float, default=0.12, help="greenness fully OPAQUE below this")
    ap.add_argument("--high", type=float, default=0.34, help="greenness fully transparent above this")
    ap.add_argument("--floor", type=float, default=0.06, help="collapse alpha below this (kills the veil)")
    ap.add_argument("--despill", type=float, default=1.0)
    ap.add_argument("--feather", type=float, default=1.0)
    ap.add_argument("--choke", type=int, default=0,
                    help="edge-color-from-body iterations (0 = off; 12 is the proven value "
                         "for dark-on-dark silhouettes, where despill leaves a yellow hairline)")
    ap.add_argument("--proof", default="")
    a = ap.parse_args()

    cut = key(Image.open(a.src), a.low, a.high, a.floor, a.despill, a.feather)
    if a.choke > 0:
        cut, green_dom = choke_edges(cut, a.choke)
        print(f"  choke x{a.choke}: green-dominant partial px remaining: {green_dom}")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    cut.save(a.out)

    alpha = np.asarray(cut.getchannel("A")).astype(np.float32) / 255.0
    print(f"{os.path.basename(a.out)}  {cut.size}  "
          f"opaque {100*(alpha > 0.98).mean():.1f}%  "
          f"partial {100*((alpha > 0.02) & (alpha <= 0.98)).mean():.1f}%  "
          f"clear {100*(alpha <= 0.02).mean():.1f}%")
    if (alpha > 0.02).mean() > 0.97:
        print("  WARNING: almost nothing was keyed out. Is the ground actually chroma green?")
    if a.proof:
        proof_sheet(cut, a.proof)
        print(f"  proof (light | dark): {a.proof}")


if __name__ == "__main__":
    main()
