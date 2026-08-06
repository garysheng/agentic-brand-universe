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


# SPEC v0.37 §12: a matrix shot with NO REGISTER AT ALL.
#
# The framework's own vocabulary has carried the concept since `face-neutral-color`
# was documented above as "a full-colour, REGISTER-NEUTRAL face plate", and nothing
# honoured it: `chain_matrix.resolve_register` refused unconditionally on a null
# `identity.register.anchor` ("the universe style is not locked; do not generate"),
# and the two escapes beside it (`--register`, `--no-style-pack`) both choose WHICH
# anchor to pass and neither can say NONE.
#
# That is an ordering deadlock for any universe built around a real person. The
# architecture Proof of Vibes states out loud (Gary, 2026-08-06: "we want to create a
# hyper realistic character of Russ, and then we can create variations that are in
# different registers") is one photoreal identity master with N register conversions
# DERIVED from it. The master must be shot before any register is blessed, because the
# master is the thing every register is later derived FROM. Under the old refusal it
# could never be shot at all: the register gates the master, and the master is exactly
# the artefact that owes the register nothing.
#
# So neutrality is DECLARED IN CANON (`structured.registerNeutral`), not chosen per
# invocation. A flag would let the next operator re-shoot the master in-register with
# nothing complaining; a durable declaration on the entity is what makes the second
# shoot refuse.
#
# THE HARD HALF: neutral means NO ANCHOR IS PASSED, not "an anchor is not required".
# Once a register IS blessed, a re-shoot would otherwise silently bake that register
# into the one asset whose entire job is to be medium-free, and a reference image
# outranks a word every time (the physics `dropSheets` and `--star` were both earned
# by). An anchor reaching a register-neutral shoot is therefore a REFUSAL.
REGISTER_NEUTRAL_CONTRACT: list[str] = [
    "the register anchor IMAGE is not passed as a reference on any shot of this matrix",
    "the register's style line is not prepended; the entity's declared `medium` leads instead",
    "the register's `rejectedPoles` are not baked as negatives, because a pole is the "
    "opposite of a medium this matrix is not being shot in (the entity's own "
    "`structured.negatives` and its prompts.md negatives still are)",
    "the anchor-subject guard is not emitted, because no anchor's subject is in play",
    "`--register` and `--no-style-pack` are REFUSED, because both of them name WHICH "
    "anchor to pass and neither can name none",
    "every shot's recipe records `registerNeutral` and a null `anchor`, so a later "
    "reader can tell a deliberate absence from a forgotten input",
]

# The one instruction a register-neutral plate owes every render that later consumes it.
# The MAKING half is the contract above; this is the CONSUMPTION half, and it composes
# with the per-slot `role` vocabulary (SPEC §12, v0.23) rather than replacing it: a role
# says what ONE plate contributes, this says what the whole entity's plate set is FOR.
REGISTER_NEUTRAL_CONSUMPTION = (
    "REGISTER-NEUTRAL MASTER: {id}'s reference plates are {medium} and are NOT a style "
    "reference. Take likeness, geometry, proportion and markings from them exactly. Take "
    "NO medium, paint language, lighting, surface treatment or colour grading from them: "
    "render {id} fully in this image's declared style."
)


def register_neutral(entity: dict) -> dict | None:
    """The entity's register-neutral declaration, or None.

    Raises ValueError when one is DECLARED MALFORMED, and that is the load-bearing
    half. Returning None on a half-written declaration would silently fall back to
    passing the register anchor, which is the exact outcome the declaration exists to
    forbid, so this fails closed: an unreadable declaration stops the shoot rather
    than downgrading it to an in-register one.

    `medium` is required because it REPLACES the register's style line in the prompt.
    Naming the medium positively is what actually moves a model (see
    `chain_matrix.style_line`); a neutral shoot with no medium named is a shoot with no
    style instruction at all, which returns whatever the base model prefers.

    `why` is required because this field says a matrix deliberately disobeys the
    anchor-first rule the rest of the framework enforces, and a standing exemption with
    no recorded reason is the thing the next author deletes or copies blindly.
    """
    rn = (entity.get("structured") or {}).get("registerNeutral")
    if rn is None or rn is False:
        return None
    eid = entity.get("id") or "<entity>"
    if not isinstance(rn, dict):
        raise ValueError(
            f"{eid}: structured.registerNeutral must be an OBJECT declaring `medium` and "
            f"`why`, not {type(rn).__name__}. A bare true cannot say what the master IS, "
            f"and the medium is what replaces the register's style line in the prompt.")
    if not str(rn.get("medium") or "").strip():
        raise ValueError(
            f"{eid}: structured.registerNeutral declares no `medium`. Say what this matrix "
            f"IS in one line (\"hyper-realistic documentary photography\"): it is passed as "
            f"the shoot's style line in place of the register, and a neutral shoot with no "
            f"medium named has no style instruction at all.")
    if not str(rn.get("why") or "").strip():
        raise ValueError(
            f"{eid}: structured.registerNeutral declares no `why`. This field exempts one "
            f"matrix from the anchor-first rule every other shoot in the universe obeys; "
            f"record why in one line (\"one photoreal master, every register derived from "
            f"it\") so the exemption is auditable.")
    return rn


def register_neutral_untyped_slots(entity: dict) -> list[str]:
    """Sheet keys on a register-neutral entity that declare no `role`. Advisory.

    A register-neutral plate is passed into renders whose medium it deliberately does
    not share, and an UNTYPED slot emits no per-ref instruction at all (`role_lines`),
    so its medium reaches the model as loudly as its likeness. `role` is the existing
    hook for exactly this ("Ignore its ... medium" appears in four of the five role
    instructions), which is why this composes with roles instead of inventing a second
    vocabulary.
    """
    try:
        if not register_neutral(entity):
            return []
    except ValueError:
        return []
    sheets = (entity.get("structured") or {}).get("sheets") or {}
    return sorted(k for k, v in sheets.items()
                  if v and not (isinstance(v, dict) and v.get("role")))


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
