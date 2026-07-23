---
name: judge-slot
description: Judge one generated slot against an entity's locked golden, item by item over its declared invariants, in a context that has NOT been told how the slot was made. A ROLE, not a service: fill it with a subagent, a fresh session, a human, or simply another turn inside the composer. Returns PASS or DEFECT per invariant with evidence, and fails closed. Use after generating any slot bound to a canon entity that declares invariants.
---

# Judge Slot

The runner for `judged` invariants (SPEC §4.10). Without it, a `judged` rule is a wish.

## This is a role, not a service

The load-bearing property is **the judge has not seen the plan**. That is a fact about context, not
about transport. Anything that can look at two images with a clean context can fill the role:

| Filled by | When |
|---|---|
| **Another turn inside the composer** | The production case. The agent already has model access, so a verification step scoped to golden + slot + checklist is a message, not infrastructure. **This costs nothing extra.** |
| A subagent or a fresh session | Interactive work, where the maker is still holding the plan |
| A person | Cheapest of all, and the most reliable. A human who never saw the intent spots drift in one glance |
| `scripts/judge.py` | Only when judging out-of-band, outside any agent runtime |

The script is the LEAST interesting implementation and exists for completeness. Reaching for it first
is the mistake this file was rewritten to correct: it invents an external dependency for something the
runtime already does.

## The protocol

Give the judge exactly three things, and nothing else:

1. The **locked golden** for the entity.
2. The **generated slot**.
3. The entity's **declared invariants**, verbatim, as a checklist.

Withhold the prompt, the intent, the plan, and what anyone hoped the slot would look like.

Ask for a verdict **per invariant**, each with one sentence of evidence describing what is visible in
the slot versus the golden.

## Three rules, each earned

- **The judge never sees the plan.** A maker shown its own reasoning defends it instead of inspecting
  the pixels. A three-element graphic once shipped with one element missing its defining feature
  because the maker read its own intent; an observer with no access to the plan caught it instantly.
- **Itemized, never gestalt.** Check each declared invariant separately. Asked "is this the same
  character?" a judge says yes while a declared property is plainly violated. Measured on a locked
  mascot: ten of twelve invariants held, and `translucent-holographic-digital-being` failed in every
  slot, rendering as opaque felt. The gestalt question passes that. The itemized one does not.
- **Against the golden, never slot-to-slot.** Slots drift together, inheriting the same drift from the
  same master-to-generation step. Compared with each other they look consistent and are uniformly
  wrong. **Consistency is not fidelity.**

**Fail closed.** Unparseable output is not a pass, and "I cannot tell" is a DEFECT, never a PASS.
