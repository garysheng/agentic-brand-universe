---
name: add-relation
description: Record ONE typed relation between two ids in an Agentic Story universe's canon graph (`crossover-with`, `appears-in`, `derived-from`, `contradicts`, `supersedes`) as a `from`/`rel`/`to`/`story`/`note` record written to `canon/relations/`. Keeps the graph queryable (every crossover, every story touching a doctrine) and makes contradictions and supersessions explicit records instead of silent edits to history. Art is NOT touched by this skill at all. Use whenever two canon entities, or an entity and a story, need a recorded relationship. Generic and universe-parameterized: pass the target universe.
---

# Add Relation

One typed relation, into a universe's canon graph, as a record written directly to `canon/relations/`. This is pure bookkeeping: no entity scaffolding, no prose, no art. It ends with a validated record the graph queries can read (`agenticstory crossovers <id>`, `agenticstory relations <id>`).

## Inputs
- The target universe (a path containing `universe.json`). Read its `canon/entities/` and `stories/` so both sides of the relation can be confirmed.
- The two ids being related, and which of the five relation types actually applies.

## Procedure

1. **Determine the relation type.** Pick exactly one:
   - `crossover-with`: two entities (usually characters) share a scene or property together.
   - `appears-in`: an entity features in a specific story (`to` is a story id).
   - `derived-from`: this entity's design or lore was built out of another entity.
   - `contradicts`: new canon conflicts with old canon. Record the conflict explicitly rather than silently editing the older entity; this is how testimony-over-prediction stays honest and history stays visible.
   - `supersedes`: new canon replaces old canon as the going-forward truth (stronger than `contradicts`: this one wins going forward).
2. **Confirm both sides resolve.** `from` and `to` must each be a known id: an entity in `canon/entities/`, or (for `appears-in`, and wherever a story is the natural target) a story in `stories/`. If either side does not exist yet, stop and run the matching `add-*` skill first (`add-character`, `add-setting`, `add-story`, etc.) rather than recording a relation to a name that isn't canon.
3. **Write the relation.** Add a file to `canon/relations/` (a new file `canon/relations/<from>--<rel>--<to>.json`, or append to an existing relations file that holds a list) with:
   ```jsonc
   { "from": "<id>", "rel": "crossover-with", "to": "<id>", "story": "<story-id-or-null>", "note": "…" }
   ```
   `story`: which story established or witnessed this relation (nullable if it is a general canon fact). `note`: the one-line reason, load-bearing for `contradicts`/`supersedes` (what changed and why, so the record explains itself without needing the git history dug up).
4. **Validate + commit.** `agenticstory validate <universe>` stays green: an unresolved `from`/`to` is a hard error ("relation references unknown id"). Commit the relation file. Spot-check with `agenticstory crossovers <universe> <id>` or `agenticstory relations <universe> <id>` that the new record reads back correctly.

## Gates honored
- **Both sides must resolve**: a relation never points at a name that isn't already real canon.
- **Contradictions are explicit**: `contradicts`/`supersedes` are recorded relations, never silent edits to the older entity.
- **The graph stays queryable**: every relation is a typed, git-versioned record the existing `crossovers`/`relations` CLI commands can read.
- **No art here**: this skill never touches `reference/` or an image model.

## Not this skill
- Creating either side of the relation: the matching `add-*` skill (`add-character`, `add-setting`, `add-visual-metaphor`, `add-motif`, `add-prop`, `add-story`).
- Generating or locking reference art: `shoot-references`.
- Rendering a story into a medium: the renderer.
