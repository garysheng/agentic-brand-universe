---
name: judge-slot
description: Run a judged invariant (SPEC 4.10) on one generated slot against an entity's locked golden, item by item, in a fresh context that never sees the plan that produced the slot. Returns PASS or DEFECT per invariant with evidence, and fails closed on unparseable output. Use after generating any slot bound to a canon entity with declared invariants.
---

# Judge Slot

The runner for `judged` invariants. Without it, a `judged` rule in a projection is a wish.

## Run

```bash
ANTHROPIC_API_KEY=... uv run --with anthropic python3 scripts/judge.py \
  --golden universe/reference/<entity>/master.png \
  --slot   out/spread-1.png \
  --invariants universe/canon/entities/<entity>.json
```

## Three rules it enforces, each earned

- **The judge never sees the plan.** It receives the golden, the slot, and the checklist. Nothing
  about intent. A maker shown its own reasoning defends it rather than looking at the pixels.
- **Itemized, not gestalt.** It checks each declared invariant separately. Asked "is this the same
  character?" a judge says yes while a specific declared property is plainly violated. Measured: on a
  locked mascot, ten of twelve invariants held and `translucent-holographic-digital-being` failed in
  every slot, rendering as opaque felt. The gestalt question passes that. The itemized one does not.
- **Against the golden, never slot-to-slot.** Slots drift together, because they inherit the same
  drift from the same master-to-generation step. Compared with each other they look consistent and
  are uniformly wrong. Consistency is not fidelity.

It **fails closed**: unparseable output is never a pass, and "cannot tell" is a DEFECT.
