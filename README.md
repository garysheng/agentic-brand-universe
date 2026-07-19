# Agentic Brand Universe

A first-principles standard for a **brand as version-controlled canon plus golden assets — the
cartridge format** — agentically writable, composable, and evolvable, that any deliverable is
rendered from.

> *A deliverable is a query over an evolving canon, rendered into a medium, held to craft and to human
> taste.*

- **The spec:** [`SPEC.md`](./SPEC.md) — the cartridge architecture (five layers, primitives, invariants).
- **Home / docs:** `agenticbranduniverse.com` (the canonical home of the standard).
- **Reference implementation:** the Nation of Fire universe (~15 illustrated books over one shared
  canon). The standard is the act of naming the system those books already use. An **Agentic Story**
  is one projection of a universe — the picture-book / comic deliverable.

## The five layers

1. **Canon** — the living universe: typed entities + relations, git-versioned (evolvable).
2. **Refs** — load-bearing resolver: every entity resolves to a real asset or the build fails.
3. **Story spec** — a medium-neutral composition: selects canon + beats + spine + provenance.
4. **Renderer** — projects canon + composition into a medium (picture-book first).
5. **Quality** — taste gates × craft-canon × provenance, wired as steps, not memory.

## Status

- **Spec v0.5** ([`SPEC.md`](./SPEC.md)) — backtested against the real 24-property roster.
- **Engine v0** ([`engine/`](./engine/)) — RUNNING: typed canon store + model validation + the
  load-bearing reference gate, stdlib only, 11 tests green (against a self-contained fixture, no
  content-repo dependency).

**Framework ≠ content.** This repo is the framework; it holds no universe's canon. A universe is data
that conforms to the schema and lives in its **own** repo. The reference universe — **Nation of
Fire** — lives at `nof-universe/` (typed `canon/entities`, `canon/relations`, `stories/`).
Validate it by pointing the engine at it:

```bash
python3 -m agenticstory.cli assert-story ../../nation-of-fire/nof-universe not-every-fire-is-holy
# resolves all 6 featured entities' real art on disk; blocks ONLY on the unlocked arena setting.
```

Next: `new-story` scaffolders, graduated craft-canon checks, migrate the standalone
`nof-universe/canon/resolve_gabr.py` onto this engine, `agenticbranduniverse.com`.
