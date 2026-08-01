#!/usr/bin/env python3
"""backfill_prompts.py — recover a shot's prompt from its recipe, into prompts.md.

THE HOLE THIS FILLS. `chain_matrix.py` REFUSES to shoot while a prompts.md still
says `TODO(author)`, which is the right refusal: a prompt in a throwaway script is
gone when the session ends, so the entity's own art has no recorded intent and can
never be reproduced. But the refusal is permanent for art that ALREADY got made
some other way. Those entities become un-reshootable: nobody can add one more
angle to them without re-authoring every prompt from scratch, and the prompts are
right there, in each plate's `.recipe.json`, which is exactly what provenance is
for.

So this is the repair verb. It reads the recipe beside each plate, strips the
parts the framework RE-ADDS on every shoot (the register style line, the
same-subject clause, the real-person clause, the negatives block), and writes what
is left into that shot's body in prompts.md.

Three rules it will not break:

  1. **It never overwrites an authored body.** Only a `TODO(author)` body is
     replaced. A human's words always win.
  2. **It never invents.** No recipe means no backfill, and it says so, because a
     plausible reconstruction of a prompt is worse than an admitted gap: it would
     look like provenance while being fiction.
  3. **It reports exactly what it stripped**, per shot, so the operator can see
     that the framework's re-added scaffolding came off and nothing else did.

  python3 backfill_prompts.py <universe> [entity-id ...] [--dry-run] [--strip REGEX]

Earned 2026-07-31: 74 detector findings across ~60 nation-of-fire entities, every
one of them recoverable and none of them recovered, because there was no verb.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TODO = "TODO(author)"

# Paragraph openings the SHOOTER re-adds on every run. Leaving them in prompts.md
# would double them on the next shoot, which is not merely untidy: the negatives
# block would appear twice, and a repeated instruction reads to the model as an
# emphasised one.
FRAMEWORK_OWNED = [
    (re.compile(r"^STYLE, AND IT OVERRIDES", re.I), "register style line"),
    (re.compile(r"^CRITICAL: every reference image after the first", re.I), "same-subject clause"),
    (re.compile(r"^IDENTITY GROUND TRUTH:", re.I), "real-person clause"),
    (re.compile(r"^NEGATIVES:", re.I), "negatives block"),
]


def _recipe_for(plate: Path):
    for c in (plate.with_suffix(plate.suffix + ".recipe.json"),
              plate.with_suffix(".recipe.json")):
        if c.exists():
            try:
                return json.loads(c.read_text())
            except (OSError, json.JSONDecodeError):
                return None
    return None


def _usable_prompt(rec) -> str | None:
    """The recipe's prompt, unless it is itself a TODO marker.

    THE CIRCLE THIS BREAKS. `abu backfill-provenance` recovers a missing recipe by
    reading the prompt out of prompts.md beside the asset. Where prompts.md was
    still a stub, it faithfully recorded `"prompt": "TODO(author): ..."`. Writing
    that back into prompts.md would look like a repair, satisfy every checker, and
    leave the entity exactly as un-reproducible as before, with the gap now
    disguised as provenance. Two recovery tools pointed at each other in a loop.

    An admitted gap is worth more than a laundered one, so this refuses.
    """
    p = (rec or {}).get("prompt")
    return None if (not p or TODO in p) else p


def strip_framework_scaffolding(prompt: str, extra: list[re.Pattern]):
    """Return (body, [what was stripped]).

    Paragraph-wise and conservative. A paragraph is dropped only when it OPENS
    with a marker the framework owns, so an authored paragraph that happens to
    mention negatives survives. Anything unrecognised is KEPT, because a stripper
    that guesses deletes somebody's prompt.
    """
    paras = [p.strip() for p in re.split(r"\n\s*\n", prompt or "") if p.strip()]
    kept, removed = [], []
    for p in paras:
        hit = next((label for rx, label in FRAMEWORK_OWNED if rx.match(p)), None)
        if hit is None:
            hit = next((f"--strip /{rx.pattern}/" for rx in extra if rx.search(p)), None)
        if hit:
            removed.append(hit)
        else:
            kept.append(p)
    return "\n\n".join(kept), removed


def shot_key(heading: str) -> str:
    """The shot id from a `## <key>  -> reference/<id>/<key>.png` heading.

    Same derivation chain_matrix.parse_prompts uses, so the two files can never
    disagree about which body belongs to which plate.
    """
    m = re.search(r"reference/[^/]+/([A-Za-z0-9._-]+)\.png", heading)
    if m:
        return m.group(1)
    return heading.split("—")[0].split("->")[0].strip()


def backfill_file(prompts_md: Path, extra: list[re.Pattern]):
    """Fill every TODO body in ONE prompts.md from the plates beside it."""
    text = prompts_md.read_text()
    lines = text.splitlines()
    out, notes = [], []
    cur, cur_start = None, None

    def flush(end):
        """Replace the current shot's body if it is still a TODO."""
        if cur is None:
            return
        body = lines[cur_start:end]
        if not any(TODO in b for b in body):
            out.extend(body)
            return
        plate = prompts_md.parent / f"{cur}.png"
        if not plate.exists():
            out.extend(body)
            notes.append(f"    {cur}: still TODO, and no plate on disk (nothing to recover)")
            return
        rec = _recipe_for(plate)
        prompt = _usable_prompt(rec)
        if not prompt:
            out.extend(body)
            # Two different failures, and the remedies differ: no recipe at all is a
            # provenance gap, while a recipe that records `"prompt": null` is a recipe
            # written by a path that never captured one.
            why = ("has a recipe whose prompt is itself a TODO stub (recovered from "
                   "this same file by backfill-provenance)" if (rec or {}).get("prompt")
                   else "has a recipe that records NO PROMPT" if rec is not None
                   else "has NO RECIPE at all")
            notes.append(f"    {cur}: plate exists but {why}, so the prompt is "
                         f"UNRECOVERABLE and must be re-authored by hand")
            return
        recovered, removed = strip_framework_scaffolding(prompt, extra)
        if not recovered:
            out.extend(body)
            notes.append(f"    {cur}: recipe held only framework scaffolding, nothing to recover")
            return
        out.append(recovered)
        out.append("")
        notes.append(f"    {cur}: recovered {len(recovered)} chars"
                     + (f" (stripped {', '.join(removed)})" if removed else ""))

    seen: list[str] = []
    for i, line in enumerate(lines):
        if re.match(r"^##\s+", line):
            flush(i)
            cur, cur_start = shot_key(line[2:].strip()), i + 1
            seen.append(cur)
            out.append(line)
        elif cur is None:
            out.append(line)
    flush(len(lines))

    # ADOPT ORPHAN PLATES: locked art with a recipe and NO section in this file.
    #
    # An entity's real matrix drifts from its scaffold (slots get renamed, trimmed,
    # or shot under different keys), and prompts.md is not updated, so the plate is
    # locked canon art whose intent is recorded in a build artifact and nowhere a
    # human reads. `beyonce` holds master / plain / incognito / at-peace while its
    # prompts.md still lists the eight scaffolded portrait slots.
    #
    # Adoption is purely ADDITIVE and never removes a scaffolded slot: whether a
    # declared-but-never-shot slot is still wanted is a judgement call, and this
    # tool does not make judgement calls.
    eid = prompts_md.parent.name
    for plate in sorted(prompts_md.parent.glob("*.png")):
        if "photos" in plate.parts or plate.stem in seen:
            continue
        rec = _recipe_for(plate)
        prompt = _usable_prompt(rec)
        if not prompt:
            continue
        recovered, removed = strip_framework_scaffolding(prompt, extra)
        if not recovered:
            continue
        out += ["", f"## {plate.stem}  -> reference/{eid}/{plate.stem}.png", recovered]
        notes.append(f"    {plate.stem}: ADOPTED (locked plate with no section), "
                     f"recovered {len(recovered)} chars"
                     + (f" (stripped {', '.join(removed)})" if removed else ""))

    new = "\n".join(out).rstrip() + "\n"
    return new, notes


def main() -> int:
    ap = argparse.ArgumentParser(prog="backfill_prompts")
    ap.add_argument("universe")
    ap.add_argument("entity", nargs="*",
                    help="entity ids to repair; default every entity in the universe")
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would be recovered and write nothing")
    ap.add_argument("--strip", action="append", default=[], metavar="REGEX",
                    help="also strip any paragraph matching REGEX. Repeatable. For a "
                         "universe-level guard block this tool does not know about.")
    a = ap.parse_args()

    uroot = Path(a.universe).expanduser()
    ref = uroot / "reference"
    if not ref.is_dir():
        print(f"backfill-prompts: no reference/ under {uroot}", file=sys.stderr)
        return 2
    extra = [re.compile(x, re.I) for x in a.strip]

    targets = sorted(ref.rglob("prompts.md"))
    if a.entity:
        want = set(a.entity)
        targets = [p for p in targets if p.parent.name in want or p.parent.parent.name in want]
        if not targets:
            print(f"backfill-prompts: no prompts.md for {', '.join(sorted(want))}",
                  file=sys.stderr)
            return 2

    changed = stuck = 0
    for md in targets:
        # NOT gated on TODO any more: a file can be fully authored and still be
        # missing a section for a locked plate entirely, which is the orphan case.
        new, notes = backfill_file(md, extra)
        recovered = [n for n in notes if "recovered " in n]
        blocked = [n for n in notes if "UNRECOVERABLE" in n]
        if not recovered and not blocked:
            continue
        rel = md.relative_to(uroot)
        print(f"  {rel}")
        for n in notes:
            print(n)
        stuck += len(blocked)
        if recovered:
            changed += 1
            if not a.dry_run:
                md.write_text(new)

    verb = "would repair" if a.dry_run else "repaired"
    print(f"\nbackfill-prompts: {verb} {changed} prompts.md file(s)"
          + (f", {stuck} shot(s) UNRECOVERABLE (no recipe)" if stuck else ""))
    if changed and not a.dry_run:
        print("  Read the recovered bodies before trusting them: they are what was ACTUALLY "
              "sent to the model, which is not always what the author would write today.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
