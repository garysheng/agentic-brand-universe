"""The record that an operator SAW a shot, and the refusals that keep it honest.

`shoot-references` has said since it was written that no shot locks until a human has
actually seen it. That was prose, and prose does not bind: an agent can crop-zoom forty
renders, pass every invariant, lock them all, and the person who commissioned the work has
seen nothing. The skill's own map named the blocker exactly -- "the blocker is not effort,
it is a definition: what COUNTS as shown" -- and left the refusal unbuilt.

**What counts as shown is a tap on an `AskUserQuestion` card** (Gary, 2026-09-14). It is the
one surface in this harness where the operator is handed a decision as options rather than
prose, and a shot is precisely the case where the options ARE the artifact, so the board
carries previews.

So the verdict is RECORDED, beside the image, in the same `<image>.readback.json` sidecar
v0.49 put the guard verdicts in. One sidecar per image, two independent records inside it:

    {"guardVerdicts": {...},                      # v0.49: did the fired prompt guards pass
     "seen": {"board": {"id": "...", "shownOn": "...", "question": "...",
                        "options": ["Keep", "Re-roll"], "digest": "8f0f..."},
              "verdict": "keep", "on": "...", "why": ""}}

Four refusals, and each one is a way the record could otherwise be forged:

  NO BOARD        a verdict for a shot that was never put on a board. Same shape as v0.49's
                  refusal of a verdict filed under a guard that never fired: a tap nobody
                  was asked for leaves the shot unseen while the command looks like it worked.
  OFF THE BOARD   a verdict that was not one of the options the operator was shown. `waived`
                  is the one exception and it REQUIRES a written reason, the same shape as a
                  voice-gate waiver, `--waive-entity` and a waived guard.
  THE PICTURE MOVED   the bytes changed between the board and the tap, or between the tap and
                  the lock. A re-roll writes a new image at the same path, so without this the
                  operator's yes to the old picture silently approves the new one.
  NO REASON       `reroll` and `waived` with nothing written down. A verdict nobody can argue
                  with later is a skip with better manners.

Like the recipe beside it, this sidecar is a build artifact and never ships.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import uuid

SIDECAR_SUFFIX = ".readback.json"

# What a tap may say. `keep` and `reroll` are the two the board offers; `waived` is the
# recorded exception for when the operator is genuinely absent, and it is never tappable
# because a waiver is by definition not a tap.
VERDICTS = ("keep", "reroll", "waived")
APPROVING = ("keep", "waived")
NEEDS_REASON = ("reroll", "waived")


def sidecar_path(image) -> pathlib.Path:
    """Where the record about `image` lives. A build artifact; never ships."""
    p = pathlib.Path(image)
    return p.with_name(p.name + SIDECAR_SUFFIX)


def digest(image) -> str | None:
    """The bytes the operator was looking at, short-hashed. None when unreadable.

    Same 16-hex shape as `authoring._digest`, so a reader comparing a seen record with a
    frozen recipe is comparing like with like.
    """
    try:
        with open(image, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()[:16]
    except OSError:
        return None


def _read_doc(image) -> dict:
    try:
        with open(sidecar_path(image)) as f:
            return json.load(f) or {}
    except (OSError, ValueError):
        return {}


def _write_doc(image, doc: dict) -> None:
    # MERGE, NEVER CLOBBER. `verify_render.py` writes `guardVerdicts` into this same file,
    # and the two records are judged at different moments by different checks.
    with open(sidecar_path(image), "w") as f:
        json.dump(doc, f, indent=2, sort_keys=True)


def read_seen(image) -> dict:
    """The seen record for `image`, or `{}`."""
    return _read_doc(image).get("seen") or {}


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def record_board(image, *, question: str, options: list[str], labels: list[str] | None = None,
                 board_id: str | None = None, entity: str | None = None,
                 shot: str | None = None, on: str | None = None) -> dict:
    """Stamp `image` as having been put on a board. Written when the board is COMPOSED.

    `options` are the VERDICT TOKENS the board offers, and `labels` the words the operator
    actually read. They are recorded separately because they differ by design -- a card
    reading "Re-roll" records `reroll` -- and comparing a verdict against a label is how a
    legitimate tap gets refused for a spelling nobody chose.

    This is the half a tap is checked against, and it is deliberately written by the
    composer rather than by whoever records the answer: a verdict filed against a board
    that was never built is the forgery the refusals below exist to catch.
    """
    p = pathlib.Path(image)
    if not p.exists():
        raise ValueError(
            f"refusing to board {p}: no file there. A board shows the operator a picture, "
            f"so a board entry for a path with no bytes records a look at nothing.")
    if not options:
        raise ValueError(f"refusing to board {p}: a board with no options is not a question.")
    unknown = [o for o in options if str(o).strip().lower() not in VERDICTS]
    if unknown:
        raise ValueError(
            f"refusing to board {p}: option(s) {unknown} are not verdicts. A board whose "
            f"options are not in {list(VERDICTS)} can never be answered, because every tap "
            f"would be refused as off the board. Pass the tokens and put the words the "
            f"operator reads in `labels`.")
    doc = _read_doc(image)
    seen = doc.setdefault("seen", {})
    # A fresh board supersedes any earlier one AND any verdict taken against it: the
    # operator is being shown this picture again, so the old yes does not carry over.
    seen.clear()
    seen["board"] = {
        "id": board_id or uuid.uuid4().hex[:12],
        "shownOn": on or _now(),
        "question": question,
        "options": [str(o).strip().lower() for o in options],
        "labels": list(labels or options),
        "digest": digest(image),
    }
    if entity:
        seen["board"]["entity"] = entity
    if shot:
        seen["board"]["shot"] = shot
    _write_doc(image, doc)
    return seen


def record_tap(image, verdict: str, why: str = "", on: str | None = None) -> dict:
    """Record the operator's tap. REFUSES anything that would forge the record."""
    p = pathlib.Path(image)
    verdict = (verdict or "").strip().lower()
    why = (why or "").strip()

    if verdict not in VERDICTS:
        raise ValueError(f"unknown verdict {verdict!r} for {p.name}; "
                         f"use one of {', '.join(VERDICTS)}")

    doc = _read_doc(image)
    board = (doc.get("seen") or {}).get("board") or {}
    if not board:
        raise ValueError(
            f"refusing to record {verdict!r} for {p.name}: it was never on a board. A "
            f"verdict for a shot nobody was shown leaves the shot unseen while the command "
            f"looks like it worked, which is the same forgery a verdict filed under a guard "
            f"that never fired would be. Compose the board first.")

    # `waived` is never on a board, because a waiver is by definition not a tap. Every
    # other verdict must be one the operator was actually offered.
    offered = {str(o).strip().lower() for o in board.get("options") or []}
    if verdict != "waived" and verdict not in offered:
        raise ValueError(
            f"refusing to record {verdict!r} for {p.name}: the board offered "
            f"{sorted(offered) or '[]'}. A verdict the operator was never shown is not "
            f"something they can have chosen.")

    if verdict in NEEDS_REASON and not why:
        raise ValueError(
            f"{p.name} was judged {verdict} with no reason. Write one. A verdict nobody "
            f"can argue with later is a skip with better manners.")

    now = digest(image)
    if board.get("digest") and now and now != board["digest"]:
        raise ValueError(
            f"refusing to record a verdict for {p.name}: the bytes changed since the board "
            f"was composed. The operator judged a different picture, and a re-roll writes "
            f"the new one at the same path, so this yes would silently approve art nobody "
            f"has looked at. Show it again.")

    seen = doc.setdefault("seen", {})
    seen["verdict"] = verdict
    seen["on"] = on or _now()
    seen["digest"] = now
    if why:
        seen["why"] = why
    else:
        seen.pop("why", None)
    _write_doc(image, doc)
    return seen


def seen_problem(image) -> str | None:
    """Why `image` may not be locked yet, or None when it may.

    The sentence `lock_shot` refuses with. It names what is missing and how to record it,
    because a refusal that only says no sends the reader looking for a flag to turn it off.
    """
    p = pathlib.Path(image)
    seen = read_seen(image)
    board = seen.get("board") or {}
    verdict = str(seen.get("verdict") or "").lower()

    if not board:
        return (f"nobody has been shown {p.name}. A golden IS human judgement frozen, so a "
                f"lock with no recorded look has frozen nothing. Put it on an "
                f"AskUserQuestion board with shoot-references' shot_board.py and record the "
                f"operator's tap; a waived verdict with a written reason is the recorded "
                f"exception when they are genuinely absent.")
    if verdict not in VERDICTS:
        return (f"{p.name} was put on a board and no verdict came back. A board nobody "
                f"answered is indistinguishable from one nobody was shown.")
    if verdict == "reroll":
        why = seen.get("why") or "no reason recorded"
        return (f"{p.name} was judged RE-ROLL ({why}). Regenerate it from scratch with the "
                f"defect named as an explicit negative; never lock a shot the operator "
                f"turned down.")
    if verdict not in APPROVING:
        return f"{p.name} carries verdict {verdict!r}, which is not an approval."

    now = digest(image)
    was = seen.get("digest") or board.get("digest")
    if was and now and now != was:
        return (f"{p.name} has changed since it was judged. The verdict is about the bytes "
                f"the operator saw, and these are not those bytes. Show it again.")
    return None
