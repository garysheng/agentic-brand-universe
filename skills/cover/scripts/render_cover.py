#!/usr/bin/env python3
"""Render a cover END TO END: compile -> generate -> conform -> report.

`compile_cover.py` emitted a JSON job and NOTHING CONSUMED IT. The SKILL.md says "never
hand-roll a cover render" and then left the operator with a compiled job and no runner, so
every book's cover was in fact hand-rolled: a raw provider call with a retyped prompt. Two
Angels and a Forklift shipped a cover with no title, no byline and no universe mark for
exactly that reason, because the hand-written version was authored as an ordinary spread
and an ordinary spread has no idea a cover carries three exact strings (Gary, 2026-07-30:
"fix the generator to embed the text on the cover").

A generator that stops one step short of the artifact is a generator nobody uses.

  render_cover.py <universe> <story> --title T [--subtitle S] [--author A]
                  [--hero ID] [--with ID ...] --out PATH [--no-mark] [--print-prompt]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from cover_provenance import write_derivative_recipe  # noqa: E402


def platform_path(out: Path) -> Path | None:
    """The platform-facing sibling of a `-raw` render, or None if there is none.

    `<anything>-raw.png` -> `<anything>.png`. Nothing else triggers, so passing
    `--out cover.png` behaves exactly as it always has and no book gains a file it
    did not ask for.
    """
    stem = out.stem
    return out.with_name(stem[:-4] + out.suffix) if stem.endswith("-raw") else None


def publish_platform_copy(out: Path) -> Path | None:
    """Emit the file the platform actually ships, WITH its provenance.

    THE TWO-LINE MANUAL STEP THIS REPLACES. `render_cover.py --out .../cover-raw.png`
    wrote `cover-raw.png` + its recipe, already conformed to 3:4, and stopped. The
    staging layer wants `cover.png`, so every single book run ended with a hand
    `cp cover-raw.png cover.png` — and then `book_doctor` FAILED with "provenance
    cover.png: no recipe.json beside the asset" until the sidecar was hand-copied too.
    Mechanical, certain to recur, and it blocked the healthy verdict on a book that was
    otherwise finished. Named on An Amazing Sex Life (nation-of-fire, 2026-08-04); the
    same two files sit beside every shipped Nation of Fire book on disk, which is the
    convention this now produces instead of asking for.

    The copy is byte-identical, so the recipe is honest by construction: same bytes,
    same hash, and `derivedFrom` points at the raw plus its own recipe, which is the
    record of the generation. A hand-copied sidecar could not say that — the one on
    An Amazing Sex Life claims `asset: cover-raw.png` while sitting beside cover.png.
    """
    dst = platform_path(out)
    if dst is None:
        return None
    dst.write_bytes(out.read_bytes())
    write_derivative_recipe(
        dst, out,
        tool="abu:cover/scripts/render_cover.py",
        args={"publish": "platform-facing copy of the conformed cover"},
        transform="copy (byte-identical; no resample, no crop, no repaint)",
        role="conformed cover",
        note=("DERIVATIVE, not a generation. This is the platform-facing name for the "
              "conformed cover: byte-identical to the file in derivedFrom, which "
              "carries the recipe of the render that made the art. Published by "
              "render_cover.py so that the copy and its provenance can never be done "
              "by hand, or half-done."))
    return dst


def _abu_root() -> Path:
    for c in [HERE, *HERE.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit("cover: cannot locate the ABU root from " + str(HERE))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe"); ap.add_argument("story")
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--author", default=None)
    ap.add_argument("--hero", default=None)
    ap.add_argument("--hero-pose", dest="hero_pose", default=None,
                    help="which of the hero's poses the cover composes (compile_cover defaults "
                         "to 'front'). A hero seen from BEHIND needs 'back': a pose is a "
                         "wardrobe selector, so the wrong one bakes front-only markings onto a "
                         "back view. Earned 2026-08-04 on You Didn't Have To.")
    ap.add_argument("--with", dest="with_", action="append", default=[])
    ap.add_argument("--out", required=True)
    ap.add_argument("--no-mark", action="store_true")
    ap.add_argument("--no-author", action="store_true",
                    help="omit the byline even when the universe declares identity.author")
    ap.add_argument("--print-prompt", action="store_true")
    ap.add_argument("--no-platform-copy", action="store_true",
                    help="do NOT publish the `-raw` render under its platform-facing "
                         "name (cover-raw.png -> cover.png + recipe). The copy is on by "
                         "default because every book needs it and hand-copying it fails "
                         "book-doctor's provenance check.")
    # compile_cover.py has accepted --scene and --anchor-ref since it was written, and this
    # wrapper silently dropped both. A cover therefore could not state its own composition,
    # and the register anchor's SUBJECT (an oil lamp and a clay jar, for nation-of-fire) leaked
    # onto the plate with no way to negate it short of bypassing this script. Earned 2026-08-01
    # on The Door She Did Not Open, whose first cover came back with the anchor's lamp and jar
    # painted onto the table in front of the hero.
    ap.add_argument("--scene", default=None,
                    help="the composition ACTION for the cover (identity still comes from canon)")
    ap.add_argument("--anchor-ref", dest="anchor_ref", default=None,
                    help="override the register anchor passed first (e.g. a second diegetic register)")
    a = ap.parse_args()

    cmd = [sys.executable, str(HERE / "compile_cover.py"), a.universe, a.story,
           "--title", a.title]
    for flag, val in (("--subtitle", a.subtitle), ("--author", a.author), ("--hero", a.hero),
                      ("--hero-pose", a.hero_pose),
                      ("--scene", a.scene), ("--anchor-ref", a.anchor_ref)):
        if val:
            cmd += [flag, val]
    for w in a.with_:
        cmd += ["--with", w]
    if a.no_mark:
        cmd += ["--no-mark"]
    if a.no_author:
        cmd += ["--no-author"]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.stderr.write(r.stderr)
        return r.returncode
    job = json.loads(r.stdout)

    if a.print_prompt:
        print(job["prompt"])
        print("\nREFS:")
        for x in job["refs"]:
            print("  " + x)

    # The compiled strings are the contract. Print them so the read-back has something
    # to check against that is not the operator's memory of what they asked for.
    print("BAKED TEXT (read every glyph back against these):")
    for s in job.get("textLines") or []:
        print(f'  "{s}"')

    sys.path.insert(0, str(_abu_root() / "engine"))
    from agenticstory.providers import resolve_str

    out = Path(a.out).expanduser()
    out.parent.mkdir(parents=True, exist_ok=True)
    gen = ["uv", "run", resolve_str("gpt-image-2"), "--prompt", job["prompt"],
           "--filename", str(out), "--size", job["size"], "--quality", "high", "--no-open"]
    for ref in job["refs"]:
        gen += ["--input-image", ref]
    if subprocess.run(gen).returncode != 0 or not out.exists():
        print("cover: generation FAILED", file=sys.stderr)
        return 1

    # The conform is MANDATORY and is part of the job, not a thing to remember. The model
    # emits a producible 2:3 and the reader wants 3:4; shipping the raw render means the
    # reader crops it, and what it crops is the bottom of the frame, where the title is.
    c = job.get("conform") or {}
    if c.get("to_aspect"):
        # A COVER CONFORM ALWAYS EXTENDS AND NEVER REMOVES (Gary, 2026-07-30: "crop is not
        # the right move it's to extend what is generated"). The model emits 2:3 and the
        # reader wants 3:4, so the image has to get WIDER relative to its height. Cropping
        # height to reach that ratio deletes a strip off the frame, and on a cover the
        # bottom strip is where the byline and the universe mark live: the first real run
        # of this runner cropped 171px and took "A NATION OF FIRE story" with it. Padding
        # the sides adds canvas and loses nothing, which is why the compiled prompt already
        # reserves the outer 10% as safe margin. Any crop-flavoured mode is honoured as pad.
        mode = "pad"
        rc = subprocess.run([sys.executable, str(HERE / "conform_cover.py"), str(out), str(out),
                             "--aspect", c["to_aspect"], "--mode", mode])
        if rc.returncode != 0:
            print("cover: CONFORM FAILED; the raw render is at " + str(out), file=sys.stderr)
            return 1

    print(f"cover: OK -> {out}")
    if not a.no_platform_copy:
        dst = publish_platform_copy(out)
        if dst:
            print(f"cover: published platform-facing copy -> {dst} (+ .recipe.json)")
    print("NOT DONE YET: read the title back glyph by glyph against the BAKED TEXT above. "
          "A typo means regenerate the whole cover, never patch the lettering.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
