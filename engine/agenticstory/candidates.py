"""What counts as the CURRENT candidate for a slot, and what never goes in front of an operator.

A universe keeps its history beside its art, on purpose: a turned-down take is parked in
`rejected/`, a replaced master in `superseded-<why>-<date>/`, a pre-re-roll backup in
`candidates/pre-reroll-<ts>/`, and an earlier roll of a work as `<slug>.rN.png`. All of that
is the record, and none of it is a candidate. An approval board that shows it is asking the
operator to judge art that has already been judged, and a `keep` tapped on it would lock a
picture somebody already turned down.

Earned 2026-09-24. The entity shot board read `reference/<id>/` and one level down per look,
skipping only `photos/`, `rejected/` and `candidates/`, so `witney/superseded-unlit-2026-09-24/`
was read as a LOOK folder and its retired plates came back as cards; Gary was shown superseded
and rejected rolls beside the live ones. The rule lives here, once, because two boards (the
entity shot board and the works board) apply it and a second copy of a refusal drifts. The
page-side copy in `skills/shoot-references/frapps/candidates.mjs` is held to this one by a test
that runs both over the same paths.
"""
from __future__ import annotations

import pathlib
import re

# A directory whose contents are the record, never a candidate. Matched against EVERY component
# between the root and the file, so `witney/casual/rejected/x.png` is caught as well as
# `witney/rejected/x.png`.
NOT_CANDIDATE_DIR = re.compile(r"^(rejected|superseded.*|candidates|photos|pre-reroll-.*)$",
                               re.IGNORECASE)

# An earlier roll kept beside the live file: `<slug>.r1.png`, `<slug>.r12.webp`. The live
# candidate for that slot is `<slug>.png`.
ROLL = re.compile(r"\.r\d+\.(png|jpe?g|webp)$", re.IGNORECASE)

IMAGE = re.compile(r"\.(png|jpe?g|webp)$", re.IGNORECASE)


def why_not_candidate(path, root=None) -> str | None:
    """Why `path` is not a current candidate, or None when it is.

    `root` bounds the directory check: only components BELOW it are read, so a universe that
    happens to live under a folder called `candidates` is not refused wholesale.
    """
    p = pathlib.Path(path)
    if not IMAGE.search(p.name):
        return f"{p.name} is not an image"
    if ROLL.search(p.name):
        return (f"{p.name} is an earlier ROLL of its slot (the `.rN` suffix); the current "
                f"candidate is the file without it")
    parts = p.parts
    if root is not None:
        try:
            parts = p.resolve().relative_to(pathlib.Path(root).resolve()).parts
        except ValueError:
            parts = p.parts
    for part in parts[:-1]:
        if NOT_CANDIDATE_DIR.match(part):
            return (f"{p.name} sits in `{part}/`, which holds turned-down, retired or backed-up "
                    f"art, never a candidate")
    return None


def is_candidate(path, root=None) -> bool:
    return why_not_candidate(path, root) is None
