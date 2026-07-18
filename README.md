# Agentic Story

A first-principles framework for **compelling, agentically writable, composable, evolvable story
generation.**

> *A story is a query over an evolving canon, rendered into a medium, held to craft and to human
> taste.*

- **The spec:** [`SPEC.md`](./SPEC.md) — the architecture (five layers, primitives, invariants).
- **Home / docs:** `agenticstory.wiki` (Docusaurus, to be scaffolded from the spec).
- **Reference implementation:** the Nation of Fire universe (~15 illustrated books over one shared
  canon). Agentic Story is the act of naming the system those books already use.

## The five layers

1. **Canon** — the living universe: typed entities + relations, git-versioned (evolvable).
2. **Refs** — load-bearing resolver: every entity resolves to a real asset or the build fails.
3. **Story spec** — a medium-neutral composition: selects canon + beats + spine + provenance.
4. **Renderer** — projects canon + story into a medium (picture-book first).
5. **Quality** — taste gates × craft-canon × provenance, wired as steps, not memory.

## Status

- **Spec v0.2** ([`SPEC.md`](./SPEC.md)) — backtested against the real 24-book roster.
- **Engine v0** ([`engine/`](./engine/)) — RUNNING: typed canon store + model validation + the
  load-bearing reference gate, stdlib only, 11 tests green (against a self-contained fixture, no
  content-repo dependency).

**Framework ≠ content.** This repo is the framework; it holds no universe's canon. A universe is data
that conforms to the schema and lives in its **own** repo. The reference universe — **Nation of
Fire** — lives at `nation-of-fire/universe/` (typed `canon/entities`, `canon/relations`, `stories/`).
Validate it by pointing the engine at it:

```bash
python3 -m agenticstory.cli assert-story ../../nation-of-fire/nof-universe not-every-fire-is-holy
# resolves all 6 featured entities' real art on disk; blocks ONLY on the unlocked arena setting.
```

Next: `new-story` scaffolders, graduated craft-canon checks, migrate the standalone
`nation-of-fire/universe/canon/resolve_gabr.py` onto this engine, `agenticstory.wiki`.
