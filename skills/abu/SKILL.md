---
name: abu
description: THE FRONT DOOR to Agentic Brand Universe. Hand it nothing and it reports where your brand universe stands, what the single highest-leverage next move is, and a ten-minute one if you are bored. Hand it a wish in plain language ("make a zine cover", "my characters look different every time", "I want this to feel more like my brand") and it routes to the right verb without you knowing any verbs exist. Use when someone says "abu", "how's my universe", "where am I", "what should I do next", "what can I do", "I'm bored", "get me to 100", "status", or opens a session cold with no idea what to ask for. Also the correct destination whenever you catch yourself about to show a non-technical user a shell command. Universe-agnostic; resolves the target universe itself.
---

# ABU

The console loads the cartridge. **This is what the cartridge says when it boots.**

Everything here is spoken in natural language. The user never types a path, a flag, or
a verb name. If they wanted to memorize verbs they would read the reference; they came
here to say what they want.

## The one hard rule

**Never show the user a shell command.** Not as an example, not "for reference", not
in a code block they could copy. You run the commands. You report what happened in
plain sentences. A command in the transcript is a defect in this skill, because the
whole promise of a playable harness experience is that the harness does the operating.

The single exception is a prerequisite the harness genuinely cannot satisfy for them,
which today is only installing the console itself and holding an API key. Say those in
prose and hand them off to `onboard`.

## Procedure

**1. Read the situation before saying anything.**

```
python3 <skill>/scripts/status.py --json
```

It resolves the universe (an explicit path, else the one you are standing in, else
everything registered), grades it via `universe-doctor`, diffs against the last score
it saw, and selects the moves worth mentioning. It exits 0 even when there are no
universes at all, because "you have none yet" is an answer, not an error.

**2. If there are no universes,** this is an onboarding moment. Do not report an
absence and stop. Ask what they are making. If they describe a look with no recurring
characters (a zine, a deck, page heroes), route to `create-style-pack`, which needs no
universe at all. If something must appear identically in many places, route to
`start-new-story-universe`. If the framework itself is not installed, route to
`onboard`.

**3. Otherwise, open with where they stand, in three sentences at most:**

- The grade and score, and the move since last time if there is one. `72 -> 78 since
  Tuesday` is the sentence people actually want.
- The biggest win available, named as an outcome rather than a verb. Not
  "run shoot-references on divine-yoke" but "the divine yoke has no art yet, so every
  book that uses it is improvising. Want me to shoot it?"
- The ten-minute option, if they might be browsing rather than committing.

**4. Propose. Do not merely await.**

The user brings desire; you bring vocabulary. They will never ask for a
content-neutral anchor or a scale plate, because they do not know those exist. So
offer the specific next thing and ask for a yes, the way a well-fed cartridge offers
"your leadership team is the two cofounders plus three contracted heads, confirm?"
instead of asking an open question into the void.

Offer at most three options. A menu of eight is another wall.

**5. Route a wish to a verb, silently.** The user says what they want; you pick.

| They say | You reach for |
|---|---|
| "make more images that look like these" | `create-style-pack`, then `on-brand-image` |
| "this character looks different every time" | `add-character` then `shoot-references` |
| "the room keeps changing shape" | `add-setting`, then its plates |
| "make a book / zine / picture book" | `make-a-book` (or the universe's cartridge skill) |
| "is this any good yet" / "get me to 100" | `universe-doctor`, then work its punch-list |
| "did I break anything" | `lint-universe`, and `validate` for schema |
| "the words don't sound like me" | `voice-gate` |
| "publish it" | the delivery skill for that surface |

Announce the outcome, not the routing. "I'll lock the divine yoke's reference sheets
first, since three books are waiting on it" beats "invoking shoot-references."

## Getting to 100

The score is `universe-doctor`'s rubric and this skill does not invent its own. Treat
it as a game board: name the weakest dimension, say what it would take to close the
gap, and offer to start. A low score on a young universe is a plan, not a failing
grade, and should be framed that way or people quit at C.

When a work session ends, run status again and report the delta. The number moving is
the reward, and a session that improved nothing should say so honestly rather than
narrating activity.

## Definition of done

- The user knows where they stand, what is worth doing next, and what a small version
  of that looks like.
- They were offered something specific rather than asked an open question.
- No shell command appeared in the conversation.
