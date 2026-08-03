#!/usr/bin/env python3
"""Assemble ONE spread's render job from canon (SPEC per-spread apply).

Deterministic: (universe, render-spec, spread-id) -> JSON with
  prompt   the full generation prompt (register-anchor register line first)
  refs     ordered reference image paths, ABSOLUTE, register anchor FIRST
  size     the model render size
  qa       the readback checklist, one line per in-frame invariant

The whole point: NOTHING load-bearing about a character or setting is retyped by
the author. Character identity — including which LOOK (default or a named
altLooks.<key>) — comes from canon/entities/<id>.json. The per-book render-spec
carries only per-spread COMPOSITION (cast + selected look + scene staging) plus
book-wide style/negatives. Because the character block, its refs, AND the
negatives are all computed from the SAME canon look, a per-book file can no
longer silently contradict a character's canon (the bug this skill exists to kill:
a global "everyone is clean-shaven" negative fighting a canon facial-hair alt-look).

Usage:
  assemble_prompt.py <universe> <render-spec.json> <spread-id>
"""
import argparse
import json
import re
import sys
from pathlib import Path


class Refuse(Exception):
    pass


# A guarded negative (e.g. "no facial hair") is satisfied only by an invariant
# that POSITIVELY declares the feature. Negatively-phrased invariants like
# "completely-clean-shaven-never-a-mustache" contain the feature word ("mustache")
# but must NOT count as declaring it — so an invariant carrying any of these
# negation markers can never satisfy a guard.
NEG_MARKER = re.compile(r"clean-shaven|beardless|\bno-|-no-|never|bare|without", re.I)

# Sheet keys that show the FACE. On an alt look these are dropped (the alt anchor
# photo IS the face+hair); BODY sheets (fullbody, pose) are kept for proportion.
FACE_SHEET_KEYS = {"face-3q", "face-neutral", "face", "expressions"}


# THE REGISTER ANCHOR IS A STYLE SAMPLE, AND ITS SUBJECT LEAKS ON A BARE SPREAD.
# Promoted from the Nation of Fire fork 2026-07-25 (earned on the-vision-of-the-ocean).
# The anchor is passed FIRST on every render, so on a spread that casts no setting and
# no characters it is one of only TWO references and the model reads it as CONTENT: a
# "look down into the water" beat came back as a first-century room full of robed
# strangers carrying the anchor's own oil lamp and clay jar. Every other spread survived
# only because setting plates and character sheets gave the model more to attend to,
# which is why passing an anchor looked safe for months. This is a property of passing
# an anchor AT ALL, so it belongs on every prompt rather than in each book's style text.
ANCHOR_STYLE_GUARD = (
    "THE FIRST REFERENCE IMAGE IS A STYLE ANCHOR ONLY. Match it for MEDIUM, BRUSHWORK, PALETTE and "
    "LIGHT QUALITY ONLY, and take NO subject from it whatsoever: none of its objects, figures, "
    "costume, props, furniture, architecture, period or location may appear in the output unless the "
    "scene description below asks for them by name."
)

# A MULTI-PANEL REFERENCE MAKES A MULTI-PANEL SPREAD.
# Promoted from the Nation of Fire fork 2026-07-25 (earned on why-do-i-get-to-meet-them).
# Several canon references are legitimately study sheets: a character turnaround, a
# visual-metaphor's states sheet. The model copies their panelled LAYOUT, and two spreads
# came back as contact-sheet grids of six framed views instead of one scene. Opt out with
# `allowMultiPanel` on the book or on one spread.
MOTION_VERBS = (
    "walk", "walking", "walks", "step", "stepping", "steps", "run", "running", "runs",
    "climb", "climbing", "enter", "entering", "leave", "leaving", "approach", "approaching",
    "head toward", "heading", "going toward", "moves toward", "coming out", "carries", "carrying",
    "flee", "fleeing", "crossing", "toward the", "out of the", "into the",
)

# A viewer-relative facing token. Without one of these, a scene that says a person
# is moving "toward the door" has told the model nothing it can act on, because the
# model does not know where the door will end up in frame.
FACING_TOKENS = (
    "from behind", "behind and", "back to camera", "back to the camera", "over his shoulder",
    "over her shoulder", "over their shoulder", "facing camera", "facing the camera",
    "toward the viewer", "away from the viewer", "faces away", "seen from the side",
    "side on", "in profile", "three-quarter", "three quarters", "profile",
    "away from camera", "toward camera", "his back", "her back", "their back",
)

MOTION_GUARD = (
    "DIRECTION OF TRAVEL. If a person in this scene is moving toward something, that "
    "destination MUST BE AHEAD OF THEM IN THE FRAME and they must be seen FROM BEHIND or "
    "from three-quarters behind, so the viewer is following them into it. A figure whose "
    "face is toward the camera is walking AWAY from everything behind them: if the thing "
    "they are moving toward is drawn behind them, the picture says the opposite of the "
    "scene. Their feet, hips, shoulders and gaze all point the same way, along the "
    "direction of travel."
)

def _has_motion(scene: str) -> bool:
    """True when the scene describes someone moving somewhere.

    Earned 2026-07-28 on Our God of Miracles Lives spread 96: the scene said a man
    was "stepping over them toward the door", and the render put him walking toward
    the CAMERA with the lit doorway behind him, so the picture said the opposite of
    the beat. Image models strongly prefer a subject's face to the lens, and a WORLD-relative
    direction ("toward the door") cannot beat that prior because the model has not
    placed the door yet when it decides which way the body points.
    """
    low = (scene or "").lower()
    if not any(v in low for v in MOTION_VERBS):
        return False
    return not any(t in low for t in FACING_TOKENS)


ADDRESSING_GUARD = (
    "SPEAKER AND AUDIENCE GEOMETRY. Someone addressing a group FACES that group, and the "
    "group FACES THEM BACK. The two are on OPPOSITE sides of one another, never on the same "
    "side. So there are exactly TWO legal cameras and you must pick one of them. EITHER the "
    "camera is BEHIND OR AMONG THE AUDIENCE, in which case the audience fills the near "
    "foreground SEEN FROM BEHIND (backs of heads and shoulders) and the speaker stands beyond "
    "them FACING THE CAMERA. OR the camera is AT THE SPEAKER, in which case we see the speaker "
    "from behind or in three-quarter rear view and the audience beyond them is TURNED TOWARD "
    "THE CAMERA with their FACES VISIBLE. THE AUDIENCE IS NEVER ARRAYED BEHIND THE SPEAKER, "
    "never scattered around them, and never seated facing the same direction the speaker "
    "faces. A speaker with listeners behind their shoulders has their back turned on the "
    "people they are talking to, which is not what the scene means."
)

AUDIENCE_NOUNS = (
    "congregation", "audience", "crowd", "assembly", "students", "pews", "auditorium",
    "listeners", "class", "attendees", "worshippers", "parishioners", "staff",
)
# A PULPIT OR LECTERN IS ITSELF AN ADDRESSING SIGNAL, because the furniture only
# exists to point one person at a group. Matching verb phrases alone was too narrow
# and MISSED THE VERY SPREAD THAT EARNED THIS GUARD: spread 67 read "standing at a
# plain pulpit", and the phrase token "at a pulpit" does not match "at a plain
# pulpit". Prefer the bare noun and accept a little noise; a guard that misses the
# case it was written for is worse than one that fires on an empty church.
ADDRESSING_VERBS = (
    "pulpit", "lectern", "podium",
    "preach", "preaching", "preaches", "teach", "teaching", "teaches", "address",
    "addressing", "speak", "speaking", "speaks to", "sermon", "lectur",
    "reads them", "reading to", "explaining", "holds up the", "holding up the",
)


def _has_audience(scene: str) -> bool:
    """True when the scene has one person addressing a group.

    Earned 2026-08-01 on The Power of Obeying, THREE separate times, which is what
    promoted it from a per-scene correction to a guard. Spreads 24 and 26 seated a
    congregation facing the BACK WALL of their own church, so a camera at the pulpit
    returned rows of backs of heads (and in 26 they voted at the rear wall). Spread 67
    put a preacher at a pulpit with the congregation arrayed BEHIND him, blurred, so the
    payoff image of a seventy-year preaching ministry showed a man with his back turned
    on everyone he was preaching to.

    The prior is strong and it is a COMPOSITION prior, not a facing prior, so the
    existing FACING_TOKENS do not neutralise it: 'church congregation' overwhelmingly
    means the view from the back over people's heads, and 'a man at a pulpit' means a
    portrait with a soft crowd behind him. Both are photographically common and both are
    geometrically impossible for the beats above. Naming the camera does not help,
    because the model satisfies the camera and then places the people by cliche.
    """
    low = (scene or "").lower()
    return (any(n in low for n in AUDIENCE_NOUNS)
            and any(v in low for v in ADDRESSING_VERBS))


BEDCLOTHES_GUARD = (
    "WHAT A PERSON WEARS IN BED. Someone who has been asleep, is waking, is sitting up in "
    "bed or is getting out of bed is wearing NIGHTCLOTHES appropriate to their period and "
    "station: a nightshirt, a plain pyjama suit, a nightgown, a plain undershirt. They are "
    "NOT wearing a business suit, a jacket, a waistcoat, a necktie, a buttoned dress shirt, "
    "a belt, dress shoes, or outdoor clothing of any kind, because nobody sleeps in those. "
    "Their hair is SLEEP-DISORDERED rather than combed or styled, and the bedclothes are "
    "rumpled around them. THE ONE EXCEPTION is when the scene explicitly says they are "
    "dressed (they have just come in from outside, or lain down in their clothes without "
    "sleeping); in that case obey the scene and dress them as it says."
)

BED_NOUNS = (
    "in bed", "on the bed", "into bed", "out of bed", "bedstead", "bedclothes", "bedspread",
    "the covers", "the blankets", "pillow", "quilt", "mattress", "nightstand",
)
SLEEP_TOKENS = (
    "asleep", "sleeping", "slept", "wakes", "woke", "waking", "awoken", "awake",
    "sat up", "sits up", "sat bolt upright", "bolt upright", "upright in bed",
    "swung his legs", "swung her legs", "swung both legs", "nightclothes", "nightshirt",
    "pyjama", "pajama", "nightgown", "half past one in the morning", "in the small hours",
    "at first light", "before dawn", "5:45", "at dawn",
)


def _in_bed(scene: str) -> bool:
    """True when a person in this scene has been sleeping or is waking in a bed.

    Earned 2026-08-01 on The Power of Obeying, where THREE spreads (37, 43, 62) put a
    man in a full business suit and necktie in his own bed at night and at dawn. The
    character entity asserted "he wears a plain suit" unconditionally, and canon prose
    outranks anything a scene leaves unsaid, so a beat that never said "pyjamas" got a
    suit. That was fixed on that one entity; this guard exists because the failure is
    not about that entity. ANY character whose canon states a default outfit will be put
    to bed in it, in any universe, and no author reliably remembers to say otherwise.

    Deliberately requires BOTH a bed noun and a sleep signal, so a scene where someone
    lies down on a bed still dressed (having just walked in) does not trip it, and the
    guard carries an explicit exception for scenes that state the person is dressed.
    """
    low = (scene or "").lower()
    return (any(n in low for n in BED_NOUNS)
            and any(t in low for t in SLEEP_TOKENS))


BED_LENGTH_GUARD = (
    "A BED IS LONG ENOUGH FOR THE WHOLE BODY IN IT. If a person is lying or reclining on a "
    "bed in this scene, draw the bed at TRUE ADULT LENGTH: head on the pillow at one end and "
    "the feet reaching most of the way to the other end, with the whole torso AND the whole "
    "length of the legs fitting inside the frame of the bed. A lying adult is roughly THREE "
    "AND A HALF TIMES their own shoulder width from crown to heel, so the mattress must be "
    "far longer than the person's torso alone. THE FOOTBOARD OR FOOT OF THE BED IS NEVER AT "
    "THE HIPS, THE THIGHS OR THE KNEES: it sits beyond the feet. Do NOT crop the bed short, "
    "do NOT let the covers end at the waist with the mattress ending just past it, and do NOT "
    "draw a child-sized or half-length bed under a grown adult. If the camera cannot fit the "
    "whole bed, let the foot of it run out of frame rather than shortening it."
)

LYING_TOKENS = (
    "lies", "lying", "lay ", "laid", "reclin", "propped", "in bed", "on the bed",
    "under the covers", "under the quilt", "bedridden", "bedfast", "asleep", "sleeping",
)


def _person_lying_on_bed(scene: str) -> bool:
    """True when a person is lying on a bed in this scene.

    Earned 2026-08-01 on The Power of Obeying spread 62 (Gary: "add a bed guard that
    checks if the bed is way too short for legs to be in it"). The render put an old
    man in a bed whose footboard reached his hips: his torso filled the whole
    mattress and there was nowhere for his legs to be. Image models compose a
    reclining figure to fill the frame and then fit the furniture around the part
    they drew, so the bed gets truncated to whatever the visible body needed. It
    reads instantly as wrong and no existing guard covered it, because the defect is
    FURNITURE PROPORTION rather than anatomy, register or facing.

    Distinct from the bedclothes guard on purpose: that one fires on bed + a SLEEP
    signal and governs what the person WEARS. This one fires on bed + a LYING signal
    and governs how long the BED IS, so a beat where someone lies down fully dressed
    still gets the length rule.
    """
    low = (scene or "").lower()
    return (any(n in low for n in BED_NOUNS)
            and any(t in low for t in LYING_TOKENS))


CROWD_MEMBER_GUARD = (
    "A NAMED CHARACTER SITTING IN A CROWD IS STILL PART OF THAT CROWD. When someone the "
    "story cares about is among an audience, congregation, class or crowd, they FACE THE SAME "
    "WAY EVERYONE ELSE FACES and hold the same posture as the people around them. They are "
    "NOT turned out toward the camera while the rest of the room faces the speaker, NOT "
    "swivelled in their seat, NOT leaning into the aisle, NOT lit differently, NOT haloed, and "
    "NOT given more space around them than their neighbours. A figure facing a different "
    "direction from everyone around them reads as detached from the room, or as though they "
    "are looking at something nobody else can see. IF THE SCENE NEEDS THEIR FACE, MOVE THE "
    "CAMERA, NOT THE PERSON: shoot the crowd from in front or from the side so their face is "
    "naturally visible while they still face what everyone else faces. Make them findable by "
    "PLACEMENT and by what they wear, never by breaking the room's shared orientation."
)

# Only phrases that place an INDIVIDUAL inside the group. Bare "seated in" / "sits in"
# were dropped: they describe the crowd itself ("the congregation sits in two blocks")
# and fired this guard on speaker-addressing scenes it has nothing to say about.
CROWD_MEMBERSHIP_TOKENS = (
    "among the", "among them", "in the audience", "in the congregation", "in the crowd",
    "in an aisle seat", "sits among", "sitting among", "seated among",
    "one of the seated", "among the seated", "in the rows", "in the pews",
)


def _cast_inside_crowd(scene: str) -> bool:
    """True when a named character is seated INSIDE an audience rather than addressing it.

    Earned 2026-08-01 on The Power of Obeying spread 61 (Gary: "why are you having
    him not face the speaker... just because the star is in the audience doesn't
    mean that they should be standing out in a weird way"). Every other listener
    faced the woman teaching; the book's subject was rotated three-quarters toward
    the lens, so he alone looked away from the person speaking.

    This is the mirror image of the addressing guard and needs its own rule. That
    one governs the geometry BETWEEN a speaker and a crowd. This one governs a
    character INSIDE the crowd, where the model's pull is not composition cliche but
    its preference for showing a protagonist's face, which it satisfies by turning
    the body rather than by moving the camera.
    """
    low = (scene or "").lower()
    return (any(n in low for n in AUDIENCE_NOUNS)
            and any(t in low for t in CROWD_MEMBERSHIP_TOKENS))


SINGLE_IMAGE_GUARD = (
    "ONE SINGLE CONTINUOUS FULL-BLEED PAINTING that fills the entire canvas edge to edge. This is "
    "NEVER a grid, NEVER a multi-panel layout, NEVER a comic page, NEVER a contact sheet, NEVER a "
    "study or turnaround sheet, NEVER a collage, and NEVER several framed views side by side. Some "
    "reference images supplied to you are multi-panel study sheets; use them ONLY for the identity "
    "and design of what they depict, and NEVER copy their panelled layout into the output. The "
    "output has exactly ONE camera, ONE moment, and NO internal borders, frames, gutters, or "
    "dividing lines of any kind."
)

# Preamble keys a SINGLE SPREAD may override. Everything else stays book-level on purpose.
#
# PER-SPREAD REGISTER OVERRIDE, promoted 2026-07-25 (earned on
# jerry-and-the-game-that-beat-gta, a book that argues its thesis in its own paint).
# A book may legitimately carry more than ONE visual register when the change is
# DIEGETIC: a game world shown on a screen, a vision blooming out of a canon device, a
# memory, a dream. Before this, `style` / `negatives` / `anchorRef` were book-level ONLY,
# so the only way to render a second register was a SECOND render-spec, which duplicates
# the whole preamble and drifts the moment one copy is edited. A spread that names none
# of these compiles byte-identically to before.
_SPREAD_OVERRIDES = (
    "style", "negatives", "guardedNegatives", "anchorRef",
    "allowMultiPanel", "allowUncast", "allowArchived", "size", "settingRule",
)


def _name_tokens(eid: str) -> set[str]:
    """The given name a scene would use for a character id.

    ONLY the first token, because entity ids are `<given-name>-<qualifier>`
    (`cynthia-gentry`, `jerry-man`, `silas-driver`) and the qualifier is usually a common
    word: matching on it made the ordinary noun "driver" in a car scene flag
    `silas-driver`. A surname is not worth the false-positive rate, since prose in these
    universes addresses people by first name.
    """
    head = eid.split("-")[0]
    return {head} if len(head) > 3 else set()


def uncast_characters(uroot: Path, scene: str, cast_ids: set[str]) -> list[tuple[str, str]]:
    """Character entities NAMED in the scene text but never CAST in this spread.

    Promoted from the Nation of Fire fork 2026-07-25 (earned on why-do-i-get-to-meet-them).
    THE most expensive defect class this pipeline produces, and it is silent: the model
    happily invents a stranger for anyone the prose names but the refs do not supply. Five
    spreads there said "a hint of Cynthia's near shoulder" or named Jerry without casting
    them, and every one came back with a wrong human being in frame, discovered only after
    paying for the render. An over-the-shoulder single still needs BOTH people cast,
    because the shoulder is a person. This is a pure-text check, so it costs nothing and
    runs before any image is generated.
    """
    ents = uroot / "canon" / "entities"
    if not ents.is_dir():
        return []
    low = (scene or "").lower()
    # DESIGNED TEXT IS NOT A PERSON IN FRAME (earned on nation-of-fire/the-higher-law, 2026-07-25).
    # In-art text is first-class (a cover title, signage, a plaque) and the spec convention is that
    # the exact string is QUOTED in the scene. A book cover reading 'APOSTLE DELMAR COWARD JR.' AND
    # 'GARY SHENG' therefore tripped this guard and demanded two characters be cast who are not in
    # the scene at all, and the tempting move was the --allow-uncast escape hatch. Inside quotes is
    # lettering to render, never a body to draw.
    low = re.sub(r"'[^']*'", " ", low)
    low = re.sub(r'"[^"]*"', " ", low)

    # A name token already ACCOUNTED FOR by something cast is not a missing character.
    # Ids of the form `<role>-of-<x>` all share one head token, so a scene that casts
    # chief-of-counterfeits and writes "the Chief of Counterfeits" was flagging the other
    # four chiefs, and a scene casting apostle-lee that writes "the Apostle" flagged every
    # other apostle. Both fired on real books and both are false: the word in the prose
    # refers to the entity that IS cast, whose refs the model is already given.
    cast_tokens: set[str] = set()
    for cid in cast_ids:
        cast_tokens |= _name_tokens(cid)

    missing: list[tuple[str, str]] = []
    for path in sorted(ents.glob("*.json")):
        eid = path.stem
        if eid in cast_ids:
            continue
        try:
            if load(path).get("kind") != "character":
                continue
        except (ValueError, OSError):
            continue
        for tok in _name_tokens(eid):
            if tok in cast_tokens:
                continue
            if re.search(rf"\b{re.escape(tok)}\b", low):
                missing.append((eid, tok))
                break
    return missing


def load(p: Path):
    with open(p) as f:
        return json.load(f)


def load_entity(uroot: Path, eid: str) -> dict:
    """An entity by id, REFUSING cleanly when canon has no such file.

    `load()` raised a bare FileNotFoundError, which is a traceback rather than a
    refusal: it names a tempdir path instead of the spread and the cast id that
    are actually wrong, and in a batch render it escapes the per-spread handler
    and takes down every remaining spread with it. An id the universe has never
    heard of is precisely what the pre-spend gate exists to name.
    """
    p = uroot / "canon" / "entities" / f"{eid}.json"
    if not p.exists():
        raise Refuse(
            f"'{eid}' is cast but is not registered in canon (no {p.name}). "
            f"Add it with abu:add-character / add-setting / add-prop / add-motif / "
            f"add-visual-metaphor, or fix the id.")
    return load(p)


def deslug(inv: str) -> str:
    # invariants are kebab slugs (they double as render-readback keys); render
    # them as plain words in the prompt while keeping the slug for QA.
    return inv.replace("-", " ")


# Real-person entities declare `photoStack` as a DIRECTORY of bare-face photos, by
# convention (see any realPerson entity). A directory is not a reference the image model
# can accept, so it must be expanded to the actual image files here. Left unexpanded, the
# generator crashed with IsADirectoryError on EVERY real-person spread, which is every
# Nation of Fire book about a real friend. Found 2026-07-23 rendering the Russ book
# through the real pipeline (the reason to use the pipeline and not a hand-rolled script).
_IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")

def resolve_ref(uroot: Path, p: str) -> list[str]:
    """Resolve a ref path to a LIST of on-disk image files. A path may be absolute,
    universe-relative, or relative to the universe's PARENT (cross-repo anchors live
    beside the universe). A DIRECTORY expands to the image files directly inside it,
    sorted, so a realPerson photoStack directory becomes its photos."""
    cand = Path(p)
    tries = [cand] if cand.is_absolute() else [uroot / p, uroot.parent / p, cand]
    for t in tries:
        if t.exists():
            if t.is_dir():
                imgs = sorted(str(f.resolve()) for f in t.iterdir()
                              if f.suffix.lower() in _IMG_EXTS)
                if not imgs:
                    raise Refuse(f"ref directory has no images: {p}")
                return imgs
            return [str(t.resolve())]
    raise Refuse(f"ref does not resolve on disk: {p}")


# CAST CLOSURE. The prompt says who IS in frame and never said that is ALL who is.
# Every other guard here is about the SCENE text; this one exists because the defect
# comes from the PREAMBLE. A book-wide `style` string is prepended to every spread,
# so any figure it mentions is present on every spread whether or not that spread
# cast them, and the uncast-character refusal cannot see it: that guard reads the
# scene, and the invention is coming from the style.
#
# It is not catchable by name either. The styles that caused this described the cast
# GENERICALLY ("a small hand-made helper", "a man at a desk"), so no entity name
# appears anywhere to match on.
#
# Cost, in one session, on two different books: eleven re-renders. A different
# invented robot in five spreads of one book, one of them three spreads before that
# character is introduced and one rendered twice in the same frame at two sizes;
# then a man appearing in two spreads of another book whose scenes said the room was
# empty. The lesson was written into this skill after the first occurrence and the
# same sentence was written again twice more, which is what a documentation-only fix
# is worth.
#
# So the assembler now states the closure itself, derived from the cast, on every
# render. An author cannot forget it and a preamble cannot contradict it.
CAST_CLOSURE_NONE = (
    "THERE ARE NO PEOPLE AND NO CHARACTERS OF ANY KIND IN THIS IMAGE. No person, no figure, no head, "
    "no shoulder, no arm, no hand, no silhouette, no reflection of a person, and nobody seated in any "
    "chair. Any place a figure might be expected is empty."
)


# ANONYMOUS FIGURES. The closure above is fail-closed, which is right, but it had no
# way to say "there ARE people here and none of them is a canon character". A crowd, a
# stranger, a class of children seen from behind, a widow at her own kitchen table: all
# are deliberately not entities, because promoting every passer-by to canon is the bug
# rule 7 exists to prevent in the other direction.
#
# Without an escape hatch the failure is silent and expensive: the scene text describes
# a person, CAST_CLOSURE_NONE says there is nobody, the model obeys the closure, and the
# render comes back as a tasteful still life of the room they were supposed to be in.
# Nothing refuses, nothing warns, and it only shows up at read-back. Earned 2026-07-29
# on Atlas Surrendered: three spreads (a widow giving, two grown children serving, a
# young woman on a church step) each rendered as an empty room.
#
# So a spread may declare `anonymous`: a short phrase naming who the unnamed figures
# are. It never grants canon identity and never relaxes the uncast-NAME refusal, so a
# real entity mentioned by name is still refused before spend. It only widens the
# closure from "nobody" to "these, and nobody else".
def _cast_closure(names: list[str], anonymous: str = "") -> str:
    anon = (anonymous or "").strip()
    if not names:
        if not anon:
            return CAST_CLOSURE_NONE
        return (
            "THE ONLY PEOPLE IN THIS IMAGE ARE ANONYMOUS FIGURES THIS SCENE DESCRIBES: " + anon + ". "
            "They are ordinary unnamed people with no identity beyond what the scene says, and they "
            "are not any named character. NOBODY ELSE APPEARS."
        )
    base = (
        "THE ONLY NAMED CHARACTERS IN THIS IMAGE ARE: " + ", ".join(names) + ". "
        if anon else
        "THE ONLY CHARACTERS IN THIS IMAGE ARE: " + ", ".join(names) + ". "
    )
    if anon:
        base += (
            "In addition this scene contains ANONYMOUS FIGURES exactly as it describes: " + anon + ". "
            "They are ordinary unnamed people and they are not any named character. "
        )
    return base + (
        "NOBODY ELSE APPEARS. Do not add any other person, figure, creature, robot, animal or "
        "bystander, whatever the style description above may suggest."
    )


def _as_neg_list(v) -> list:
    """Coerce a negatives field to a list, tolerating a bare string.

    `negatives` is DOCUMENTED as a list, and the code simply did `list(v)`. That
    is silently catastrophic when a book hands over a string: `list("NO STRAY
    TEXT")` is `['N','O',' ','S',...]`, so every negative reaches the model as a
    comma-separated spray of single characters and the whole paragraph stops
    functioning as a negative. Nothing raises, nothing warns, and the render
    looks merely mediocre rather than broken.

    This is the same shape confusion the SPEC already records for
    `realPerson.photoStack` ("a string photoStack gets iterated character by
    character"), which makes it a recurring authoring mistake rather than a
    one-off, and the argument for fixing it at the chokepoint. It had already
    shipped: `the-best-news-ever` and `the-room-it-was-made-in` both carry a
    string here, so every spread either of them rendered went out with its
    book-wide negatives destroyed.

    A string is treated as ONE negative, which is what the author meant.
    """
    if v is None:
        return []
    if isinstance(v, str):
        return [v] if v.strip() else []
    return list(v)


def resolve_render_block(ent: dict, pose: str | None, look: str | None = None):
    """Return (extra_sheet_keys, prose) from an entity's `structured.render`.

    Canon may carry PRESCRIBED PROMPT-CRAFT that a deslugged invariant list cannot
    express: an invariant is a short kebab QA key ("north-star-cross-pendant-front"),
    while the render block holds the sentence that actually steers the model ("a
    faceted dimensional four-point STAR ... NOT a Latin cross, NOT a crucifix").
    Ignoring it meant a universe could write the fix into canon and never have it
    reach a single prompt — which is how signature wardrobe (jacket patches) and a
    star-vs-crucifix pendant silently regressed across a whole batch.

    `render.always` applies to every pose. `render.poses.<pose>` may add a `bake`
    sentence and its own `sheets` list. Pose defaults to "front" when the entity
    defines one, because front-facing is the common case and the case canon warns
    about; a descriptor sets `pose` explicitly for anything else (e.g. "back").
    """
    r = render_block_for(ent, look)
    if not r:
        return [], None
    parts = []
    if r.get("always"):
        parts.append(r["always"])
    sheets: list[str] = []
    p = selected_pose(ent, pose, look)
    if p is not None:
        if p.get("bake"):
            parts.append(p["bake"])
        sheets = list(p.get("sheets") or [])
    return sheets, (" ".join(parts) if parts else None)


def render_block_for(ent: dict, look: str | None) -> dict:
    """`structured.render`, honouring an alt look that REPLACES it wholesale.

    dropSheets already stops a contradicted base SHEET reaching the model; this
    stops the contradicted base PROSE. Without it, jerry-man's `render.always`
    kept asserting "his gold NORTH STAR pendant" and "do NOT change his age" on a
    college-era look whose invariants say the neck is bare and he is twenty, and
    the prose won: the render came back with a necklace on a man who does not own
    one yet.
    """
    st = ent.get("structured") or {}
    r = st.get("render") or {}
    if look:
        al = (st.get("altLooks") or {}).get(look) or {}
        if "render" in al:
            r = al["render"] or {}
    return r or {}


def selected_pose(ent: dict, pose: str | None, look: str | None = None) -> dict | None:
    """The pose declaration this spread selected, or None when no pose applies.

    Pose defaults to "front" when the entity defines one, because front-facing is
    the common case and the case canon warns about; a descriptor sets `pose`
    explicitly for anything else (e.g. "back"). Factored out of
    `resolve_render_block` in v0.29 so the pose's SUPERSEDES can be read by the
    invariant and negative compilers without re-deriving which pose won.
    """
    poses = (render_block_for(ent, look).get("poses") or {})
    if not poses:
        return None
    key = pose or ("front" if "front" in poses else None)
    if key is None:
        return None
    if key not in poses:
        raise Refuse(f"{ent['id']} has no render pose '{key}'")
    p = poses[key]
    if not isinstance(p, dict):
        # lint-universe already flags this as CAST-POSE-SHAPE. Refusing here too keeps
        # it a stated refusal rather than an AttributeError three frames down.
        raise Refuse(f"{ent['id']}: render pose '{key}' is a {type(p).__name__}, not an "
                     f"object. A pose is {{'sheets': [...], 'bake': '...'}}.")
    return p


def pose_invariants(base: list[str], ent: dict, pose: str | None,
                    look: str | None = None) -> list[str]:
    """Apply a POSE's `supersedes` / `invariants` to an already-look-resolved list.

    A POSE COULD NOT SUPERSEDE A BASE INVARIANT UNTIL v0.29, AND ONLY AN altLook COULD.
    That is the wrong tool for the job whenever the FACE must not change: an altLook
    auto-drops the base face sheets, so expressing "in this one pose the jacket is worn
    half-on, left sleeve off the shoulder" as a look also throws away the identity
    anchor. The only remaining way to say it was to hand-word the base invariant as
    "...except in pose X", which is a rule enforced by an author remembering to phrase
    it, and a read-back checklist that then reads as a contradiction of itself.

    Earned on nation-of-fire's `theo-doorchaser` (The Tithe Is a Test, 2026-08-02),
    whose half-on jacket was the spine of the book and was expressed nowhere a gate
    could read it.

    Exact-string matching, exactly like `altLooks.<key>.supersedes` (SPEC 12), so the
    two mechanisms behave identically and a pose can retire a look's invariant too.
    """
    p = selected_pose(ent, pose, look)
    if not p:
        return list(base)
    dead = set(p.get("supersedes") or [])
    return [i for i in base if i not in dead] + list(p.get("invariants") or [])


# How many real photographs from a `realPerson.photoStack` reach the model.
#
# UNCAPPED BY DEFAULT (changed 2026-07-29). A good bare-face photo stack is an ASSET:
# more angles make a stronger identity lock, which is the entire reason a real-person
# entity carries photographs at all. Two was an arbitrary ceiling and it was the wrong
# default. An entity that genuinely needs a ceiling now says so with
# `realPerson.photoLimit`.
PHOTO_LIMIT_DEFAULT = None  # None = pass them all


def _photo_refs(ent: dict, uroot=None) -> list[str]:
    """The real photographs for a realPerson entity: EXPANDED first, then capped.

    `photoStack` may name individual files OR a DIRECTORY (the documented convention,
    see resolve_ref). The cap must therefore be applied AFTER expansion. The old code
    sliced the RAW list with `[:2]`, so a one-entry directory stack sailed straight past
    the cap and passed every photograph in the folder: the ceiling silently did nothing
    in exactly the case the convention encourages.

    Found 2026-07-29 building `she-had-everything-but-peace`. Nation of Fire's `victory`
    declares `photoStack: ["reference/victory/photos"]`, so seventeen spreads each
    received SIX photo refs rather than two, two of which were multi-person family-band
    photographs. Passing a group photo as an identity anchor is how a scene grows an
    extra confident stranger, and nothing warned.

    A STRING photoStack is treated as one path rather than iterated character by
    character, which is the authoring mistake the SPEC already records.
    """
    rp = ent.get("realPerson") or {}
    stack = rp.get("photoStack")
    if not stack:
        return []
    if isinstance(stack, str):
        stack = [stack]
    out: list[str] = []
    for entry in stack:
        expanded = [entry]
        if uroot is not None:
            try:
                expanded = resolve_ref(uroot, entry)
            except Refuse:
                expanded = [entry]
        for p in expanded:
            if p not in out:
                out.append(p)
    limit = rp.get("photoLimit", PHOTO_LIMIT_DEFAULT)
    if isinstance(limit, int) and limit >= 0:
        out = out[:limit]
    return out


# ── VARIANT VALIDITY WINDOWS (SPEC v0.18) ────────────────────────────────────
#
# A variant is a body a thing wears for part of its life: a character's altLook,
# a setting's era plate. Until now NOTHING gated WHICH variant a spread could
# select, so on a book spanning three ages of one man there was no reason a 1933
# beat could not pick the `elder` look, and no reason a 1990 beat could not
# silently fall through to the default young face. Both are silent: the render
# succeeds, it is simply of the wrong person, and it costs a full spread to find
# out.
#
# So a variant may DECLARE the window it is legal in, and a spread may declare
# WHEN it happens. The gate then runs pre-spend, in the assembler, with the rest
# of the refusals.
#
#   entity.structured.validFor                  the DEFAULT look's window
#   entity.structured.altLooks.<key>.validFor   an alt look's window
#   entity.contract.plates.<plate>.validFor     a setting plate's era window
#   spread.when                                 a number: a year, or a beat index
#
# `validFor` is `{"from": <n>, "to": <n>}` with either bound optional, so an
# open-ended era ("from 1974 onward") is expressible.
#
# DELIBERATELY OPT-IN AT BOTH ENDS. A spread with no `when`, or an entity whose
# variants declare no window, is unconstrained and compiles exactly as before, so
# no universe has to migrate and nothing already shipped changes shape. The gate
# only fires when someone has stated BOTH facts and they contradict each other.
#
# Earned 2026-07-31 on the-power-of-obeying (69 spreads, 1917 to 2003, three eras
# of one man plus one setting that must be the SAME GROUND in two eras). The look
# was named by hand on all 71 spreads because nothing could check it.


def _window(vf):
    """`{"from": a, "to": b}` as a (lo, hi) pair, either bound possibly None."""
    if not isinstance(vf, dict):
        return None
    lo, hi = vf.get("from"), vf.get("to")
    if lo is None and hi is None:
        return None
    for b in (lo, hi):
        if b is not None and not isinstance(b, (int, float)):
            raise Refuse(f"validFor bounds must be numbers, got {b!r}")
    if lo is not None and hi is not None and lo > hi:
        raise Refuse(f"validFor is inverted: from {lo} is after to {hi}")
    return (lo, hi)


def _covers(vf, when) -> bool:
    w = _window(vf)
    if w is None:
        return True          # no declared window: legal everywhere
    lo, hi = w
    return (lo is None or when >= lo) and (hi is None or when <= hi)


def _describe(vf) -> str:
    w = _window(vf)
    if w is None:
        return "any time"
    lo, hi = w
    if lo is not None and hi is not None:
        return f"{lo} to {hi}"
    return f"from {lo} onward" if lo is not None else f"up to {hi}"


def gate_variant(eid, kind_word, selected, variants, when, spread_id):
    """Refuse a variant selected outside its declared window, NAMING the legal one.

    `variants` maps a key (None for the default look) to its declaring dict.
    Fails closed and pre-spend: a wrong era costs a whole spread to discover by
    looking at it, and the operator usually does not look, because the render is
    beautiful and internally consistent and simply of somebody else.
    """
    if when is None:
        return
    declared = {k: (v or {}).get("validFor") for k, v in variants.items()}
    if not any(_window(vf) for vf in declared.values()):
        return                                   # nothing declares a window
    if _covers(declared.get(selected), when):
        return
    legal = [k for k, vf in declared.items() if _covers(vf, when)]
    names = ", ".join(
        ("the default look" if k is None else repr(k)) + f" ({_describe(declared[k])})"
        for k in legal) or "NONE"
    picked = "the default look" if selected is None else repr(selected)
    raise Refuse(
        f"WRONG ERA ({spread_id}): {eid} selects {picked}, valid "
        f"{_describe(declared.get(selected))}, but the spread is set at when={when}. "
        f"Legal here: {names}. Change the {kind_word}, correct the spread's `when`, "
        f"or widen the variant's validFor in canon.")


def character_variants(ent: dict) -> dict:
    st = ent.get("structured") or {}
    out = {None: {"validFor": st.get("validFor")}}
    for k, v in (st.get("altLooks") or {}).items():
        out[k] = v or {}
    return out


def setting_variants(ent: dict) -> dict:
    """A setting's era axis is its PLATES, which already carry a per-plate config
    map (`contract.plates`), so an era window needs no new schema shape.

    This is why a setting does not get its own `eras[]`: two eras of one place are
    ONE entity on ONE massing blueprint (splitting them destroys the only claim
    such a setting exists to make, that it is the same ground), and the plates are
    already the per-era artifacts.
    """
    con = ent.get("contract") or (ent.get("structured") or {}).get("contract") or {}
    plates = con.get("plates") or {}
    out = {k: (v or {}) for k, v in plates.items()}
    for p in con.get("emptyPlates") or []:
        key = Path(str(p)).stem if isinstance(p, str) else None
        if key and key not in out:
            out[key] = {}
    return out


def _sheet_path(v):
    """A sheet slot is a bare path or {path, role} (SPEC v0.23). Give me the path.

    Mirrors `model.sheet_parts`; kept local because this compiler is deliberately
    importable without the engine. Every read of a slot goes through here, or a typed
    slot resolves to a dict, gets appended as a "path", and the render dies far from
    the cause.
    """
    if isinstance(v, dict):
        return v.get("path")
    return v if isinstance(v, str) else None


# What a typed slot is TOLD to contribute, emitted per-ref into the reference block.
#
# The plate that earned this was a watercolour-and-ink costume study whose own sidecar
# read "garment design ONLY; the render stays hyperreal". A human reading the sidecar
# understood it. Nothing in the pipeline could, so the plate was simply another ref and
# its MEDIUM was as loud as its cut. Saying it per-ref, in the prompt, is the whole fix.
ROLE_INSTRUCTION = {
    "identity": "supplies IDENTITY ONLY: the face and likeness. Ignore its clothing, "
                "background, lighting and medium.",
    "geometry": "supplies SHAPE AND PROPORTION ONLY. Ignore its surface, colour and medium.",
    "garment": "supplies GARMENT CUT AND CONSTRUCTION ONLY. Ignore its medium, its "
               "colour treatment, and any face or body shown wearing it.",
    "medium": "supplies the MEDIUM: the paint language, mark-making and surface. Ignore "
              "its subject.",
    "scale": "supplies SCALE: how big the subject is against its measured reference. "
             "Ignore its styling.",
}


def role_lines(ent: dict, look: str | None = None) -> list[str]:
    """One instruction per TYPED slot, so a ref cannot contribute more than it should.

    Untyped slots emit nothing, which is why adding roles broke no existing universe.
    """
    sheets = (ent.get("structured") or {}).get("sheets") or {}
    out = []
    for key, v in sheets.items():
        if not isinstance(v, dict):
            continue
        role, path = v.get("role"), v.get("path")
        if role in ROLE_INSTRUCTION and path:
            out.append(f"- {path} ({key}) {ROLE_INSTRUCTION[role]}")
    return out


def resolve_character(ent: dict, look: str | None, uroot=None):
    """Return (ref_paths, invariants) for a character in the selected look.

    Default look: requiredForRender sheets + the real photo stack
    (expanded and capped by _photo_refs; uncapped unless the entity sets
    realPerson.photoLimit).
    Alt look: the alt anchor photo (+ any alt sheets), and invariants with the
    superseded base invariants removed and the alt invariants added. The default
    clean-shaven sheets are NOT passed for an alt look, so they cannot fight it.
    """
    st = ent.get("structured", {})
    sheets = st.get("sheets", {})
    base_inv = list(st.get("invariants", []))
    refs: list[str] = []

    if look:
        al = (st.get("altLooks") or {}).get(look)
        if al is None:
            raise Refuse(f"{ent['id']} has no altLook '{look}'")
        if al.get("anchorPhoto"):
            refs.append(al["anchorPhoto"])
        for v in (al.get("sheets") or {}).values():
            pth = _sheet_path(v)
            if pth:
                refs.append(pth)
        # keep the base BODY sheets (pose/proportion/wardrobe); drop the base FACE
        # sheets, which show the default look and would fight the alt anchor photo.
        # EXCEPT what the look explicitly KEEPS. The auto-drop assumes the alt look
        # supplies its own face (an anchorPhoto), which is true for a look that
        # changes the FACE (a beard, an age era). It is exactly wrong for a
        # DECLARED-FUTURE look, where the face is CONTINUOUS and the BODY changes:
        # the future has no photograph to anchor, so dropping the face sheets left
        # such a look with no identity reference at all and the model drew a
        # stranger. `keepSheets` names base sheets to pass anyway; `keepPhotos`
        # passes the real person's photo stack, which is otherwise default-look only.
        # Earned 2026-07-26 adding beef-jones' 2028/2030 prophetic eras.
        # `dropSheets` additionally drops base sheets the alt look CONTRADICTS.
        # Guarded negatives already stop a blanket negative fighting a canon look;
        # nothing did the same for REFS, so a look whose invariant said "neck
        # completely bare" still had the adult PENDANT sheet passed to the model,
        # and a reference image outranks a word. Caught adding jerry-man's age eras.
        dropped = set(al.get("dropSheets") or [])
        kept = set(al.get("keepSheets") or [])
        for key in st.get("requiredForRender", []) + list(kept):
            if key in dropped:
                continue
            if key in FACE_SHEET_KEYS and key not in kept:
                continue
            p = _sheet_path(sheets.get(key))
            if p and p not in refs:
                refs.append(p)
        if al.get("keepPhotos"):
            for p in _photo_refs(ent, uroot):
                if p not in refs:
                    refs.append(p)
        # A BODY sheet is not an identity anchor. The check is whether anything in
        # this look shows the FACE: its own anchorPhoto or alt sheets, a kept base
        # face sheet, or the kept photo stack. Body-only refs pass the silhouette
        # being superseded and nothing that says who this is.
        has_face = bool(al.get("anchorPhoto") or (al.get("sheets") or {})
                        or al.get("keepPhotos")
                        or (kept & FACE_SHEET_KEYS) - dropped)
        if not has_face:
            raise Refuse(
                f"{ent['id']} look '{look}' has NO identity reference: it supplies no "
                "anchorPhoto and no sheets of its own, and every base face sheet is "
                "auto-dropped for an alt look. Only the body sheets would reach the model, "
                "which is the silhouette this look supersedes. A declared-future or "
                "prophetic look must set keepSheets (a base face sheet) and/or keepPhotos, "
                "so the face stays continuous while the body changes."
            )
        supers = set(al.get("supersedes", []))
        inv = [i for i in base_inv if i not in supers] + list(al.get("invariants", []))
    else:
        for key in st.get("requiredForRender", []):
            p = _sheet_path(sheets.get(key))
            if not p:
                raise Refuse(f"{ent['id']}.{key} is required but unlocked")
            refs.append(p)
        for p in _photo_refs(ent, uroot):
            if p not in refs:
                refs.append(p)
        inv = base_inv
    return refs, inv


def _norm_key(s: str) -> str:
    """Fold a key to compare a slug against a camelCase sheet name."""
    return "".join(ch for ch in s.lower() if ch.isalnum())


def _selector_bake_guard(c: dict, ent: dict, spread_id: str) -> None:
    """Refuse a `bake` that is really a SHEET/POSE SELECTOR written in fork vocabulary.

    THE SILENT DEFECT THIS CATCHES. In this assembler `plate` (non-characters) and
    `pose` (characters) SELECT which locked reference is passed, and `bake` is FREE
    PROSE appended to the entity's block. Nation of Fire's retired local compiler used
    `bake` as the selector instead, so every render-spec written in that dialect, and
    every new spec copied from one as a template, names a state that this assembler
    treats as a stray sentence fragment.

    Nothing errored, which is the whole problem: the entity's state plate was simply
    never passed, the spread rendered off the style anchor alone, and the raw slug was
    pasted into the prompt as text. Earned 2026-07-31 on `looked-like-hate`, whose
    three-state spine object rendered with ZERO of its locked plates in the refs. It was
    caught only by dumping the assembled refs by hand and noticing the count was 1.

    The signal is unambiguous, so this fails CLOSED. A real bake is a sentence; a
    selector is a bare slug that also happens to name one of this entity's own sheets or
    poses. Both conditions must hold, which is why an ordinary prose bake mentioning a
    state name in passing does not trip it.
    """
    bake = (c.get("bake") or "").strip()
    if not bake or len(bake) > 60 or "." in bake or bake.count(" ") > 2:
        return  # a sentence, not a selector
    st = ent.get("structured") or {}
    candidates: dict[str, str] = {}
    for k in (st.get("sheets") or {}):
        candidates.setdefault(_norm_key(k), f"\"plate\": \"{k}\"")
    for k in ((st.get("render") or {}).get("poses") or {}):
        candidates.setdefault(_norm_key(k), f"\"pose\": \"{k}\"")
    hit = candidates.get(_norm_key(bake))
    if not hit:
        return
    raise Refuse(
        f"BAKE USED AS A SELECTOR ({spread_id}, cast '{c['id']}'): bake={bake!r} is not "
        f"prose, it names one of this entity's own reference slots. In this assembler "
        f"`bake` is free prose appended to the block, and the SELECTOR is {hit}. Left "
        f"alone, the locked reference is never passed and the slug is pasted into the "
        f"prompt as stray text, with no error. Fix the descriptor: set {hit}, and either "
        f"drop `bake` or replace it with an actual sentence. This is the retired "
        f"NoF compile_render.py dialect; `migrate_render_spec.py translate <spec>` "
        f"converts a whole spec."
    )


def resolve_plate(ent: dict, plate: str | None) -> list[str]:
    """Resolve ONE named plate/sheet for a non-character entity.

    Prefer the entity's own `structured.sheets` map, which is where every locked
    entity actually records its files, and fall back to the reference/<id>/<plate>.png
    convention for entities that predate the map. Promoted 2026-07-25: a motif or prop
    could previously only ever be passed its requiredForRender default, so a book with
    a multi-sheet prop (a book that is sometimes open and sometimes closed, a lamp that
    is lit and unlit) had no way to ask for the right one. 100 such selections were
    already in use in nation-of-fire, expressed only in its local fork.
    """
    if not plate:
        return []
    sheets = (ent.get("structured") or {}).get("sheets") or {}
    p = _sheet_path(sheets.get(plate))
    if p:
        return [p]
    return [f"reference/{ent['id']}/{plate}.png"]



def _abu_root(start=None):
    """The ABU repo root, found by walking up for engine/agenticstory.

    Mirrors render_spread._abu_root. This script is otherwise stdlib-only; the
    engine is imported ONLY for nested-setting resolution, and a universe with no
    `partOf` anywhere never reaches this.
    """
    p = Path(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    return None


def _resolve_nesting(uroot: Path, ent: dict) -> dict:
    """Fold every ancestor's law into `ent`. Refuses loudly on a bad chain."""
    root = _abu_root()
    if root is None:
        raise Refuse(
            f"'{ent.get('id')}' declares partOf '{ent.get('partOf')}' but the ABU engine "
            "could not be located to resolve it. Reinstall the plugin.")
    eng = str(root / "engine")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    from agenticstory.nesting import resolve, NestingError
    try:
        return resolve(lambda eid: _load_entity_or_none(uroot, eid), ent["id"])
    except NestingError as e:
        raise Refuse(f"NESTED SETTING: {e}")


def _load_entity_or_none(uroot: Path, eid: str):
    p = uroot / "canon" / "entities" / f"{eid}.json"
    if not p.exists():
        return None
    with open(p) as f:
        return json.load(f)


def entity_block(cid: str, derived: str | None, bake: str | None,
             kind: str | None = None, mode: str | None = None,
             setting_rule: dict | None = None,
             warnings: list | None = None) -> str | None:
    """Combine a cast entry's `bake` with the entity's derived block.

    `bake` REPLACES by default, and that is load-bearing for a multi-state prop or
    motif whose derived block is prose describing EVERY state it documents: hand that
    to the model whole and it draws all of them at once, a chart of variations instead
    of one scene. 181 such overrides were already in use in nation-of-fire.

    A SETTING IS THE EXCEPTION AND USED TO LOSE ITS GEOMETRY (v0.29). A setting's
    derived block is not a list of states; it is `map` + `blocking` + `dressing` +
    `scale`, which is what the place IS, which way round it is and how big. Replacing
    that with a per-spread bake deletes the room. Measured on the-lit-pulpit
    (movies-are-sermons, 2026-08-02): its five spreads each carried a state bake, and
    `contract.map` reached the model on NONE of them. It only rendered correctly
    because the author had also written the auditorium into every scene by hand, which
    is the duplication canon exists to remove. Nothing warned.

    So `setting` now APPENDS (geometry first, then the bake). Zero blast radius: a
    sweep of every render-spec in nation-of-fire found 62 bakes on non-characters and
    all 62 were visual-metaphors, none a setting.

    `visual-metaphor` KEEPS replace, because those 62 live in nine shipped books and
    were authored expecting it. It now WARNS when it drops a non-empty geometry block,
    so the same defect is visible instead of silent. A cast entry can settle it
    explicitly either way with `"bakeMode": "append" | "replace"`.
    """
    m = mode or ("append" if kind == "setting" else "replace")
    if bake and derived and m == "append":
        out = f"{derived} {bake}"
    elif bake:
        if derived and kind in ("setting", "visual-metaphor"):
            (warnings if warnings is not None else []).append(
                f"{cid}: bake REPLACED the setting block, so its map/blocking/dressing/"
                f"scale did not reach the model. Set \"bakeMode\": \"append\" on this "
                f"cast entry to keep the geometry, or move the room description into the "
                f"scene text deliberately.")
        out = bake
    else:
        out = derived
    rule = (setting_rule or {}).get(cid)
    if rule:
        out = f"{out} {rule}" if out else rule
    return out


def resolve_setting(ent: dict, plate: str | None, entry: dict | None = None):
    """Return (ref_paths, block) for a setting, from its WHOLE contract.

    THE GEOMETRY FIELDS USED TO BE DROPPED. This built the block from
    `contract.dressing` alone, so `map`, `blocking` and `scale` never reached the
    model in any universe. Those are exactly the three fields that exist to fix
    what the place IS, which way round it is, and how big it is, and they were
    dead weight in every entity file that carried them.

    That left a setting's consistency resting entirely on the plate image, which
    is not enough and fails systematically rather than occasionally. The plate is
    one reference among many; on a spread that also passes two character masters
    and a motif sheet its geometry is diluted, and the model keeps the vibe while
    re-inventing the layout. On it-only-has-to-fly the same shed had its doorway
    camera-left on most spreads and camera-right on another, its window and
    shelves migrated between walls, and the room changed proportion, across a
    picture book whose premise is that this is one small shed the reader comes to
    know.

    Order is deliberate: map (what the place is), then blocking (the law
    governing every camera on it), then dressing (what is lying around), then
    scale. Handedness comes before dressing because handedness is what a reader
    actually notices.
    """
    refs = resolve_plate(ent, plate)
    con = ent.get("contract", {})
    entry = entry or {}

    # THE SEATING CHART AS A PICTURE (SPEC v0.19). `blocking` is prose and
    # `structured.seating` is one sentence; a model paraphrases both and then decides
    # the geometry itself. Earned on the-creamery-counter (will-there-be-ice-cream,
    # 2026-08-01): a two-hander whose two people swapped viewer-left and viewer-right
    # across six of twenty-six spreads, and whose stools rendered in front of a glass
    # display case where neither person could set a bowl down. Both are placement
    # facts, and neither prose field could show them.
    #
    # contract.blockingPlate is the room with featureless mannequins in the LEGAL seat
    # positions at correct relative size. It rides along on every render of the setting,
    # regardless of which camera plate is selected, because placement is continuity
    # rather than composition. Advisory: absent the field, behaviour is unchanged.
    #
    # AND IT RIDES ALONG INTO EVERY OTHER BOOK THAT REUSES THE SETTING (v0.29). A
    # blocking plate is drawn for the book that earned it, so its mannequins hold that
    # book's props. `the-park-bench` was authored for will-there-be-ice-cream: its plate
    # shows two figures holding ice cream cones and its `contract.dressing` says each of
    # them holds a cone. Three of the first seven spreads of an UNRELATED book came back
    # with both men holding ice cream, through scene text and a per-spread negative that
    # banned ice cream BY NAME on every one of them. A reference image plus an injected
    # contract sentence together outrank a negative word, every time.
    #
    # So a spread may scope the plate out, with `"blockingPlate": false` on the cast
    # entry, and a plate may do it for every spread that selects it with
    # `contract.plates.<plate>.includeBlockingPlate: false`. Absent either, behaviour is
    # unchanged. The DURABLE fix for a leaking setting is still to reshoot the plate
    # propless (lint-universe warns SETTING-DRESSING-NAMES-HELD-PROP); this is the escape
    # hatch for the spread in front of you.
    pcfg = ((con.get("plates") or {}).get(plate) or {}) if plate else {}
    bp = con.get("blockingPlate")
    if entry.get("blockingPlate") is False or pcfg.get("includeBlockingPlate") is False:
        bp = None
    if bp and bp not in refs:
        refs = list(refs) + [bp]

    # A CLOSE-UP DOES NOT CONTAIN THE SAME ELEMENTS AS A WIDE SHOT.
    #
    # This used to inject the WHOLE contract on every render regardless of camera.
    # `blocking` is room-wide law ("sixteen guests seated in the tiers, two banks, a
    # centre aisle"), so a close two-shot of two chairs was still told the room was
    # full of seated people. The model put them in, and re-invented them every time,
    # because no plate showed them at that distance. Earned 2026-07-30 in
    # nation-of-fire (gain-everything-lose-nothing): the audience kept reappearing in
    # close-ups and its seating drifted spread to spread.
    #
    # So a plate may now scope what the model is told, via contract.plates:
    #   "plates": {"chairsCloseUp": {"note": "...", "includeBlocking": false}}
    # `note` is appended for that plate; includeBlocking:false drops the room-wide
    # blocking law, which is exactly what a close-up needs. Absent config, behaviour
    # is unchanged, so every existing universe renders byte-identically.
    keys = ["map", "blocking", "dressing", "scale"]
    if pcfg.get("includeBlocking") is False:
        keys.remove("blocking")
    parts = [con.get(k) for k in keys]
    parts = [p.strip() for p in parts if isinstance(p, str) and p.strip()]
    note = pcfg.get("note")
    if isinstance(note, str) and note.strip():
        parts.append(note.strip())
    if not parts:
        return refs, None
    return refs, f"{ent['id']} exactly as its reference plate: " + " ".join(parts)


def build(uroot: Path, spec: dict, spread_id: str) -> dict:
    uni = load(uroot / "universe.json")
    ident = uni.get("identity", {})
    reg = ident.get("register", {})

    sp = next((s for s in spec.get("spreads", []) if s["id"] == spread_id), None)
    if sp is None:
        raise Refuse(f"spread '{spread_id}' not in render-spec")

    # Advisory findings for the operator. A REFUSAL stops a render; a warning is for the
    # class of defect that is legal, silent and usually wrong, which until now had no
    # channel at all and so was discovered by reading assembled prompts by hand.
    warnings: list[str] = []

    # A spread may override the book preamble for the keys in _SPREAD_OVERRIDES, so ONE
    # book can carry more than one register when the change is diegetic. A spread naming
    # none of them resolves exactly as before.
    eff = {**spec, **{k: sp[k] for k in _SPREAD_OVERRIDES if k in sp}}

    # Anchor: the book (or one spread) may override identity.register.anchor when that
    # anchor is unsuitable (e.g. it points at a photograph, a painterly universe's own
    # rejectedPole, or this spread renders a second register). The override is DATA in
    # the render-spec, with a reason.
    anchor = eff.get("anchorRef") or reg.get("anchor")
    if not anchor:
        raise Refuse("no anchor: identity.register.anchor is null and render-spec has no anchorRef")

    refs: list[str] = [anchor]
    ent_blocks: list[str] = []
    qa: list[str] = []
    char_invsets: dict[str, list[str]] = {}
    char_scales: dict[str, dict] = {}
    entity_scales: dict[str, dict] = {}
    seating_charts: dict[str, str] = {}

    def add_refs(paths):
        for p in paths:
            if p not in refs:
                refs.append(p)

    # A spread's location can be given as a top-level {setting, plate} or as a
    # cast member; handle both, characters and settings alike, from canon.
    entries = list(sp.get("cast", []))
    if sp.get("setting"):
        # A SETTING CAST WITH NO PLATE PASSES NO SETTING IMAGE AT ALL.
        #
        # resolve_plate returns [] for a null plate, so the spread renders the place from
        # prose alone and the model invents the room from scratch, differently every time.
        # This was silent: nothing warned, and the render looked plausible. An audit of
        # nation-of-fire found 10 such spreads across shipped books, plus 42 selecting a
        # plate absent from the entity's `sheets` map and resolving only through a
        # filename fallback. Earned 2026-07-30.
        st_id = sp["setting"]
        st_plate = sp.get("plate")
        if not st_plate and not sp.get("allowPlatelessSetting"):
            raise Refuse(
                f"SETTING CAST WITH NO PLATE ({sp.get('id')}): casts setting "
                f"'{st_id}' but selects no plate, so NO setting image is passed and the "
                "place is invented from prose. Name a plate from the entity's sheets, or "
                "set allowPlatelessSetting if the place genuinely must not be shown.")
        entries.append({"id": st_id, "plate": st_plate})

    # A book may append EXTRA prose to one entity's block without editing canon: the
    # same room legitimately reads colder in a cancellation beat than in a homecoming.
    # Promoted 2026-07-25 (44 uses in nation-of-fire, fork-only until now). Per-spread
    # override is allowed via _SPREAD_OVERRIDES.
    setting_rule = eff.get("settingRule") or {}


    # ARCHIVED ENTITIES ARE REFUSED AT THE POINT OF NEW CASTING (SPEC v0.19).
    # Not at the pre-render gate: archiving must never retroactively break a book that
    # already shipped. So an old book re-renders only after someone consciously sets
    # allowArchived on the spread, which leaves an auditable trace of the decision,
    # while a NEW book cannot quietly pick the retired thing back up.
    if not eff.get("allowArchived"):
        retired = []
        for c in entries:
            ent0 = load_entity(uroot, c["id"])
            if ent0.get("lifecycle") == "archived":
                a = ent0.get("archived") or {}
                note = f"'{c['id']}' is ARCHIVED"
                if a.get("on"):
                    note += f" on {a['on']}"
                if a.get("reason"):
                    note += f" ({a['reason']})"
                if a.get("supersededBy"):
                    note += f" -> cast '{a['supersededBy']}' instead"
                retired.append(note)
        if retired:
            raise Refuse(
                f"ARCHIVED ENTITY CAST ({spread_id}): "
                + "; ".join(retired)
                + ". Cast the replacement, or set allowArchived on this spread if you are "
                  "deliberately re-rendering a book that shipped before the archive."
            )

    # WHEN this spread happens: a year, or a beat index. Whatever scale the
    # universe uses, the gate only ever compares numbers.
    when = sp.get("when")
    if when is not None and not isinstance(when, (int, float)):
        raise Refuse(f"{spread_id}: `when` must be a number (a year or a beat "
                     f"index), got {when!r}")

    for c in entries:
        ent = load_entity(uroot, c["id"])
        kind = ent.get("kind")
        _selector_bake_guard(c, ent, spread_id)
        # PRE-SPEND ERA GATE. Runs before any ref is resolved, so a wrong-era
        # selection costs nothing instead of costing a whole spread.
        if kind == "character":
            gate_variant(c["id"], "look", c.get("look"),
                         character_variants(ent), when, spread_id)
        elif kind in ("setting", "visual-metaphor") and c.get("plate"):
            gate_variant(c["id"], "plate", c.get("plate"),
                         setting_variants(ent), when, spread_id)
        # Scale is collected for EVERY kind, not only characters: a recurring PROP
        # drifting size across a book is the commonest form of this defect.
        entity_scales[c["id"]] = (ent.get("structured") or {}).get("scale") or {}
        seating_charts.update((ent.get("structured") or {}).get("seating") or {})
        # READ-BACK QA IS NOT A CHARACTER-ONLY CONCERN (SPEC v0.24).
        #
        # `qa` used to be built only in the character branch below, and every other kind
        # `continue`s before reaching it. So a setting, visual-metaphor, motif or prop could
        # DECLARE `structured.invariants`, have them validate and lint clean, and still
        # contribute NOTHING to the readback checklist. The entity looked guarded and was not.
        #
        # Earned on the-only-scoreboard (nation-of-fire, 2026-08-02): the-one-lit-board is the
        # spine object of the book and declares twelve invariants covering the things most
        # likely to drift (no board is ever gold, the marked row is a solid dark dot and never
        # a white fill, the lit board is never enlarged, never a screen, never a sports
        # scoreboard). `compose-spread --dry-run` reported "0 qa invariants" on every one of the
        # seven spreads that cast it, so all twelve were checked by eye. Three drifted anyway
        # across the run, twice on the gold rule the entity states first.
        #
        # Collected for EVERY kind here, before the per-kind branches return, for the same
        # reason `scale` is: the defect it catches is not specific to people.
        #
        # `render.qa` IS PART OF THE CHECKLIST AND WAS READ BY NOTHING (v0.29). SPEC 4.6
        # has stated since v0.4 that "qa = the union of every in-frame entity's
        # `invariants` + `render.qa`", and the second half of that union was never
        # implemented in any compiler. So an entity could carry a well-written six-item
        # `structured.render.qa`, validate, lint clean, and contribute ZERO lines to the
        # read-back checklist. Earned on nation-of-fire's `theo-doorchaser`: a dry
        # assemble reported 13 QA invariants on a two-hander (all 13 the other man's) and
        # zero on the spread where he stands alone, so the signature detail the whole book
        # turns on was checked only by a human who happened to look.
        # Look-aware, because an altLook may replace the render block wholesale.
        # NESTED SETTINGS (SPEC v0.29). A room declares `partOf` its house, and the
        # house's LAW (invariants, qa, dressing, render.always) folds in here while its
        # ART never does. Resolved BEFORE the invariant sweep below so an inherited
        # house rule is checked by read-back exactly like a room's own, which is the
        # whole reason the slipper rule had to be hand-copied before this existed.
        if kind in ("setting", "visual-metaphor") and (ent.get("partOf") or "").strip():
            ent = _resolve_nesting(uroot, ent)
        if kind != "character":
            for i in (ent.get("structured") or {}).get("invariants") or []:
                qa.append(f"{c['id']}: {i}")
        for i in _as_neg_list(render_block_for(ent, c.get("look")).get("qa")):
            qa.append(f"{c['id']}: {i}")
        # A POSE ON A NON-CHARACTER SELECTS NOTHING, SO SAY SO.
        #
        # `pose` is a character selector. Every other kind chooses its variant with
        # `plate`, and none of the branches below read pose at all, so a cast entry
        # writing {"id": "a-visual-metaphor", "pose": "dark"} was accepted in silence
        # and resolved to the DEFAULT plate. A multi-state object then rendered the
        # same state everywhere while the spec looked correct. Nine spreads of a real
        # book shipped that way (2026-08-03), every one showing a wall of lights the
        # story needed dark.
        #
        # Same shape as the lookbook that recorded its own name and steered nothing,
        # and as `import-asset --crop` recording a crop it never performed: canon that
        # reads as a rule and does nothing. A typo in a selector is a REFUSAL here,
        # exactly as an unknown sheet name is for REFS.
        if kind != "character" and c.get("pose"):
            _avail = sorted((ent.get("structured") or {}).get("sheets") or {})
            raise Refuse(
                f"{c['id']} is a {kind}, which selects its variant with 'plate', not "
                f"'pose' (got pose={c['pose']!r}). Poses are a character selector and no "
                f"other kind reads them, so this entry would silently render the default. "
                f"Available plates: {_avail or 'none'}.")
        if kind in ("setting", "visual-metaphor"):
            r, block = resolve_setting(ent, c.get("plate"), c)
            add_refs(r)
            block = entity_block(c["id"], block, c.get("bake"), kind, c.get("bakeMode"), setting_rule, warnings)
            if block:
                ent_blocks.append(block)
            continue
        if kind not in ("character",):
            # motif / prop: honour an explicit plate, else its locked default refs.
            r = resolve_plate(ent, c.get("plate"))
            if not r:
                r, _inv = resolve_character(ent, c.get("look"), uroot)
            add_refs(r)
            derived = ((ent.get("prose") or {}).get("rules")
                       or ((ent.get("structured") or {}).get("render") or {}).get("bake"))
            block = entity_block(c["id"], derived, c.get("bake"), kind, c.get("bakeMode"), setting_rule, warnings)
            if block:
                ent_blocks.append(block)
            continue
        # A BAKE MUST NOT SILENTLY REPLACE A LOCKED CHARACTER'S IDENTITY.
        #
        # entity_block() lets a cast entry's `bake` REPLACE the derived block. That is
        # right for a multi-state prop, and catastrophic for a character: the canon block
        # is where ONE LOCKED FACE, the wardrobe rules and the modesty anatomy live, so a
        # hand-typed paragraph in a render-spec quietly becomes the whole description and
        # the character stops looking like herself. Earned 2026-07-30: all 17 spreads of
        # gain-everything-lose-nothing carried a typed Selah paragraph that replaced her
        # canon block, even aging her a decade past what canon says. It shipped.
        #
        # Refuse when the replaced entity declares identity invariants. Opting out stays
        # possible but must be deliberate and auditable.
        _inv_keys = set((ent.get("structured") or {}).get("invariants") or [])
        _identity = {k for k in _inv_keys
                     if "locked-face" in k or "one-locked" in k or k.startswith("face-")}
        if c.get("bake") and _identity and not c.get("allowIdentityOverride"):
            raise Refuse(
                f"BAKE WOULD REPLACE A LOCKED IDENTITY ({sp.get('id')}): cast entry for "
                f"'{c['id']}' sets `bake`, which REPLACES the canon render block that "
                f"carries {sorted(_identity)}. The character stops being described by canon "
                "and starts being described by the render-spec. Use `look`/`pose` for a "
                "variation, put scene-specific detail in `scene` (which is additive), or "
                "set allowIdentityOverride if you really mean to override canon.")
        r, inv = resolve_character(ent, c.get("look"), uroot)
        # A POSE MAY SUPERSEDE A BASE INVARIANT (v0.29). Applied here so the prompt
        # block, the QA checklist and the computed negatives below all read the SAME
        # resolved list, exactly as `supersedes` already works for an alt look.
        inv = pose_invariants(inv, ent, c.get("pose"), c.get("look"))
        add_refs(r)
        # Canon's prescribed prompt-craft (structured.render) is emitted ALONGSIDE
        # the invariant list: the invariants remain the QA keys, the render block
        # is the wording that actually steers the model. Its pose may also require
        # sheets beyond requiredForRender (e.g. the jacket-back sheet on a back pose).
        pose_sheets, render_prose = resolve_render_block(ent, c.get("pose"), c.get("look"))
        sheets_map = (ent.get("structured") or {}).get("sheets") or {}
        # a pose's extra sheets obey the selected look's dropSheets too, or the
        # render block quietly reintroduces the very sheet the look contradicts.
        look_dropped = set(
            (((ent.get("structured") or {}).get("altLooks") or {}).get(c.get("look")) or {}).get("dropSheets")
            or []
        )
        add_refs([sheets_map[k] for k in pose_sheets
                  if sheets_map.get(k) and k not in look_dropped])
        derived = (
            f"{c['id']} rendered exactly per the supplied reference images: "
            + "; ".join(deslug(i) for i in inv)
            + "."
            + (f" {render_prose}" if render_prose else "")
        )
        block = entity_block(c["id"], derived, c.get("bake"))
        if block:
            ent_blocks.append(block)
        # A TYPED slot says what it contributes, so the model is told per-ref rather than
        # left to weigh every reference equally. Untyped slots emit nothing, which is why
        # this could not disturb an existing universe. SPEC v0.23.
        rl = role_lines(ent, c.get("look"))
        if rl:
            ent_blocks.append("REFERENCE ROLES, obey exactly: " + " ".join(rl))
        qa += [f"{c['id']}: {i}" for i in inv]
        char_invsets[c["id"]] = inv
        char_scales[c["id"]] = (ent.get("structured") or {}).get("scale") or {}

    # Auto-disambiguation: when two or more characters share the frame, name what
    # makes each one distinct (the invariants NOT common to all of them), so the
    # model does not blur two faces/hairstyles together. Fully derived.
    disambig = None
    if len(char_invsets) >= 2:
        sets = [set(v) for v in char_invsets.values()]
        common = set.intersection(*sets)
        parts = []
        for cid, inv in char_invsets.items():
            uniq = [i for i in inv if i not in common]
            if uniq:
                parts.append(f"{cid} is the one with " + ", ".join(deslug(i) for i in uniq))
        if parts:
            disambig = (
                "TELL THEM APART, keep every face and hairstyle distinct: "
                + "; ".join(parts)
                + "."
            )

    # RELATIVE SCALE. Two characters in one frame have a height relationship, and
    # nothing in the matrix could state it: every entity was described alone, so the
    # model made both men the same height (or reversed them) and the drift was
    # invisible until somebody who knows them said "he is much shorter than that."
    # Same reasoning as the v0.9 setting scalePlate: a dimension nothing depicts
    # cannot be judged. Emitted only when two or more in-frame characters actually
    # declare a relation to each other, so a solo spread is unchanged.
    scale_lines = []
    for cid in char_invsets:
        rel = ((char_scales.get(cid) or {}).get("relativeTo") or {})
        for other, phrase in rel.items():
            if other in char_invsets:
                scale_lines.append(f"{cid} is {phrase} {other}")
    heights = [f"{cid} is {(char_scales[cid] or {}).get('height')}"
               for cid in char_invsets
               if (char_scales.get(cid) or {}).get("height")]
    scale_block = None
    if scale_lines:
        scale_block = (
            "RELATIVE SCALE, hold it exactly: "
            + "; ".join(scale_lines)
            + ((". " + "; ".join(heights) + ".") if len(heights) >= 2 else ".")
        )

    # ABSOLUTE SCALE. The relative block above only fires when TWO OR MORE
    # CHARACTERS declare a relation to each other, and `char_scales` is only ever
    # filled from characters. So two whole classes of drift had no way to be
    # stated at all: a PROP could not contribute scale even when it declared one,
    # and a SOLO entity's own size was never emitted.
    #
    # That is how a recurring prop ends up a different size on every page. On
    # what-a-book-is-made-of the supercharged laptop appears in most of twenty-one
    # spreads and ranged from a notebook to a small television, because the entity
    # declared its FORM, its COLOUR and its rules and never once declared its SIZE.
    # Colour was meaning; scale was a guess. Gary caught it by eye: "why does the
    # laptop look different sizes?"
    #
    # Any in-frame entity of ANY kind may now carry `structured.scale.absolute`, a
    # plain sentence pinning its size to things a render already contains (a desk,
    # a mug, a hand). It is emitted whenever that entity is in frame, alone or not.
    abs_lines = [f"{eid} is {(sc or {}).get('absolute')}"
                 for eid, sc in entity_scales.items()
                 if (sc or {}).get("absolute")]
    abs_block = ("TRUE SIZE, hold it exactly: " + "; ".join(abs_lines) + ".") if abs_lines else None

    # FIXED PLACEMENT. A setting where the same people talk to each other again and
    # again has a SEATING CHART, and nothing in the contract could state it: `blocking`
    # describes the CAMERAS and `map` describes the ROOM, so who sits where was decided
    # afresh in every spread's scene text. Fifteen spreads into one dining room the two
    # women had swapped sides, and a reader cannot tell whether they moved or the book
    # made a mistake.
    #
    # The universe had already learned this once, per-book, and written it down as an
    # entity note: brendas-suv carries "FIXED SEATING, continuity-critical: Brenda drives
    # front-LEFT, Jerry rides front-RIGHT, never swapped." That note is prose a human has
    # to remember to obey. This makes it data the compiler emits.
    #
    # A setting (or any entity) may declare `structured.seating` as {entity-id: phrase}.
    # Emitted only when TWO OR MORE of the named entities are in the SAME frame, because
    # "on the viewer's left" is meaningless about a person standing alone, and a solo
    # over-the-shoulder single must stay free to put them wherever the camera needs.
    seated = [(eid, ph) for eid, ph in seating_charts.items() if eid in char_invsets]
    seating_block = None
    if len(seated) >= 2:
        seating_block = (
            "FIXED PLACEMENT, hold it exactly and never swap it between spreads: "
            + "; ".join(f"{eid} is {ph}" for eid, ph in seated)
            + ". This placement is continuity, not composition: it is the same in every "
              "spread of this setting. If the camera moves to the far side of the room, the "
              "people do NOT change places; their apparent left/right is whatever the stated "
              "placement looks like from the NEW camera position."
        )

    # Negatives: universe rejectedPoles + book-wide unconditional negatives, then
    # GUARDED negatives — a blanket negative (e.g. "no facial hair") is emitted
    # ONLY when no in-frame character's selected look positively satisfies it.
    negs = _as_neg_list(reg.get("rejectedPoles"))
    negs += _as_neg_list(eff.get("negatives"))
    all_inv = set().union(*[set(v) for v in char_invsets.values()]) if char_invsets else set()
    for g in eff.get("guardedNegatives", []):
        pat = g.get("satisfiedByInvariantMatching")
        satisfied = bool(pat) and any(
            re.search(pat, i) and not NEG_MARKER.search(i) for i in all_inv
        )
        if not satisfied:
            negs.append(g["text"])

    # ENTITY-SCOPED NEGATIVES (SPEC v0.23): emitted ONLY when that entity is in frame.
    #
    # Some negatives name one person and are wrong as universe-wide poles. Six of the
    # nineteen banned-visual entries migrated out of the Sheng Family brand OS are of
    # this kind ("no glasses on Gary", no black leather jacket, no stubble, no tattoos),
    # and the same source EXPLICITLY permits glasses on other people. As flat pack
    # `rejectedPoles` they would have forbidden those universe-wide, quietly overruling
    # a decision the author had made the other way. Scoping them to the entity is what
    # lets a rule be absolute about one person and silent about everyone else.
    for _cid in char_invsets:
        _e = load_entity(uroot, _cid) or {}
        _st = _e.get("structured") or {}
        # LOOK-AWARE (v0.26). A look's `supersedes` retires a negative exactly as it
        # retires an invariant. Merging the flat list regardless of look put 32
        # pendant negatives into a bare-neck render, one of them "more than one
        # necklace", which affirms the very thing the look removes.
        _entry = next((c for c in entries if c.get("id") == _cid), {})
        _look = _entry.get("look")
        _neg = list(_st.get("negatives") or [])
        if _look:
            _al = (_st.get("altLooks") or {}).get(_look) or {}
            _dead = set(_al.get("supersedes") or [])
            _neg = [n for n in _neg if n not in _dead] + list(_al.get("negatives") or [])
        # POSE-AWARE TOO (v0.29), for the same reason a look is: a pose that inverts a
        # signature invariant ("worn half-on, left sleeve off the shoulder") is fighting
        # the entity's own negative ("never worn off the shoulder") on every render that
        # selects it, and a reference plus a negative outrank a scene sentence.
        _pose = selected_pose(_e, _entry.get("pose"), _look) or {}
        _pdead = set(_pose.get("supersedes") or [])
        if _pdead:
            _neg = [n for n in _neg if n not in _pdead]
        _neg += list(_pose.get("negatives") or [])
        negs += _as_neg_list(_neg)

    # Resolve every ref to an absolute on-disk path (register anchor stays first).
    resolved: list[str] = []
    for p in refs:
        for r in resolve_ref(uroot, p):
            if r not in resolved:
                resolved.append(r)

    style = eff.get("style", "")
    scene = sp.get("scene", "")

    # Refuse BEFORE returning a job that will invent a stranger. Costs nothing: pure text.
    if not eff.get("allowUncast"):
        cast_ids = {c["id"] for c in entries}
        uncast = uncast_characters(uroot, scene, cast_ids)
        if uncast:
            named = "; ".join(f"scene says '{tok}' but never casts '{eid}'" for eid, tok in uncast)
            raise Refuse(
                f"UNCAST CHARACTERS NAMED IN SCENE TEXT ({spread_id}): {named}. "
                "The model invents a stranger for each. Cast them, or set allowUncast if the "
                "mention is genuinely not an in-frame person."
            )

    prompt = " ".join(
        x
        for x in [
            f"Picture-book spread painted in the {reg.get('name', 'locked')} register of the FIRST reference image.",
            ANCHOR_STYLE_GUARD,
            style,
            ("SCENE: " + scene) if scene else "",
            *ent_blocks,
            disambig or "",
            scale_block or "",
            abs_block or "",
            seating_block or "",
            _cast_closure(sorted(char_invsets), sp.get("anonymous", "")),
            sp.get("extra", ""),  # authored per-spread instruction (e.g. bake a title glyph); DATA, not improvisation
            ("NEGATIVES: " + ", ".join(negs) + ".") if negs else "",
            "" if eff.get("allowMultiPanel") else SINGLE_IMAGE_GUARD,
            MOTION_GUARD if _has_motion(scene) else "",
            ADDRESSING_GUARD if _has_audience(scene) else "",
            BEDCLOTHES_GUARD if _in_bed(scene) else "",
            BED_LENGTH_GUARD if _person_lying_on_bed(scene) else "",
            CROWD_MEMBER_GUARD if _cast_inside_crowd(scene) else "",
        ]
        if x
    )

    # De-duped, order preserved: `invariants` and `render.qa` legitimately overlap on an
    # entity that stated the same rule in both, and a checklist that asks twice teaches
    # its reader to skim.
    qa = list(dict.fromkeys(qa))
    return {"prompt": prompt, "refs": resolved, "size": eff.get("size", "1536x1024"),
            "qa": qa, "warnings": warnings}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("render_spec")
    ap.add_argument("spread")
    args = ap.parse_args()
    try:
        out = build(Path(args.universe), load(Path(args.render_spec)), args.spread)
    except Refuse as e:
        print(f"REFUSE: {e}", file=sys.stderr)
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
