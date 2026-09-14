#!/usr/bin/env python3
"""shot_board.py — put every shot in front of the operator as an AskUserQuestion card,
and record the tap that comes back.

WHAT COUNTS AS SEEN (SPEC v0.50). `shoot-references` has said since it was written that no
shot locks until a human has actually seen it, and its own map named the open half: "the
blocker is not effort, it is a definition -- what COUNTS as shown". Gary settled it on
2026-09-14: an AskUserQuestion card. It is the one surface in this harness where a decision
reaches the operator as tappable options rather than prose, and a reference shot is exactly
the case where the options ARE the artifact, so the board carries previews.

Two verbs, and they are deliberately separate, because the board is composed BEFORE the
operator answers and the answer arrives afterwards:

    shot_board.py board <png> [<png> ...] --universe <u> --entity <id>
        Composes the board (up to four questions per AskUserQuestion call, so a nine-shot
        matrix comes back as three boards) and STAMPS each image's sidecar as having been
        shown. Prints the payload as JSON with --json.

    shot_board.py tap <png> --verdict keep
    shot_board.py tap <png> --verdict reroll --why "screen on the wrong side"
    shot_board.py tap <png> --verdict waived --why "operator unreachable, shipping deadline"
        Records ONE operator verdict about ONE picture.

THE OTHER ROW IS NOT DRAWN, SO THE ESCAPE GOES IN THE QUESTION TEXT. A board whose options
carry a preview flips AskUserQuestion into its side-by-side layout, which does not render
the visible `Other` row at all. An answer the operator might need that is not one of the
options would therefore be invisible. So every question this script composes ends with
ESCAPE, appended by the script rather than by whoever calls it: a rule that fires only when
remembered is the same prose this whole file exists to replace.

The refusals that keep the record honest live in the ENGINE (`agenticstory.seen`), because
`lock-shot` reads the same record and two copies of that vocabulary would drift.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _abu_root(start=None) -> Path:
    """Walk up for a marker, never count parents: a fixed depth encodes ONE layout and this
    runs from a clone and from a plugin cache. Same finder as next_actions.py."""
    p = Path(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit("shot_board: cannot locate the ABU root from " + str(p))


sys.path.insert(0, str(_abu_root() / "engine"))
from agenticstory.seen import (  # noqa: E402
    VERDICTS, read_seen, record_board, record_tap, seen_problem,
)

# AskUserQuestion takes at most four questions in one call. A fifth is a shot the operator
# is told about and cannot answer, so a matrix is chunked into boards rather than truncated.
MAX_QUESTIONS = 4

KEEP, REROLL = "Keep", "Re-roll"

ESCAPE = ("If neither fits -- something else is wrong, canon needs to change, or the shoot "
          "should stop -- say so in the chat. These options carry previews, so the Other row "
          "is not drawn and this is the only way to say it.")


def _read_entity(universe: Path | None, eid: str | None) -> dict:
    if not (universe and eid):
        return {}
    p = Path(universe) / "canon" / "entities" / f"{eid}.json"
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def shot_name(entity: dict, image: Path, universe: Path | None) -> str:
    """The slot this picture is for: the entity's own key when canon knows it, else the stem.

    Canon is asked FIRST because an entity's id is not a promise about where its art lives
    (SPEC v0.33) and a filename is a convention, not a contract.
    """
    sheets = ((entity.get("structured") or {}).get("sheets") or {})
    for key, val in sheets.items():
        if not isinstance(val, str):
            continue
        cand = Path(val)
        if universe is not None and not cand.is_absolute():
            cand = Path(universe) / val
        try:
            if cand.resolve() == image.resolve():
                return key
        except OSError:
            continue
    return image.stem


def assertions(entity: dict) -> list[str]:
    """What the operator is being asked to look for: the entity's own law, never a paraphrase."""
    inv = (entity.get("structured") or {}).get("invariants") or []
    return [str(i) for i in inv if str(i).strip()]


def compose_question(image: Path, entity: dict, universe: Path | None) -> dict:
    shot = shot_name(entity, image, universe)
    look_for = assertions(entity)
    checklist = ("Look for: " + "; ".join(look_for) if look_for
                 else "No invariants are declared on this entity, so there is no checklist "
                      "beyond your own eye.")
    return {
        "header": shot[:12],
        "question": (f"{shot} — {image.name}\n{checklist}\n\n{ESCAPE}"),
        "multiSelect": False,
        "options": [
            {
                "label": KEEP,
                # The token to pass to `tap`. The label is what the operator reads and the
                # verdict is what the record stores; they differ by design ("Re-roll" ->
                # `reroll`), and guessing one from the other is how a legitimate tap gets
                # refused for a spelling nobody chose.
                "verdict": "keep",
                "description": f"Lock it as {shot}. Provenance freezes at this yes.",
                # The preview is the artifact: which plate, what it must satisfy, and what
                # the tap commits to. A label alone asks the operator to approve a word.
                "preview": f"{image}\nslot: {shot}\n{checklist}",
            },
            {
                "label": REROLL,
                "verdict": "reroll",
                "description": "Regenerate from scratch with the defect named. Nothing locks.",
                "preview": (f"{image}\nslot: {shot}\nRe-rolling replaces these bytes, and "
                            f"the new picture goes back on a board before anything locks."),
            },
        ],
        "image": str(image),
        "shot": shot,
    }


def build(images: list[Path], entity: dict, universe: Path | None, eid: str | None) -> list[dict]:
    """Compose the boards AND stamp every image as shown. One write per image."""
    questions = [compose_question(p, entity, universe) for p in images]
    boards = []
    for n in range(0, len(questions), MAX_QUESTIONS):
        chunk = questions[n:n + MAX_QUESTIONS]
        bid = None
        for q in chunk:
            rec = record_board(
                q["image"],
                question=q["question"],
                options=[o["verdict"] for o in q["options"]],
                labels=[o["label"] for o in q["options"]],
                board_id=bid,
                entity=eid,
                shot=q["shot"],
            )
            bid = rec["board"]["id"]
        boards.append({
            "boardId": bid,
            "questions": [{k: v for k, v in q.items() if k != "image"} for q in chunk],
            "images": [q["image"] for q in chunk],
        })
    return boards


def cmd_board(a) -> int:
    universe = Path(a.universe).expanduser().resolve() if a.universe else None
    entity = _read_entity(universe, a.entity)
    images = [Path(p).expanduser().resolve() for p in a.png]
    missing = [str(p) for p in images if not p.exists()]
    if missing:
        print("shot-board: no file at " + ", ".join(missing), file=sys.stderr)
        return 2

    boards = build(images, entity, universe, a.entity)
    payload = {
        "entity": a.entity,
        "boards": boards,
        "askWith": ("Each board is ONE AskUserQuestion call, in order. The questions, options "
                    "and previews are ready to use; do not rewrite them. The escape for an "
                    "off-list answer is already in each question's text, because a preview "
                    "costs the visible Other row."),
        "thenRecord": ("For every answer, record the tap: shot_board.py tap <png> --verdict "
                       "keep|reroll [--why ...]. Nothing locks until that verdict is on disk."),
    }
    if a.json:
        print(json.dumps(payload, indent=2))
        return 0

    for i, b in enumerate(boards, 1):
        print(f"\n[board {i}/{len(boards)}] id {b['boardId']}")
        for q in b["questions"]:
            print(f"  Q: {q['question'].splitlines()[0]}")
            for o in q["options"]:
                print(f"     - {o['label']}: {o['description']}")
    print(f"\n[shot-board] {len(images)} shot(s) stamped as shown across {len(boards)} board(s).")
    print("[shot-board] " + payload["askWith"])
    print("[shot-board] " + payload["thenRecord"])
    return 0


def cmd_tap(a) -> int:
    image = Path(a.png).expanduser().resolve()
    try:
        seen = record_tap(image, a.verdict, why=a.why or "")
    except ValueError as e:
        print(f"shot-board: {e}", file=sys.stderr)
        return 2
    why = f" ({seen['why']})" if seen.get("why") else ""
    print(f"[shot-board] recorded {seen['verdict']} for {image.name}{why}")
    blocked = seen_problem(image)
    print("[shot-board] " + (f"still not lockable: {blocked}" if blocked
                             else "lockable: the verdict is on disk and the bytes match."))
    return 0


def cmd_status(a) -> int:
    rows = []
    for p in a.png:
        image = Path(p).expanduser().resolve()
        seen = read_seen(image)
        rows.append({
            "image": str(image),
            "board": (seen.get("board") or {}).get("id"),
            "verdict": seen.get("verdict"),
            "why": seen.get("why"),
            "blocked": seen_problem(image),
        })
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        state = r["verdict"] or ("shown, unanswered" if r["board"] else "never shown")
        print(f"  {Path(r['image']).name:<32} {state}")
        if r["blocked"]:
            print(f"      {r['blocked']}")
    return 0 if not any(r["blocked"] for r in rows) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("board", help="compose the AskUserQuestion board(s) and stamp each "
                                     "shot as shown")
    b.add_argument("png", nargs="+")
    b.add_argument("--universe", default=None, help="universe path, so the slot name and the "
                                                    "checklist come from canon")
    b.add_argument("--entity", default=None, help="the entity these shots belong to")
    b.add_argument("--json", action="store_true")

    t = sub.add_parser("tap", help="record ONE operator verdict about ONE picture")
    t.add_argument("png")
    t.add_argument("--verdict", required=True, choices=list(VERDICTS))
    t.add_argument("--why", default="", help="required for reroll and waived")

    s = sub.add_parser("status", help="what has been shown, what came back, what still blocks")
    s.add_argument("png", nargs="+")
    s.add_argument("--json", action="store_true")

    a = ap.parse_args(argv)
    return {"board": cmd_board, "tap": cmd_tap, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
