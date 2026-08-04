---
name: voice-gate
description: Run a voice check on any manuscript, narration script, or overlaid caption text BEFORE it is locked or rendered to audio, in an Agentic Brand Universe. The rules come from the voice spec published at https://garysheng.com/voice.md, not from a restated copy: em dashes, filler, performative "not X but Y" inversions, totalizing emphasis ("the whole ___", "the entire ___"), tautology-then-negation, plus the universe's own term rules from identity.voice. Blocks the lock until every finding is fixed or waived with a written reason. Generic and universe-parameterized: pass the target universe.
---

# Voice Gate

The last check before words lock or become audio. Run it at the words-before-art blessing
gate and before every narration render.

## RUN THE SCRIPT. Do not perform this check by reading.

```bash
python3 <abu>/skills/voice-gate/scripts/voice_gate.py <universe> <manuscript.md> [more files...]
```

Naming the script here and in `make-a-book` is load-bearing. This skill shipped for months
as prose describing checks an agent was supposed to carry out by eye, and the checks did not
happen: three totalizing-emphasis violations reached two finished books on 2026-08-02, in a
chain whose step 4 already said "run voice-gate first". **A check you perform by reading is a
check you skip when you are carrying a book's momentum.** The script exits non-zero, so it
cannot be agreed with and forgotten.

Useful flags:

| Flag | For |
|---|---|
| `--emit-waivers` | WRITE waiver stubs for every open REVIEW into the waivers file, ready to annotate. Do NOT redirect it with `>`: it writes the file itself, and it refuses rather than clobbering reasons you already adjudicated |
| `--waivers PATH` | a waiver file somewhere other than `<manuscript>.voice-waivers.json` |
| `--offline` | skip the spec fetch (checks against the vendored copy) |
| `--adopt-spec` | re-vendor the published spec, AFTER reading the diff and porting new rules |

## The rules are PUBLISHED, and the gate proves it is current

The authority is <https://garysheng.com/voice.md>. The script fetches it, hashes it, and
compares against the hash its rule table was derived from. **When the published spec moves,
the gate fails with the diff** rather than passing against stale rules, because the failure
that actually happens is silent: totalizing emphasis was added to the spec on 2026-07-28 and
was still unenforced here five days later.

A drift failure is fixed by reading the diff, porting any new hard rule into `RULES`, then
running `--adopt-spec`. Adopting without porting silences the alarm and changes nothing else.

Network failure never fails the gate: it falls back to the vendored copy and says so.

## Three severities, and only two of them stop you

| Tier | Examples | Behavior |
|---|---|---|
| **BLOCK** | em dash, `Christo-futurist`, Claude co-author credit, a `oneWord` term split | fix it; nothing waives it |
| **REVIEW** | totalizing emphasis, `not X but Y`, filler, tautology-then-negation, `automate` | fix it, **or** waive it with a written reason |
| **ADVISORY** | `capitalize` terms, `neverDisparage` | printed, never gated |

ADVISORY exists because some rules are genuinely undecidable by grep. Nation of Fire's own
`capitalizeNote` says the `Spirit` rule INVERTS on the possessive: "his spirit" is a man's
own spirit-man, and capitalizing it is a doctrinal error rather than a style win. A checker
that blocked on that would train the author to force the gate, and a forced gate is worse
than none because it also lies about having checked.

## Waivers are decisions, not a mute button

`<manuscript>.voice-waivers.json`, beside the manuscript, in the same commit:

```json
{ "waived": [
  { "rule": "totalizing-emphasis",
    "match": "the whole thing",
    "line": "She read it under the covers, the whole thing.",
    "reason": "concrete: she read all of it, and cutting the word loses that" }
]}
```

- A reason still reading `TODO` waives nothing. An emitted stub is not a decision.
- A waiver is keyed on the **line text**, never the line number, so inserting a spread does
  not shift a waiver onto a sentence nobody adjudicated. Edit the sentence and the waiver
  retires itself and is reported as STALE, which is correct: the reasoning was about a
  sentence that no longer exists.

## Quotation marks are NOT an exemption

Only a markdown blockquote (and the `**Closing verse.**` convention) is exempt, because that
is where this framework sets Scripture and verbatim sourced testimony.

Straight quotes used to exempt a span, and that one decision is why the rules did not bind:
a picture book is almost entirely authored dialogue inside quotes, so the manuscript was
exempt from its own voice rules. Two of the three totalizing hits in the two most recent
books sat inside dialogue. Genuinely verbatim source material goes in a blockquote or in a
waiver, where the reason is written down.

## Gates honored
- **Voice is load-bearing:** no words lock and no audio renders until this exits zero.

## Not this skill
- Rewriting the text (report the violations; the author fixes them).
- Rendering the audio (that is the renderer, after this passes).
