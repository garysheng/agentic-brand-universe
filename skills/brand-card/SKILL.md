---
name: brand-card
description: Emit a two-panel brand card (share card, thank-you card, simple flyer) deterministically: a code-laid text panel beside a pre-generated art panel. Use when a form has a `deterministic` slot for card-shaped layout. Refuses art whose aspect does not match the panel, because cropping a square into a tall panel clips exactly the edges the composition needed.
---

# Brand Card

The deterministic emitter behind card-shaped forms. It exists because a slot typed
`deterministic` with no emitter is unspecified rather than deterministic (SPEC §4.8).

## Run

`python3 scripts/card.py <spec.json>` where the spec carries `width`, `height`, `split`, `art`,
`out`, and the text fields (`eyebrow`, `headline`, `body`, `signoff`).

## The two gates it enforces

- **Art aspect must match the panel** within tolerance. Generate the art AT the panel's ratio. If
  this fails, fix the *geometry or the generation*, never by cropping: a square forced into a tall
  panel loses the wings, the hands, the outstretched arms, which is the part that carried the image.
- **Text must not overflow its panel.** Checked against a floor, so a long headline fails loudly
  instead of running under the fold.

## The trap this was built from

A card declared a 1200x1200 surface with a two-thirds text split. That makes the art panel 400x1200,
an aspect of 0.333, and **no image generator emits 0.333**. The contract was internally valid and
undeliverable. Check that a form's surface is feasible against its generators' producible
aspects BEFORE composing, not an hour in.
