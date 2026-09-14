"""Where your universes are, and where you left off.

The framework could grade a universe from the day `universe-doctor` shipped, but you
had to know that verb existed, know you wanted a grade, and know the path to hand it.
That is a destination, not a front door. A cartridge should open by telling you where
you are.

This module is the small amount of state that makes that possible:

  ~/.abu/universes.json   the universes you work on, so nothing has to be typed
  ~/.abu/state.json       the last score seen per universe, so a session can say
                          "B- to B since Tuesday" instead of only "B"

Both are plain JSON under `$ABU_HOME` (default `~/.abu`), because state you cannot
open in an editor is state you cannot fix when it is wrong.

Deliberately NOT here: any grading logic. `universe-doctor` owns the rubric and stays
the single definition of a good universe. This only answers *which* universes and
*compared to when*.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

MARKER = "universe.json"


def home() -> Path:
    return Path(os.environ.get("ABU_HOME", "~/.abu")).expanduser()


def registry_path() -> Path:
    return home() / "universes.json"


def state_path() -> Path:
    return home() / "state.json"


def _read(path: Path, default):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return default


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")


# ------------------------------------------------------------------ discovery


def is_universe(path: Path) -> bool:
    return (Path(path).expanduser() / MARKER).is_file()


def find_upward(start: Path | None = None) -> Path | None:
    """The nearest universe at or above `start`.

    Walking UP matters: you are usually deep inside a universe (in `stories/`, in a
    book folder) when you want to know how it is doing, and being asked for a path
    you are already standing in is exactly the friction this removes.
    """
    cur = Path(start or Path.cwd()).expanduser().resolve()
    for candidate in [cur, *cur.parents]:
        if is_universe(candidate):
            return candidate
    return None


# ------------------------------------------------------------------ registry


def registered() -> list[Path]:
    """Known universes, dropping any that no longer exist on disk."""
    raw = _read(registry_path(), {"universes": []})
    out = []
    for entry in raw.get("universes", []):
        p = Path(entry).expanduser()
        if is_universe(p):
            out.append(p.resolve())
    return out


def register(path: Path) -> Path:
    """Remember a universe. Idempotent, and refuses a directory that is not one."""
    p = Path(path).expanduser().resolve()
    if not is_universe(p):
        raise ValueError(f"not a universe (no {MARKER}): {p}")
    known = [str(x) for x in registered()]
    if str(p) not in known:
        known.append(str(p))
    _write(registry_path(), {"universes": sorted(known)})
    return p


def forget(path: Path) -> None:
    p = str(Path(path).expanduser().resolve())
    _write(registry_path(), {"universes": [x for x in (str(y) for y in registered()) if x != p]})


def resolve(explicit: str | None = None, start: Path | None = None) -> list[Path]:
    """Which universes this invocation is about, in priority order.

    An explicit path wins; then the one you are standing in; then everything
    registered. Empty means the honest answer is "you have no universes yet", which
    is an onboarding moment rather than an error.
    """
    if explicit:
        p = Path(explicit).expanduser().resolve()
        if not is_universe(p):
            raise ValueError(f"not a universe (no {MARKER}): {p}")
        return [p]
    here = find_upward(start)
    if here:
        # Seeing a universe is enough to remember it. Without this, `abu` from
        # anywhere else reports "you have none" about a universe you were standing
        # in five minutes ago, which reads as amnesia rather than as a front door.
        try:
            register(here)
        except (ValueError, OSError):
            pass
        return [here]
    return registered()


# ------------------------------------------------------------------ progress


def last_seen(universe: Path) -> dict | None:
    """The previous reading for a universe, or None the first time."""
    return _read(state_path(), {}).get(str(Path(universe).expanduser().resolve()))


def record(universe: Path, score: int, grade: str, on: str | None = None) -> dict:
    """Save this reading and return the delta against the previous one.

    `on` is injectable so a test never depends on today's date.
    """
    key = str(Path(universe).expanduser().resolve())
    all_state = _read(state_path(), {})
    prev = all_state.get(key)
    entry = {"score": int(score), "grade": grade, "on": on or date.today().isoformat()}
    # Keep a short trail. One previous reading answers "did it move"; a trail answers
    # "am I on a run", which is the question that actually keeps someone going.
    hist = list((prev or {}).get("history") or [])
    if prev and prev.get("on") != entry["on"]:
        hist.append({"score": prev["score"], "grade": prev["grade"], "on": prev["on"]})
    entry["history"] = hist[-10:]
    all_state[key] = entry
    _write(state_path(), all_state)
    return {
        "now": entry,
        "previous": prev,
        "delta": None if prev is None else int(score) - int(prev.get("score", 0)),
    }


# ------------------------------------------------------------------ next moves


# What each dimension means in a sentence a person would say, with `{n}` for the count.
# The grader's own `fix` strings are written for whoever maintains the grader
# ("write canon/properties/<id>.json, then `abu build-canon`"), and a front door whose
# entire premise is that you never see a command cannot hand those to a human. The
# grader keeps its vocabulary; this translates at the edge.
# NO COUNTS HERE, deliberately. The obvious version interpolated the group size and
# said "1 image(s) cannot say how they were made" about 276 images: the grader
# AGGREGATES, so one issue record can stand for hundreds of files. That is the same
# trap that made the first `small` selector pick the largest job. The sentence carries
# the meaning; the grader's own `what` string carries the numbers, because it is the
# only thing that actually knows them.
# THE FRONT DOOR'S ONE HARD RULE, AS CODE (SPEC v0.49).
#
# `abu`'s whole promise is that a person never sees a command: "a command in the
# transcript is a defect in this skill". That was prose, and prose does not bind, so the
# framework's own strings broke it. The grader's `fix` field is written for whoever
# maintains the GRADER ("write canon/properties/<id>.json, then `abu build-canon`",
# "split the rooms into settings with `partOf`", "abu backfill-provenance (records what
# is knowable)"), and two paths carried it straight to a human:
#
#   humanize()          used `fix` as its FALLBACK for any dimension with no sentence
#                       here, and `setting_nesting` had no sentence here, so its
#                       backticked identifiers went into `plan.headline.human` -- the one
#                       field `abu`'s SKILL.md tells the agent to say out loud.
#   next_actions.board  shows a non-verb-shaped `fix` as the LABEL of a tappable option,
#                       so the same strings became the board.
#
# The old test suite named the hole and blessed it: `test_unknown_dimension_falls_back`
# asserted the leak was the behaviour. So: every dimension the grader can emit needs a
# sentence here (a test reads grade.py's own RUBRIC and refuses a missing one), and
# anything command-shaped is refused as user-facing text whatever its source.
#
# The detector is deliberately conservative. A PATH is not a command and is not caught;
# what is caught is an invocation (`abu validate`, `python3 x.py`), a flag, a script by
# name, and a shell operator. Over-triggering would silently blank real sentences, which
# is a worse failure than the one being fixed.
_CLI = ("abu", "python3", "python", "uv", "npx", "node", "git", "bash", "sh", "pip", "make", "cd", "ls")
_BARE_CLI = ("abu", "python3", "npx", "git")
_COMMAND_TELLS = (
    # a backticked span that starts with, or contains, an invocation
    re.compile(r"`[^`]*\b(?:" + "|".join(_CLI) + r")\s+\S[^`]*`"),
    # a bare invocation in running prose: "abu validate", "python3 grade.py"
    re.compile(r"(?<![\w/-])(?:" + "|".join(_BARE_CLI) + r")\s+[a-z][\w-]*(?![\w-])"),
    re.compile(r"(?<!\S)--[a-z][\w-]+"),                 # a flag
    re.compile(r"(?<!\S)\S+\.(?:py|sh|ts|mjs|bash|zsh)(?!\w)"),  # a script by name
    re.compile(r"&&|\|\||\$\("),                          # shell operators
)


def command_in(text: str) -> str | None:
    """The first command-shaped span in `text`, or None.

    Used wherever a string is about to reach a person through the front door. It is a
    detector, never a formatter: callers decide whether to drop the string, swap it, or
    refuse, because the right answer differs between a report and a tappable option.
    """
    for pat in _COMMAND_TELLS:
        m = pat.search(text or "")
        if m:
            return m.group(0)
    return None


OUTCOMES = {
    "validity":       "some canon records do not parse, so the universe cannot be trusted to load",
    "identity":       "the universe has no settled look yet: no register anchor, mark, or voice to render against",
    "entities":       "some characters, places or objects have no art yet, so every render invents them fresh",
    "setting_size":   "some places cannot prove their own size, so people and rooms drift out of scale",
    # Added v0.49. Its absence was the live leak: with no sentence here, the fallback was
    # the grader's own fix, which names two JSON keys in backticks.
    "setting_nesting": "one place is modelled as several rooms at once, so each room is "
                       "judged against the other rooms' rules",
    "provenance":     "some images cannot say how they were made",
    "craft_canon":    "the universe has no recorded rules of craft, so taste lives in prompts instead of in canon",
    "stories":        "something you have made is not registered as a story over this canon",
    "self_contained": "some references point outside the universe, so a copy of it would not render",
}


def humanize(dimension: str, detail: str = "", fallback: str = "") -> str:
    """The outcome in a sentence, with the grader's own detail carrying the numbers.

    NOTHING COMMAND-SHAPED SURVIVES THIS FUNCTION, whichever argument it arrived in.
    `fallback` is the grader's `fix`, which is written for the grader's maintainer and
    routinely holds an invocation; it is used only when it reads as plain language.
    A command-shaped fallback or detail is DROPPED rather than raised on, because this
    sits on the front door's reporting path and a crash there costs more than a
    vaguer sentence.
    """
    sentence = OUTCOMES.get(dimension)
    if not sentence:
        fallback = " ".join((fallback or "").split())
        sentence = (fallback if fallback and not command_in(fallback)
                    else f"open items in {dimension.replace('_', ' ')}")
    detail = " ".join((detail or "").split())
    if detail and command_in(detail):
        detail = ""
    out = f"{sentence} ({detail})" if detail else sentence
    # Last line of defence: a sentence that still reads as a command is not shown at all.
    return out if not command_in(out) else f"open items in {dimension.replace('_', ' ')}"


def plan(issues: list[dict], small_max: int = 2) -> dict:
    """Turn a long issue list into the few things worth saying out loud.

    A real universe returns hundreds of issues (227 on the first run against Nation
    of Fire). Reciting them is not a front door, it is a wall. So group identical
    fixes, then surface:

      headline  the highest-impact group, for when there is real time
      small     the LOWEST-impact group, for "I have ten minutes and I'm bored"
      rest      how much is omitted, so the summary is honest about what it hid

    `small` is chosen by low impact, NOT by group size. The first version used size
    and picked wrong: the grader already aggregates, so "835 images have no recipe"
    arrives as a single issue and looked like the smallest job available when it was
    the largest. Impact is the grader's own judgement and does not lie about scale.
    `count` is still reported, but it counts ISSUE RECORDS, which is not the same as
    units of work, and nothing here pretends otherwise.
    """
    groups: dict[tuple, dict] = {}
    for i in issues:
        key = (i.get("dimension", ""), i.get("fix", ""))
        g = groups.setdefault(key, {
            "dimension": key[0], "fix": key[1], "count": 0, "impact": 0, "examples": [],
        })
        g["count"] += 1
        g["impact"] = max(g["impact"], int(i.get("impact", 0)))
        g["human"] = humanize(g["dimension"], i.get("what", ""), g["fix"])
        if len(g["examples"]) < 3:
            g["examples"].append(i.get("what", ""))

    ranked = sorted(groups.values(), key=lambda g: (-g["impact"], -g["count"], g["fix"]))
    headline = ranked[0] if ranked else None
    # Cheapest first, and never the headline again: offering the biggest job twice
    # is how a "if you're bored" suggestion becomes useless.
    small = next((g for g in sorted(ranked, key=lambda g: (g["impact"], g["count"], g["fix"]))
                  if g is not headline), None)
    return {
        "headline": headline,
        "small": small,
        "groups": ranked,
        "total_issues": len(issues),
        "remaining_groups": max(0, len(ranked) - len([x for x in (headline, small) if x])),
    }
