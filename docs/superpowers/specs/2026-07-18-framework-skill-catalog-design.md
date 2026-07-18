# Agentic Story — framework skill catalog + reference-matrix standard (v0.4)

Date: 2026-07-18
Status: design approved, pending spec review
Parent: `agenticstory/SPEC.md` (extends v0.3 §11 Skills & Identity layer)

## Goal

Give the Agentic Story framework a **complete catalog of generic, atomic, universe-parameterized skills** — one per load-bearing unit of building and growing a universe — plus a **reference-matrix standard** that defines what "a locked entity" means per kind, and a **first-class register/style** so a universe renders in a consistent illustrative look. Then **migrate the nine Nation of Fire skills** onto this catalog so NoF becomes the reference *data*, not a fork of the machinery.

The test of success: standing up universe #2 (AITX) and adding a character, a setting, and a story to it uses only framework skills reading AITX's `identity` + canon. No per-universe skill code. No path or style hardcoded in a skill.

## Principle (from SPEC §11, unchanged)

**The framework ships skills; a universe ships data.** Every skill here is generic, lives in the `agenticstory` plugin, and takes a target universe (`--universe <path>` or discovers `universe.json` upward). A universe ships canon (entities/relations/stories), self-contained assets (§3a), an `identity` block, and craft-canon records. If renaming a universe folder would edit a skill, that skill is hardcoding what belongs in `identity`.

## The reference-matrix standard (SPEC §12)

"Locked" must *mean* something checkable per kind. The reference matrix is the canonical set of reference shots an entity of each kind needs before it is renderable, so the gate can refuse an under-referenced entity the same way it refuses a missing file today.

- **character** — the anti-uncanny-valley set: `face-neutral`, `face-3q`, `expressions`, `forward-fullbody`, `profile-left`, `profile-right`, `back`, `signature-pose`. A subset is `requiredForRender` (at minimum `forward-fullbody` + `face-neutral`); the rest strengthen identity consistency. Real people are generated from a photo stack (never a painting-of-a-painting); fictional from a locked design.
- **setting** — the existing `contract`: `turnaround`, `emptyPlates[]`, `blueprint` (files) + `map`, `blocking`, `dressing` (descriptors). Unchanged; folded into the matrix vocabulary.
- **visual-metaphor** — `state` plates (the object across its argued states) + a locked master.
- **prop / motif** — `hero` + `detail` crops.

The matrix is declared per kind in the SPEC and encoded as a small table the engine reads, so `resolve_entity_assets` / setting resolution can report "locked vs under-referenced" against the kind's matrix, not just "file on disk."

**Engine change (additive, back-compatible):** the matrix is advisory-by-default at v0.4 (an entity with the pre-v0.4 shape still validates). A new `lockLevel(entity) -> "stub" | "partial" | "locked"` helper reports matrix completeness; renderers may require `locked`. Existing `requiredForRender` semantics are unchanged — the gate still hard-fails on a missing *required* sheet.

## Register / style as first-class identity (SPEC §11 extension)

A universe renders in one illustrative register. Encode it in `identity`:

```jsonc
"identity": {
  "...": "...",
  "register": {
    "name": "detailed comic book",                 // the named style
    "anchor": "reference/register/style-anchor.png",// content-neutral swatch, passed FIRST on every render
    "rejectedPoles": ["photoreal", "anime", "washed-out"]
  }
}
```

- `start-new-story-universe` defaults `register.name` to **"detailed comic book"** and runs a **style-lock** step: generate a content-neutral style anchor, get the operator's approval, save it to `reference/register/style-anchor.png`. Until locked, `register.anchor` is null and renderers warn.
- Every renderer and art-generation step passes `register.anchor` as the first reference and bakes `rejectedPoles` as negatives. This is what actually holds style across hundreds of renders (the NoF "register" per-story lesson, SPEC §4.3, promoted to a universe default with per-property override still allowed).

## The skill catalog

All generic, all in `agenticstory`. Two layers: **authoring** (deterministic, no image gen — absorb info → typed entity + reference-matrix slots + ready-to-run prompts) and **art** (generate → readback → lock). Gates cross-cut.

### Authoring skills (scaffold, don't generate)

- **`add-character`** — interview one character into canon. Real person: absorb story/role/wardrobe-eras/sensitive-list, collect a photo stack into `reference/<id>/photos/`, set the `realPerson` dossier + subject-approval gate. Fictional: a design brief. Always: run `casting-sweep` first (reuse-first), then scaffold the typed `character` entity with the **character reference matrix** slots (empty paths + a ready-to-run generation prompt per shot, each templated to pass the register anchor). Output: a committed entity + populated `reference/<id>/` + a prompts file. Art is NOT generated here.
- **`add-setting`** — scaffold a typed `setting` with its `contract` slots (turnaround/empty-plates/blueprint files + map/blocking/dressing descriptors) and ready-to-run plate prompts. Stays `status: "unlocked"` (correctly refused) until plates exist.
- **`add-visual-metaphor`** — scaffold a `visual-metaphor` with its state-plate slots + master.
- **`add-motif` / `add-prop`** — scaffold a `motif`/`prop` with hero + detail-crop slots.
- **`add-story`** — scaffold a `story`: `stub` (spine + logline) or `full` (features + beats + per-beat provenance + register). Runs `casting-sweep` over the beats' named entities and flags any not yet in canon (hand-off to `add-*`).
- **`add-relation`** — write a typed relation (`crossover-with` / `appears-in` / `derived-from` / `contradicts` / `supersedes`), so the graph stays queryable and contradictions are explicit.

### Art skill (generate + readback + lock)

- **`lock-references`** — take an entity's scaffolded matrix slots + prompts, generate each shot (image model, passing `register.anchor` + the entity's other locked shots for identity consistency), run `render-readback` per shot (crop-zoom each invariant, PASS/DEFECT), and lock only passers into the entity's `structured.sheets`. Real-subject entities stay subject-approval-gated until blessed. Idempotent (re-run regenerates only DEFECT/missing shots).

### Gates (cross-cutting, generalized from NoF)

- **`canon-resolve`** — resolve every named entity's refs (via the engine gate) before any render prompt is written; output locked sheet paths + invariants + the ref-pass/negative-bake block.
- **`render-readback`** — crop-zoom each invariant after every render; DEFECT ⇒ regenerate from scratch.
- **`voice-gate`** — voice-check text before lock, reading `identity.voice` term rules (capitalize / one-word) plus the universal rules (no em dashes, no filler, no "not X but Y").
- **`casting-sweep`** — reuse-first sweep of canon before naming a new entity.

### Renderers (generalized from NoF + identity)

- The picture-book renderer (`create-brand-os-picture-book`), `cover`, `book-platform`, `update-book` — generalized to read `identity` (mark, register, platform id, closing ornament) instead of hardcoding NoF. NoF's genre craft-canon (expectant-biography, visualized-epistle, expectant-future-present-fable) is extracted into `nof-universe` craft-canon records the renderer reads.

## Migration mapping (the nine NoF skills → framework)

| NoF skill | Becomes |
|---|---|
| `entity-register` | absorbed into `add-character` / `add-setting` / `add-visual-metaphor` / `add-motif` / `add-prop` |
| `casting-sweep` | generic `casting-sweep` (universe-param) |
| `canon-resolve` | generic `canon-resolve` (universe-param) |
| `render-readback` | generic `render-readback` (already ~generic) |
| `voice-gate` | generic `voice-gate` (reads `identity.voice`) |
| `picture-book` | generic renderer + `identity`; genres → `nof-universe` craft-canon records |
| `cover` | generic `cover` + `identity.mark` / `identity.register` |
| `book-platform` | generic `book-platform` + `identity.platformUniverseId` / theme / ornament |
| `update-book` | generic `update-book` (universe-param) |

End state: the `garysheng/nof` plugin is retired; NoF book-making runs on framework skills + `nof-universe` data.

## Phasing (each phase independently shippable + testable on AITX)

- **A. Reference-matrix standard** — SPEC §12 + engine `lockLevel()` + per-kind matrix table. Verify: engine tests green; `lockLevel` reports correctly on AITX's michael-daigler (partial) and a fully-locked entity.
- **B. Register/style in identity** — extend `identity`, scaffold, and `start-new-story-universe` (default comic-book + style-lock step); add `reference/register/`. Verify: fresh scaffold carries `register`; AITX gets its register block.
- **C. Atomic authoring skills** — `add-character/-setting/-visual-metaphor/-motif/-prop/-story/-relation` in the framework. Verify: `add-character` on **jake-oshea** and `add-setting` on an AITX venue produce valid canon + populated reference slots + prompts, `validate` green.
- **D. Art skill** — `lock-references`. Verify: lock jake-oshea's matrix (or a fictional test character) end-to-end; readback gates defects.
- **E. Migrate the nine NoF skills** — gates → generic; renderers → generic + identity; extract NoF genres to `nof-universe` craft-canon. Verify: an existing NoF book re-renders a spread through the generic path; `nof-universe` still A=0/B=0/C=0.
- **F. Retire the NoF plugin** — repoint everything; verify NoF + AITX both run entirely on framework skills + their own data.

Each phase is its own spec-slice → plan → implementation cycle; this document is the umbrella. Phase A+B share one plan (coupled: standard + identity + scaffold/engine/spec). C, D, E, F get their own plans as reached.

## Version

Bumps the framework to **v0.4** (reference-matrix standard + register-in-identity + skill catalog). `SPEC_VERSION` and the scaffold's emitted `conformsTo` move to `0.4`; the changelog records the three additions.

## Non-goals

- No new medium renderers (still picture-book only; the architecture permits more).
- No mass re-render of existing NoF books (they stay as shipped; only the *machinery* generalizes).
- No auto-generation inside authoring skills (art is the separate `lock-references` step, per the scaffold-then-generate decision).
- No change to the load-bearing gate's hard-fail semantics on missing required sheets (the matrix adds a `lockLevel` report; it does not weaken existing refusals).
- Not building a per-universe skill layer (framework skills + universe data only).
