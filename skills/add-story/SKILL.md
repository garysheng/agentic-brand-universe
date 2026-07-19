---
name: add-story
description: Add ONE story to an Agentic Story universe as a typed StorySpec (a medium-neutral composition, NOT an `add-entity` kind). Interview the logline, its declared spine (obedient-servant, thesis, primer, testimony, or another open-set value; a story is never assumed to be a hero-journey), its refrain, its register (defaults to the universe's `identity.register`, with a per-story override allowed), and its beats with per-beat provenance. Registers as `status: "stub"` (logline + spine only) or `"full"` (features + beats + provenance filled). Runs a casting sweep over the beats' named entities and hands off anything not yet in canon to add-character/add-setting/add-visual-metaphor/add-motif/add-prop. Art is NOT generated here. Use when composing a new property (book, chapter, or other unit) out of existing or new canon. Generic and universe-parameterized: pass the target universe.
---

# Add Story

One story, into a universe's canon, as a typed `StorySpec` written directly to `stories/<id>.json`. This is authoring, not art and not `add-entity` (a story is a composition over canon, not a canon entity itself). It ends with a validated record; the picture-book renderer projects it into a medium later, and `lock-references` still owns any new entity's art.

## Inputs
- The target universe (a path containing `universe.json`). Read its `identity` (mark, register, voice) and existing `canon/entities/` + `stories/`.
- The story's source material (a testimony, a design brief, a braindump) and whether it is ready to be fully beaten out or only worth registering as a placeholder.

## Procedure

1. **Interview (one question at a time).**
   - **Logline.** One sentence: what this story is about.
   - **Spine.** The story's declared arc invariant, drawn from an open set (`obedient-servant`, `thesis`, `primer`, `testimony`, or a new value if none fits). Never assume hero-journey by default: an explainer is a `primer`, a property built around one object's argued states is a `thesis`. Ask which shape this actually is.
   - **Refrain.** The one line the whole property returns to or proves.
   - **Register.** Defaults to the universe's `identity.register` (same anchor + rejected poles as everything else). Ask only if this specific story needs an override (e.g. anchored to a real artist's own body of work) and if so capture it as this story's own `register` block.
   - **Features + beats.** Which canon entities this story selects, and the ordered beat sheet. For each beat: its text, its `location` (a setting/visual-metaphor id, if any), the `characters` it features, and its **provenance** (what real source this beat traces to: testimony, research, the author's own words). An unsourced vivid detail does not go in a beat.
2. **Decide status.** `"stub"`: logline + spine only, no beats yet, when the roster should reflect a planned property before it is fully built (mirrors an `unlocked` setting). `"full"`: features + beats + provenance are filled in and required to validate.
3. **Casting sweep over the beats' named entities (reuse wins).** For every character, setting, visual-metaphor, motif, or prop named in `features` or a beat's `characters`/`location`, sweep `canon/entities/` + any CANON.md. Anything already there: reuse its id. Anything missing: hand off to the matching sibling skill (`add-character`, `add-setting`, `add-visual-metaphor`, `add-motif`, `add-prop`) BEFORE finalizing this story. A `full` story whose `features` names an unresolved id fails `validate`.
4. **Write `stories/<id>.json` directly** (no `add-entity`; this is a StorySpec, per SPEC §4.3):
   ```jsonc
   {
     "id": "<id>",
     "logline": "…",
     "spine": "…",
     "refrain": "…",
     "status": "stub" | "full",
     "register": { "id": null, "anchor": null, "anchoredToRealArt": null, "rejectedPoles": [] },
     "features": ["…"],
     "beats": [ { "n": 1, "text": "…", "location": null, "characters": ["…"], "provenance": "…" } ],
     "writesBack": [],
     "gates": { "wordsBlessed": null, "subjectApproval": null }
   }
   ```
5. **Validate + commit.** `agenticstory validate <universe>` stays green: a `stub` story is exempt from the features/beats/provenance requirements; a `full` story must have non-empty `features` + `beats`, every beat's `provenance` non-empty, and every featured id known to canon. Commit `stories/<id>.json` + any entities the casting sweep created. Report the story's `status` and that rendering still requires `assert-story` (the deeper, asset-on-disk gate) to pass separately.

## Gates honored
- **Reuse-first casting sweep** (step 3): never invent an entity a story's beats could cast from existing canon.
- **Provenance**: every beat in a `full` story cites a real source; unsourced vivid detail is flagged before it ships.
- **Spine not assumed**: every story declares its own arc invariant instead of inheriting a single hero-journey default.
- **No art here**: art generation is `lock-references`; medium projection is the renderer. This skill only writes the composition.

## Not this skill
- Creating a canon entity named in a beat → the matching sibling `add-*` skill.
- Generating or locking any entity's reference art → `lock-references`.
- Rendering the story into a medium (a picture book, etc.) → the renderer.
- Recording a typed relationship between two ids (e.g. `appears-in` this story) → `add-relation`.
