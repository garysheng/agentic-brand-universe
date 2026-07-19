"""Deterministic entity scaffolding (SPEC v0.4 §12 reference matrix).

The `add-*` skills call this so authoring is tested machinery, not hand-written
JSON. A scaffolded entity validates green immediately with lock_level == "stub":
its reference-matrix slots are null and requiredForRender is empty until the art
step (lock-references) fills paths and promotes the required set.
"""
from __future__ import annotations

from .matrix import matrix_for


def scaffold_entity(
    kind: str,
    eid: str,
    name: str,
    origin_story: str | None = None,
    photo_stack: list[str] | None = None,
) -> dict:
    """A schema-valid entity stub for `kind`. Raises ValueError on an unknown kind.

    - character/prop/motif: `structured.sheets` carries the kind's matrix keys as
      null slots; `requiredForRender` is [] (populated when art locks).
    - setting/visual-metaphor: an `unlocked` `contract` (refused until locked).
    - a non-empty `photo_stack` (character only) adds a `gated` `realPerson` block.
    """
    KNOWN = {"character", "setting", "visual-metaphor", "doctrine", "motif", "beat", "prop", "group"}
    if kind not in KNOWN:
        raise ValueError(f"unknown kind '{kind}' (allowed: {sorted(KNOWN)})")

    ent: dict = {
        "id": eid,
        "kind": kind,
        "originStory": origin_story,
        "authority": {"lockedBy": "TODO-you", "lockedOn": None},
    }

    if kind in ("character", "prop", "motif"):
        m = matrix_for(kind)
        shots = m["shots"] if m else ["hero"]
        ent["structured"] = {
            "sheets": {s: None for s in shots},   # null slots -> filled by lock-references
            "requiredForRender": [],               # promoted to the matrix required set on lock
            "invariants": [],
        }
        ent["prose"] = {"voice": "", "lore": "", "rules": ""}
        if kind == "character" and photo_stack:
            ent["realPerson"] = {
                "photoStack": list(photo_stack),
                "canonicalPhotos": {},
                "approval": {"state": "gated", "by": eid, "on": None},
                "sensitiveList": "RESEARCH.md#sensitive",
                "wardrobeEras": {"default": ""},
                "groupCount": None,
            }
    elif kind in ("setting", "visual-metaphor"):
        ent["status"] = "unlocked"
        ent["contract"] = {
            "turnaround": None, "emptyPlates": [], "blueprint": None,
            "map": "", "blocking": "", "dressing": "",
        }
        ent["prose"] = {"rules": ""}
    else:  # doctrine, beat, group
        ent["structured"] = {"sheets": {}, "requiredForRender": []}
        ent["prose"] = {"rules": ""}

    return ent
