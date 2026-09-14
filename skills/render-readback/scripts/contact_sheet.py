#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
# ^ PEP 723 inline metadata, so `uv run <this script>` resolves Pillow itself.
#   Before this, every invocation needed `uv run --with pillow` typed from memory,
#   and the takeoff-thursdays run (2026-08) paid that tax on every single readback.
"""Build a labelled contact sheet from renders, for read-back.

`render-readback` says a contact sheet of four is the right read-back unit, because it
catches composition, wrong character, invented people, panels, photoreal drift and gross
canon breaches in one look. It shipped no tool, so every run hand-rolled the same PIL
montage. Ten times in one session (nation-of-fire, 2026-07-30) before this was promoted.

  python3 contact_sheet.py --out sheet.png a.png b.png c.png d.png
  python3 contact_sheet.py --out sheet.png --cols 3 --width 700 spreads/*.png
  python3 contact_sheet.py --out sheet.png --cover reference/jerry a.png b.png

A PARTIAL SHEET IS A LIE, AND `--cover` IS THE HALF THAT WAS MISSING (SPEC v0.49).
`shoot-references` tells its reader that this script "already refuses a partial one, so a
short sheet cannot read as 'everything I rendered'". That was only ever true of a file
that does not exist. Nothing here knew what the BATCH was, so a sheet built from three of
twelve renders was built happily and read, to the operator looking at it, as twelve. That
is the exact failure the refusal below was described as preventing, and the SHOW THE
OPERATOR EVERY SHOT gate is the rule it was protecting.

`--cover DIR` names the batch: every `*.png` in DIR that is not itself a sheet or a
parked candidate must appear on the sheet, or this REFUSES and names what is missing.
"""
import argparse, os, sys

# A sheet is not one of its own inputs, and neither is a parked roll: `candidates/` is
# history, by the make-a-book rule that every roll the operator has seen is copied there
# before the next one overwrites it.
_NOT_A_SHOT = ("contact-sheet", "contact_sheet", "sheet", "crop", "zoom", "montage")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("images", nargs="+")
    ap.add_argument("--out", required=True)
    ap.add_argument("--cols", type=int, default=2)
    ap.add_argument("--width", type=int, default=690, help="per-cell width in px")
    ap.add_argument("--label", action="store_true", default=True)
    ap.add_argument("--no-label", dest="label", action="store_false")
    ap.add_argument("--cover", metavar="DIR", default=None,
                    help="the batch this sheet must cover: refuse unless every shot in "
                         "DIR is on it, so a short sheet cannot read as everything")
    a = ap.parse_args()
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return int(bool(sys.stderr.write(
            "contact_sheet: needs pillow. Run via `uv run <this script>` (it declares "
            "pillow inline, PEP 723) or install Pillow in this env.\n")))

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

    if a.cover:
        if not os.path.isdir(a.cover):
            sys.stderr.write(f"contact_sheet: --cover {a.cover} is not a directory\n")
            return 1
        on_sheet = {os.path.realpath(p) for p in paths}
        want = []
        for name in sorted(os.listdir(a.cover)):
            if not name.lower().endswith(".png"):
                continue
            if any(tell in name.lower() for tell in _NOT_A_SHOT):
                continue
            full = os.path.join(a.cover, name)
            if os.path.realpath(full) == os.path.realpath(a.out):
                continue
            want.append(full)
        absent = [p for p in want if os.path.realpath(p) not in on_sheet]
        if absent:
            sys.stderr.write(
                f"contact_sheet: REFUSING a partial sheet. {len(absent)} of "
                f"{len(want)} shot(s) in {a.cover} are not on it:\n")
            for p in absent:
                sys.stderr.write(f"  {p}\n")
            sys.stderr.write(
                "  A short sheet reads to whoever looks at it as everything that was\n"
                "  rendered, which is how a shot reaches nobody while the step reports\n"
                "  success. Add them, or point --cover at the batch you actually mean.\n")
            return 1

    # NEVER DISTORT. Until 2026-09-12 the cell was shaped from the FIRST image and every
    # image was hard-resized into it, so a sheet mixing orientations stretched everything
    # that did not match. Measured on a real sheet: a 1024x1536 plate first, then two
    # 1536x1024 frames squashed into a portrait cell, a 2.25x aspect error.
    #
    # THAT IS A CORRECTNESS BUG, NOT A COSMETIC ONE, because this sheet is the surface a
    # human picks from. A distorted plate means a pick made on an image that is not the
    # image. The operator caught it by eye: "Results sheet shouldn't distort the images
    # like that."
    #
    # The cell is now shaped by the TALLEST aspect present, and every image is fitted
    # inside it preserving its own aspect and centred. On a sheet whose images all share
    # one shape, which is most of them, this is a no-op and reproduces the old output.
    sizes = [Image.open(p).size for p in paths]
    cell_h = max(1, max(round(a.width * h / w) for w, h in sizes))
    pad = 22 if a.label else 0
    cols = max(1, min(a.cols, len(paths)))
    rows = (len(paths) + cols - 1) // cols
    sheet = Image.new("RGB", (a.width * cols, (cell_h + pad) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for i, p in enumerate(paths):
        im = Image.open(p).convert("RGB")
        # Fit inside the cell rather than filling it: the scale is the tighter of the two
        # axes, so nothing is cropped either. Cropping would be the same lie as stretching,
        # told more quietly.
        k = min(a.width / im.size[0], cell_h / im.size[1])
        im = im.resize((max(1, round(im.size[0] * k)), max(1, round(im.size[1] * k))),
                       Image.LANCZOS)
        x, y = (i % cols) * a.width, (i // cols) * (cell_h + pad)
        # A faint grey behind the letterbox, so the image's TRUE BOUNDS are visible even
        # when the image itself has a white background. On a white sheet a white plate has
        # no edge, and not knowing where a plate ends is its own way of misreading it.
        draw.rectangle([x, y + pad, x + a.width - 1, y + pad + cell_h - 1], fill=(238, 238, 238))
        sheet.paste(im, (x + (a.width - im.size[0]) // 2, y + pad + (cell_h - im.size[1]) // 2))
        if a.label:
            draw.text((x + 8, y + 6), os.path.basename(p), fill="black")
    os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
    sheet.save(a.out)
    print(f"[contact-sheet] {len(paths)} image(s), {cols}x{rows} -> {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
