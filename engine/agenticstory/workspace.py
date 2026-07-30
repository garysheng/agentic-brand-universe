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
    all_state[key] = entry
    _write(state_path(), all_state)
    return {
        "now": entry,
        "previous": prev,
        "delta": None if prev is None else int(score) - int(prev.get("score", 0)),
    }


# ------------------------------------------------------------------ next moves


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
