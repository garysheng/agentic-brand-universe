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
outranks the entity blocks that follow.

A SHOT CHANGES WHERE THE CAMERA IS AND NOTHING ELSE. It never moves the
subject, never empties their seat, never removes the furniture they are sitting
at, and never deletes the other people in the room. That sentence is here
because the first version of this module got it wrong in three separate ways
and shipped all three (2026-08-05, Bless You More, second pass):

  1. Shots carried a `dropsBlocking` flag that suppressed the setting's
     room-wide `contract.blocking` on every close shot. The reasoning came from
     a real precedent (a close-up told "sixteen guests are seated in the tiers"
     re-invents sixteen guests), but `blocking` in practice carries SEATING AND
     HANDEDNESS, which are continuity and must hold at EVERY camera distance,
     most of all up close where the model has least context. Dropping it swapped
     a husband and wife across their own table. The flag is gone; the narrow
     per-plate `contract.plates[...].includeBlocking` escape hatch remains,
     where a human opts in for one plate that genuinely has crowd content.
  2. The `close` framing said "most of the room is simply OUTSIDE this picture",
     which the model read as permission to delete the table its subject was
     sitting at. A close-up of a seated man still has his table in it.
  3. Nothing said the OTHER PEOPLE stay. Authors cut the cast to the subject,
     the cast closure duly deleted everyone else, and a third person vanished
     from a table he had not left.

CONTINUITY below is prepended to every framing, so none of the three can recur
by an author forgetting.
"""

# Prepended to EVERY shot's framing. A camera move is not a scene change.
CONTINUITY = (
    "THE CAMERA MOVES; NOTHING ELSE DOES. Every person keeps the exact seat, side "
    "and place the setting's blocking gives them, and if a BLOCKING PLATE is supplied "
    "it is the authority on who sits where: obey it at every distance. Whatever the "
    "subject is sitting at, leaning on or standing beside is STILL IN THIS PICTURE, in "
    "the near foreground if the camera is close. Everyone else present in this place is "
    "STILL PRESENT in the picture, behind or beside the subject, soft and out of focus "
    "if they are not the subject, and NOBODY leaves and NO seat empties because the "
    "camera came closer. "
)

# Each entry:
#   summary        one line, projected into SPEC.md
#   framing        the composition instruction injected into the prompt
#   peopleInFrame  advisory count for the variety auditor: "many" | "few" | "none"
SHOTS: dict[str, dict] = {
    "wide": {
        "summary": "The establishing view: the whole place, figures small inside it.",
        "peopleInFrame": "many",
        "framing": (
            CONTINUITY +
            "FRAMING, WIDE: the camera is well back and the PLACE is the subject. "
            "Any figures sit inside the space at full length and no taller than half "
            "the frame, so the room, its geometry and its light all read at once."
        ),
    },
    "two-shot": {
        "summary": "Two figures together, waist up, the space soft behind them.",
        "peopleInFrame": "few",
        "framing": (
            CONTINUITY +
            "FRAMING, TWO-SHOT: TWO figures fill the middle of the frame from the waist "
            "up and are the subject of the picture. The camera is closer than an "
            "establishing view. Behind them the place falls away softly and out of "
            "focus, present but never competing with them."
        ),
    },
    "group": {
        "summary": "Three or more figures together, waist up, closer than an establishing view.",
        "peopleInFrame": "many",
        "framing": (
            CONTINUITY +
            "FRAMING, GROUP: THREE OR MORE figures fill the middle of the frame from the "
            "waist up and are the subject of the picture, close enough that every face "
            "reads. The camera is nearer than an establishing view and the place is "
            "present behind them without competing."
        ),
    },
    "close": {
        "summary": "One face, chest up, filling the frame; the plate's camera distance is overridden.",
        "peopleInFrame": "few",
        "framing": (
            CONTINUITY +
            "FRAMING, CLOSE-UP. IGNORE THE CAMERA DISTANCE IN THE SUPPLIED REFERENCE "
            "PLATE, and only the distance: in that plate the camera is far back, and HERE "
            "IT HAS WALKED IN CLOSE TO ONE PERSON WITHOUT ANYTHING ELSE CHANGING. ONE face "
            "fills the frame from the chest up and the head alone is at least a third of "
            "the frame height. If that person is seated at a table, THE NEAR EDGE OF THAT "
            "TABLE AND WHAT IS LAID ON IT RUNS ACROSS THE BOTTOM OF THE FRAME in front of "
            "them, because that is where they are sitting. What is behind them is what was "
            "actually behind them, closer now and thrown soft."
        ),
    },
    "over-shoulder": {
        "summary": "From behind one figure onto the other; the near shoulder frames the far face.",
        "peopleInFrame": "few",
        "framing": (
            CONTINUITY +
            "FRAMING, OVER-THE-SHOULDER. IGNORE THE CAMERA DISTANCE IN THE SUPPLIED "
            "REFERENCE PLATE, and only the distance. The camera sits just behind and beside "
            "ONE person, whose near shoulder and the back of whose head are large, dark and "
            "soft at one edge of the frame, looking past them at the OTHER person, who is "
            "sharp and is the subject. BOTH KEEP THEIR OWN SEATS: the near shoulder belongs "
            "to whoever the blocking seats on that side, and the far face to whoever it "
            "seats opposite. Everything between them, the table and what is laid on it, is "
            "still there and unchanged."
        ),
    },
    "insert": {
        "summary": "Hands, an object, a surface. No faces, no whole figures.",
        "peopleInFrame": "none",
        "framing": (
            CONTINUITY +
            "FRAMING, INSERT. IGNORE THE CAMERA DISTANCE IN THE SUPPLIED REFERENCE "
            "PLATE, and only the distance. This is a CLOSE DETAIL: an object, the surface "
            "it rests on and possibly a hand, filling the frame. No whole figures and no "
            "faces are in shot, because the camera is too close for them, NOT because "
            "anybody left the room."
        ),
    },
    "reverse": {
        "summary": "The opposite camera on the same locked geometry, so handedness mirrors on purpose.",
        "peopleInFrame": "few",
        "framing": (
            CONTINUITY +
            "FRAMING, REVERSE ANGLE: the camera has moved to the OPPOSITE side of the "
            "same space and looks back the way the reference plate looks from. Left and "
            "right are therefore MIRRORED with respect to that plate, deliberately, and "
            "the scene text below states which fixed feature is on which side HERE. "
            "Every material, colour and light source is the same room."
        ),
    },
    "thought-bubble": {
        "summary": "The speaker small at one edge; a large soft-edged bubble holds what they are describing.",
        "peopleInFrame": "few",
        "framing": (
            CONTINUITY +
            "FRAMING, THOUGHT BUBBLE. The picture has TWO parts. SMALL, at ONE EDGE of "
            "the frame and occupying no more than a quarter of it, the speaker is drawn "
            "in their real place, mid-sentence. FILLING THE REST OF THE FRAME, a single "
            "large BUBBLE holds the thing they are describing, painted as its own little "
            "scene. THE BUBBLE IS PAINTED, NOT DRAWN: its edge is a soft feathered "
            "cloud-like border of the same paint as the rest of the picture, with a few "
            "small round bubbles trailing from the speaker up to it. THE SPEAKER STAYS IN "
            "THEIR OWN SEAT on their own side of the room, and anyone sitting with them is "
            "still sitting with them. It is NEVER a hard "
            "black comic-book outline, NEVER a speech balloon with a pointed tail, NEVER "
            "a flat white shape, and it carries NO lettering of any kind. This is ONE "
            "continuous painted image containing a bubble, and it is NOT a grid, NOT "
            "split panels and NOT a comic strip."
        ),
    },
    "imagined": {
        "summary": "The frame IS what is being described; the speakers are not in it at all.",
        "peopleInFrame": "none",
        "framing": (
            CONTINUITY +
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
