# Agentic Story — Engine v0

The first executable slice of the framework. Stdlib Python, no dependencies (same discipline as the
Nation of Fire resolver it generalizes). Implements the load-bearing layers of [`../SPEC.md`](../SPEC.md):
a typed **canon store**, **model** validation, and the **load-bearing reference** gate.

## Run it

```bash
cd engine

# tests (runs against the real Nation of Fire reference universe)
python3 -m unittest tests.test_engine -v

# CLI, on the reference universe
python3 -m agenticstory.cli list         ../universes/nation-of-fire
python3 -m agenticstory.cli validate     ../universes/nation-of-fire
python3 -m agenticstory.cli crossovers   ../universes/nation-of-fire jerry-man
python3 -m agenticstory.cli assert-story ../universes/nation-of-fire not-every-fire-is-holy
python3 -m agenticstory.cli assert-spread ../universes/nation-of-fire --characters anjali-sambalu,wally-boone
```

## What it proves

`assert-story not-every-fire-is-holy` resolves **all six** featured entities' locked art on real disk
and blocks on **exactly one** thing — the `the-arena` setting is `unlocked` (its turnaround /
blueprint / $MAP / blocking / dressing contract is null). That is a reference being *load-bearing*:
the story cannot render until the arena is really locked, and the engine says so precisely instead of
letting the book drift.

## Shape

| File | Owns |
| --- | --- |
| `agenticstory/model.py` | Entity / Relation / StorySpec + structural validation (no filesystem) |
| `agenticstory/store.py` | CanonStore: load a universe dir, index + graph queries |
| `agenticstory/refs.py` | load-bearing resolution: `assert_story`, `assert_spread`, `resolve_*` |
| `agenticstory/cli.py` | `validate · list · crossovers · assert-story · assert-spread` (non-zero exit gates CI/gen) |
| `universes/nation-of-fire/` | the reference-implementation seed: real entities/relations/story pointing at real art |

## Next (not built yet)
- `new-story` / `new-entity` scaffolders (write-back proposals)
- the graduated craft-canon checks (mechanical hard-block; subjective judge-panel)
- migrate the standalone `nation-of-fire/universe/canon/resolve_gabr.py` to call this engine
