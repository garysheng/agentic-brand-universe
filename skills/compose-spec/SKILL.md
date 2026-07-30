---
name: compose-spec
description: Scaffold and RE-SYNC a book's render-spec from its StorySpec, filling everything canon determines, enumerating every legal choice canon constrains, and never overwriting authored scene text. Use when starting a new book's render-spec, after adding or removing a beat, after shooting a new plate or wardrobe look, or whenever you catch yourself hand-writing a per-book authoring script. Trigger phrases: "scaffold the render-spec", "re-sync the spec", "compose-spec", "the spec is out of date with the story", "I added a beat".
---

# Compose Spec

A story already knows its beats, their locations, and who is in them. A render-spec restates
all of it by hand, so every book grows a bespoke authoring script, and **those scripts rot**:
the spec gets hand-edited afterwards, the script does not, and re-running it silently reverts
the edits. Earned 2026-07-30 in nation-of-fire, where the stale generator still carried an
identity-overriding `bake` and crowd prose that six hours of fixes had removed. Re-running it
would have undone the lot.

**This is not a spec generator.** It fills what canon DETERMINES, enumerates what canon merely
CONSTRAINS, and never touches what a human AUTHORED.

| class | fields | on re-run |
|---|---|---|
| derived | `id`, `setting`, cast membership, preamble, size | refreshed every run |
| chosen | `plate`, `pose`, `look`, `bake` | enumerated, carried forward, never chosen for you |
| authored | `scene`, `negatives`, flags | never modified without `--force` |

```bash
python3 scripts/compose_spec.py <universe> <story-id> --book <folder> --out render-spec.json
```

## Why the enumeration is the point

A `null` plate beside its legal values is **visible**. A missing wardrobe pose is invisible,
which is exactly how Selah went 20 spreads with her clothes unpinned. The scaffold prints
what still needs a human:

```
  spread-02: setting 'the-teaching-room' has no plate chosen
             (available: master, chairsCloseUp, fromTheChairs, fromTheChairsFull)
  spread-02: 'selah' has 7 poses and none selected (ql-shirt-trousers, ql-gown, ...)
  spread-02: scene is empty and must be authored
```

## Merge rules

- **New beat** appends a spread; every existing authored scene is untouched.
- **A spread not in the story** (a cover, a closing plate, a beat you removed) is KEPT and
  reported, never deleted.
- **A cast member in the spec but not in the beat** is kept and reported, on the assumption
  the author cast them deliberately.
- `--force` is the only way to lose authored text, and it says so.

## Definition of done

- The spec is a build artifact you can re-run at any time without fear.
- No per-book authoring script survives the session. If one does, it will rot.
