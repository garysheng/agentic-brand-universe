#!/usr/bin/env python3
"""Build a labelled contact sheet from renders, for read-back.

`render-readback` says a contact sheet of four is the right read-back unit, because it
catches composition, wrong character, invented people, panels, photoreal drift and gross
canon breaches in one look. It shipped no tool, so every run hand-rolled the same PIL
montage. Ten times in one session (nation-of-fire, 2026-07-30) before this was promoted.

  python3 contact_sheet.py --out sheet.png a.png b.png c.png d.png
  python3 contact_sheet.py --out sheet.png --cols 3 --width 700 spreads/*.png
"""
import argparse, os, sys

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--width", type=int, default=690, help="per-cell width in px")
    ap.add_argument("--label", action="store_true", default=True)
    ap.add_argument("--no-label", dest="label", action="store_false")
    a = ap.parse_args()
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return int(bool(sys.stderr.write("contact_sheet: needs pillow (uv run --with pillow)\n")))

    paths = [p for p in a.images if os.path.exists(p)]
    missing = [p for p in a.images if not os.path.exists(p)]
    if missing:
        # Fail loudly: a silently short contact sheet reads as "everything I rendered",
        # which is exactly how a missing spread goes unnoticed.
        sys.stderr.write("contact_sheet: MISSING, refusing to build a partial sheet:\n")
        for m in missing:
            sys.stderr.write(f"  {m}\n")
        return 1
    if not paths:
        sys.stderr.write("contact_sheet: no images\n")
        return 1

    first = Image.open(paths[0])
    cell_h = max(1, round(a.width * first.size[1] / first.size[0]))
    pad = 22 if a.label else 0
    cols = max(1, min(a.cols, len(paths)))
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (a.width * cols, (cell_h + pad) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB").resize((a.width, cell_h))
        x, y = (i % cols) * a.width, (i // cols) * (cell_h + pad)
        sheet.paste(im, (x, y + pad))
        if a.label:
            draw.text((x + 8, y + 6), os.path.basename(p), fill="black")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    sheet.save(a.out)
    print(f"[contact-sheet] {len(paths)} image(s), {cols}x{rows} -> {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
