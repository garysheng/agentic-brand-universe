---
name: create-style-pack
description: Scaffold a Style Pack (SPEC §4.7) — a portable folder (pack.json + refs/) that defines ONE look and is consumable by on-brand-image with no universe. Use when you have a set of blessed images that share a look and want to make more that match (a register's paint-language extracted into a reusable artifact), or when a universe's register should source its anchor + rejected poles from a shared pack. Copies the refs INTO the pack (self-contained), writes the manifest with a load-bearing read-back gate, and validates. Pairs with on-brand-image (which consumes the pack) and shoot-references (locked masters passed alongside). Invoke via create-style-pack, "make a style pack", "extract this look into a pack", or as the fix when you catch yourself generating on-brand images with no pack (a look with no Style Pack is the gap evolve-agentic-story names).
---

# Create Style Pack

Turn a blessed set of images into a **Style Pack** (SPEC §4.7): `pack.json` + `refs/`. This is the artifact `on-brand-image` consumes, and the thing to build the moment you notice you are generating "in a look" by re-typing the same style words each time. The look lives in the **references**, not the wording; the pack makes that reusable and gated.

## Inputs you need first

- **3-8 blessed reference images** that share the look. Fewer than 3 and the model has too little to lock onto; more than 8 and you are curating, not defining. Prefer at least one **content-neutral** image as the `anchor` (a swatch of palette + light + finish with no subject), because a reference outranks negative words and a busy anchor leaks its content into every render (the Nation of Fire lesson: a style anchor must never depict a canon character).
- **The style line** — one sentence naming the look (medium, line, fills, light, finish).
- **Palette** — ground / fill / line colors (hex).
- **Rejected poles** — the looks to bake as negatives (what this is NOT).
- **Gate assertions** — the read-back checklist `on-brand-image` verifies against the pixels. This is the load-bearing half; a pack without a gate is a mood board, and the scaffolder refuses to write one.

## Procedure

1. **Gather + bless the refs.** Only images a human approved. If the anchor is not content-neutral, generate a content-neutral swatch first (palette + light + finish, no subject) and use that as `anchor`.
2. **Scaffold:**
   ```bash
   python3 ~/.../skills/create-style-pack/scripts/scaffold.py \
     --dir <where>/reference/style/<pack-id> --id <pack-id> --name "<Name>" \
     --anchor <anchor.png> --ref <a.png> --ref <b.png> [...] \
     --style-line "<one line>" \
     --palette-ground '#..,#..' [--palette-fill '#..'] [--palette-line '#..'] \
     --reject painterly --reject photoreal [...] \
     --gate "<assertion 1>" --gate "<assertion 2>" [...] \
     --max-elements 5
   ```
   It copies every ref INTO `<pack>/refs/` (self-contained, §3a), writes `pack.json`, and fails loudly if a ref is missing, the count is out of 3-8, the anchor is not among the refs, or there is no gate.
3. **Sanity-read the manifest.** Confirm `anchor` is the content-neutral one and listed first; the gate reads like checkable pixel assertions ("ground is one flat X", "no text"), not vibes.
4. **Prove it round-trips.** Run `on-brand-image` once against the new pack with a simple scene; read back against the gate. If a defect slips the gate, the gate is too loose — tighten an assertion and note it.
5. **(Optional) Wire a universe to it.** If a universe should render its canon in this look, set `identity.register.stylePack: "<pack-id-or-relative-path>"` (SPEC §4.7 full mode) so canon renders and one-off images share ONE definition of the look. Registers that inline their anchor stay valid; this is additive.

## Where the pack lives

Standalone anywhere, OR inside a universe at `reference/style/<pack-id>/`. It resolves every ref within its own folder, so it is copyable. `on-brand-image` only ever needs the pack path.

## Definition of done

- `<pack>/pack.json` + `<pack>/refs/*` exist; every ref resolves inside the folder; the anchor is content-neutral and first; the gate has real read-back assertions.
- One `on-brand-image` round-trip passed its own gate.
- No caller re-types the style words: they pass the pack.
