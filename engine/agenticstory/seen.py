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

AND THE BOARD MUST CARRY THE PICTURE, NOT ITS PATH (v0.51). A tap proves a decision was
made; it does not prove there was anything to decide FROM. An `AskUserQuestion` preview is
TEXT, so the v0.50 record proved the operator tapped a card NAMING a file. So every board
declares the CHANNEL it was shown on (`agenticstory.display`), a frapp records the moment it
SERVES the image bytes, and an approving tap against a frapp board that never served is
refused. The card channel survives as the honest fallback for a machine with no Freedom
install, and it writes its own weakness into the record under a different key, so the two
kinds of yes cannot be mistaken for each other by anything reading them later.

Six refusals, and each one is a way the record could otherwise be forged:

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
  NEVER SERVED    an approving tap on a FRAPP board whose page never sent the picture. The
                  browser not asking for the bytes is the case where the operator was looking
                  at a broken image, and the tap that followed is a tap on a caption.

Like the recipe beside it, this sidecar is a build artifact and never ships.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import pathlib
import uuid

from . import display as display_module

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


def record_board(image, *, question: str, options: list[str], display: dict,
                 labels: list[str] | None = None,
                 board_id: str | None = None, entity: str | None = None,
                 shot: str | None = None, on: str | None = None) -> dict:
    """Stamp `image` as having been put on a board. Written when the board is COMPOSED.

    `options` are the VERDICT TOKENS the board offers, and `labels` the words the operator
    actually read. They are recorded separately because they differ by design -- a card
    reading "Re-roll" records `reroll` -- and comparing a verdict against a label is how a
    legitimate tap gets refused for a spelling nobody chose.

    `display` is the CHANNEL record (`agenticstory.display.pending`), and it is required
    rather than optional because a board with no declared channel is exactly the board this
    version exists to stop: one that asks the operator to approve art it never shows them.
    It is stamped here as not-yet-served in both channels; on the frapp channel the page
    flips it when the bytes go out, which is the only witness that is not somebody's word.

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
    if not isinstance(display, dict) or display.get("channel") not in display_module.CHANNELS:
        raise ValueError(
            f"refusing to board {p}: no display channel. A board is a question ABOUT A "
            f"PICTURE, and an AskUserQuestion preview is TEXT -- it carries the path and the "
            f"checklist and cannot carry the art. Composing one without declaring how the "
            f"picture reaches the operator records a look at a filename. Pass "
            f"agenticstory.display.pending(*display.resolve_channel()).")
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
        # The channel travels INSIDE the board, because it is a fact about this showing and
        # a re-board on another machine is a different showing.
        "display": dict(display),
    }
    if entity:
        seen["board"]["entity"] = entity
    if shot:
        seen["board"]["shot"] = shot
    _write_doc(image, doc)
    return seen


def record_serve(image, *, sent_digest: str | None = None, url: str | None = None,
                 on: str | None = None) -> dict:
    """Record that the picture's BYTES went out. Written by the page that sent them.

    This is the whole point of v0.51 and the reason it is not another attestation: nobody
    claims the art was displayed, the thing that displayed it says so, at the moment it did,
    about the bytes it actually wrote. An agent has no way to call this truthfully on a
    picture no browser asked for, because the refusals below are about the file on disk and
    the board that was composed from it, and the honest caller is the frapp handler.

    `sent_digest` is what the server hashed on its way out. It is checked against the file
    rather than trusted, so a page that read one file and reported another is refused.
    """
    p = pathlib.Path(image)
    doc = _read_doc(image)
    board = (doc.get("seen") or {}).get("board") or {}
    if not board:
        raise ValueError(
            f"refusing to record a serve for {p.name}: it was never on a board. A picture "
            f"served against no question is a file download, not a showing.")

    disp = board.get("display") or {}
    if disp.get("channel") != display_module.FRAPP:
        raise ValueError(
            f"refusing to record a serve for {p.name}: the board was composed on the "
            f"{disp.get('channel')!r} channel, which serves nothing. Only a frapp can report "
            f"having sent the bytes, because only a frapp sent any.")

    now = digest(image)
    if board.get("digest") and now and now != board["digest"]:
        raise ValueError(
            f"refusing to record a serve for {p.name}: the bytes changed since the board was "
            f"composed, so the page is showing a picture this board is not about. Compose the "
            f"board again against what is on disk now.")
    if sent_digest and now and sent_digest != now:
        raise ValueError(
            f"refusing to record a serve for {p.name}: the page reports sending {sent_digest} "
            f"and the file on disk hashes to {now}. A serve record is about the bytes that "
            f"left, and these are not the same bytes.")

    disp = dict(disp)
    disp["served"] = True
    disp["servedOn"] = on or _now()
    disp["digest"] = now
    if url:
        disp["url"] = url
    disp.pop("why", None)
    board["display"] = disp
    _write_doc(image, doc)
    return disp


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

    # AND SOMETHING MUST HAVE SHOWN IT (v0.51). On the frapp channel the page records the
    # moment it sends the bytes, so a `keep` with no serve means the browser never asked for
    # the picture: the operator was looking at a broken image and the tap is a tap on a
    # caption. `reroll` is deliberately exempt -- turning art down is the safe direction and
    # refusing it would trap the operator -- and `waived` is exempt because a waiver is by
    # definition not a look.
    disp = board.get("display") or {}
    if verdict == "keep" and disp.get("channel") == display_module.FRAPP and not disp.get("served"):
        raise ValueError(
            f"refusing to record 'keep' for {p.name}: the board's page never served this "
            f"picture, so nothing has put it in front of anyone. Open the board and look at "
            f"the shot; if the image is broken there, fix the path rather than the record. "
            f"An operator who is genuinely absent is a `waived` verdict with a written "
            f"reason, which says on the record that nobody looked.")

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
    # THE DEGRADED YES DOES NOT LOOK LIKE THE REAL ONE. An approval taken against a board
    # that displayed nothing carries its own key and the reason it displayed nothing, so
    # every lock resting on a filename is one grep away and can never be mistaken later for
    # a lock resting on a picture. A degrade whose record matched the real thing would be
    # this gate's own failure mode, one level along.
    if verdict in APPROVING and not disp.get("served"):
        seen["unshown"] = {"channel": disp.get("channel"),
                           "why": disp.get("why") or "the art was not displayed"}
    else:
        seen.pop("unshown", None)
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

    # Defence in depth against a hand-edited sidecar (v0.51). `record_tap` already refuses
    # this, so reaching it here means the file was written by something other than the verbs.
    disp = (board.get("display") or {})
    if verdict == "keep" and disp.get("channel") == display_module.FRAPP and not disp.get("served"):
        return (f"{p.name} was approved on a frapp board that never served the picture. The "
                f"page records the moment the bytes go out, and for this shot it never did, "
                f"so the yes is about a caption.")

    now = digest(image)
    was = seen.get("digest") or board.get("digest")
    if was and now and now != was:
        return (f"{p.name} has changed since it was judged. The verdict is about the bytes "
                f"the operator saw, and these are not those bytes. Show it again.")
    return None


def seen_caveat(image) -> str | None:
    """What a lockable shot's approval does NOT prove, or None when it proves what it says.

    `seen_problem` is the gate and this is the footnote. On a machine with no Freedom install
    there is no frapp, the board falls back to a text card, and the resulting `keep` is a
    legitimate verdict about a filename. It locks -- refusing it would make ABU unusable
    anywhere but one machine -- and it says what it is, everywhere anybody prints it.
    """
    seen = read_seen(image)
    un = seen.get("unshown") or {}
    if not un:
        return None
    return (f"{pathlib.Path(image).name} was approved WITHOUT the art being displayed: "
            f"{un.get('why') or 'no reason recorded'} The verdict is a tap on a card naming "
            f"a file, which is weaker than one taken on a frapp that served the picture.")
