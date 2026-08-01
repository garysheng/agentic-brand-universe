#!/usr/bin/env python3
"""Insert (or remove) a beat mid-book and renumber every artifact that indexes it.

WHY THIS EXISTS
---------------
`update-book` has always claimed to own "add, insert, revise, or remove a spread,
renumber", and it shipped no tool that renumbers. So every insert was hand-rolled,
and the hand-rolled version is a three-artifact edit with an ordering trap in it:

  1. stories/<id>.json    beats[] and every beat's `n`
  2. <book>/render-spec.json   the spreads[] array and every spread's `id`
  3. <book>/spreads/*.png      the rendered art, plus each `.png.recipe.json`

The trap is step 3. Renaming ascending overwrites: spread-05 -> spread-06 lands on
a spread-06 that has not moved yet, and the book quietly loses a page. It must be
done DESCENDING. Nothing enforced that, and the failure is silent: you end up with
the right file count and the wrong pages.

Earned 2026-08-01 on The Door She Did Not Open, which took two mid-run inserts
(the meeting exchange, then four beats on the men who took from her) in a book
that already had 56 rendered spreads. Gary inserts beats mid-run as a matter of
course and runs several books at once, so this is not a one-off.

WHAT IT DOES NOT DO
-------------------
It does not render the new spread and it does not write its scene. It renumbers,
opens the hole, and tells you exactly what to author next. A spread with no scene
is refused by the compiler anyway, which is the backstop.

It also does NOT touch `aimDiscipline`, `spineNote` or any prose that cites beat
numbers by hand. It REPORTS every such citation it can find, because renumbering
silently invalidates them and only a human can rewrite them. Same discipline as
recast_story.py: swap what you can prove, report what you cannot.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

BEAT_CITATION = re.compile(r"\bbeats?\s+(\d+)\b", re.I)


def _spread_id(n: int) -> str:
    return f"spread-{n:02d}"


def _load(p: Path):
    try:
        return json.loads(p.read_text())
    except FileNotFoundError:
        raise SystemExit(f"REFUSE: no such file: {p}")
    except json.JSONDecodeError as e:
        raise SystemExit(f"REFUSE: {p} is not valid JSON: {e}")


def _numbered_art(spreads_dir: Path):
    """Every rendered interior keyed by its number. Endcaps are NOT renumbered:
    a cover and a closing plate are not indexed by beat and never shift."""
    out = {}
    if not spreads_dir.is_dir():
        return out
    for f in spreads_dir.iterdir():
        m = re.fullmatch(r"spread-(\d+)\.png(\.recipe\.json)?", f.name)
        if m:
            out.setdefault(int(m.group(1)), []).append(f)
    return out


def cite_report(story: dict, at: int, delta: int) -> list[str]:
    """Prose that names a beat number is invalidated by a shift and cannot be fixed
    mechanically, because 'beat 12' in a sentence may mean the old 12 or the new one."""
    hits = []
    for field in ("spineNote", "refrainNote", "logline"):
        val = story.get(field)
        if isinstance(val, str):
            for m in BEAT_CITATION.finditer(val):
                if int(m.group(1)) >= at:
                    hits.append(f"{field}: '{m.group(0)}'")
    for i, line in enumerate(story.get("aimDiscipline") or []):
        for m in BEAT_CITATION.finditer(line):
            if int(m.group(1)) >= at:
                hits.append(f"aimDiscipline[{i}]: '{m.group(0)}'")
    for b in story.get("beats") or []:
        prov = b.get("provenance")
        if isinstance(prov, str):
            for m in BEAT_CITATION.finditer(prov):
                if int(m.group(1)) >= at:
                    hits.append(f"beat {b.get('n')} provenance: '{m.group(0)}'")
    return hits


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("universe")
    ap.add_argument("story")
    ap.add_argument("--book", required=True, help="the book FOLDER holding render-spec.json")
    ap.add_argument("--at", type=int, required=True,
                    help="1-based beat position. Insert puts the new beat HERE, "
                         "shifting this beat and everything after it down.")
    ap.add_argument("--remove", action="store_true", help="delete the beat at --at instead")
    ap.add_argument("--text", default=None, help="the new beat's caption text")
    ap.add_argument("--characters", default="", help="comma-separated canon ids")
    ap.add_argument("--location", default=None, help="canon setting id, or omit for none")
    ap.add_argument("--provenance", default="", help="where this beat comes from")
    ap.add_argument("--apply", action="store_true", help="write. Default is a dry run.")
    a = ap.parse_args()

    if not a.remove and a.text is None:
        raise SystemExit("REFUSE: an insert needs --text (or pass --remove)")

    u = Path(a.universe).expanduser()
    story_p = u / "stories" / f"{a.story}.json"
    book = Path(a.book).expanduser()
    spec_p = book / "render-spec.json"
    spreads_dir = book / "spreads"

    story = _load(story_p)
    spec = _load(spec_p)
    beats = story.get("beats") or []
    if not beats:
        raise SystemExit(f"REFUSE: {story_p} has no beats")

    n_beats = len(beats)
    if not (1 <= a.at <= (n_beats if a.remove else n_beats + 1)):
        raise SystemExit(f"REFUSE: --at {a.at} is outside 1..{n_beats + (0 if a.remove else 1)}")

    interiors = [s for s in spec.get("spreads", []) if re.fullmatch(r"spread-\d+", s.get("id", ""))]
    if len(interiors) != n_beats:
        raise SystemExit(
            f"REFUSE: story has {n_beats} beats but the render-spec has {len(interiors)} "
            f"numbered spreads. They are already out of sync; fix that before renumbering, "
            f"or the shift will make it worse.")

    delta = -1 if a.remove else 1
    verb = "REMOVE" if a.remove else "INSERT"
    print(f"{verb} at beat {a.at}: {n_beats} beats -> {n_beats + delta}")

    art = _numbered_art(spreads_dir)
    moves = []
    for num in sorted(art, reverse=(delta > 0)):
        if num >= a.at + (1 if a.remove else 0):
            for f in art[num]:
                moves.append((f, f.with_name(f.name.replace(_spread_id(num), _spread_id(num + delta), 1))))
    doomed = [f for f in art.get(a.at, [])] if a.remove else []

    print(f"  art: {len(moves)} file(s) shift, {len(doomed)} deleted")
    cites = cite_report(story, a.at, delta)
    if cites:
        print("\n  BEAT-NUMBER CITATIONS INVALIDATED BY THIS SHIFT. Nothing rewrites these for")
        print("  you, because 'beat 12' in a sentence may mean the old 12 or the new one:")
        for c in cites:
            print(f"    - {c}")

    if not a.apply:
        print("\nDRY RUN. Nothing written. Re-run with --apply.")
        return 0

    # --- beats -------------------------------------------------------------
    if a.remove:
        beats.pop(a.at - 1)
    else:
        beats.insert(a.at - 1, {
            "n": 0,
            "text": a.text,
            "location": a.location,
            "characters": [c.strip() for c in a.characters.split(",") if c.strip()],
            "provenance": a.provenance,
        })
    for i, b in enumerate(beats):
        b["n"] = i + 1
    story["beats"] = beats
    story_p.write_text(json.dumps(story, indent=2, ensure_ascii=False) + "\n")

    # --- art, DESCENDING on insert so a rename never lands on a live file ---
    for f in doomed:
        f.unlink()
    for src, dst in moves:
        shutil.move(str(src), str(dst))

    # --- spec --------------------------------------------------------------
    spreads = spec.get("spreads", [])
    idx = next((i for i, s in enumerate(spreads) if s.get("id") == _spread_id(a.at)), None)
    if a.remove:
        if idx is not None:
            spreads.pop(idx)
    else:
        at_i = idx if idx is not None else len(interiors)
        spreads.insert(at_i, {
            "id": "PENDING",
            "plate": None,
            "cast": [{"id": c.strip()} for c in a.characters.split(",") if c.strip()],
            "scene": "",
            "_caption": a.text,
            **({"setting": a.location} if a.location else {}),
        })
    k = 0
    for s in spreads:
        if s.get("id") == "PENDING" or re.fullmatch(r"spread-\d+", s.get("id", "")):
            k += 1
            s["id"] = _spread_id(k)
    spec["spreads"] = spreads
    spec_p.write_text(json.dumps(spec, indent=2, ensure_ascii=False) + "\n")

    print(f"\nwrote {story_p}")
    print(f"wrote {spec_p}")
    if not a.remove:
        print(f"\nNEXT: {_spread_id(a.at)} has an empty scene and no pose selections. Author them,")
        print(f"  then render ONLY that spread. Everything else is already on disk and must NOT")
        print(f"  be re-rendered: the renumber moved the art, it did not invalidate it.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
