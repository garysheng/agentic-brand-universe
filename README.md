# Agentic Brand Universe

A first-principles standard for a **brand as version-controlled canon plus golden assets — the
cartridge format** — agentically writable, composable, and evolvable, that any deliverable is
rendered from.

> *A deliverable is a query over an evolving canon, rendered into a medium, held to craft and to human
> taste.*

- **The spec:** [`SPEC.md`](./SPEC.md) — the cartridge architecture (six layers, primitives, invariants).
- **The architecture:** [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) — how the layers fit, what the
  linter checks, and why the runtime is Managed Agents. Diagrams included, all machine-emitted.
- **The engine spec:** [`BRAND-OS-SPEC.md`](./BRAND-OS-SPEC.md) — the Agentic Brand OS (the console/runtime that loads a cartridge and generates on-brand deliverables). **v0.1, early draft.**
- **Home / docs:** `agenticbranduniverse.com` (the canonical home of the standard).
- **Reference implementations:** the Nation of Fire universe (~15 illustrated books over one shared
  canon), and [`hyperagentic-age`](https://github.com/garysheng/hyperagentic-age), a public universe
  declaring seven projections across image, text, and audio.

## The six layers

1. **Canon** — the living universe: typed entities + relations, git-versioned (evolvable).
2. **Goldens** — locked reference assets: the visual answer of record, passed rather than described.
3. **Projection** — the typed contract for a KIND of deliverable (surface, requires, slots, invariants).
4. **Composition** — ONE instance of a projection, binding actual canon ids to its requirements.
5. **Composer** — the agentic layer: plans, compiles, generates, and repairs, answering to a gate.
6. **Quality** — taste gates × craft-canon × provenance, wired as steps, not memory.

Layers 3 and 4 arrived in v0.6 and are what let the standard express a flyer, a diagram, or a
thank-you card rather than only a story. See [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

## Status

- **Spec v0.6** ([`SPEC.md`](./SPEC.md)) — the projection release. Backtested against the 24-property
  roster, then re-proven against seven deliberately unlike deliverables.
- **Engine v0** ([`engine/`](./engine/)) — RUNNING: typed canon store + model validation + the
  load-bearing reference gate, stdlib only, 34 tests green (against a self-contained fixture, no
  content-repo dependency).
- **Tests: 127 green** across the engine and seven skill suites. `./run-tests.sh` needs no API key,
  no network, and generates nothing. It discovers test files rather than listing them, so a new
  test file cannot sit unrun.

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

## License

MIT — see [`LICENSE`](./LICENSE). The Agentic Brand Universe is an open standard: fork it, build on it, run your own Brand OS.
