"""The SHOT vocabulary: how a spread is framed, declared rather than described.

WHY THIS EXISTS. A book whose beats are a conversation used to render as N
copies of one picture. The cause is structural, not authorial:

  1. `plate` fixes the composition, and the framework already documents that a
     cast plate's COMPOSITION wins over prose. A setting with one conversation
     camera therefore hands every spread the same wide three-shot.
  2. There was no way to DECLARE the framing. An author writing "closer, chest
     up" put it in free `scene` prose, where the plate outvoted it and no tool
     could read it.
  3. Nothing measured variety, so the defect was invisible until a human
     scrolled the finished book.

Earned 2026-08-05 on nation-of-fire's Bless You More, whose first fifteen
spreads shared one setting, one plate and one cast, and read as the same
image fifteen times. Gary: "It's the same image again and again and again."

The fix is a declared, ENUMERABLE `shot` on each spread. Declaring it makes
the framing (a) enforceable, because the composer can emit an explicit
override that beats the plate, (b) measurable, because a linter can read it,
and (c) THINKABLE, because an author choosing from a vocabulary varies the
book by default instead of by inspiration.

`framing` is injected right after the SCENE, where a composition instruction
outranks the entity blocks that follow. `dropsBlocking` drops the room-wide
blocking law for shots that cannot contain the room, which is the same
reasoning `contract.plates[...].includeBlocking` already encodes per plate:
a close-up told "sixteen guests are seated in the tiers" re-invents sixteen
guests every render.
"""

# Each entry:
#   summary        one line, projected into SPEC.md
#   framing        the composition instruction injected into the prompt
#   dropsBlocking  True when the shot cannot contain the room-wide blocking law
#   peopleInFrame  advisory count for the variety auditor: "many" | "few" | "none"
SHOTS: dict[str, dict] = {
    "wide": {
        "summary": "The establishing view: the whole place, figures small inside it.",
        "dropsBlocking": False,
        "peopleInFrame": "many",
        "framing": (
            "FRAMING, WIDE: the camera is well back and the PLACE is the subject. "
            "Any figures sit inside the space at full length and no taller than half "
            "the frame, so the room, its geometry and its light all read at once."
        ),
    },
    "two-shot": {
        "summary": "Two figures together, waist up, the space soft behind them.",
        "dropsBlocking": False,
        "peopleInFrame": "few",
        "framing": (
            "FRAMING, TWO-SHOT: TWO figures fill the middle of the frame from the waist "
            "up and are the subject of the picture. The camera is closer than an "
            "establishing view. Behind them the place falls away softly and out of "
            "focus, present but never competing with them."
        ),
    },
    "group": {
        "summary": "Three or more figures together, waist up, closer than an establishing view.",
        "dropsBlocking": False,
        "peopleInFrame": "many",
        "framing": (
            "FRAMING, GROUP: THREE OR MORE figures fill the middle of the frame from the "
            "waist up and are the subject of the picture, close enough that every face "
            "reads. The camera is nearer than an establishing view and the place is "
            "present behind them without competing."
        ),
    },
    "close": {
        "summary": "One face, chest up, filling the frame; the plate's camera distance is overridden.",
        "dropsBlocking": True,
        "peopleInFrame": "few",
        "framing": (
            "FRAMING, CLOSE-UP. IGNORE THE CAMERA DISTANCE AND THE FIGURE PLACEMENT IN "
            "THE SUPPLIED REFERENCE PLATE: in that plate the camera is far back and the "
            "figures are small inside the space, and HERE THE CAMERA IS CLOSE IN ON ONE "
            "PERSON. ONE face fills the frame from the chest up and the head alone is at "
            "least a third of the frame height. Take the place's light, palette, "
            "materials and handedness from the plate, never its camera distance. "
            "Everything behind the face is soft, close and thrown out of focus, and most "
            "of the room is simply OUTSIDE this picture."
        ),
    },
    "over-shoulder": {
        "summary": "From behind one figure onto the other; the near shoulder frames the far face.",
        "dropsBlocking": True,
        "peopleInFrame": "few",
        "framing": (
            "FRAMING, OVER-THE-SHOULDER. IGNORE THE CAMERA DISTANCE IN THE SUPPLIED "
            "REFERENCE PLATE. The camera sits just behind and beside ONE person, whose "
            "near shoulder and the back of whose head are large, dark and soft at one "
            "edge of the frame, looking past them at the OTHER person, who is sharp, "
            "faces the camera and is the subject. Both people are cast, because a "
            "shoulder is a person."
        ),
    },
    "insert": {
        "summary": "Hands, an object, a surface. No faces, no whole figures.",
        "dropsBlocking": True,
        "peopleInFrame": "none",
        "framing": (
            "FRAMING, INSERT. IGNORE THE CAMERA DISTANCE IN THE SUPPLIED REFERENCE "
            "PLATE. This is a CLOSE DETAIL: hands, an object and the surface it rests "
            "on, filling the frame. NO whole figures and NO faces appear; a hand or a "
            "forearm may. Take the place's light, palette and materials from the plate "
            "and nothing else."
        ),
    },
    "reverse": {
        "summary": "The opposite camera on the same locked geometry, so handedness mirrors on purpose.",
        "dropsBlocking": False,
        "peopleInFrame": "few",
        "framing": (
            "FRAMING, REVERSE ANGLE: the camera has moved to the OPPOSITE side of the "
            "same space and looks back the way the reference plate looks from. Left and "
            "right are therefore MIRRORED with respect to that plate, deliberately, and "
            "the scene text below states which fixed feature is on which side HERE. "
            "Every material, colour and light source is the same room."
        ),
    },
    "thought-bubble": {
        "summary": "The speaker small at one edge; a large soft-edged bubble holds what they are describing.",
        "dropsBlocking": True,
        "peopleInFrame": "few",
        "framing": (
            "FRAMING, THOUGHT BUBBLE. The picture has TWO parts. SMALL, at ONE EDGE of "
            "the frame and occupying no more than a quarter of it, the speaker is drawn "
            "in their real place, mid-sentence. FILLING THE REST OF THE FRAME, a single "
            "large BUBBLE holds the thing they are describing, painted as its own little "
            "scene. THE BUBBLE IS PAINTED, NOT DRAWN: its edge is a soft feathered "
            "cloud-like border of the same paint as the rest of the picture, with a few "
            "small round bubbles trailing from the speaker up to it. It is NEVER a hard "
            "black comic-book outline, NEVER a speech balloon with a pointed tail, NEVER "
            "a flat white shape, and it carries NO lettering of any kind. This is ONE "
            "continuous painted image containing a bubble, and it is NOT a grid, NOT "
            "split panels and NOT a comic strip."
        ),
    },
    "imagined": {
        "summary": "The frame IS what is being described; the speakers are not in it at all.",
        "dropsBlocking": True,
        "peopleInFrame": "none",
        "framing": (
            "FRAMING, IMAGINED: this picture shows the THING BEING DESCRIBED, full "
            "bleed, and the people describing it are NOT in the frame at all. Nobody "
            "listens, nobody speaks, and no part of the room the conversation happens in "
            "appears. Paint the idea itself as a real place or a real object, in the same "
            "register as the rest of the book, with no bubble, no border, no vignette and "
            "no lettering."
        ),
    },
}

# The shots whose whole point is that the conversation's SETTING is not the subject.
# A run of these is what breaks up a talking book, so the auditor counts them.
RELIEF_SHOTS = frozenset({"thought-bubble", "imagined", "insert"})


def framing(shot: str) -> str:
    return SHOTS[shot]["framing"]


def known(shot: str) -> bool:
    return shot in SHOTS


def names() -> list[str]:
    return list(SHOTS)
