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
    },
    "prop":  {"shots": ["hero", "detail"], "required": ["hero"]},
    "motif": {"shots": ["hero", "detail"], "required": ["hero"]},
}


def matrix_for(kind: str) -> dict | None:
    """The reference matrix for a kind, or None if the kind is not sheet-matrixed."""
    return REFERENCE_MATRIX.get(kind)
