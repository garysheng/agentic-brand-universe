---
name: lint-universe
description: Lint a brand universe. Static checks over the universe and everything it declares (style packs, projections, slots, emitters, generators, goldens, invariants, provider quirks) with no generation, no API calls, and no cost. Catches the failure classes that were previously only discovered by running a composition, sometimes an hour into one. Run it before composing anything.
---

# Brand Universe Linter

`python3 scripts/lint.py <universe-dir>`

Exit **0** clean, **1** warnings only, **2** errors.

## Why this exists

Every check here corresponds to a failure that actually shipped and was only caught by executing a
composition. A contract can be internally valid, reviewed by two people, and undeliverable. The linter
moves those discoveries to the cheapest possible moment.

On its first run against the reference universe it found a generated slot with **no generator declared
for it**, which had been silently parking every cover as a defect for an entire session.

## What it checks

**Universe.** `universe.json` parses. `identity.register.anchor` is set and resolves. A null anchor
means the style is not locked and generation should refuse.

**The spec pin.** `spec.version` is declared (error if absent: an unpinned universe conforms to nothing
anyone can check, and cannot detect its own drift), and it matches the engine's `SPEC_VERSION` (warns
if the universe is behind). This catches the class where three surfaces each give a consistent but
different answer: on 2026-07-24 `SPEC.md` said v0.6, the engine constant said 0.4.1, and the reference
universe pinned 0.5, and every one was internally consistent. Consistency is not truth; the pin is now
verified against the engine rather than trusted.

**Style packs.** `pack.json` parses; the anchor and every ref resolve on disk; a `gate` exists, because
a pack without one is a mood board; `styleLine` exists. Warns under three refs.

**Projections.**
- A `deterministic` slot names an `emitter`, that emitter is known, and its script exists on disk.
- A `generated` slot has a generator that declares `for` it.
- `surface` is FEASIBLE: the slot's required aspect is within tolerance of the provider's
  `producibleAspects`. This is the 0.333 class, where the contract is coherent and no model can make it.
- `extends` resolves to a projection that exists.
- Every invariant is typed `computed` or `judged`. A projection with no invariants is flagged: nothing
  can fail, so nothing is checked.

**Goldens.** Every sheet named in an entity's `requiredForRender` resolves to a file
(`GOLDEN-UNDECLARED`, `GOLDEN-MISSING`). And every LOCKED sheet, required or not, carries a
`<golden>.recipe.json` provenance sidecar:
- `GOLDEN-NO-RECIPE` (warn): the approval recorded only a path, so nothing can say what it was
  approved against. It is un-auditable and cannot enter a divergence check. Re-lock with
  `lock-shot --recipe`.
- `GOLDEN-STALE` / `GOLDEN-INPUT-GONE` (warn): the sidecar recorded each input's bytes at approval;
  one of them has since changed or vanished. The golden was blessed against an input that no longer
  exists, and no human is looking. This is the free half of the divergence loop: the whole approved
  corpus audited statically at zero cost.

A golden is Gary's approved answer of record. These checks make the golden library an auditable eval
set rather than a pile of images with no memory of how they were judged.

**Quirks.** The provider registry parses, and a pinned provider that the registry has never heard of is
flagged, because it will silently inherit no quirks.

## Where it belongs

Before `compose`, always. It is free, it is instant, and the alternative is finding the same problem
after paying for generation.
