"""Standing prompt guards, shared by EVERY image generator.

WHY THIS FILE EXISTS. These rules used to live as prose in a SKILL.md saying "ALWAYS
append this preamble", which works exactly as often as a caller remembers. They were
then moved into chatgpt-images/scripts/generate_image.py, at the chokepoint most
callers funnel through. That was better and still not enough: `nano-banana-pro` is a
SECOND generator with its own generate_image.py and it had NO guards at all, so any
render routed through it silently lost every rule. A duplicated rule is almost never
duplicated exactly twice.

So the rules live HERE, once, and both generators import them. Add a rule to this
file, never to a caller and never to a per-book prompt.

A guard is appended only when the prompt actually mentions the thing it governs, and
only when the prompt has not already said it, so a hand-written prompt that already
carries the rule is not double-stuffed.
"""

_DEVICE_WORDS = (
    "phone", "smartphone", "laptop", "tablet", "monitor", "screen",
    "display", "ipad", "iphone", "computer", "handset", "kiosk",
)

# EVERY word here was earned. "card" was missing until 2026-07-29, when a spread whose
# whole subject was a handwritten CARD rendered its text rotated flat to the lens: the
# surface guard only fired at all because the words "book" and "page" happened to appear
# elsewhere in that prompt's negatives list. If a shape can carry writing, it belongs
# here.
_SURFACE_WORDS = (
    "book", "letter", "scroll", "page", "note", "notepad", "sign", "map",
    "menu", "newspaper", "document", "journal", "notebook", "card", "postcard",
    "envelope", "ledger", "receipt", "label", "poster", "contract", "form",
    "certificate", "recipe", "invitation", "tag", "plaque", "banner", "diary",
    "manuscript", "telegram", "prescription", "chart", "score", "sheet music",
    "handwriting", "handwritten", "lettering", "inscription",
)

# Words that mean a character is MOVING RELATIVE TO A PLACE. Earned 2026-07-29 on
# she-had-everything-but-peace spread 18: the beat was "she drove down to Encounter and
# went in", and the render put the building BEHIND her while she walked toward the
# camera, so she read as LEAVING the place she was arriving at.
_TRAVEL_WORDS = (
    "arriv", "entering", "enters", "enter the", "walking up", "walks up", "approach",
    "coming to", "comes to", "going in", "goes in", "steps into", "stepping into",
    "on her way", "on his way", "on their way", "heading", "pulls up", "pulling up",
    "leaving", "leaves the", "departing", "walking away", "walks away", "walking out",
    "walks out", "exiting", "exits", "turns back", "on the threshold", "at the door",
)

# A person seated AT A TABLE is the commonest two-hander in a picture book and it has a
# specific, ugly failure: the torso is painted emerging straight out of the tabletop, with
# no waist, no lap and no seat under it, so the figure reads as part of the furniture.
# Earned 2026-08-06 on he-kept-the-appointment spreads 17 and 19 (a restaurant booth), where
# it survived a contact-sheet read-back, a per-spread negatives list that already named the
# seating, book-doctor, and shipping. Gary caught it on the published book: "Josh is stuck in
# the table." The guard fires only when a TABLE word and a SEATING word are BOTH present, so
# it stays quiet on a standing scene or a bare still life of a table.
_TABLE_WORDS = (
    "table", "tabletop", "table top", "desk", "counter", "booth", "banquette", "bar top",
)
_SEATED_WORDS = (
    "seat", "seated", "sits", "sitting", "sat at", "sat down", "bench", "banquette",
    "chair", "stool", "pew", "booth", "lap",
)

# A TWO-HANDER AT A TABLE is the commonest scene in a picture book and it has two failures
# that arrive in sequence, because the fix for the first walks straight into the second.
# Both were earned on he-kept-the-appointment spreads 17 and 19, both by operator correction:
#   round 1  both men staged WHOLE, side-on, same distance, flat to the lens. The near man was
#            painted growing out of the tabletop. "Josh is stuck in the table."
#   round 2  near man moved to profile, but his CHEST stayed square to the camera with his head
#            swivelled ninety degrees. "Why do you feel like the chest needs to be facing the
#            camera? How awkward is that first shot?"
# Naming the shot `over-shoulder` in the render-spec did NOT prevent either one. Stating the
# anatomy did. So it is stated here, where every render passes.
_TWO_PERSON_CUES = (
    "each other", "across the table", "across from", "opposite him", "opposite her",
    "two men", "two women", "two people", "two figures", "both men", "both women",
    "both of them", "facing him", "facing her", "the other man", "the other woman",
)

_GUARD_DEVICE = (
    "DEVICE ANATOMY, NON-NEGOTIABLE: any phone, laptop, tablet or monitor is anatomically correct. "
    "The GLOWING DISPLAY is on the SCREEN side, and that side FACES ITS USER. A person looking at a "
    "device sees its screen; the viewer therefore sees the device's BACK or EDGE plus the light it "
    "throws onto the user's face and hands. NEVER put the screen image on the back of a phone, on a "
    "laptop's outer lid, or on a monitor's rear. NEVER show a screen facing the camera while the "
    "person using it looks at the opposite side. If both the user's face and the screen content must "
    "be visible, shoot it over the user's shoulder."
)

_GUARD_TWO_HANDER = (
    "TWO-HANDER STAGING, NON-NEGOTIABLE: two people at one table are NEVER staged as two equal whole "
    "figures at the same distance, flat and side-on to the lens. That is a line-up, not a camera "
    "position. ONE OF THEM IS NEAR AND ONE IS FAR. The NEAR figure sits at the OUTER EDGE of their "
    "seat closest to the camera, is LARGE in the frame, is CROPPED by the frame edge, is softly OUT "
    "OF FOCUS, and is very often seen FROM BEHIND; their lap, legs and feet fall outside the picture "
    "and are not drawn. The FAR figure is the SHARP SUBJECT, seen from the waist up. "
    "AND THE TORSO FOLLOWS THE HEAD: each person is turned toward the other, so a near figure whose "
    "HEAD is turned across the table has their CHEST turned across the table too, away from the lens. "
    "The camera behind them therefore sees the BACK AND OUTER SIDE of one shoulder, the back of the "
    "head, and at most a sliver of cheek; that person's CHEST AND SHIRT FRONT ARE NOT IN FRAME. NEVER "
    "rotate a head ninety degrees on a chest that is still square to the camera. No relaxed person "
    "holds that posture and it reads as wrong instantly."
)

_GUARD_SEATED = (
    "SEATED ANATOMY AT A TABLE, NON-NEGOTIABLE: a seated person is a WHOLE BODY resting ON a seat, "
    "and the table passes IN FRONT OF them, never THROUGH them. Their SHOULDERS AND CHEST are ABOVE "
    "the tabletop, their WAIST, LAP AND THIGHS are BELOW it and IN FRONT of the seat, and the trunk "
    "continues DOWN BEHIND the near edge of the table to that seat. There is a VISIBLE GAP between "
    "the front edge of the table and the person's chest and stomach. NEVER paint a torso emerging "
    "directly out of a tabletop with no waist, no lap and no seat beneath it. NEVER let the table's "
    "edge, apron or slab cut across a body as though the body were part of the furniture, and never "
    "let a thigh, hip or knee merge into the table. If the camera cannot see the seat itself, the "
    "body must still read as supported by one. Every seated figure has somewhere to sit and that "
    "seat is under them."
)

# REWRITTEN 2026-07-29 because the previous version CONTRADICTED ITSELF on the commonest
# real case and the model resolved the contradiction the wrong way.
#
# The old text said "compose over-the-shoulder or from behind" (camera advice) and also
# "any handwriting is abstract line work with NO real readable letters". So a scene that
# legitimately specifies exact designed text -- a title, a signed name, a word on a card,
# all first-class in universes whose canon makes in-art text a design element -- put the
# model in a bind: make it legible, or make it illegible. It chose legible, and got there
# the easy way: by rotating the page flat to the lens.
#
# Gary caught it twice, on `it-was-not-broken` spread 36 ("you continuously flip the
# book") and again on `she-had-everything-but-peace` spread 16. The fix is to name the
# resolution explicitly: legibility is a CAMERA problem, never a page-rotation problem.
_GUARD_SURFACE = (
    "READABLE SURFACES ARE ORIENTED FOR THEIR READER, NEVER FOR THE CAMERA. Any book, page, letter, "
    "card, note, ledger, document, sign or map that a character is reading, writing on or holding "
    "belongs to THAT PERSON, so it is oriented to THEM: its TOP EDGE points AWAY from them and its "
    "lines run the direction they read. From wherever the camera happens to stand, it is therefore "
    "foreshortened, tilted, or partly upside down. NEVER rotate a surface flat and square to the lens "
    "so the viewer can read it comfortably. That is the single most common failure on this rule and it "
    "reads as staged the instant anyone notices it. "
    "IF THE SCENE SPECIFIES EXACT TEXT THAT MUST BE LEGIBLE, SOLVE IT WITH THE CAMERA AND NEVER BY "
    "TURNING THE PAGE: move the camera round to the reader's OWN side, over their shoulder or beside "
    "their head and looking down as they look down, so the writing is legible AND still correctly "
    "oriented for them. Legibility and correct orientation are never in conflict; a page squared up to "
    "the lens means the camera was put in the wrong place. "
    "Handwriting the scene does NOT specify is abstract handwriting-like line work with no real "
    "readable letters. Text the scene DOES specify as an exact quoted string is designed lettering and "
    "must be spelled exactly as quoted."
)

# The same failure shape as the readable-surface guard, and the same resolution: the
# author wanted the character's FACE, so they turned the CHARACTER around, which
# inverted the thing the scene was actually about. Fix the camera, never the subject.
_GUARD_TRAVEL = (
    "TRAVEL DIRECTION MUST MATCH THE STORY. If a character is ARRIVING at a place, going IN, or "
    "approaching it, then that place is AHEAD of them: they face it, they move toward it, and its "
    "entrance is in front of them, NEVER behind them. If a character is LEAVING, the reverse. A "
    "figure walking toward the camera with the building behind them reads unmistakably as LEAVING, "
    "whatever the caption says, and it silently inverts the beat. "
    "IF THE SCENE NEEDS THE ARRIVING CHARACTER'S FACE VISIBLE, SOLVE IT WITH THE CAMERA AND NEVER BY "
    "TURNING THEM ROUND: put the camera on the DESTINATION side, at or beside the entrance, looking "
    "BACK along their direction of travel so they walk toward the lens AND toward the door at the "
    "same time. A three-quarter angle from just beside the doorway shows the face, the doorway and "
    "the approach all at once. Never place the destination behind a character who is arriving at it."
)

_GUARD_UI = (
    "NO USER INTERFACE ANYWHERE: no windows, menu bars, buttons, icons, toolbars, panels, form "
    "fields, cursors, floating rectangles or screenshot-like elements. Screens carry only soft glow "
    "or vague painterly shapes."
)

# "Already said it" probes. These match ONLY each guard's OWN SIGNATURE PHRASE, so
# re-applying the guards is idempotent, and nothing else.
#
# They deliberately do NOT match paraphrases. That was the first shape of this fix and it
# was wrong: the probe list included wordings like "oriented for that person", which a
# per-book negatives list happened to contain -- the WEAKER wording that had already
# failed twice. A caller's paraphrase would therefore have SUPPRESSED the authoritative
# guard, which is precisely backwards. A weak restatement must be superseded by this
# file, never allowed to silence it. The guard is appended last, so it wins.
_DEVICE_PROBES = ("the glowing display is on the screen side",)
_SURFACE_PROBES = ("readable surfaces are oriented for their reader",)
_TRAVEL_PROBES = ("travel direction must match the story",)
_UI_PROBES = ("no user interface anywhere:",)
_SEATED_PROBES = ("seated anatomy at a table",)
_TWO_HANDER_PROBES = ("two-hander staging, non-negotiable",)


def apply_prompt_guards(prompt: str, enabled: bool = True) -> tuple[str, list[str]]:
    """Append the standing guards the prompt's own content calls for.

    Returns (prompt, names_of_guards_added) so the caller can print what fired.

    IDEMPOTENT. The word-scan runs against the prompt with any ALREADY-APPENDED guard
    text stripped out, because the guards' own wording contains trigger words: _GUARD_UI
    says "Screens carry only soft glow", so a naive second pass saw the word "screen",
    decided the scene contained a device, and stapled the device-anatomy guard onto a
    prompt that never had a device in it. Callers legitimately double-apply (a wrapper
    pre-guards a prompt, then the generator guards it again), so this has to hold.
    """
    if not enabled:
        return prompt, []
    scan = prompt.lower()
    for block in (_GUARD_DEVICE, _GUARD_SURFACE, _GUARD_TRAVEL, _GUARD_UI, _GUARD_SEATED, _GUARD_TWO_HANDER):
        scan = scan.replace(block.lower(), " ")
    added: list[str] = []
    has_device = any(w in scan for w in _DEVICE_WORDS)
    has_surface = any(w in scan for w in _SURFACE_WORDS)
    has_travel = any(w in scan for w in _TRAVEL_WORDS)
    has_seated = any(w in scan for w in _TABLE_WORDS) and any(w in scan for w in _SEATED_WORDS)
    has_two_hander = has_seated and any(w in scan for w in _TWO_PERSON_CUES)
    low = prompt.lower()   # probes look at the WHOLE prompt, guard text included

    if has_device and not any(p in low for p in _DEVICE_PROBES):
        prompt += "\n\n" + _GUARD_DEVICE
        added.append("device-anatomy")
    if has_surface and not any(p in low for p in _SURFACE_PROBES):
        prompt += "\n\n" + _GUARD_SURFACE
        added.append("readable-surface")
    if has_travel and not any(p in low for p in _TRAVEL_PROBES):
        prompt += "\n\n" + _GUARD_TRAVEL
        added.append("travel-direction")
    if has_two_hander and not any(p in low for p in _TWO_HANDER_PROBES):
        prompt += "\n\n" + _GUARD_TWO_HANDER
        added.append("two-hander-staging")
    if has_seated and not any(p in low for p in _SEATED_PROBES):
        prompt += "\n\n" + _GUARD_SEATED
        added.append("seated-at-table")
    if (has_device or has_surface) and not any(p in low for p in _UI_PROBES):
        prompt += "\n\n" + _GUARD_UI
        added.append("no-ui-chrome")
    return prompt, added
