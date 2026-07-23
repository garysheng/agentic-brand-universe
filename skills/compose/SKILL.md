---
name: compose
description: Run the composer (SPEC 4.10) over a composition: resolve the projection and its extends chain, refuse an undeliverable surface at PLAN time, then execute each slot with durable per-slot state, parking a defective slot and continuing rather than halting. Use to produce any artifact declared by a projection.
---

# Compose

`python3 scripts/compose.py <composition.json>`

The composition names its `universe`, its `projection`, and fills the projection's slots.

## What it actually enforces

**`extends` resolution.** A projection may fork another rather than copying it. The chain is merged
key-wise, child over parent, and printed so the resolution is never implicit.

**Plan-time feasibility refusal.** Before generating anything, every generated slot's required aspect
is checked against the capability's `producibleAspects`. A contract can be internally valid and
physically undeliverable: a 1200x1200 card with a two-thirds split needs an art panel at aspect 0.333,
and no image generator emits 0.333. Exit code 2, nothing generated, nothing cropped to fit.

**Durable per-slot state.** Each slot writes a state record. A re-run resumes what already passed
instead of recomputing it. This is the requirement that makes the runtime argument concrete rather
than rhetorical.

**Park and continue.** A slot that fails its gate is marked DEFECT, the remaining slots still run, and
the artifact emits INCOMPLETE with a per-slot report. Exit code 1. One defect costs one slot.

**Retry defects, resume successes.** Resuming a DEFECT would freeze the artifact broken forever, so
only PASS and SKIP resume; a defective slot is always re-attempted. Repair the composition, re-run,
and pay only for the slot you fixed.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every slot passed |
| 1 | emitted incomplete; defective slots listed |
| 2 | refused at plan time; nothing was generated |
