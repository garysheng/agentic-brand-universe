#!/usr/bin/env python3
"""Audit a render-spec for SHOT VARIETY, before a single render is paid for.

WHY THIS EXISTS. `audit_spec_refs.py` proves every cast entity reached the
model. Nothing proved the book was worth looking at. A conversation book whose
beats all happen at one table in one setting will happily assemble N valid,
well-referenced, identical pictures, and the defect is invisible until a human
scrolls the finished book.

Earned 2026-08-05 on nation-of-fire's Bless You More: fifteen consecutive
spreads shared one setting, one plate and one cast, and every scene's "closer,
chest up" prose lost to the plate's own wide composition. Gary, seeing it:
"It's the same image again and again and again and again."

THE CHECKS, all read off the DECLARED `shot` (SPEC 4.13) plus the spread's
setting/plate/cast, so this is static, free, and runnable before spending:

  R1 SAMENESS RUN     >= RUN_LIMIT consecutive spreads with an identical
                      (setting, plate, cast, shot) signature.
  R2 DOMINANT SHAPE   one signature covering more than DOMINANT_FRACTION of
                      the interior spreads.
  R3 NO RELIEF        a TALKING BOOK (one setting carrying most of it) with no
                      relief shot: nothing that leaves the room and shows what
                      is being talked about instead of the people talking.

R3 is the one with an opinion in it. A book can be perfectly varied in camera
and still be a wall of two people at a table, because the argument of a
teaching book lives in what is SAID and the pictures keep drawing the saying.
`thought-bubble`, `imagined` and `insert` are the shots that draw the said
thing, which is why they are the relief set.

    audit_spec_shots.py <universe> <render-spec> [--json]
"""
import argparse
import json
import os
import pathlib
import sys

RUN_LIMIT = 4
DOMINANT_FRACTION = 0.50
TALKING_BOOK_FRACTION = 0.60
TALKING_BOOK_MIN_SPREADS = 8
RELIEF_PER_SPREADS = 8


def _engine_on_path():
    p = pathlib.Path(__file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            sys.path.insert(0, str(c / "engine"))
            return True
    return False


def signature(sp: dict) -> tuple:
    """Same place, same camera, same people, same framing.

    POSE IS DELIBERATELY NOT IN HERE. A pose is a wardrobe-and-expression
    selector, not a composition one: two spreads at the same plate with the same
    cast render as the same picture whether the man is listening or speaking,
    which is precisely the defect that earned this script. Including pose made
    the first version of R1 miss a run of fifteen and report a run of four.
    """
    cast = tuple(sorted(
        c.get("id") for c in (sp.get("cast") or [])
        if isinstance(c, dict) and c.get("id")))
    return (sp.get("setting") or "-", sp.get("plate") or "-", cast, sp.get("shot") or "-")


def human(sig: tuple) -> str:
    setting, plate, cast, shot = sig
    return f"setting={setting} plate={plate} shot={shot} cast={','.join(c.split('@')[0] for c in cast) or 'none'}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("render_spec")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    if not _engine_on_path():
        print("REFUSE: could not locate the ABU engine to read the shot vocabulary.",
              file=sys.stderr)
        return 2
    from agenticstory.shots import SHOTS, RELIEF_SHOTS

    spec = json.loads(pathlib.Path(a.render_spec).expanduser().read_text())
    spreads = [s for s in spec.get("spreads", [])
               if str(s.get("id", "")).startswith("spread-")]
    if not spreads:
        print("audit-spec-shots: no interior spreads in this spec.")
        return 0

    problems: list[str] = []
    notes: list[str] = []

    # An unknown shot would otherwise only surface at render time, one spread at a
    # time, after the earlier ones were already paid for.
    for sp in spreads:
        sh = sp.get("shot")
        if sh is not None and sh not in SHOTS:
            problems.append(f"{sp['id']}: unknown shot {sh!r}. Valid: {', '.join(SHOTS)}.")

    declared = [s for s in spreads if s.get("shot")]
    notes.append(f"{len(declared)}/{len(spreads)} spread(s) declare a shot")

    sigs = [signature(s) for s in spreads]

    # ---- R1 sameness run ---------------------------------------------------
    run_start = 0
    for i in range(1, len(sigs) + 1):
        if i < len(sigs) and sigs[i] == sigs[run_start]:
            continue
        length = i - run_start
        if length >= RUN_LIMIT:
            ids = f"{spreads[run_start]['id']}..{spreads[i - 1]['id']}"
            problems.append(
                f"R1 SAMENESS RUN: {length} consecutive spreads ({ids}) are the same shot: "
                f"{human(sigs[run_start])}. The plate's composition wins over scene prose, "
                f"so these will render as one picture repeated {length} times. Vary the "
                f"`shot` on them (SPEC 4.13).")
        run_start = i

    # ---- R2 dominant shape -------------------------------------------------
    counts: dict[tuple, int] = {}
    for sg in sigs:
        counts[sg] = counts.get(sg, 0) + 1
    top, n = max(counts.items(), key=lambda kv: kv[1])
    if n > DOMINANT_FRACTION * len(spreads):
        problems.append(
            f"R2 DOMINANT SHAPE: {n}/{len(spreads)} spreads ({n / len(spreads):.0%}) share one "
            f"shot: {human(top)}. Over half a book is one picture.")

    # ---- R3 no relief ------------------------------------------------------
    setting_counts: dict[str, int] = {}
    for s in spreads:
        setting_counts[s.get("setting") or "-"] = setting_counts.get(s.get("setting") or "-", 0) + 1
    home, hn = max(setting_counts.items(), key=lambda kv: kv[1])
    if (len(spreads) >= TALKING_BOOK_MIN_SPREADS
            and home != "-" and hn > TALKING_BOOK_FRACTION * len(spreads)):
        relief = [s["id"] for s in spreads if s.get("shot") in RELIEF_SHOTS]
        want = max(1, hn // RELIEF_PER_SPREADS)
        notes.append(f"talking book: '{home}' carries {hn}/{len(spreads)} spreads")
        if len(relief) < want:
            problems.append(
                f"R3 NO RELIEF: '{home}' carries {hn}/{len(spreads)} spreads and only "
                f"{len(relief)} of them leave the room to show what is being talked about "
                f"(want at least {want}). A teaching book's argument is in what is SAID, and "
                f"these pictures all draw the saying. Use {', '.join(sorted(RELIEF_SHOTS))}.")

    if a.json:
        print(json.dumps({"problems": problems, "notes": notes}, indent=2))
        return 2 if problems else 0

    for sp, sg in zip(spreads, sigs):
        print(f"  {sp['id']:<12} shot={sp.get('shot') or '(none)':<14} {human(sg)}")
    print()
    for nline in notes:
        print(f"  note: {nline}")
    if not problems:
        print(f"\naudit-spec-shots: OK ({len(spreads)} spreads, no monotony findings)")
        return 0
    print(f"\naudit-spec-shots: {len(problems)} problem(s):")
    for p in problems:
        print(f"  - {p}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
