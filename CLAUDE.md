# Agentic Brand Universe — agent notes

This file exists for ONE reason: **27 scripts ship in this repo and they are filed by which
skill owns them, not by what job they do.** A script under `render-readback/scripts/` is
invisible to anyone who has not already decided to run render-readback, which is how a
session on 2026-08-01 hand-rolled the same contact-sheet montage roughly fifteen times with
`contact_sheet.py` sitting in the repo the whole time.

**Before you write a script, check this table.** It is indexed by JOB, in the words you
would use at the moment you need it.

## I need to...

| ...do this | Use |
|---|---|
| **make a contact sheet** of several renders | `render-readback/scripts/contact_sheet.py --out X.png --cols 3 *.png` |
| **crop in on a detail** to check an invariant (jaw, throat, a mark) | `render-readback/scripts/crop_zoom.py` |
| **measure a figure** in a plate | `render-readback/scripts/measure.py` (`figure` mode only; `star` mode was withdrawn for false precision) |
| **generate ANY image** | `on-brand-image/scripts/generate.py` — the single provider adapter. Never call a provider directly; this is what writes provenance. |
| **knock out a background** | `on-brand-image/scripts/chroma_key.py` |
| **see where a universe stands** | `abu/scripts/status.py --json` |
| **grade a universe** | `universe-doctor/scripts/grade.py` |
| **grade a rendered book** | `book-doctor/scripts/book_doctor.py` |
| **static-check before rendering** (free, no API calls) | `lint-universe/scripts/lint.py` |
| **list what a universe can MAKE** | `make-a-work/scripts/forms.py list <universe>` |
| **scaffold a style pack / lookbook** | `create-style-pack/scripts/scaffold.py`, `create-lookbook/scripts/scaffold.py` |
| **assemble a spread prompt from canon** | `compose-spread/scripts/assemble_prompt.py` |
| **scaffold or re-sync a book render-spec** | `compose-spec/scripts/compose_spec.py` |
| **add / insert / renumber a spread** | `update-book/scripts/insert_spread.py` |
| **recast one entity as another across a story** | `update-book/scripts/recast_story.py` |
| **chain an entity's matrix shots** | `shoot-references/scripts/chain_matrix.py` |
| **backfill prompts onto old plates** | `shoot-references/scripts/backfill_prompts.py` |
| **judge a slot against its golden** | `judge-slot/scripts/judge.py` |
| **voice-check text before locking** | `voice-gate/scripts/voice_gate.py` |
| **find what a session hand-rolled** | `pave-the-path/scripts/detect_handroll.py` |
| **install the framework for someone** | `onboard/scripts/install.py` |
| **render one spread** | `compose-spread/scripts/render_spread.py` |
| **render / compile / conform a cover** | `cover/scripts/render_cover.py`, `compile_cover.py`, `conform_cover.py` |
| **make an explanatory plate** (diagram-style) | `explanatory-plate/scripts/plate.py` |

Engine verbs (`python3 -m agenticstory.cli <verb>` from `engine/`):
`validate` · `list` · `list-craft` · `assert-story` · `assert-spread` · `lock-level` ·
`wardrobe` · `lock-shot` · `archive` · `import-asset` · `add-entity` · `build-canon` ·
`build-docs` · `backfill-provenance` · `massing` · `elevation` · `land` · `init`

## Rendering a named person: ALWAYS use the look binding

```bash
python3 skills/on-brand-image/scripts/generate.py \
  --out <path>.png --no-open --no-wardrobe \
  --entity "<universe>:<entity>@<look-id>" \
  --prompt "<the SCENE only. Never describe the outfit.>"
```

**`@<look-id>` is the whole point.** It resolves the person's locked plates AND the look's
own `invariants`, which state the garment. Bare `--entity selah` with a hand-written outfit
description is how a blessed A-line gown came back as a fitted trumpet and blessed
straightened hair came back curly: the binding existed, was not used, and nothing complained.

**Never hand-assemble a prompt by slicing an older recipe.** A `.split("SETTING:")[0]` on a
previous prompt silently dropped an entire dress description, and the render looked plausible
enough that only the owner caught it. If the look is bound, the words come from canon.

Looks bound in `christofuturism` today:

| Pass this | Wears |
|---|---|
| `gary@usa-flag-jacket` | American-flag leather bomber |
| `gary@texas-denim` | denim trucker with the Proof of Vibes patch |
| `gary@at-home-loungewear` | silk pyjamas, indoors only, no pendant |
| `selah@wedding-dress` | ivory lace A-line, two hair sheets (below) |
| `selah@usa-flag-dress` | American-flag fit-and-flare |
| `selah@at-home-robe` | silk wrap robe, indoors only |

A look may carry EXTRA SHEETS beyond `look`. `selah@wedding-dress` has
`hair-curls-down` and `hair-ironed-side`; name the one you want in the prompt, or the model
picks. A look may also `supersede` a base invariant, which is how the ironed style is legal
inside that look and nowhere else.

**Verify before you look at the image.** Read the recipe back and confirm the canon actually
arrived. This has caught silent bypasses four times:

```bash
python3 -c "import json,sys; p=json.load(open(sys.argv[1]))['prompt']; \
  print('invariants:', 'LOCKED canonical traits' in p)" <out>.png.recipe.json
```

Also check for a dead render. Two came back pure black after a metaphor about light
("catch the light like a constellation") was read as a night scene:

```bash
python3 -c "from PIL import Image;import sys; \
  print('BLACK' if Image.open(sys.argv[1]).convert('RGB').getextrema()==((0,0),(0,0),(0,0)) else 'ok')" <out>.png
```

## The rule this file encodes

**Discoverability is a just-in-time problem, not a documentation problem.** Anything that
depends on having read something earlier and remembered it fails on a long session. The
plugin description is ~6,900 characters loaded once at session start; by hour six it has
lost to whatever is in front of you. So:

- When you add a script, **add its row here**, in the words someone would search for.
- When a skill's method should call a script, **name the script inside that method**, not
  only here. The `fashion-look` form's `PROMPT.md` does this and it is the pattern.
- Prefer a tool that **refuses loudly at the moment of misuse** over a doc that explains the
  right way. `validate` catching a bad wardrobe key taught faster than any prose.

## Two standing gotchas

- **zsh eats `"$VAR:id"`** as a parameter modifier, so `--entity "$CF:gary"` silently
  mangles the path. Build it first: `ENT="${CF}:gary"`, then pass `"$ENT"`.
- **Never rewrite a historical record.** `.recipe.json` files and dated canon attestations
  state what actually ran. Change live INSTRUCTIONS; leave every ATTESTATION alone, even
  when it points at a file that has since been deleted.

## Provenance invariants (both were bugs, both are now enforced)

- **A recorded transform is a PERFORMED transform.** `import-asset --crop` used to
  `shutil.copy2` the original while writing `transform.crop` into the recipe from the
  caller's argument, so the provenance asserted an edit that never happened. It now crops
  or REFUSES, including when Pillow is missing or the box does not fit the source. A false
  record is worse than none: it passes an audit.
- **A recipe records the output geometry it asked for.** `--size` and `--quality` were
  forwarded to the provider and never written down, so a reader could not tell an intended
  aspect from a provider default.
