---
name: create-lookbook
description: Scaffold a Lookbook (SPEC §4.7.1) — a portable folder (lookbook.json + refs/) that defines a curated but intentionally VARIED visual vocabulary (a wardrobe/fashion, a range of building silhouettes, a set of faces), the complement of a Style Pack. Use when a recurring aspect must stay on-aesthetic yet DIFFER per instance, and modeling it as a motif/prop (which force sameness) or a Style Pack (a render medium) is wrong. It writes 4-12 varied exemplars, a varietyRule (the "vary, never clone" instruction), and a read-back gate that checks for variety. Consumed by on-brand-image via --lookbook, and bound to a universe through a craft-canon register-rule that names it. Invoke via create-lookbook, "make a lookbook", "build a fashion/wardrobe aesthetic", or when you catch yourself wanting variety from a primitive that enforces sameness.
---

# Create Lookbook

The Style Pack answers "make more that look like this ONE look." The **Lookbook** answers "make more that belong to this FAMILY but each differ" — a wardrobe, a fashion, a range of homes, a crowd of faces. It is the primitive for curated **variety**, and it exists because the alternatives are wrong: a `motif`/`prop` locks a thing to render identically (the exact opposite of fashion), and a Style Pack is a rendering medium, not subject content. Improvising a folder of "clothing refs" with no manifest is the drift this skill kills.

## When to reach for a Lookbook vs its neighbors

- **One look, cloned every render** → Style Pack (`create-style-pack`).
- **One thing, identical every render** → `motif` / `prop` (`add-motif` / `add-prop`).
- **A family that must VARY per instance** → **Lookbook** (this).
- **The law that governs it** → a `craft-canon` register-rule that names the lookbook (e.g. rule `godly-aligned-dress` binds lookbook `christofuturist-fashion`).

## Inputs

- **4-12 VARIED exemplars.** Range is the whole point — a lookbook of near-identical images teaches uniformity, which is the failure it exists to prevent. Import blessed ones and/or generate a spread that deliberately spans body types, cultures, colors, silhouettes.
- **The aesthetic** — one line naming the vocabulary ("modest, dignified, individual, timeless-yet-modern Kingdom dress").
- **The varietyRule** — the instruction the renderer applies on EVERY use ("dress each person differently, drawn from this range; never a uniform, never two people matching").
- **Gate** — read-back assertions that check VARIETY in the output ("no two people dressed alike", "not a single palette across the crowd"). A lookbook with no variety gate silently drifts back to a uniform.

## Procedure

1. **Gather + bless the exemplars** (4-12, deliberately varied). Import + generate as needed.
2. **Scaffold:**
   ```bash
   python3 ~/.../skills/create-lookbook/scripts/scaffold.py \
     --dir <where>/reference/lookbook/<id> --id <id> --name "<Name>" \
     --ref <a.png> --ref <b.png> [...] \
     --aesthetic "<one line>" \
     --variety-rule "<the vary-never-clone instruction>" \
     --gate "<variety assertion 1>" --gate "<...>" [...] \
     --min-refs 3
   ```
   It copies every exemplar into `<lookbook>/refs/`, writes `lookbook.json`, and fails loudly on <4 or >12 refs or a missing gate.
3. **Bind it to the universe (optional but recommended):** add a `craft-canon` register-rule whose `rules` name this lookbook, so every renderer honors it (`dress per lookbook <id>`).
4. **Prove it varies.** Render one crowded scene with `on-brand-image --lookbook <path>`; read back against the variety gate. If the crowd is uniform, the varietyRule is too weak or the exemplars too similar — widen the range, tighten the rule.

## How it is consumed

`on-brand-image` (or any renderer) takes `--lookbook <path>`: it samples 2-4 of the lookbook's refs, prepends the `varietyRule` to the prompt, and adds the lookbook's `gate` assertions to the read-back. The lookbook rides ALONGSIDE the Style Pack (the pack sets the render medium; the lookbook sets the varied subject vocabulary).

## Definition of done

- `<lookbook>/lookbook.json` + `refs/*` exist; 4-12 exemplars resolve inside the folder; a real `varietyRule` and variety gate are set.
- One `on-brand-image --lookbook` render passed its variety gate (the crowd is not a uniform).
- A craft-canon register-rule (if the universe wants it enforced everywhere) names the lookbook.
- No caller hand-lists clothing refs: they pass the lookbook.
