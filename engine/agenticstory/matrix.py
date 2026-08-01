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
        #
        # `scale-plate` (v0.21): a solo head-to-toe plate against a MEASURED reference,
        # so a character can prove its own height.
        #
        # v0.9 gave settings this and stated the reason in one line: a plate cannot be
        # judged on a dimension it does not depict. That reasoning was never applied to
        # people. `structured.scale` (v0.10) looks like it closes the gap and does not:
        # its `height` is prose that NOTHING depicts, and its `scalePlate` is explicitly
        # a two-up of a PAIR at true relative height. Between them they answer "is he
        # taller than her" and never "how tall is he" — so a solo `forward-fullbody` on
        # a blank ground still carries no unit of comparison, the model picks a stature,
        # and every render inherits the guess.
        #
        # Same `optional` reasoning as above: promoting it to `shots` would demote every
        # already-locked character in every universe. Advisory instead, exactly as
        # SETTING-NO-SCALE-PLATE was advisory in v0.9.
        "optional": ["face-neutral-color", "scale-plate"],
    },
    # `scale-plate` on an object answers the same question for the other half of Gary's
    # ask (2026-08-01): "how tall different people AND DIFFERENT THINGS are." A prop had
    # no size record of any kind — neither a descriptor nor a plate — so a chair, a
    # pendant and a door were all whatever size the model felt like.
    "prop":  {"shots": ["hero", "detail"], "required": ["hero"],
              "optional": ["scale-plate"]},
    "motif": {"shots": ["hero", "detail"], "required": ["hero"]},
}


# What a scale plate must satisfy to be worth shooting, independent of register.
# The framework fixes the GEOMETRY (these); a universe supplies the TREATMENT via
# `identity.scaleReference`, so a luminous symbolic universe is not forced to render
# a gym stadiometer to say how tall someone is.
SCALE_PLATE_CONTRACT: list[str] = [
    "solo subject, no second figure in frame",
    "full head-to-toe, feet visible and flat on even ground, nothing cropped",
    "camera at mid-torso height, square to the subject, no low or high angle",
    "no perspective foreshortening; the figure reads at true proportion",
    "a MEASURED reference in frame whose real size is stated in the recipe",
    "the subject's declared `structured.scale.height` is legible against that reference",
]

# The default measured reference, when a universe declares no `identity.scaleReference`.
# Deliberately architectural rather than clinical: Gary asked for "a measuring stick or
# something TASTEFUL", and a graduated batten or a door of stated height reads as part of
# a built world in nearly every register, where a medical stadiometer reads as a prop.
SCALE_REFERENCE_DEFAULT = (
    "a discreet graduated vertical batten marked at each foot, or an architectural element "
    "of stated height (a door, a standard step riser, a counter) with its real dimension "
    "recorded in the plate's recipe"
)


# SPEC v0.27: what it takes to reproduce a REAL PERSON with confidence.
#
# `lock-level` answers "are the files on disk". It has never answered the question a
# brand actually needs: is there enough coverage here to reproduce this person
# reliably, in a new pose, months from now, without their likeness drifting.
#
# The kind matrix requires TWO shots for a character. For an invented character that is
# defensible. For a real person it is not, and this universe proved it in one session:
# `gary` reached the required set early and his likeness still had to be rebuilt across
# five rerolls, nine photographs and a purpose-built chest-up plate before it held.
#
# Three things the old model could not express, each of which cost real renders:
#
#  1. ANGLE COVERAGE. The rule "a single reference lets a face drift, pass six varied
#     angles" lived in one universe's prose preamble and was right all day. Nothing
#     enforced it, and `realPerson.photoStack` accepted a single photo.
#  2. EXPRESSION COVERAGE. A stack of one expression reproduces that expression. Gary
#     supplied two open-smile photographs precisely because every render was coming
#     back closed-lipped and it read wrong to him.
#  3. CONTEXT COVERAGE. The sharpest one. His pendant kept rendering wrong not for want
#     of pendant references, but because no plate showed it at a size the model could
#     resolve: in a head-to-toe frame it is about forty pixels. The fix was a chest-up
#     plate where the prop is legible. A matrix that only asks "which angles of the
#     person" cannot ask that.
REAL_PERSON_COVERAGE = {
    "photoStack": {
        "min": 6,
        "why": "Six varied angles is the floor at which a face stops drifting between "
               "renders. Earned across two universes and restated in every one of them.",
    },
    "requiredShots": ["face-neutral", "face-3q", "forward-fullbody"],
    "expressions": {
        "min": 2,
        "why": "A stack carrying one expression reproduces one expression. At least a "
               "neutral and a genuine smile, so the face is known at rest and in use.",
    },
    "contextPlate": {
        "why": "Any character carrying a recurring prop needs one plate where that prop "
               "is LEGIBLE at render scale. Without it the prop is re-invented every "
               "time, because no reference ever showed it big enough to copy.",
    },
}


def real_person_gaps(entity: dict) -> list[str]:
    """What still stands between a real person and confident reproduction.

    Advisory, exactly like `lock_level`. It never blocks a render; it answers a
    question the framework could not previously answer at all.
    """
    st = entity.get("structured") or {}
    rp = st.get("realPerson") or entity.get("realPerson") or {}
    if not rp:
        return []
    gaps = []
    stack = rp.get("photoStack") or []
    n = REAL_PERSON_COVERAGE["photoStack"]["min"]
    if len(stack) < n:
        gaps.append(f"photoStack has {len(stack)} entr(ies); {n} varied angles is the floor "
                    f"at which a face stops drifting between renders")
    sheets = st.get("sheets") or {}
    for shot in REAL_PERSON_COVERAGE["requiredShots"]:
        if not sheets.get(shot):
            gaps.append(f"no `{shot}` plate; a real person needs face-neutral, face-3q and "
                        f"forward-fullbody before a likeness can be called reproducible")
    if not sheets.get("expressions") and not rp.get("expressionsNote"):
        gaps.append("no `expressions` plate; a stack carrying one expression reproduces one "
                    "expression")
    props = rp.get("recurringProps") or []
    if props and not (sheets.get("chest-up") or rp.get("contextPlate")):
        gaps.append(f"carries recurring prop(s) {props} but has no context plate where the "
                    f"prop is legible at render scale; in a head-to-toe frame a pendant is "
                    f"about forty pixels and gets re-invented every render")
    return gaps


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
