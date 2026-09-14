"""The CHANNEL a decision is shown on, and what each channel can prove about it.

v0.50 settled what SEEN means -- a tap on an `AskUserQuestion` card -- and built the
refusals that keep the tap honest. It left one gap open, and `shoot-references`' own map
recorded it rather than letting the closed question read as complete:

    "Still open, and genuinely the owner's call: whether the board should carry the picture
    itself rather than its path. The preview is text, so what the operator taps against is a
    filename plus the entity's invariants."

**AN `AskUserQuestion` PREVIEW IS TEXT.** It carries the path and the checklist and it
cannot carry the picture. So the v0.50 record proved the operator tapped a card NAMING a
file and proved nothing about whether the art was ever in front of them. Left alone that is
worse than no gate: it refuses to lock art nobody tapped, which reads as rigour, while
training the operator to tap through a list of filenames.

**THE DISCRIMINATOR, AND IT IS GENERAL (v0.51).** A decision the operator can answer FROM
WORDS stays an `AskUserQuestion` card in the terminal: it is faster there, and a web page
for a yes/no spends their attention for nothing. A decision that requires SEEING the thing
goes to a frapp -- a Freedom app, a page served off the operator's own machine, reachable
from their phone. Shot approval is the first and clearest case, because it is not answerable
from a filename.

**WHY A FRAPP AND NOT A VIEWER ON THIS MACHINE.** A local image viewer would have to be
DRIVEN by the agent and then ATTESTED to, which is the same unverifiable claim one level
along: an agent that says it opened a window is exactly as checkable as an agent that says
the operator looked. The frapp removes the claim instead of patching it, because the thing
that SERVES the image is the thing that RECORDS the tap. "Was the art displayed" stops being
something anybody asserts and becomes something the page knows: the browser asked for the
bytes, the bytes went out, and the verdict came back over the same connection. It also goes
where the operator is rather than where the render happened, which is the failure
`shoot-references` earned on 2026-07-30 when Preview reported ten images opened to a screen
the operator was nowhere near.

**NOTHING OF THE FRAPP LIBRARY IS VENDORED HERE.** The token gate, the tailnet phone route,
the journal, the secure-origin refusal and the design system are Freedom's, shipped in
`freedom-frapp.mjs`, and ABU DEPENDS on them: this module only locates the newest installed
copy, exactly as a scaffolded frapp does at its own start, and `shot-board.mjs` imports it at
runtime. A copy would fork and diverge inside a month.

**AND IT DEGRADES HONESTLY, WHICH MEANS THE TWO RECORDS DO NOT LOOK ALIKE.** ABU runs on
machines that are not this one. With no Freedom install there is no frapp, so the board falls
back to the text card -- and the fallback is written into the record as `channel: "card"`
with the reason it fell back, so a lock that rests on a filename says so forever and can be
found with a grep. A degrade that produced the same record as the real thing would be this
whole gate's own failure mode, one level along.

WHAT THE FRAPP CHANNEL PROVES, EXACTLY. That the picture's bytes were delivered to the
browser the operator answered from, at a named moment, hashed, and that the verdict arrived
from that same page. It does not prove a human looked at the screen, and nothing can: eyes
are not addressable. The claim is deliberately small and deliberately true.
"""
from __future__ import annotations

import datetime as _dt
import os
import pathlib
import shutil

FRAPP = "frapp"
CARD = "card"
CHANNELS = (FRAPP, CARD)

# Where a Freedom install keeps its versioned libraries. Same location and same
# newest-wins rule a scaffolded frapp resolves at ITS start; see `freedomLib()` in
# create-or-manage-frapp/scripts/scaffold.mjs. Never a pinned version: the next plugin
# update deletes that directory (freedom#106).
FREEDOM_CACHE = "~/.claude/plugins/cache/freedom-workspace/freedom"
ENV_LIB = "FREEDOM_LIB_DIR"   # a dev checkout's .agents/lib, for the maintainer's machine
LIB_FILE = "freedom-frapp.mjs"


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def freedom_lib(file: str = LIB_FILE, env=None) -> pathlib.Path | None:
    """The newest installed Freedom library file, or None when Freedom is not installed."""
    env = os.environ if env is None else env
    override = (env.get(ENV_LIB) or "").strip()
    if override:
        p = pathlib.Path(override).expanduser() / file
        return p if p.is_file() else None
    cache = pathlib.Path(env.get("FREEDOM_CACHE_DIR") or FREEDOM_CACHE).expanduser()
    try:
        versions = [d for d in cache.iterdir() if (d / ".agents" / "lib" / file).is_file()]
    except OSError:
        return None
    if not versions:
        return None
    # Numeric-aware sort, so 4.269.0 beats 4.9.0 the way it does in the .mjs resolver.
    def key(d):
        return [int(x) if x.isdigit() else x for x in d.name.replace("-", ".").split(".")]
    try:
        versions.sort(key=key)
    except TypeError:
        versions.sort(key=lambda d: d.name)
    return versions[-1] / ".agents" / "lib" / file


def node(env=None) -> str | None:
    """The node binary, or None. A frapp is a node program; without one there is no frapp."""
    env = os.environ if env is None else env
    explicit = (env.get("ABU_NODE") or "").strip()
    if explicit:
        return explicit if shutil.which(explicit) or pathlib.Path(explicit).is_file() else None
    return shutil.which("node")


def resolve_channel(env=None) -> tuple[str, str]:
    """`(channel, why)`: which surface this machine can put a picture on, and why not the other.

    `why` is empty for the frapp channel and is the sentence the record carries for the card
    channel, because a refusal or a caveat that only says no sends the reader looking for a
    flag to turn the gate off.
    """
    env = os.environ if env is None else env
    forced = (env.get("ABU_DISPLAY_CHANNEL") or "").strip().lower()
    if forced == CARD:
        return CARD, ("ABU_DISPLAY_CHANNEL=card was set, so the board is a text card and the "
                      "art was not displayed by anything that can vouch for it.")
    if not node(env=env):
        return CARD, ("no `node` on this machine, and a frapp is a node program, so the board "
                      "is an AskUserQuestion card. Its preview is TEXT: it carries the path and "
                      "the checklist and cannot carry the picture. Nothing here has shown the "
                      "operator the art.")
    if freedom_lib(env=env) is None:
        return CARD, (f"no Freedom install on this machine (no {LIB_FILE} under "
                      f"{FREEDOM_CACHE}), so there is no frapp to serve the picture and the "
                      f"board is an AskUserQuestion card. Its preview is TEXT: it carries the "
                      f"path and the checklist and cannot carry the picture. Nothing here has "
                      f"shown the operator the art.")
    return FRAPP, ""


def pending(channel: str, why: str = "", on: str | None = None) -> dict:
    """The display record a board is stamped with BEFORE anything has been served.

    `served` is false here in both channels and stays false forever in the card one. On the
    frapp channel it is flipped by the page itself, at the moment the bytes go out, which is
    the point of the whole mechanism: the server of the image is the recorder of the serve.
    """
    channel = (channel or "").strip().lower()
    if channel not in CHANNELS:
        raise ValueError(f"unknown display channel {channel!r}; use one of {list(CHANNELS)}")
    rec = {"channel": channel, "served": False, "on": on or _now()}
    if why:
        rec["why"] = why
    return rec
