# Phase E3 — Generic renderers + resolution proof Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development or superpowers:executing-plans. Steps use `- [ ]`.

**Goal:** Author generic, universe-parameterized renderer skills (`render-book`, `cover`, `update-book`) that read a universe's `identity` + craft-canon records + canon, instead of hardcoding Nation of Fire. Then prove the generic path resolves a REAL NoF spread end-to-end (canon-resolve on a real story's cast + location from `nof-universe`, its genre + register from craft/identity). Parallel-safe: the `nof:*` skills stay live and untouched. Platform-delivery generalization (`book-platform` / the garysheng-books reader code) is DEFERRED to a follow-up. Phase F (retiring the plugin) waits until Gary personally renders a real book on the generic path.

**Architecture:** The generic renderers are thin: they wrap the universal `create-brand-os-picture-book` / `picture-book-platform` pipelines (which already own the mechanics) and add only the universe layer, read from data: `identity.register` (style anchor + rejectedPoles), `identity.mark` (the byline), `identity.closingOrnament`, the story's `spine` + `genre` (craft-canon records), and canon resolution via `canon-resolve`. Text passes `voice-gate`; every render passes `render-readback`.

**Tech Stack:** Markdown (skills). Engine CLI for the resolution proof (`assert-story`, `list-craft`, `canon-resolve` via `assert-spread`). No engine change in E3.

## Global Constraints

- **Parent design:** `docs/superpowers/specs/2026-07-18-framework-skill-catalog-design.md` (Phase E3). Builds on the full v0.4.1 framework.
- **Additive + parallel-safe:** author NEW generic skills in `agenticstory/skills/`. Do NOT edit or delete any `nof:*` skill or the `picture-book`/`cover`/`book-platform`/`update-book` prose. Do NOT touch the garysheng-books platform code (deferred).
- **Generic + universe-parameterized:** never hardcode a universe name, the mark string, the theme, or "the wisp". Read them from `identity` + craft records. A generic renderer names NO specific universe.
- **Faithful:** the generic skills preserve the universal render discipline (words-before-art gate, register anchor first, canon-resolve before prompts, read-back after every render, spine + genre honored). The NoF-specific specifics now come from data.
- **No plugin retirement in E3:** F is a separate, Gary-gated step.
- **Voice:** no em dashes in committed prose or commit messages.

**Absolute paths:** framework `/Users/garysheng/Documents/github-repos/agenticstory`; NoF source skills `/Users/garysheng/Documents/github-repos/garysheng-claude-plugins/plugins/nof/skills/`; nof-universe `/Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe`.

---

## File Structure

- Create: `skills/render-book/SKILL.md` — the generic universe picture-book renderer.
- Create: `skills/cover/SKILL.md` — the generic cover renderer.
- Create: `skills/update-book/SKILL.md` — the generic existing-book editor.
- Modify: `README.md` (agenticstory) — list the renderer skills + note book-platform generalization is deferred.

---

## Task 1: `render-book` (generic universe renderer)

**Files:** Create `skills/render-book/SKILL.md`.

Read the SOURCE `.../plugins/nof/skills/picture-book/SKILL.md` for the discipline to preserve, and the framework skills (`add-character`, `canon-resolve`, `lock-references`) for house style. Author a generic renderer whose NoF-specific bits are replaced by data reads.

- [ ] **Step 1: Write the skill.** Frontmatter `name: render-book` + a description: "Render a story from an Agentic Story universe into a picture book. Wraps the universal create-brand-os-picture-book pipeline and adds the universe layer from DATA: the story's spine + genre (craft-canon records), the universe's register (identity.register style anchor, passed first on every render), the mark (identity.mark), canon resolved via canon-resolve, text checked by voice-gate, every render checked by render-readback. Generic and universe-parameterized: pass the target universe + story id." Procedure:
  1. **Load the universe + story.** Read `identity` (register anchor + rejectedPoles, mark, closingOrnament) and the `stories/<id>.json` (its `spine`, `features`, `beats`, `register` override if any). If `identity.register.anchor` is null, STOP (style not locked).
  2. **Read the craft.** Load the story's `spine` craft record and its `genre` craft record (from `canon/craft/`) plus the universe `register-rule` records. These carry the arc discipline, the book-type format canon, and the universe-wide laws (via `list-craft` / reading the records). Honor them.
  3. **Words before art (gate).** Draft/confirm the manuscript. Run `voice-gate` on it. Do NOT proceed to art until the words are blessed and voice-clean.
  4. **Per spread: resolve, generate, read back.** For each spread: run `canon-resolve` on the spread's cast + location (resolves the locked GABRs + invariants + the register anchor, and runs the assert gate). Generate via `create-brand-os-picture-book`'s mechanics, passing `identity.register.anchor` FIRST, baking `rejectedPoles` + the register-rules as negatives, honoring the genre's format canon. Run `render-readback` on every render (DEFECT means regenerate from scratch).
  5. **Close + write back.** Apply the universe closing (the mark from `identity.mark`, the `closingOrnament` if any). On completion, propose the story's write-back (new/updated canon) for the author to accept.
  Gates honored: words-before-art + voice-gate, canon-resolve before prompts, register-anchor-first, read-back after every render, spine + genre + register-rules honored, subject-approval for real people. Not this skill: authoring entities (`add-*`), locking an entity's reference matrix (`lock-references`), shipping to a platform (`book-platform`, deferred).

- [ ] **Step 2: Commit.** `git add skills/render-book/SKILL.md && git commit -m "feat(skill): render-book (generic universe picture-book renderer)"`

---

## Task 2: `cover` (generic cover renderer)

**Files:** Create `skills/cover/SKILL.md`.

Read SOURCE `.../plugins/nof/skills/cover/SKILL.md` for the discipline (correct portrait aspect, the diegetic title, the mark, read-back on title spelling + hero likeness).

- [ ] **Step 1: Write the skill.** Frontmatter `name: cover` + description: "Create a picture-book cover for a story in an Agentic Story universe, at the platform's portrait aspect. Bakes the diegetic title + the universe mark (identity.mark), passes the register anchor first, and runs render-readback on the title spelling + hero likeness + register discipline. Generic and universe-parameterized." Procedure: read `identity` (mark + register); render the cover at the correct portrait aspect (never a landscape spread size) through the guarded renderer; bake the title + `identity.mark` byline; pass `register.anchor` first; read back the title spelling, the hero likeness (via the hero entity's invariants), and register discipline; regenerate from scratch on any DEFECT. Gates: register-first, read-back, correct aspect. Not this skill: the interior spreads (`render-book`), platform shipping (`book-platform`, deferred).

- [ ] **Step 2: Commit.** `git add skills/cover/SKILL.md && git commit -m "feat(skill): cover (generic universe cover renderer)"`

---

## Task 3: `update-book` (generic existing-book editor)

**Files:** Create `skills/update-book/SKILL.md`.

Read SOURCE `.../plugins/nof/skills/update-book/SKILL.md` for the edit discipline (add/insert/revise/remove a spread, renumber, regenerate touched art + narration, words-before-art on any text change).

- [ ] **Step 1: Write the skill.** Frontmatter `name: update-book` + description: "Edit or extend an existing picture book in an Agentic Story universe: add, insert, revise, or remove a spread, renumber, and regenerate only the touched art + narration. Honors the words-before-art gate (voice-gate on any changed text) and re-resolves canon (canon-resolve) + reads back (render-readback) on every regenerated spread. Generic and universe-parameterized." Procedure: take the universe + the book + the edit; apply the structural edit (renumber cleanly); for any changed text run `voice-gate` before art; regenerate only the touched spreads via the same discipline as `render-book` (canon-resolve, register-anchor-first, read-back); leave untouched spreads alone. Gates: words-before-art, canon-resolve, read-back, minimal-regeneration. Not this skill: creating a new book (`render-book`), platform delivery (`book-platform`, deferred).

- [ ] **Step 2: Commit.** `git add skills/update-book/SKILL.md && git commit -m "feat(skill): update-book (generic existing-book editor)"`

---

## Task 4: Resolution proof on a real NoF spread

Prove the generic path drives a real NoF book end-to-end through the framework primitives (short of the taste-gated art generation, which Gary runs). Target: the story `not-every-fire-is-holy` (its cast + `the-arena` location are locked in `nof-universe`).

- [ ] **Step 1: The story's craft resolves.** Run `python3 -m agenticstory.cli list-craft /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe` and confirm the spine (`obedient-servant`) + register-rules the renderer would read are present. Read `stories/not-every-fire-is-holy.json`'s `spine`.

- [ ] **Step 2: canon-resolve resolves the real cast from nof-universe.** Run `python3 -m agenticstory.cli assert-story /Users/garysheng/Documents/github-repos/nation-of-fire/nof-universe not-every-fire-is-holy` (the load-bearing gate the generic render-book calls per spread). Expected: `OK` (every featured entity's required GABRs resolve from the self-contained nof-universe, and the-arena is locked). This proves the generic renderer would resolve the real book's canon.

- [ ] **Step 3: The register is available.** Confirm `nof-universe/universe.json` `identity.register` exists (name + rejectedPoles). Note: `register.anchor` may be null (NoF's style anchor was never locked as a separate file, because NoF predates the register standard); the generic render-book would either use NoF's existing per-book register or prompt to lock a universe anchor. Record this as the one gap between NoF-today and the generic path.

- [ ] **Step 4: Write the proof summary.** Append to `docs/superpowers/plans/2026-07-18-phase-E3-generic-renderers.md` (or a PROOF note) what resolved cleanly (craft + canon + gate) and the one gap (NoF's register anchor is not a locked file yet). This is the handoff for Gary's real-book run.

---

## Verification

- [ ] All 3 renderer skills exist with valid frontmatter (`name` matches folder), 0 em dashes, 0 universe hardcodes (`grep -il "nation of fire\|nof-universe\|the wisp\|aitx"`).
- [ ] `assert-story not-every-fire-is-holy` on nof-universe returns OK (the generic render path would resolve it).
- [ ] Parallel-safe: `nof` plugin untouched; no `nof:*` skill or `nof-universe` file modified by E3 (only new agenticstory skills committed).
- [ ] Engine unchanged: 23 tests still OK.

## Out of scope (deferred / F)

- Generalizing `book-platform` + the garysheng-books `nof-picture-book-reader` / `NofBookReader` / `WispDot` / `NOF_THEME` to read `identity` (platform-code follow-up).
- Actually generating a real NoF book's art through the generic path (Gary runs this; he is the taste gate).
- Locking NoF's universe register anchor as a file (a small data step Gary can do when he first runs render-book on NoF).
- Phase F: retiring the `nof` plugin (only after Gary personally renders a real book on the generic path and confirms the look holds).
