---
name: casting-sweep
description: Before naming any NEW character, setting, or motif in a story, sweep the universe's canon for an existing entity that fits the role natively, and emit a casting table (each role: reuse an entity id, or NEW plus a one-line justification). Reuse wins by default: it saves the whole reference-matrix build and every reuse is a crossover receipt. Generic and universe-parameterized: pass the target universe.
---

# Casting Sweep

The reuse-first gate that runs before a manuscript names anyone. It stops the universe from growing redundant entities (two characters that are really one) and turns every reuse into a crossover. Run it during story brainstorming, before the draft commits to names.

## Inputs
- The target universe (a path with `universe.json`).
- The roles the draft needs (the protagonist, a mentor, a place, a recurring object).

## Procedure
1. **Sweep the canon.** Read `canon/entities/` (and any CANON.md) and index the existing entities by kind and role.
2. **Match each role.** For each role the draft needs, find the existing entity that fits it natively (same kind, compatible description, right era). Prefer reuse: a mentor role that an existing mentor entity can play is a reuse, not a new character.
3. **Emit the casting table.** One row per role: `role -> reused-entity-id`, OR `role -> NEW` with a one-sentence justification for why no existing entity fits. Reuse is the default; a NEW entity must earn its place against the swept canon.
4. **Hand off the NEWs.** For each NEW row, hand off to the matching authoring skill (`add-character`, `add-setting`, `add-visual-metaphor`, `add-motif`, `add-prop`).

## Gates honored
- **Reuse-first:** never invent an entity an existing one already covers. Every reuse is a crossover receipt.

## Not this skill
- Creating the NEW entities (that is the `add-*` skills).
- Writing the story (that is `add-story`).
