---
title: "Catalog one brand piece or one no-go, so a ruling is read by a gate instead of remembered"
id: HDSOP-ABU-039
version: 0.1
skill: add-piece-or-no-go
doc_status: drafting
tags: [authoring, canon, craft, brand, gate]
frequency: "whenever a human rules on a brand detail, and on every harvest of scattered refusals"
est_time_per_run: "10 min"
automation_potential: "high"
related_skills: [lint-universe, evolve-abu, add-relation]
related_workflows: []
concepts: [canon, craft-canon, kit, piece, no-go, supersession]
---

# Purpose

The brand's reusable parts and its refusals live in one typed record, with who decided each, when
and in what words, so `validate` can hold them to live canon and `abu check-kit` can refuse a
surface that uses a refused shape.

# When to use (Trigger)

A human rules on a brand detail ("I don't like it when you...", "use this instead"), a refusal is
found scattered in rule prose or a project STATE file, or the same CSS recipe for a brand part is
about to be hand-written a second time.

# Inputs / Prerequisites

- The target universe, and `abu kit <universe>` read first.
- The ruling verbatim with its date, or the exact canon line it was lifted from.

# Steps

1. Find or create the kit record (`canon/craft/brand-kit.json`, kind `kit`).
2. Add the piece (pointer if canon already defines it, recipe if it is new) or the no-go (refuses,
   why, instead, decided, source).
3. If it contradicts a live canon line, rewrite the line to point at the piece, keep the old words
   in a supersession note, and add `supersedes` to the no-go.
4. Add a `detect` pattern when the shape is mechanical; test it on the shipped shape and the
   replacement.
5. `abu validate`, the universe's own gate, then `abu check-kit` over every governed surface.
6. Commit by explicit path. List outside hits for their owners; do not edit them.

# Outputs

One validated kit entry, any superseded canon line updated with its history kept, and a list of
file:line places outside the universe that still use the refused shape.

# Failure modes

- A second id for a part the kit already has (two sources of truth).
- A ruling with no verbatim (an opinion the next agent overrides).
- Deleting the superseded words (history lost; the record can no longer be reasoned with).
- A detector that also fires on the replacement (a gate people learn to skip).
