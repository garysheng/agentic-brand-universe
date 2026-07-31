#!/usr/bin/env python3
"""Compile a cover render job from canon (SPEC §4.6 applied to covers).

Deterministic: (universe, story, title strings, platform aspect) -> JSON with
  prompt    the full generation prompt, safe-margin block included
  refs      ordered reference image paths (register anchor FIRST)
  size      the model render size (portrait)
  conform   {from_aspect, to_aspect, mode} the mandatory post-step
  qa        the readback checklist compiled from the same canon

Nothing load-bearing is retyped by the author: title/subtitle/mark are quoted
verbatim; invariants and negatives come from canon/entity records.

Usage:
  compile_cover.py <universe> <story-id> --title "..." [--subtitle "..."]
      [--hero <entity-id>] [--with <entity-id> ...] [--platform-aspect 3:4]
"""
import argparse
import json
import sys
from pathlib import Path

SAFE_MARGIN_BLOCK = (
    "CRITICAL SAFE MARGINS: the top 10% and bottom 10% of the frame are pure "
    "background texture with NO lettering and NO important elements; ALL text "
    "and the figure sit inside the central 80% of the frame, because the outer "
    "edges will be trimmed."
)

# THE CONFORM EXTENDS, IT NEVER REMOVES. The model emits 2:3 and the reader wants 3:4, so
# the image must get WIDER relative to its height; cropping height to reach that ratio
# deletes a strip, and on a cover the bottom strip carries the byline and the universe
# mark. This field used to say "safe-margin-crop", a mode `conform_cover.py` does not
# implement, so every consumer had to guess what it meant and a runner guessing by
# substring picked "crop" and cropped the mark off a finished cover (2026-07-30).
# Emit a mode the conformer actually has.
RENDER_SIZE = "1024x1536"  # the only portrait size gpt-image offers (2:3)


def load(p: Path):
    with open(p) as f:
        return json.load(f)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("story")
    ap.add_argument("--title", required=True)
    ap.add_argument("--subtitle", default=None)
    ap.add_argument("--hero", default=None)
    ap.add_argument("--with", dest="extras", action="append", default=[])
    ap.add_argument("--platform-aspect", default="3:4")
    ap.add_argument("--scene", default=None,
                    help="the composition ACTION (the only free text; identity comes from canon)")
    ap.add_argument("--author", default=None,
                    help="author/byline baked on the cover as 'by <author>' (e.g. two co-authors)")
    ap.add_argument("--no-mark", action="store_true",
                    help="omit identity.mark from the cover (a book that opts out of the universe byline)")
    ap.add_argument("--no-text", action="store_true",
                    help="render ART ONLY with no baked lettering, for platforms that typeset the title "
                         "deterministically (vector type) after the render. The qa title-spelling lines are "
                         "still emitted: they become checks on the TYPESET file, and vector type guarantees "
                         "them where hand-lettering wobbles.")
    ap.add_argument("--anchor-ref", default=None,
                    help="override identity.register.anchor (absolute path) when it is unsuitable, "
                         "e.g. a photograph in a painterly universe (a rejectedPole)")
    args = ap.parse_args()

    uroot = Path(args.universe)
    uni = load(uroot / "universe.json")
    ident = uni.get("identity", {})
    reg = ident.get("register", {})
    anchor = args.anchor_ref or reg.get("anchor")
    if not anchor:
        print("REFUSE: identity.register.anchor is null (style not locked)", file=sys.stderr)
        return 2
    mark = ident.get("mark")
    if not mark and not args.no_mark:
        print("REFUSE: identity.mark is null", file=sys.stderr)
        return 2

    story = load(uroot / "stories" / f"{args.story}.json")
    features = story.get("features", [])
    hero_id = args.hero
    if not hero_id:
        for eid in features:
            ent = load(uroot / "canon" / "entities" / f"{eid}.json")
            if ent.get("kind") == "character":
                hero_id = eid
                break
    if not hero_id:
        print("REFUSE: no hero character in story features; pass --hero", file=sys.stderr)
        return 2

    refs = [anchor]
    qa: list[str] = []
    ent_blocks: list[str] = []
    for spec in [hero_id] + args.extras:
        # "<id>" or "<id>:<plate>" — the same plate selection compose-spread's
        # descriptor already supports. Without it a multi-state visual-metaphor
        # always contributed emptyPlates[0], so a cover of the metaphor's LIT
        # state could be conditioned on its UNLIT plate and quietly fight the
        # scene text (caught on Kingdom Moments: the lit cairn cover was being
        # conditioned on a single unlit stone in a palm).
        eid, _, want_plate = spec.partition(":")
        ent_file = uroot / "canon" / "entities" / f"{eid}.json"
        if not ent_file.exists():
            print(f"REFUSE: '{eid}' is not a canon entity", file=sys.stderr)
            return 2
        ent = load(ent_file)
        if ent.get("kind") in ("setting", "visual-metaphor"):
            con = ent.get("contract", {})
            if ent.get("status") != "locked":
                print(f"REFUSE: setting {eid} is not locked", file=sys.stderr)
                return 2
            plates = con.get("emptyPlates") or []
            if want_plate:
                sheets = (ent.get("structured") or {}).get("sheets") or {}
                cand = sheets.get(want_plate) or next(
                    (p for p in plates + [con.get("turnaround")]
                     if p and Path(p).stem == want_plate), None)
                if not cand:
                    print(f"REFUSE: {eid} has no plate '{want_plate}'", file=sys.stderr)
                    return 2
                plate = cand
            else:
                plate = plates[0] if plates else con.get("turnaround")
            if plate and not (uroot / plate).exists():
                print(f"REFUSE: {eid} plate -> {uroot / plate} (NOT ON DISK)", file=sys.stderr)
                return 2
            if plate and plate not in refs:
                refs.append(plate)
            if con.get("dressing"):
                ent_blocks.append(f"{eid} exactly as its reference plate: {con['dressing']}")
            continue
        st = ent.get("structured", {})
        sheets = st.get("sheets", {})
        required = st.get("requiredForRender", [])
        for key in required:
            p = sheets.get(key)
            if not p:
                print(f"REFUSE: {eid}.{key} is required but unlocked", file=sys.stderr)
                return 2
            if p not in refs:
                refs.append(p)
        # A real person anchors HARDER on a photo than on a painted sheet; pass up
        # to two (some real-person entities carry only photos, no requiredForRender).
        rp = ent.get("realPerson") or {}
        for ph in (rp.get("photoStack") or [])[:2]:
            if ph not in refs:
                refs.append(ph)
        # Canon's PRESCRIBED PROMPT-CRAFT (structured.render), same contract as
        # compose-spread's assembler. An invariant is a kebab QA key and cannot
        # carry the sentence that steers the model, so a cover that used only the
        # slugs lost signature wardrobe and star-vs-crucifix pendant wording that
        # canon had already spelled out. Covers are front-facing by definition.
        r = st.get("render") or {}
        render_parts = []
        if r.get("always"):
            render_parts.append(r["always"])
        poses = r.get("poses") or {}
        if "front" in poses:
            if poses["front"].get("bake"):
                render_parts.append(poses["front"]["bake"])
            for key in poses["front"].get("sheets") or []:
                p = sheets.get(key)
                if p and p not in refs:
                    refs.append(p)

        inv = st.get("invariants", [])
        if inv or render_parts:
            block = f"{eid} exactly as its reference sheets"
            block += (": " + "; ".join(inv) + ".") if inv else "."
            if render_parts:
                block += " " + " ".join(render_parts)
            ent_blocks.append(block)
            qa.extend(f"{eid}: {i}" for i in inv)

    # Resolve every ref to an ABSOLUTE on-disk path, matching the sibling
    # assemble_prompt.py. Emitting universe-relative paths here made the caller's
    # cwd load-bearing: running the generator from the book dir (the normal case)
    # fed the image model paths that did not exist, and it failed with a bare
    # FileNotFoundError long after this script had already exited 0.
    # A ref may live under the universe, or beside it (cross-repo anchors).
    resolved: list[str] = []
    for p in refs:
        cand = Path(p)
        for t in ([cand] if cand.is_absolute() else [uroot / p, uroot.parent / p, cand]):
            if t.exists():
                resolved.append(str(t.resolve()))
                break
        else:
            print(f"REFUSE: ref does not resolve on disk: {p}", file=sys.stderr)
            return 2
    refs = resolved

    negatives = list(reg.get("rejectedPoles", []))
    negatives += ["extra words", "gibberish lettering", "text touching the frame edges"]

    text_lines = [args.title] + ([args.subtitle] if args.subtitle else [])
    if args.author:
        text_lines.append(f"by {args.author}")
    if not args.no_mark:
        text_lines.append(mark)
    if args.no_text:
        # The title is typeset as vector type after the render, so the art must
        # carry NO lettering and must leave the type its room.
        text_block = (
            "ART ONLY: absolutely NO text, NO lettering, NO title, NO byline, NO numbers and NO "
            "signature anywhere in the frame. The title is typeset separately afterwards, so keep "
            "the upper third of the frame calm, uncluttered background with nothing that must be read"
        )
    else:
        text_block = (
            "Bake these text lines by hand-lettering, spelled EXACTLY, and NO other text anywhere: "
            + " | ".join(f'"{t}"' for t in text_lines)
        )

    prompt = " ".join(
        [
            f"PORTRAIT picture-book COVER in the {reg.get('name', 'locked register')} style of the FIRST reference image.",
            text_block + ".",
            *ent_blocks,
            *( [args.scene] if args.scene else [] ),
            SAFE_MARGIN_BLOCK,
            "NEGATIVES: " + ", ".join(negatives) + ".",
        ]
    )

    qa = [f'title line spelled exactly: "{t}"' for t in text_lines] + qa
    qa.append(f"shipped file aspect == {args.platform_aspect} (run conform_cover.py; a 2:3 file does not ship)")

    print(
        json.dumps(
            {
                "prompt": prompt,
                "refs": refs,
                "size": RENDER_SIZE,
                # mode is "pad" because the conform EXTENDS and never removes; see the
                # note beside RENDER_SIZE for the cover this rule was earned on.
                "conform": {"from_aspect": "2:3", "to_aspect": args.platform_aspect,
                            "mode": "pad"},
                "textLines": text_lines,
                "qa": qa,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
