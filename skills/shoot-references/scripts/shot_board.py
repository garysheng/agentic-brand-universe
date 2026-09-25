#!/usr/bin/env python3
"""shot_board.py — put every shot IN FRONT OF the operator, and record the tap that comes back.

WHAT COUNTS AS SEEN (SPEC v0.50). `shoot-references` has said since it was written that no
shot locks until a human has actually seen it, and its own map named the open half: "the
blocker is not effort, it is a definition -- what COUNTS as shown". Gary settled it on
2026-09-14: an AskUserQuestion card. It is the one surface in this harness where a decision
reaches the operator as tappable options rather than prose, and a reference shot is exactly
the case where the options ARE the artifact, so the board carries previews.

AND THE BOARD MUST CARRY THE PICTURE (SPEC v0.51). An AskUserQuestion preview is TEXT: it
carries the path and the checklist and cannot carry the art, so v0.50's record proved the
operator tapped a card NAMING a file. The discriminator is general and worth stating: a
decision the operator can answer FROM WORDS stays a card in the terminal, because a web page
for a yes/no spends their attention for nothing; a decision that requires SEEING the thing
goes to a FRAPP, a page served off the operator's own machine and reachable from their phone.
Shot approval is the first and clearest case, because it is not answerable from a filename.

So `board` opens the frapp and the frapp records its own serves, which is why this is not
another attestation: the thing that sends the bytes is the thing that takes the verdict. On a
machine with no Freedom install there is no frapp; the board falls back to the text card and
the record says so, under its own key, so a lock resting on a filename is one grep away.

Three verbs, and they are deliberately separate, because the board is composed BEFORE the
operator answers and the answer arrives afterwards:

    shot_board.py board <png> [<png> ...] --universe <u> --entity <id>
        Composes the board, STAMPS each image's sidecar with the channel it is being shown
        on, and on the frapp channel STARTS the page and prints the link to send the
        operator. On the card channel it prints AskUserQuestion payloads instead (up to four
        questions per call, so a nine-shot matrix comes back as three boards).

    shot_board.py served <png> --digest <hex>
        Records that the picture's bytes went out. Called BY THE FRAPP, from inside the
        response that sent them; an agent has no way to call it truthfully about a picture no
        browser asked for.

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
import os
import subprocess
import sys
import tempfile
import time
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
from agenticstory import display  # noqa: E402
from agenticstory.candidates import why_not_candidate  # noqa: E402
from agenticstory.seen import (  # noqa: E402
    VERDICTS, read_seen, record_board, record_serve, record_tap, seen_caveat, seen_problem,
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


def build(images: list[Path], entity: dict, universe: Path | None, eid: str | None,
          display_rec: dict) -> list[dict]:
    """Compose the boards AND stamp every image with the channel it is shown on.

    `display_rec` is required all the way down to `record_board`, which refuses without it,
    so no path through this script can compose a board that shows the operator nothing.
    """
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
                display=display_rec,
            )
            bid = rec["board"]["id"]
        boards.append({
            "boardId": bid,
            "questions": [{k: v for k, v in q.items() if k != "image"} for q in chunk],
            "images": [q["image"] for q in chunk],
        })
    return boards


FRAPP = HERE.parent / "frapps" / "shot-board.mjs"

TEXT_IT = ("TEXT THE PHONE LINK TO THE OPERATOR, with freedom:message-myself, without being "
           "asked. The moment they want to judge a shoot is rarely the moment they are at "
           "this keyboard, and a 127.0.0.1 link is one they can only use where they already "
           "were, which is the one place they did not need it.")


BOARD_RECORDS = Path(os.environ.get("ABU_BOARD_RECORDS")
                     or Path.home() / ".freedom" / "frapps" / "abu-shot-board")


def _record_path(eid: str | None) -> Path:
    return BOARD_RECORDS / f"{eid or '_'}.json"


def _alive(pid: int) -> bool:
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def live_board(eid: str | None) -> dict | None:
    """The board already serving this entity, if its process is still up.

    ONE BOARD PER ENTITY. Until 2026-09-18 every `board` call started another page on the same
    store slug, so a re-roll and a chained batch left four boards stacked in one morning, each
    with its own stale idea of one file; the operator saw two full-body cards and asked which
    was new. The page now reads the entity's whole folder per request, so a second `board`
    call only has to stamp the sidecars and hand back the link that is already live.
    """
    try:
        rec = json.loads(_record_path(eid).read_text())
    except (OSError, ValueError):
        return None
    if not rec.get("pid") or not _alive(rec["pid"]) or not rec.get("mac"):
        return None
    return rec


def _remember_board(eid: str | None, rec: dict) -> None:
    try:
        BOARD_RECORDS.mkdir(parents=True, exist_ok=True)
        _record_path(eid).write_text(json.dumps(rec))
    except OSError:
        pass  # a record that cannot be written costs a duplicate board, never a lost verdict


def launch_frapp(images: list[Path], universe: Path | None, eid: str | None,
                 wait: float = 45.0) -> dict:
    """Start the board that SERVES the art, and wait for its URLs; or reuse the one already up.

    Returns `{"ok": True, "mac": ..., "phone": ..., "pid": ..., "log": ...}` (plus
    `"reused": True` when an earlier board for this entity is still serving) or
    `{"ok": False, "why": ...}`. It never raises: a frapp that will not start is a fact the
    board record has to carry, not an exception to swallow, and the caller degrades to the
    card channel with the failure written into the record.
    """
    if universe and eid:
        prior = live_board(eid)
        if prior:
            return {**prior, "ok": True, "reused": True}
    node = display.node()
    if not node:
        return {"ok": False, "why": "no `node` on this machine"}
    if not FRAPP.is_file():
        return {"ok": False, "why": f"the board page is missing at {FRAPP}"}
    work = Path(tempfile.mkdtemp(prefix="abu-shot-board-"))
    urls_out, log = work / "urls.json", work / "frapp.log"
    argv = [node, str(FRAPP), "--urls-out", str(urls_out)]
    if universe:
        argv += ["--universe", str(universe)]
    if eid:
        argv += ["--entity", eid]
    argv += [str(p) for p in images]
    try:
        with open(log, "w") as fh:
            # Its own session, so the page outlives this command: the operator answers
            # minutes later, and a frapp that died with the shell that started it would
            # have shown them nothing.
            proc = subprocess.Popen(argv, stdout=fh, stderr=subprocess.STDOUT,
                                    start_new_session=True)
    except OSError as e:
        return {"ok": False, "why": f"could not start the board page: {e}"}

    deadline = time.time() + wait
    urls: dict = {}
    while time.time() < deadline:
        if proc.poll() is not None:
            tail = ""
            try:
                tail = log.read_text().strip()[-500:]
            except OSError:
                pass
            return {"ok": False, "why": f"the board page exited ({proc.returncode}): {tail}",
                    "log": str(log)}
        try:
            urls = json.loads(urls_out.read_text())
        except (OSError, ValueError):
            urls = {}
        if urls.get("mac"):
            # The phone URL is announced a beat after the Mac one, in the same block.
            time.sleep(1.2)
            try:
                urls = json.loads(urls_out.read_text())
            except (OSError, ValueError):
                pass
            break
        time.sleep(0.25)
    if not urls.get("mac"):
        return {"ok": False, "why": f"the board page did not announce a URL within {wait:.0f}s",
                "log": str(log)}
    rec = {"ok": True, "mac": urls.get("mac"), "phone": urls.get("phone"),
           "pid": proc.pid, "log": str(log)}
    if universe and eid:
        _remember_board(eid, rec)
    return rec


def cmd_board(a) -> int:
    universe = Path(a.universe).expanduser().resolve() if a.universe else None
    entity = _read_entity(universe, a.entity)
    images = [Path(p).expanduser().resolve() for p in a.png]
    missing = [str(p) for p in images if not p.exists()]
    if missing:
        print("shot-board: no file at " + ", ".join(missing), file=sys.stderr)
        return 2
    # NEVER A TURNED-DOWN OR RETIRED TAKE. A shot under `rejected/` or `superseded*/`, or an
    # earlier roll kept as `<slot>.rN.png`, has already been judged; boarding it asks the
    # operator to judge it again and a `keep` would lock art somebody turned down (v0.52).
    stale = [f"{p}: {why}" for p in images
             for why in [why_not_candidate(p, Path(universe) / "reference" if universe else None)]
             if why]
    if stale:
        print("shot-board: refusing to board what is not a current candidate:\n  "
              + "\n  ".join(stale), file=sys.stderr)
        return 2

    # WHICH SURFACE CAN SHOW THE PICTURE. A decision answerable from words stays a card; one
    # that needs SEEING goes to a frapp, and a reference shot is not answerable from a
    # filename. The channel is stamped into every board before anything else happens.
    channel, why = display.resolve_channel()
    boards = build(images, entity, universe, a.entity, display.pending(channel, why))

    frapp = None
    if channel == display.FRAPP:
        frapp = launch_frapp(images, universe, a.entity)
        if not frapp["ok"]:
            # DEGRADE HONESTLY: re-stamp as the card channel, carrying the real reason, so
            # the record never claims a showing that did not happen. No tap exists yet, so
            # superseding the boards costs nothing.
            channel = display.CARD
            why = (f"the frapp could not start, so the board fell back to a text card: "
                   f"{frapp['why']}. Nothing here has shown the operator the art.")
            boards = build(images, entity, universe, a.entity, display.pending(channel, why))

    payload = {
        "entity": a.entity,
        "channel": channel,
        "boards": boards,
        "thenRecord": ("Nothing locks until every shot carries a verdict: "
                       "shot_board.py status <png>... names what is still missing."),
    }
    if channel == display.FRAPP:
        payload["frapp"] = {k: frapp.get(k) for k in ("mac", "phone", "pid", "log", "reused")}
        payload["showWith"] = (
            "The board is OPEN and it serves the pictures itself. Send the operator the phone "
            "link; the page records each serve and each tap, so no verdict here is anybody's "
            "claim about what they were shown.")
        payload["textIt"] = TEXT_IT
    else:
        payload["unshown"] = why
        payload["askWith"] = (
            "Each board is ONE AskUserQuestion call, in order. The questions, options and "
            "previews are ready to use; do not rewrite them. The escape for an off-list "
            "answer is already in each question's text, because a preview costs the visible "
            "Other row.")
        payload["thenRecord"] = (
            "For every answer, record the tap: shot_board.py tap <png> --verdict keep|reroll "
            "[--why ...]. Nothing locks until that verdict is on disk.")

    if a.json:
        print(json.dumps(payload, indent=2))
        return 0

    if channel == display.FRAPP:
        print(f"[shot-board] {len(images)} shot(s) on the board, and the board SHOWS them.")
        print(f"  Mac:    {frapp['mac']}")
        print(f"  phone:  {frapp['phone'] or 'NOT AVAILABLE (run /freedom:set-up-frapps once)'}")
        print(f"  log:    {frapp['log']}")
        print("\n[shot-board] " + payload["showWith"])
        print("[shot-board] " + TEXT_IT)
        print("[shot-board] " + payload["thenRecord"])
        return 0

    for i, b in enumerate(boards, 1):
        print(f"\n[board {i}/{len(boards)}] id {b['boardId']}")
        for q in b["questions"]:
            print(f"  Q: {q['question'].splitlines()[0]}")
            for o in q["options"]:
                print(f"     - {o['label']}: {o['description']}")
    print(f"\n[shot-board] {len(images)} shot(s) on a TEXT board across {len(boards)} board(s).")
    print(f"[shot-board] THE ART IS NOT BEING DISPLAYED: {why}")
    print("[shot-board] Every approval taken here is recorded as `unshown`, with that reason, "
          "so a lock resting on a filename can never be mistaken for one resting on a picture.")
    print("[shot-board] " + payload["askWith"])
    print("[shot-board] " + payload["thenRecord"])
    return 0


def cmd_served(a) -> int:
    """Record that the bytes went out. Called by the frapp, from inside the response."""
    image = Path(a.png).expanduser().resolve()
    try:
        disp = record_serve(image, sent_digest=a.digest, url=a.url)
    except ValueError as e:
        print(f"shot-board: {e}", file=sys.stderr)
        return 2
    print(f"[shot-board] served {image.name} ({disp.get('digest')})")
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
    caveat = seen_caveat(image)
    if caveat:
        print("[shot-board] BUT: " + caveat)
    return 0


def cmd_status(a) -> int:
    rows = []
    for p in a.png:
        image = Path(p).expanduser().resolve()
        seen = read_seen(image)
        disp = ((seen.get("board") or {}).get("display") or {})
        rows.append({
            "image": str(image),
            "board": (seen.get("board") or {}).get("id"),
            "channel": disp.get("channel"),
            "served": bool(disp.get("served")),
            "verdict": seen.get("verdict"),
            "why": seen.get("why"),
            "blocked": seen_problem(image),
            "caveat": seen_caveat(image),
        })
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        state = r["verdict"] or ("boarded, unanswered" if r["board"] else "never boarded")
        shown = "shown" if r["served"] else f"NOT shown ({r['channel'] or 'no channel'})"
        print(f"  {Path(r['image']).name:<32} {state:<22} {shown}")
        if r["blocked"]:
            print(f"      {r['blocked']}")
        if r["caveat"]:
            print(f"      {r['caveat']}")
    return 0 if not any(r["blocked"] for r in rows) else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("board", help="open the board that SHOWS the shots (a frapp), or fall "
                                     "back to AskUserQuestion cards and say so")
    b.add_argument("png", nargs="+")
    b.add_argument("--universe", default=None, help="universe path, so the slot name and the "
                                                    "checklist come from canon")
    b.add_argument("--entity", default=None, help="the entity these shots belong to")
    b.add_argument("--json", action="store_true")

    t = sub.add_parser("tap", help="record ONE operator verdict about ONE picture")
    t.add_argument("png")
    t.add_argument("--verdict", required=True, choices=list(VERDICTS))
    t.add_argument("--why", default="", help="required for reroll and waived")

    v = sub.add_parser("served", help="record that a picture's bytes went out (the frapp "
                                      "calls this; an agent cannot call it truthfully)")
    v.add_argument("png")
    v.add_argument("--digest", default=None, help="what the server hashed on the way out")
    v.add_argument("--url", default=None)

    s = sub.add_parser("status", help="what has been shown, what came back, what still blocks")
    s.add_argument("png", nargs="+")
    s.add_argument("--json", action="store_true")

    a = ap.parse_args(argv)
    return {"board": cmd_board, "served": cmd_served, "tap": cmd_tap,
            "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
