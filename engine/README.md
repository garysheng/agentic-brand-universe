# Agentic Brand Universe — Engine v0

The first executable slice of the framework. Stdlib Python, no dependencies (same discipline as the
Nation of Fire resolver it generalizes). Implements the load-bearing layers of [`../SPEC.md`](../SPEC.md):
a typed **canon store**, **model** validation, and the **load-bearing reference** gate.

## Run it

```bash
cd engine

# tests (self-contained synthetic fixture — no content-repo dependency)
python3 -m unittest tests.test_engine -v

# CLI, pointed at the REAL Nation of Fire universe (which lives in its own repo)
NOF=../../nation-of-fire/universe
python3 -m agenticstory.cli list         "$NOF"
python3 -m agenticstory.cli validate     "$NOF"
python3 -m agenticstory.cli crossovers   "$NOF" jerry-man
python3 -m agenticstory.cli assert-story "$NOF" not-every-fire-is-holy
python3 -m agenticstory.cli assert-spread "$NOF" --characters anjali-sambalu,wally-boone
```

The engine is universe-agnostic: point it at any `<universe>/` dir (one with `universe.json` +
`canon/` + `stories/`). The framework repo ships only a synthetic test fixture, never a universe's
canon.

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
| `tests/fixtures/example/` | a self-contained synthetic universe for the tests (no content-repo dependency) |

## Next (not built yet)
- `new-story` / `new-entity` scaffolders (write-back proposals)
- the graduated craft-canon checks (mechanical hard-block; subjective judge-panel)
- migrate the standalone `nation-of-fire/universe/canon/resolve_gabr.py` to call this engine
