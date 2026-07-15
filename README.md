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

v0.1 spec. Engine v0 = the Nation of Fire load-bearing GABR resolver
(`nation-of-fire/universe/canon/`), to be generalized here. First dogfood: *Not Every Fire Is Holy*.
