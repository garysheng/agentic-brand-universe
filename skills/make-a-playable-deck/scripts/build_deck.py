#!/usr/bin/env python3
"""ABU's playable deck: a WRAPPER over Freedom's deck builder that adds the universe's palette.

    build_deck.py <deck.json> --out <dir> [--palette <palette.json>] [--assets <dir>]
                  [--repo-root <universe>]

Same arguments as Freedom's builder, which it runs. The builder and its shell moved into Freedom
on 2026-09-18 (create-or-update-deck) and this file stopped being a copy on 2026-09-23: two
renderers of one deck disagree within a week, which is the failure the move existed to end.

WHAT THIS ADDS is the one thing a universe knows that Freedom does not: which palette a deck
should wear. It passes `--palette` itself, resolved in this order, and a flag you pass wins:

  1. the deck's own `palette` (a palette.json) or `universe` (a universe root), relative to the
     deck file, which is freedom#163's declaration and works from any builder that runs it;
  2. `--repo-root <universe>`, when that universe has canon/craft/palette.json;
  3. the universe the deck SITS in: the nearest folder above the deck holding
     canon/craft/palette.json, so a deck in <universe>/works/ is on-brand with no flag.

Resolving the declaration here too, rather than leaving it to the builder, means a machine on
an older Freedom that predates the declaration still gets the right look instead of a neutral
deck that looks finished. A declared brand that does not resolve is REFUSED, same reason.

WHERE FREEDOM IS: $FREEDOM_DECK_BUILDER (a build_deck.py), else
$FREEDOM_PLUGIN/.agents/skills/create-or-update-deck/scripts/build_deck.py, else the same under
~/.freedom/plugin, which is the symlink every Freedom install keeps to its current version.
"""
from __future__ import annotations

import json
import os
import pathlib
import sys

REL = pathlib.Path(".agents") / "skills" / "create-or-update-deck" / "scripts" / "build_deck.py"
PALETTE = pathlib.Path("canon") / "craft" / "palette.json"


def freedom_builder() -> pathlib.Path:
    tried = []
    env = os.environ.get("FREEDOM_DECK_BUILDER")
    if env:
        tried.append(pathlib.Path(env).expanduser())
    for root in (os.environ.get("FREEDOM_PLUGIN"), "~/.freedom/plugin"):
        if root:
            tried.append(pathlib.Path(root).expanduser() / REL)
    for p in tried:
        if p.is_file():
            return p
    sys.exit("make-a-playable-deck: Freedom's deck builder was not found. It lives in the "
             "Freedom plugin (create-or-update-deck) since 2026-09-18; ABU's skill wraps it. "
             "Install or update Freedom, or set FREEDOM_DECK_BUILDER to its build_deck.py.\n"
             "  looked at: " + ", ".join(str(p) for p in tried))


def arg(argv: list[str], flag: str) -> str | None:
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv):
            return argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


def palette_for(argv: list[str]) -> pathlib.Path | None:
    positional = [a for i, a in enumerate(argv)
                  if not a.startswith("--") and (i == 0 or not argv[i - 1].startswith("--"))]
    if not positional:
        return None  # let the builder print its own usage
    deck_file = pathlib.Path(positional[0]).expanduser().resolve()
    try:
        deck = json.loads(deck_file.read_text())
    except (OSError, ValueError):
        return None  # the builder names the real problem better than a guess here would
    base = deck_file.parent
    for key in ("palette", "universe"):
        v = deck.get(key)
        if not isinstance(v, str) or not v.strip():
            continue
        q = pathlib.Path(v).expanduser()
        q = q if q.is_absolute() else base / q
        path = q / PALETTE if key == "universe" else q
        if not path.is_file():
            sys.exit(f"make-a-playable-deck: the deck declares {key} {v!r}, but {path} does "
                     f"not exist. A deck that names its brand and renders without it looks "
                     f"finished and is wrong.")
        return path
    root = arg(argv, "--repo-root")
    if root and (pathlib.Path(root).expanduser() / PALETTE).is_file():
        return pathlib.Path(root).expanduser() / PALETTE
    for d in [base, *base.parents]:
        if (d / PALETTE).is_file():
            return d / PALETTE
    return None


def main() -> None:
    argv = sys.argv[1:]
    builder = freedom_builder()
    if arg(argv, "--palette") is None and not any(a in ("-h", "--help") for a in argv):
        pal = palette_for(argv)
        if pal:
            argv += ["--palette", str(pal)]
            print(f"[abu] palette: {pal}", file=sys.stderr)
    os.execv(sys.executable, [sys.executable, str(builder), *argv])


if __name__ == "__main__":
    main()
