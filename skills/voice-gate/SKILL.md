---
name: voice-gate
description: Run a voice check on any manuscript, narration script, or overlaid caption text BEFORE it is locked or rendered to audio, in an Agentic Story universe. Blocks the lock until the text is clean of the universal rules (no em dashes, no filler, no performative "not X but Y" inversions) plus the universe's own term rules from identity.voice (words to capitalize, words to keep one-word). Generic and universe-parameterized: pass the target universe.
---

# Voice Gate

The last check before words lock or become audio. It keeps voice drift out of a property. Run it at the words-before-art blessing gate and before every narration render.

## Inputs
- The target universe (a path with `universe.json`). Read `identity.voice` (`capitalize` list, `oneWord` list).
- The text to check (a manuscript, a narration script, an overlaid caption).

## Procedure
1. **Load the universe's term rules.** From `identity.voice`: the `capitalize` terms (must appear capitalized) and the `oneWord` terms (must appear as one word).
2. **Check the universal rules.** No em dashes (use colons, periods, parentheses, or two sentences). No filler (really, just, very, truly). No performative "not X but Y" inversions.
3. **Check the universe rules.** Each `capitalize` term is capitalized wherever it appears; each `oneWord` term is spelled as one word.
4. **Report + block.** List every violation with the offending line. BLOCK the lock (or the audio render) until the text is clean. This is a hard gate, not an advisory pass.

## Gates honored
- **Voice is load-bearing:** no words lock and no audio renders until the check passes.

## Not this skill
- Rewriting the text (report the violations; the author fixes them).
- Rendering the audio (that is the renderer, after this passes).
