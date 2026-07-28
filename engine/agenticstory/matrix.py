"""Reference matrix (SPEC v0.4 §12): what 'locked' means per entity kind.

ADVISORY in v0.4 — `lock_level` (in refs.py) reports completeness against this
table. It does NOT change the load-bearing gate's hard-fail on a missing
REQUIRED sheet (refs.assert_story / assert_spread are unchanged).
"""
from __future__ import annotations

# Per-kind canonical reference shots for kinds addressed by `structured.sheets`.
# `shots` is the full matrix (needed for 'locked'); `required` is the minimum.
# setting / visual-metaphor are matrixed via their `contract` (see refs.resolve_setting),
# not sheet keys, so they are intentionally absent here.
REFERENCE_MATRIX: dict[str, dict] = {
    "character": {
        "shots": ["face-neutral", "face-3q", "expressions", "forward-fullbody",
                  "profile-left", "profile-right", "back", "signature-pose"],
        "required": ["forward-fullbody", "face-neutral"],
        # `face-neutral-color`: a full-colour, register-neutral face plate.
        #
        # OPTIONAL because a face sheet in any NON-PHOTOGRAPHIC medium carries
        # facial architecture and NO complexion. A blue ballpoint engraving, an
        # ink line drawing, a graphite study: none of them contain a skin tone for
        # the renderer to copy. Pass one and you correct the bone structure while
        # leaving colouring entirely to the style pack, which reverts to the base
        # model's bias. That cost seven render batches on gary-sheng-art's `jesus`
        # (2026-07-27) before anyone opened the plates and saw they were monochrome.
        #
        # It is NOT in `shots`, because `shots` is the COMPLETENESS list: putting it
        # there would demote every already-locked character in every universe to
        # `partial` over a plate most of them do not need. Characters defined from
        # colour references are already fine. Entities that DO need it declare it in
        # `structured.requiredForRenderOnLock`, which is what `optional` exists to
        # permit without weakening the typo check.
        "optional": ["face-neutral-color"],
    },
    "prop":  {"shots": ["hero", "detail"], "required": ["hero"]},
    "motif": {"shots": ["hero", "detail"], "required": ["hero"]},
}


def matrix_for(kind: str) -> dict | None:
    """The reference matrix for a kind, or None if the kind is not sheet-matrixed."""
    return REFERENCE_MATRIX.get(kind)


def known_shots_for(kind: str) -> list[str]:
    """Every shot key the framework recognises for a kind: matrix + optional.

    `shots` alone is the completeness list and is deliberately narrow. This is the
    NAME-VALIDITY list, so an entity can require a legitimate extra plate without
    that plate dragging every peer entity's lock level down with it.
    """
    m = matrix_for(kind) or {}
    return list(m.get("shots") or []) + list(m.get("optional") or [])
