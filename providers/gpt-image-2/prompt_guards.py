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

_GUARD_DEVICE = (
    "DEVICE ANATOMY, NON-NEGOTIABLE: any phone, laptop, tablet or monitor is anatomically correct. "
    "The GLOWING DISPLAY is on the SCREEN side, and that side FACES ITS USER. A person looking at a "
    "device sees its screen; the viewer therefore sees the device's BACK or EDGE plus the light it "
    "throws onto the user's face and hands. NEVER put the screen image on the back of a phone, on a "
    "laptop's outer lid, or on a monitor's rear. NEVER show a screen facing the camera while the "
    "person using it looks at the opposite side. If both the user's face and the screen content must "
    "be visible, shoot it over the user's shoulder."
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
    for block in (_GUARD_DEVICE, _GUARD_SURFACE, _GUARD_TRAVEL, _GUARD_UI):
        scan = scan.replace(block.lower(), " ")
    added: list[str] = []
    has_device = any(w in scan for w in _DEVICE_WORDS)
    has_surface = any(w in scan for w in _SURFACE_WORDS)
    has_travel = any(w in scan for w in _TRAVEL_WORDS)
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
    if (has_device or has_surface) and not any(p in low for p in _UI_PROBES):
        prompt += "\n\n" + _GUARD_UI
        added.append("no-ui-chrome")
    return prompt, added
