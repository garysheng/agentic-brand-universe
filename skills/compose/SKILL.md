---
name: compose
description: Run the composer (SPEC 4.10) over a work: resolve the form and its extends chain, refuse an undeliverable surface at PLAN time, then execute each slot with durable per-slot state, parking a defective slot and continuing rather than halting. Use to produce any artifact declared by a form.
---

# Compose

```
python3 scripts/compose.py <work.json>                    compose
python3 scripts/compose.py <work.json> --recipes-only      freeze recipes, no generation
python3 scripts/compose.py <work.json> --check-drift <dir> compare recipes to a baseline
```

The work names its `universe`, its `form`, and fills the form's slots.

## What it actually enforces

**`extends` resolution.** A form may fork another rather than copying it. The chain is merged
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
only PASS and SKIP resume; a defective slot is always re-attempted. Repair the work, re-run,
and pay only for the slot you fixed.

**The full slot loop.** A generated slot runs compile, generate, judge, repair. The compiler
assembles the prompt and ref list from the style pack and the locked goldens, so nothing load-bearing
is retyped. Locked masters are passed LAST, so identity rides on top of style. A judged DEFECT
re-rolls that slot up to `maxRolls`.

**UNJUDGED is not a pass.** When a slot carries judged invariants and no independent judge can be
reached, the slot is recorded UNJUDGED and the artifact emits incomplete. A gate you cannot run is not
a gate, and silently promoting an unverified slot to PASS is the exact failure the gate exists to
prevent. Inside a composer that has model access this never arises, because judging is another turn.

**Every slot writes its recipe before it generates.** `work/recipes/<slot>-<index>.json` records the
model, the exact prompt, the spec version the universe pinned, and every input by path AND by content
hash. It is written before generation, so a slot that then fails still says what it was about to make.
This is the composer paying its own provenance debt: it was the one pipeline that assembled prompts
from canon and kept none of what it sent. Nothing machine-specific enters a recipe (no work directory,
no output path), so a recipe is reproducible across machines.

**Drift is checked against recipes, not artifacts.** A generated image cannot be byte-reproduced, so
re-running the composer proves nothing about drift. The recipe can be reproduced exactly. Unchanged
canon plus an unchanged spec must assemble to an identical recipe.

- `--recipes-only` assembles and freezes every recipe. No image model is reached, so it is free and
  safe in CI. Commit `work/recipes/` as the baseline.
- `--check-drift <baseline>` re-assembles and compares. It reports three conditions, because
  collapsing them hides the interesting one: **DRIFT** (a digest changed, and it names the field),
  **UNFROZEN** (a recipe with no baseline, new work nobody froze), and **VANISHED** (a baseline slot
  the plan no longer produces, the one a naive check misses because nothing "changed"). Exit 1 on any.

A golden re-locked in place under the same filename is the drift a path-only check cannot see, and it
is the likeliest kind. The content hash catches it.

## Slot states

| State | Meaning |
|---|---|
| PASS | produced and, where required, judged clean |
| SKIP | nothing to do for this slot in this run |
| DEFECT | failed its gate, or exhausted its rolls. Parked; the run continues |
| UNJUDGED | produced, but its judged invariants could not be checked. Not a pass |

## Exit codes

| Code | Meaning |
|---|---|
| 0 | every slot passed (compose), or no drift (`--check-drift`), or recipes written (`--recipes-only`) |
| 1 | emitted incomplete; defective or unjudged slots listed. Under `--check-drift`: drift found |
| 2 | refused at plan time; nothing was generated. Under the recipe modes: assembly failed |
| 3 | slots await an independent judge; nothing is regenerated on re-run |
