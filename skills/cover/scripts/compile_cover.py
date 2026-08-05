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


def anchor_subject_guard(subject) -> str:
    """Name what the register anchor DEPICTS, and ban it, on the cover.

    Ported from `shoot-references/scripts/chain_matrix.py`, which has auto-negated
    `identity.register.anchorSubject` on every matrix shot since v0.29. This
    compiler passes the anchor FIRST like everything else and did not read the
    field, so a cover render inherited the exact leak the field exists to stop:
    the readiness-lamp anchor painted an ancient burning oil lamp onto the cover
    wall (eleventh-hour-heroes, 2026-08-02, one paid re-roll). The field is
    declared once per universe; reading it here makes the cover honour the same
    law as the matrix shoot and the render.
    """
    if not subject:
        return ""
    return (
        "SPECIFICALLY, NONE OF THE FOLLOWING FROM THAT FIRST STYLE-ANCHOR REFERENCE MAY APPEAR "
        "ANYWHERE IN THIS IMAGE, on any table, shelf, floor, sill, wall or surface, or in any "
        f"figure's hands: {subject}. If the cover scene does not ask for them by name, they are "
        "not in this picture at all."
    )


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
    ap.add_argument("--hero-pose", dest="hero_pose", default="front",
                    help="which of the hero's poses the cover composes (default 'front'). "
                         "A hero seen from BEHIND on a cover is 'back', and needs this: a pose "
                         "is a wardrobe selector, so the wrong one bakes front-only markings "
                         "onto a back view.")
    ap.add_argument("--with", dest="extras", action="append", default=[])
    ap.add_argument("--platform-aspect", default="3:4")
    ap.add_argument("--scene", default=None,
                    help="the composition ACTION (the only free text; identity comes from canon)")
    ap.add_argument("--author", default=None,
                    help="author/byline baked on the cover as 'by <author>' (e.g. two co-authors). "
                         "DEFAULTS TO identity.author when the universe declares one, so a byline "
                         "cannot be forgotten; pass --no-author to deliberately omit it.")
    ap.add_argument("--no-author", action="store_true",
                    help="omit the byline even when the universe declares identity.author "
                         "(an anthology piece, or a cover that carries the byline elsewhere)")
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
        # canon had already spelled out.
        #
        # A COVER IS NOT FRONT-FACING BY DEFINITION, WHICH THIS BLOCK USED TO ASSUME.
        # It hardcoded poses["front"] with no way to ask for another, while make-a-book
        # says in as many words: "A character seen from behind on a cover is a `back`
        # pose, with its sheet." A pose is a WARDROBE SELECTOR, so the assumption does
        # not merely pick a camera, it bakes the wrong markings: nation-of-fire's Jerry
        # carries chest patches on `front` and an upper-back patch on `back`.
        #
        # Earned 2026-08-04 on You Didn't Have To, whose cover is a man seen from behind
        # with his arms open on a hilltop. It came back wearing the FRONT chest patches
        # on his back, and the only way out with the tool as it stood was to re-compose
        # the whole cover front-facing. One paid re-roll.
        r = st.get("render") or {}
        render_parts = []
        if r.get("always"):
            render_parts.append(r["always"])
        poses = r.get("poses") or {}
        want_pose = args.hero_pose if eid == hero_id else "front"
        if poses and want_pose not in poses:
            print(f"REFUSE: '{eid}' has no pose {want_pose!r} "
                  f"(available: {', '.join(sorted(poses))})", file=sys.stderr)
            return 2
        if want_pose in poses:
            if poses[want_pose].get("bake"):
                render_parts.append(poses[want_pose]["bake"])
            for key in poses[want_pose].get("sheets") or []:
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

    # THE BYLINE COMES FROM CANON, SO IT CANNOT BE FORGOTTEN.
    #
    # `--author` was an optional flag with no default, which meant every cover
    # depended on the operator remembering to type the author's name. That is the
    # same shape as any rule that lives only in prose, and it failed exactly that
    # way: You Didn't Have To shipped a cover with no byline on 2026-08-04, because
    # the flag simply was not passed and nothing anywhere noticed.
    #
    # A universe that declares `identity.author` now gets it automatically, next to
    # `identity.mark`, which was already automatic. Universes that declare no author
    # are unchanged, so this is back-compatible. Omitting a byline is still possible
    # but must now be DELIBERATE (--no-author) rather than accidental.
    author = args.author or (ident.get("author") if not args.no_author else None)
    if args.no_author and args.author:
        print("REFUSE: --author and --no-author are contradictory", file=sys.stderr)
        return 2

    text_lines = [args.title] + ([args.subtitle] if args.subtitle else [])
    if author:
        text_lines.append(f"by {author}")
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
        # RESERVE THE ROOM, NOT JUST THE WORDS.
        #
        # The block used to say only "bake these lines" and never told the model to
        # leave anywhere to put them. A scene that composes edge to edge then wins,
        # and the lettering is silently dropped: on 2026-08-05, four of twelve Nation
        # of Fire covers came back carrying the title alone, and the worst of them
        # took THREE attempts because its scene filled the lower third with a lit lamp,
        # which is exactly where the series mark goes.
        #
        # The first fix for that was typed by hand into one book's scene text. Gary:
        # "why is the prompt hand rolled though". Right: "leave a calm band for the
        # lettering" is true of EVERY cover, so it belongs in the compiled prompt where
        # every cover inherits it, not in a scene somebody remembered to write.
        n = len(text_lines)
        text_block = (
            f"THIS COVER CARRIES {n} LINE(S) OF HAND-LETTERED TEXT AND EVERY ONE IS REQUIRED. "
            "Bake them spelled EXACTLY, and NO other text anywhere: "
            + " | ".join(f'"{t}"' for t in text_lines)
            + ". COMPOSE THE ART SO THERE IS ROOM FOR THEM: keep an uncluttered, quiet, "
            "low-detail area behind every line so each one reads clearly, with the first "
            "line(s) toward the top of the frame and the last line small along the bottom. "
            "Busy detail, faces, bright highlights and hard edges must not sit under any "
            "line of lettering. IF ANY OF THESE LINES IS MISSING FROM THE FINISHED IMAGE "
            "THE IMAGE IS WRONG, however good the art is"
        )

    # `--anchor-ref` replaces the image passed first, so the register's declared
    # anchorSubject no longer describes what that first reference depicts; negating
    # it would ban content the override may legitimately want. Mirrors chain_matrix,
    # where a register override reads the pack's own anchorSubject instead.
    subject_guard = "" if args.anchor_ref else anchor_subject_guard(reg.get("anchorSubject"))

    prompt = " ".join(
        x for x in [
            f"PORTRAIT picture-book COVER in the {reg.get('name', 'locked register')} style of the FIRST reference image.",
            *ent_blocks,
            *( [args.scene] if args.scene else [] ),
            subject_guard,
            SAFE_MARGIN_BLOCK,
            # THE TEXT REQUIREMENT GOES LAST, AFTER THE SCENE.
            #
            # It used to be emitted second, before the scene. A book's scene is often
            # long and highly prescriptive about composition -- the-king-is-coming runs
            # 4,400 characters and assigns the lower third to a lit lamp and the upper
            # half to sky -- and a specific instruction that arrives later reliably beats
            # a general one that arrived first. That cover dropped its byline and series
            # mark on FOUR consecutive attempts, including one after the text block had
            # been taught to demand room, because the demand was buried above the scene
            # that contradicted it.
            #
            # Putting it last costs nothing when the scene is short and is the whole
            # difference when the scene is long. Same shape as every other fix in this
            # file: the rule has to arrive where it can still win.
            text_block + ".",
            "NEGATIVES: " + ", ".join(negatives) + ".",
        ] if x
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
