---
name: compose-strip
description: Compose a STRIP, two to four panels (three by default) assembled into ONE image, from a spec file instead of a prose brief. Each panel names its world, its canon entities, its refs and its scene; the composer renders each roll through on-brand-image's entity route, runs the binding check, and records the agent's read-back verdict per roll (a DEFECT needs a reason, the reject is moved into panels/rejected/ with it, and its counter binds every later roll of that panel), capped at the first roll plus four re-rolls. Then it composes in CODE (panel widths, cream gutters, no drawn borders, no text) and writes ONE composite recipe that a wiki's provenance gate accepts by construction (every panel's exact prompt, every ref, model, provider, timestamp, the asset path, and each panel's full recipe under panelRecipes), refusing to write one that would not pass. Optionally exports the wiki's WebP copy with the recipe restated for where it will sit, and stages the result on the works board, whose re-roll tap then reopens the right panel instead of re-rolling the composite. Use when a hero, a header or any piece is a sequence of beats rather than one frame, when someone says "make a strip", "three-panel hero", "compose these panels", or when you catch yourself writing a compose.py beside a work. NOT for a single image (on-brand-image) and NOT for a picture book spread (compose-spread).
---

# Compose a strip

A strip is a spec and five verbs. Everything a machine can check, the script does; the one thing
it cannot do is look, and `judge` is where your look is recorded.

**Why it exists.** Four wiki-hero strips were hand-built on 2026-09-25 from long prose briefs,
and every one wrote its own `compose.py` whose recipe the supersuit.wiki provenance gate refused
(`provider: "code"`, no prompt, no refs, no model, and an asset path the gate cannot match). They
were fixed by hand in the wiki worktree. A strip made here cannot fail that gate: `compose`
validates the recipe against the gate's own rules, plus a stricter completeness check, before it
writes it.

## The spec (`strip.json`, in the work folder)

```json
{
  "id": "you-are-the-source",
  "universe": "../..",
  "out": "you-are-the-source.png",
  "title": "You Are The Source", "argues": "one line: what the page argues",
  "page": "supersuit-repos/supersuit-wiki/docs/perspectives/....md",
  "asset": "static/img/illustrations/you-are-the-source.webp",
  "canvas": {"size": "1536x1024", "margin": 16, "gutter": 16, "colour": "#F0ECE5"},
  "render": {"quality": "high", "noWardrobe": true, "timeout": 600},
  "maxRerolls": 4,
  "promptBlocks": {"medium": "...", "glow": "...", "clean": "..."},
  "panels": [
    {"id": "p1", "beat": "the ask, in the real room", "world": "real-room",
     "blocks": ["medium", "scene", "glow", "clean"],
     "entities": ["witney", "the-freedom-watch"],
     "refs": ["reference/christofuturist-spatial-lenses/hero.png"],
     "scene": "...", "size": "1024x1536", "width": 480, "shift": 0}
  ],
  "canon": ["canon/entities/witney.json"]
}
```

- **2 to 4 panels.** One is a single hero; use `on-brand-image`.
- **Every panel has a `beat`, a `scene` and `entities`.** Words before art, and canon arrives as
  plates and invariants through `--entity`, never as a description. `@look` works as usual.
- **`blocks` name `promptBlocks` in order**, with `scene` where the scene goes (else last). The
  scene and the defect counters are the only free text in a prompt. A universe's form supplies
  the blocks; this skill knows nothing about any universe.
- **`width`** on every panel or none (none is an equal split); they must fill the canvas exactly.
  **`shift`** moves the crop window, -1 keeps the left edge, +1 the right.
- Refs resolve against the universe, `out` against the spec's folder. A ref that does not resolve
  is refused before anything renders.

## The verbs

```bash
S=<abu>/skills/compose-strip/scripts/strip.py
python3 $S plan    strip.json                 # validate; per panel, rolls so far and the next move
python3 $S prompt  strip.json --panel p1      # the exact prompt the next roll sends
python3 $S render  strip.json --panel p1      # one roll through generate.py, then the binding check
python3 $S judge   strip.json --panel p1 --roll 1 --verdict pass --guard device-anatomy=pass
python3 $S judge   strip.json --panel p1 --roll 1 --verdict defect \
        --reason "watch on the right wrist" --counter "The watch is on her LEFT wrist."
python3 $S compose strip.json --export <wiki>/static/img/illustrations/x.webp \
        --export-asset static/img/illustrations/x.webp
python3 $S stage   strip.json --manifest heroes.json --board-id <id> --title "<T>"
```

1. **`plan` first.** It refuses a spec that cannot make an honest strip.
2. **`render` one panel at a time, in the background when several run** (a high-tier render is
   minutes; three at once is the working concurrency, per `on-brand-image`). It records the roll
   and whether the canon binding held.
3. **Look, then `judge`.** Read the roll at full size (`render-readback`, and `crop_zoom.py`
   before you call a detail a defect). A PASS is refused while `verify_render.py` reports anything,
   including a fired guard with no verdict, so pass each guard's verdict with `--guard`. A DEFECT
   needs `--reason`; give it a `--counter` sentence and every later roll of that panel carries it.
   The reject is MOVED to `panels/rejected/` with a `.reject.json`. Nothing is deleted.
4. **The cap is the first roll plus `maxRerolls` (default 4).** Past it, `render` refuses. Stop and
   report the surviving defects; the rejects and their reasons are on disk.
5. **`compose`** refuses until every panel is kept, then draws the canvas and writes the recipe.
   `--export` writes the wiki's WebP (EXIF-transposed, 1600 max edge, q82) with the recipe
   restated for `--export-asset`. Drop both files into a wiki worktree and
   `npx wiki check provenance` passes; the test suite runs the real gate when it is on the machine.
6. **`stage`** adds the strip to a works manifest (once, by id) and opens the works board. Text
   the phone link through `freedom:message-myself`. A RE-ROLL tap on a strip does not re-roll the
   composite: its brief sends the job to `reopen` the panel the note is about.

`reopen --panel p2 --reason "..."` un-keeps a kept panel (the kept roll goes to `rejected/` with the
reason) and restarts that panel's cap, because a person's objection is a new judgement.

`check-recipe <recipe.json> [--asset REL]` runs the gate's rules on any recipe.

## Files

- `scripts/strip.py` the verbs. State in `strip-state.json` beside the spec; rolls in `panels/`.
- `tests/test_strip.py` spec refusals, the roll loop, the cap, compose geometry, recipe
  completeness with every required field mutation-checked, the export, and the real wiki gate.

## Not this skill

- One image: `abu:on-brand-image`. A book spread: `abu:compose-spread`.
- What a particular universe's strip should SAY: that is a form (`<universe>/forms/<id>/`),
  which writes the spec and hands it here.
