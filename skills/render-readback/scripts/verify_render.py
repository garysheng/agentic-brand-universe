#!/usr/bin/env python3
"""Read a render back and say whether the canon actually arrived.

WHY THIS IS A SCRIPT AND NOT A DOC. The repo's own CLAUDE.md carried these checks as two
python one-liners to paste, and a check you paste is a check you skip when you are tired
or in a hurry. Both have caught real silent failures — a bypassed binding four separate
times, and two pure-black frames after a metaphor about light was read as a night scene —
and both were still being retyped by hand on 2026-08-02.

The checks, in the order they catch things:

  RECIPE EXISTS        no recipe means the render did not go through the adapter at all,
                       which means no provenance was written and nothing below is knowable.
  INVARIANTS ARRIVED   the prompt carries the entity block. Its absence is the signature of
                       a hand-assembled prompt: the render looks plausible and is off-canon.
  BINDING HELD         the entity and look you MEANT are the ones in the recipe. Passing
                       `selah` when you meant `selah@wedding-dress` is silent and produced
                       a fitted trumpet where an A-line was blessed.
  NOT A DEAD FRAME     a pure-black image. The provider returns one happily.
  SCENE IS CLEAN       (opt-in) the scene text names no garment. This is the only test that
                       proves a look is BOUND rather than merely typed out: if the words
                       appear in the prompt, the render proves nothing about the binding.

Exits non-zero if any check fails, so it can gate a loop.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

# Substring the entity block always contributes to a prompt. Anchored on the phrase
# generate.py actually emits; if that wording ever changes this must change with it,
# which is why it is one named constant and not five scattered string literals.
INVARIANT_MARKER = "LOCKED canonical traits"

# A starting vocabulary for --forbid. Deliberately not exhaustive: a look's own hero words
# belong on the command line, because only the caller knows what this look is made of.
GARMENT_WORDS = [
    "dress", "gown", "suit", "jacket", "coat", "shirt", "trousers", "skirt", "sleeve",
    "collar", "lace", "silk", "denim", "velvet", "satin", "wearing", "outfit", "veil",
    "cap", "hat", "shoes", "boots", "necklace", "pendant", "earrings", "hair",
]


def fail(problems: list[str], msg: str) -> None:
    problems.append(msg)


def check_one(png: str, *, expect: list[str], scene: str | None,
              forbid: list[str]) -> list[str]:
    problems: list[str] = []
    recipe_path = png + ".recipe.json"

    if not os.path.exists(png):
        return [f"{png}: NOT ON DISK"]

    # A dead frame is checked even when the recipe is missing, because it is a fact about
    # the image and does not depend on provenance.
    try:
        from PIL import Image
        with Image.open(png) as im:
            if im.convert("RGB").getextrema() == ((0, 0), (0, 0), (0, 0)):
                fail(problems, f"{png}: DEAD FRAME (pure black). Re-roll; check the prompt "
                               f"for a metaphor about light or darkness being read literally.")
    except ImportError:
        fail(problems, f"{png}: cannot check for a dead frame, Pillow is not installed")

    if not os.path.exists(recipe_path):
        fail(problems, f"{png}: NO RECIPE. The render did not go through "
                       f"on-brand-image/scripts/generate.py, so nothing about it is "
                       f"attested. Never call a provider directly.")
        return problems

    r = json.loads(open(recipe_path).read())
    prompt = r.get("prompt") or ""
    ents = r.get("entities") or []

    if ents and INVARIANT_MARKER not in prompt:
        fail(problems, f"{png}: entities resolved but the invariant block is MISSING from "
                       f"the prompt. This is the signature of a hand-assembled prompt.")

    # `--expect selah@wedding-dress` must match BOTH parts. Matching only the id is how a
    # bare `--entity selah` passes a check that was meant to prove the look was bound.
    got = {f"{e.get('id')}@{e['look']}" if e.get("look") else str(e.get("id")) for e in ents}
    for want in expect:
        if want not in got:
            fail(problems, f"{png}: expected entity '{want}' but the recipe resolved "
                           f"{sorted(got) or '[]'}")

    if scene is not None:
        hits = sorted({w for w in forbid if w.lower() in scene.lower()})
        if hits:
            fail(problems, f"scene text names garment words {hits}, so a render from it "
                           f"cannot prove the look is BOUND. Remove them and re-run: the "
                           f"whole point is that the clothes arrive from canon.")

    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("png", nargs="+", help="rendered image(s); the recipe is found beside each")
    ap.add_argument("--expect", action="append", default=[], metavar="ID[@LOOK]",
                    help="assert this entity (and look) is in every recipe. Repeatable.")
    ap.add_argument("--scene", default=None,
                    help="the scene text, to assert it names no garment (the binding test)")
    ap.add_argument("--forbid", default=None, metavar="w1,w2",
                    help="comma-separated words the scene must not contain; "
                         "defaults to a general garment vocabulary. Add the look's own words.")
    a = ap.parse_args(argv)

    forbid = ([w.strip() for w in a.forbid.split(",") if w.strip()]
              if a.forbid else list(GARMENT_WORDS))

    problems: list[str] = []
    for i, p in enumerate(a.png):
        # The scene is a property of the batch, not of each file: checking it once keeps
        # one typo from being reported N times.
        problems += check_one(p, expect=a.expect,
                              scene=a.scene if i == 0 else None, forbid=forbid)

    if problems:
        print(f"verify-render: {len(problems)} problem(s):", file=sys.stderr)
        for p in problems:
            print(f"  - {p}", file=sys.stderr)
        return 1

    for p in a.png:
        r = json.loads(open(p + ".recipe.json").read())
        ents = r.get("entities") or []
        who = ", ".join(f"{e.get('id')}{'@' + e['look'] if e.get('look') else ''}"
                        f" ({len(e.get('sheets') or {})} plates"
                        f"{', +%d photos' % len(e['photoStackPassed']) if e.get('photoStackPassed') else ''})"
                        for e in ents) or "no entities"
        print(f"[verify] {os.path.basename(p)}: OK — {who}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
