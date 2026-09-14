#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
# ^ PEP 723 inline metadata, so `uv run <this script>` resolves Pillow itself.
#   Before this, every invocation needed `uv run --with pillow` typed from memory,
#   and the takeoff-thursdays run (2026-08) paid that tax on every single readback.
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
  GUARD GATE JUDGED    every standing prompt guard that FIRED on this render has a recorded
                       PASS, and a DEFECT is a failure. See below.

Exits non-zero if any check fails, so it can gate a loop.

THE GUARD GATE, AND WHY IT IS RECORDED RATHER THAN TRUSTED (SPEC v0.49)
----------------------------------------------------------------------
v0.47 made every standing prompt guard write a matching read-back assertion into the
recipe (`guards` names them, `guardGate` holds the assertions), and `render-readback`'s
method says to evaluate every one, PASS or DEFECT. That instruction was prose, and the
incident it was built from is precisely an instruction losing: on the appliedai.wiki hero
the device-anatomy guard fired, the prompt carried it verbatim, the render put the screen
toward the camera with its user behind the lid, and the read-back passed it because
nothing told the reader to look. v0.47 gave the reader the line. It did not give anyone a
way to tell whether the line was read, so a skipped gate and a passed gate looked
identical from outside, which is the same shape of failure one level up.

So the judgement is RECORDED, beside the image, the way `measure.py` records how it
measured. The agent still supplies the eyes; this supplies the refusal:

    verify_render.py OUT.png                       # FAILS until every fired guard is judged
    verify_render.py OUT.png --guard device-anatomy=pass
    verify_render.py OUT.png --guard no-ui-chrome=defect:"invented menu bar on the laptop"
    verify_render.py OUT.png --guard readable-surface=waived:"the page is illegible by design"

A DEFECT is a failure here, not a note: the rule is regenerate FROM SCRATCH. A waiver is
the recorded exception and needs a written reason, the same shape as voice-gate's waivers
and `--waive-entity`. Verdicts land in `<image>.readback.json`, which is a build artifact
and never ships.
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


VERDICTS = ("pass", "defect", "waived")


def readback_path(png: str) -> str:
    """Where a recorded judgement about `png` lives. A build artifact; never ships."""
    return png + ".readback.json"


def load_verdicts(png: str) -> dict:
    try:
        with open(readback_path(png)) as f:
            return (json.load(f) or {}).get("guardVerdicts") or {}
    except (OSError, ValueError):
        return {}


def record_verdicts(png: str, new: dict) -> dict:
    """Merge verdicts into the sidecar, so judging one guard does not erase the others."""
    try:
        with open(readback_path(png)) as f:
            doc = json.load(f) or {}
    except (OSError, ValueError):
        doc = {}
    doc.setdefault("guardVerdicts", {}).update(new)
    with open(readback_path(png), "w") as f:
        json.dump(doc, f, indent=2)
    return doc["guardVerdicts"]


def parse_guard_arg(s: str) -> tuple[str, dict]:
    """`name=pass` / `name=defect:why` / `name=waived:why`. REFUSES anything else.

    A reason is REQUIRED for defect and waived, and refused rather than defaulted: a
    waiver with no reason is a skip with better manners, and the whole value of the
    record is that a later reader can argue with it.
    """
    name, sep, rest = s.partition("=")
    name = name.strip()
    if not sep or not name:
        raise ValueError(f"--guard wants NAME=VERDICT[:reason], got {s!r}")
    verdict, _, why = rest.partition(":")
    verdict, why = verdict.strip().lower(), why.strip()
    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r} for guard {name!r}; "
                         f"use one of {', '.join(VERDICTS)}")
    if verdict in ("defect", "waived") and not why:
        raise ValueError(f"guard {name!r} was judged {verdict} with no reason. Write one: "
                         f"--guard {name}={verdict}:\"why\". A verdict nobody can argue "
                         f"with is a skip with better manners.")
    return name, ({"verdict": verdict} if not why else {"verdict": verdict, "why": why})


def fail(problems: list[str], msg: str) -> None:
    problems.append(msg)


def check_guard_gate(png: str, recipe: dict) -> list[str]:
    """Every guard that FIRED on this render must carry a recorded verdict.

    Nothing fires on a recipe with no `guards`, so a render that tripped no standing guard
    is unaffected. A recipe written before v0.47 carries `guards` and no `guardGate`; it
    still demands verdicts, because the guard NAMES are the checkable half and the
    assertions can be read from `providers/*/prompt_guards.py` (`READBACK_GATE`).
    """
    problems: list[str] = []
    fired = [g for g in (recipe.get("guards") or []) if isinstance(g, str)]
    if not fired:
        return problems
    gate = recipe.get("guardGate") or []
    verdicts = load_verdicts(png)
    for n, name in enumerate(fired):
        v = verdicts.get(name) or {}
        verdict = str(v.get("verdict") or "").lower()
        assertion = gate[n] if n < len(gate) else (
            f"(no assertion in this recipe; it predates v0.47. Read {name!r} from "
            f"providers/gpt-image-2/prompt_guards.py READBACK_GATE.)")
        if verdict not in VERDICTS:
            fail(problems,
                 f"{png}: guard {name!r} FIRED on this render and has no recorded verdict. "
                 f"The prompt half asks and the gate half refuses, and an unjudged gate is "
                 f"indistinguishable from a passed one. Look, then record it:\n"
                 f"      {assertion}\n"
                 f"      --guard {name}=pass   (or =defect:\"why\" / =waived:\"why\")")
        elif verdict == "defect":
            why = v.get("why") or "no reason recorded"
            fail(problems,
                 f"{png}: guard {name!r} was judged DEFECT ({why}). Regenerate FROM "
                 f"SCRATCH with the defect named as an explicit negative; never stack an "
                 f"edit pass on a defective render.")
    return problems


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

    problems += check_guard_gate(png, r)

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
    ap.add_argument("--guard", action="append", default=[], metavar="NAME=VERDICT[:why]",
                    help="record a read-back verdict for a fired prompt guard: "
                         "pass, defect:why, or waived:why. Repeatable.")
    a = ap.parse_args(argv)

    # RECORD BEFORE CHECKING, and only ever for ONE image. A verdict is a statement about
    # one picture: applying `--guard device-anatomy=pass` across a batch would let one
    # look stand in for four, which is the failure this whole gate exists to stop.
    if a.guard:
        if len(a.png) != 1:
            print("verify-render: --guard judges ONE image; a verdict is a statement about "
                  "one picture and must not be spread across a batch.", file=sys.stderr)
            return 2
        try:
            new = dict(parse_guard_arg(g) for g in a.guard)
        except ValueError as e:
            print(f"verify-render: {e}", file=sys.stderr)
            return 2
        try:
            recipe = json.loads(open(a.png[0] + ".recipe.json").read())
        except (OSError, ValueError):
            print(f"verify-render: no readable recipe beside {a.png[0]}, so there is no "
                  f"record of which guards fired and nothing to judge.", file=sys.stderr)
            return 2
        fired = set(recipe.get("guards") or [])
        # A TYPO MUST NOT READ AS A JUDGEMENT. `readback_gate` refuses an unknown guard
        # name for the same reason: a verdict filed under a name nothing fired leaves the
        # guard that DID fire still unjudged, while the command looked like it worked.
        unknown = sorted(set(new) - fired)
        if unknown:
            print(f"verify-render: no guard named {', '.join(unknown)} fired on this "
                  f"render. Fired: {', '.join(sorted(fired)) or 'none'}.", file=sys.stderr)
            return 2
        record_verdicts(a.png[0], new)
        for name, v in sorted(new.items()):
            print(f"[verify] recorded {name}: {v['verdict']}"
                  + (f" ({v['why']})" if v.get("why") else ""))

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
