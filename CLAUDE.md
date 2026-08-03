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
| **verify a render** — did the canon arrive, did the look bind, is the frame dead | `render-readback/scripts/verify_render.py <png> --expect "id@look"` |
| **crop in on a detail** to check an invariant (jaw, throat, a mark) | `render-readback/scripts/crop_zoom.py` — **use it BEFORE calling a defect.** A contact sheet is downsampled; a lace hem called "vertical stripes" from a 3-up was a correct horizontal band when zoomed. |
| **measure a figure** in a plate | `render-readback/scripts/measure.py` (`figure` mode only; `star` mode was withdrawn for false precision) |
| **generate ANY image** | `on-brand-image/scripts/generate.py` — the single provider adapter. Never call a provider directly; this is what writes provenance. |
| **knock out a background** | `on-brand-image/scripts/chroma_key.py` (add `--choke 12` for a dark-on-dark silhouette, or despill leaves a yellow edge hairline) |
| **see where a universe stands** | `abu/scripts/status.py --json` |
| **grade a universe** | `universe-doctor/scripts/grade.py` |
| **grade a rendered book** | `book-doctor/scripts/book_doctor.py` |
| **static-check before rendering** (free, no API calls) | `lint-universe/scripts/lint.py` |
| **list what a universe can MAKE** | `make-a-work/scripts/forms.py list <universe>` |
| **scaffold a style pack / lookbook** | `create-style-pack/scripts/scaffold.py`, `create-lookbook/scripts/scaffold.py` |
| **scaffold a new form** (a new KIND of work) | `create-form/scripts/scaffold.py` (refuses on zero evidence works; the method lives in the create-form SKILL) |
| **assemble a spread prompt from canon** | `compose-spread/scripts/assemble_prompt.py` |
| **scaffold or re-sync a book render-spec** | `compose-spec/scripts/compose_spec.py` |
| **add / insert / renumber a spread** | `update-book/scripts/insert_spread.py` |
| **recast one entity as another across a story** | `update-book/scripts/recast_story.py` |
| **chain an entity's matrix shots** | `shoot-references/scripts/chain_matrix.py` |
| **backfill prompts onto old plates** | `shoot-references/scripts/backfill_prompts.py` |
| **judge a slot against its golden** | `judge-slot/scripts/judge.py` |
| **voice-check a manuscript before locking** | `voice-gate/scripts/voice_gate.py <universe> <manuscript.md>` — rules fetched from https://garysheng.com/voice.md; fails on unadjudicated findings, waivable with a written reason |
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

**`structured.render.always` is honoured here.** It is prompt-craft that applies to every
render of an entity: register, staging, standing composition. `compose-spread` always read
it and `on-brand-image` did not until v0.29, so the same field was live in one renderer and
inert in the other, and a canon edit could look correct while steering nothing. Put standing
STAGING there; put facts about the body in `invariants`, where a readback can check them.

**TWO OR MORE PEOPLE IN ONE FRAME:** `--entity` is repeatable and every entity's plates,
invariants and negatives merge. Landscape `1536x1024` suits two figures, portrait suits one.
Three things that are not obvious and each cost real renders:

- **State "EXACTLY ONE of each person in frame, never duplicated."** Multi-person renders
  duplicate a face otherwise. At least one universe's craft canon already forbids this and
  nothing enforced it.
- **Name each person's ethnicity in the scene line** when they differ, or one drifts toward
  the other across a batch.
- **Never dress them in a matching set.** Same palette family and formality, cut for each
  separately. Matching reads as costume; a shared register reads as one household. Two
  re-shoots were caused by this: an emerald dress beside a forest-green suit, and cream
  beside cream. Related means several shades apart in value AND saturation.

Opposing invariants resolve correctly and can be trusted: a pair render where one entity's
canon asserts a chest patch and the other's forbids one produces exactly that asymmetry with
neither mentioned in the prompt.

**Verify before you look at the image**, with the script, not by eye:

```bash
python3 skills/render-readback/scripts/verify_render.py <out>.png \
  --expect "selah@wedding-dress"           # asserts the LOOK bound, not just the person
```

It checks that the recipe exists, that the invariant block reached the prompt, that the
entity AND look you meant are the ones that resolved, and that the frame is not pure black.
It exits non-zero, so it can gate a loop. These were two paste-in one-liners in this file
until 2026-08-02, and a check you paste is a check you skip: between them they had already
caught four silent binding bypasses and two dead frames, and were still being retyped by
hand. **`--expect selah` does NOT satisfy `--expect selah@wedding-dress`** — matching the
id alone is exactly how the bare-entity bug stayed invisible.

**To prove a look is BOUND, render a scene that never names the clothes**, and let the
script check the scene text too:

```bash
python3 skills/render-readback/scripts/verify_render.py <out>.png \
  --expect "selah@wedding-dress-highneck" --scene "$SCENE"
```

If the garment words are in the prompt, the render proves nothing: it shows the model can
follow instructions, which was never in doubt. Add the look's own hero words with
`--forbid`, since only you know what this look is made of.

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

## Proving a test bites

When you add a test for existing behaviour, revert the behaviour and confirm the test
fails. A test written against code that already passes proves only that it compiles.

**Assert the mutation actually applied.** Patch by string replacement and the string will
eventually not match — a comment between two lines is enough — and the run then reports the
mutation as SURVIVED when nothing was ever mutated. That reads as "the test is weak" and
sends you rewriting a test that was fine. It happened on 2026-08-02:

```python
assert old in src, "PATCH DID NOT MATCH"   # without this the no-op is silent
```

Same family as every other bug in this file: a check that did not run looks exactly like a
check that passed.

## Two standing gotchas

- **zsh eats `"$VAR:id"`** as a parameter modifier, so `--entity "$CF:gary"` silently
  mangles the path. Build it first: `ENT="${CF}:gary"`, then pass `"$ENT"`.
- **Never rewrite a historical record.** `.recipe.json` files and dated canon attestations
  state what actually ran. Change live INSTRUCTIONS; leave every ATTESTATION alone, even
  when it points at a file that has since been deleted.

## Provenance invariants (each was a bug, each is now enforced)

- **A recorded transform is a PERFORMED transform.** `import-asset --crop` used to
  `shutil.copy2` the original while writing `transform.crop` into the recipe from the
  caller's argument, so the provenance asserted an edit that never happened. It now crops
  or REFUSES, including when Pillow is missing or the box does not fit the source. A false
  record is worse than none: it passes an audit.
- **A recipe records the output geometry it asked for.** `--size` and `--quality` were
  forwarded to the provider and never written down, so a reader could not tell an intended
  aspect from a provider default.
- **DECLARED is not PASSED, so a recipe states both.** The entity block recorded
  `photoStack` from canon whether or not the photographs were sent. Since `--entity-photos`
  is OFF by default, the ordinary recipe listed a stack that never reached the provider,
  and anyone auditing what conditioned a render would conclude it did. Now
  `photoStackDeclared` and `photoStackPassed` are separate fields. The general rule: when a
  record can state either what canon SAYS or what the run DID, and they can differ, it must
  say which one it is saying.
