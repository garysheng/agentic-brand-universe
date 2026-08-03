# Wiki Article Hero: one door, two engines, one contract

**Date:** 2026-08-03
**Status:** design, approved for planning
**Repos touched:** `supersuit-repos/wiki-template`, `supersuit-repos/truth-management-wiki` (hosted generators), `agentic-brand-universe`

## Why this spec lives here

It covers two units in two repos. It is filed in `agentic-brand-universe` because
that repo already carries the `docs/superpowers/` convention and, unlike
`wiki-template`, it is not a forkable template. A spec placed in `wiki-template`
would ship into every wiki anyone ever forks from it.

## The problem

A friend is being handed the Truth Management frameworks and told to gamify his
learning by running a personal wiki that his phone-driven agent writes into. The
new-wiki experience has to be seamless for someone who is not generating images
today, does not have ABU installed, and has never used an API key.

It currently is not. The image path is the weakest part of the chain, and the
specific path he would run is the one most likely to produce no images at all.

A second, related want: a wiki article hero image is the same kind of artifact
across every brand universe. It should be a `make-a-work` form, not a per-wiki
script. Today it cannot be, because forms are per-universe only.

## Audit findings

Each finding below is evidence-backed against the tree as of 2026-08-03.

### F1. The documented image interface is broken off Gary's machine

`wiki-template/illustrations/scripts/render-page.sh:90` calls:

```bash
uv run ~/.agents/skills/chatgpt-images/scripts/generate_image.py
```

That is a private skills folder. `find wiki-template -name "*.py"` returns
nothing, so the template vendors no generator. A fork gets a sanctioned
interface that dies with `No such file or directory` on first use.

`starting-your-own-wiki/GENERATE.md` names this script as "the only sanctioned
interface" and explicitly forbids calling `chatgpt-images` directly, so the
documented path and the only working path are mutually exclusive for a new user.

### F2. The template ships a second, dead generator

`wiki-template/scripts/render-graphic.sh` resolves a hosted brand OS
(`brand_os_url` -> `brand.txt` -> GABRs). Three problems:

- That pattern was retired 2026-07 (`supersuit-repos/CLAUDE.md`: "Reading
  brand.txt before generating produces a wrong-register image").
- `wiki.config.json` ships `"brand_os_url": ""`, so it exits 1 at line 37 on
  first invocation.
- `grep -c render-graphic starting-your-own-wiki/GENERATE.md` returns `0`. It is
  undocumented.

It is a trap, not a feature.

### F3. No API key onboarding exists anywhere in the chain

`OPENAI_API_KEY`, `uv`, and image prerequisites appear zero times across the
390-line `starting-your-own-wiki/GENERATE.md`. The only guidance is an error
string inside a private script the new user does not have.

### F4. The template carries a reversed visual law

`wiki-template/illustrations/SPEC.md:63` reads:

> Single focal scene per illustration. One thing is happening.

The multipanel reversal (2026-07-26, family-wide, Gary: "i have made the call,
yes") never reached the template. Every new wiki is born with the law that was
reversed, which is the opposite of the stated default.

### F5. The gamify path produces no images at all

`gamify-your-learning-wiki/GENERATE.md` mentions images zero times. Q4 states
"visual polish is not the optimization." Its Phase 2 and Phase 4 seed five posts
with no hero step. This is the exact recipe the friend runs.

### F6. Provenance lands in two different places

Both generators do write recipes (`chatgpt-images/generate_image.py:63`,
`on-brand-image/generate.py`). They disagree on destination:

| Engine | Recipe lands beside |
|---|---|
| `render-page.sh` (chatgpt-images) | the archived PNG, not the shipped WebP |
| `render-graphic.sh` (userexperience, on-brand-image) | the shipped WebP (line 163) |

The deployed asset in the template path carries no provenance. This is a
contract problem, not a missing feature.

### F7. Four divergent hero paths across the corpus

| Path | Wikis | Layout |
|---|---|---|
| `supersuit-org-comic` -> `abu:on-brand-image` | 5 family wikis | multipanel, 3 beats |
| `scripts/render-graphic.sh` + `hero_register` | userexperience only | multipanel, 3 beats |
| `illustrations/scripts/render-page.sh` | 7 live wikis + template (plus 5 in retired corpuses) | single plate |
| `traction-wiki-strip`, politicalstrategy wrapper | 2 | varies |

`hero_register` is the good config-driven design and exists in exactly one
`wiki.config.json`.

### F8. Cross-ABU forms do not exist

`make-a-work/scripts/forms.py` `survey(root)` reads only `root / "forms"`. There
is no shared or framework-level forms root. Exactly one universe on the machine
declares any forms (`christofuturism`: `event-flyer`, `fashion-look`,
`scrolling-diorama`). `hyperagentic-age`, which powers all five wiki heroes,
declares none.

A wiki-article-hero form cannot be cross-ABU today because cross-ABU forms are
not a concept the resolver has.

## Design

### The seam

The wiki never knows which engine drew its hero. It knows an output contract.

```
./scripts/render-hero.sh <slug> "<scene>"        the ONE door, every wiki
         |
         +- reads hero_register.mode in wiki.config.json
              |
              +- "local" -> vendored generate.py           (zero ABU)
              +- "abu"   -> abu:make-a-work <u> wiki-article-hero
```

A wiki born on `local` graduates to `abu` by editing one field. No page
rewrites, no re-render of existing heroes, no change to any MDX.

This is the `make-a-work` compatibility the ask names: the wiki is a consumer of
a contract, and an ABU form is one legal producer of it.

### The output contract (identical in both modes)

Both engines MUST emit all five, for slug `<s>`:

| Artifact | Path | Notes |
|---|---|---|
| Deploy asset | `static/img/illustrations/<s>.webp` | what MDX embeds |
| Source archive | `illustrations/<s>.png` | never deleted |
| Provenance | `static/img/illustrations/<s>.webp.recipe.json` | beside the SHIPPED asset (resolves F6) |
| Alt text | in the MDX | the verbatim prompt, per SPEC.md:125 |
| Frontmatter | `image: "/img/illustrations/<s>.webp"` | the og:image rule |

The last two are prose conventions today and unenforced. The door prints them
ready to paste, and a checker verifies them (see Verification).

### `hero_register` schema

Extends the existing key from `userexperience-wiki/wiki.config.json` rather than
inventing a fifth convention. New field: `mode`.

```jsonc
// mode: "local"  (the default for a new wiki)
"hero_register": {
  "mode": "local",
  "layout": "multipanel",
  "defaultPanels": 3,
  "spec": "illustrations/SPEC.md",
  "refs": ["illustrations/refs/style-01.png",
           "illustrations/refs/style-02.png",
           "illustrations/refs/style-03.png"],
  "outputDir": "static/img/illustrations"
}

// mode: "abu"  (the graduation)
"hero_register": {
  "mode": "abu",
  "universe": "~/Documents/github-repos/hyperagentic-age",
  "form": "wiki-article-hero",
  "stylePack": "universe/reference/style/warm-editorial-neutral",
  "characterRef": "universe/reference/maya/master.png",
  "motifRefs": ["universe/reference/supercharged-laptop/orange.png"],
  "layout": "multipanel",
  "defaultPanels": 3,
  "outputDir": "static/img/illustrations"
}
```

Existing `hero_register` blocks with no `mode` resolve as `"abu"`, so
userexperience-wiki keeps working untouched.

---

## Unit A: the local engine and the new-wiki experience

Lands in `supersuit-repos/wiki-template` and
`supersuit-repos/truth-management-wiki/static/generators/`.

### A1. Vendor the generator

Add `wiki-template/illustrations/scripts/generate.py`, vendored from
`chatgpt-images/scripts/generate_image.py`, reduced to what a wiki needs:
prompt, refs, size, quality, out, and the recipe writer. Model default
`gpt-image-2`.

Deps: `python3`, `OPENAI_API_KEY`, `cwebp`. Not ABU, not a universe, not
`forms.py`, not a style pack, not node.

Resolves F1.

### A2. The one door

`illustrations/scripts/render-page.sh` is DELETED from the template and replaced
by `illustrations/scripts/render-hero.sh`. Every reference to the old name in
`starting-your-own-wiki/GENERATE.md` and `illustrations/SPEC.md` updates in the
same commit, so no doc points at a script that is gone. The new door:

- Reads `hero_register` from `wiki.config.json`; routes on `mode`.
- Multipanel default at 3 panels. `--panels N`. `--single` as the documented
  exception.
- Lifts the proven layout law verbatim from
  `userexperience-wiki/scripts/render-graphic.sh:107-111`, generalized off the
  wiki's own SPEC instead of hardcoding Maya and the amber laptop.
- Preflights `OPENAI_API_KEY` and `cwebp`, each failing with the exact fix.
- Keeps the existing banned-vocabulary pre-flight grep (line 40).
- Emits all five contract artifacts and prints the MDX and frontmatter lines
  ready to paste.

Resolves F1, F4 at the generator, F6, and part of F7.

### A3. Delete the dead generator, carefully

Remove `wiki-template/scripts/render-graphic.sh`. Resolves F2.

`brand_os_url` has FOUR consumers, not one, and removing it naively breaks the
documented scaffold invocation:

| Consumer | What it needs |
|---|---|
| `wiki.config.json` | drop the key |
| `wiki.config.schema.json` | drop the property |
| `scripts/render-graphic.sh` | deleted above |
| `scripts/init-wiki.sh` | **prompt 7 of 11** |

`start-new-wiki/SKILL.md` documents driving the scaffold non-interactively:

```bash
printf '%s\n' "<title>" "<tagline>" "<url>" "<org>" "<repo>" "<description>" \
  "" "<block-indexing>" "<intake-mode>" "<field-note-sharers>" "<register-skills>" \
  | bash scripts/init-wiki.sh
```

The empty string in position 7 IS the Brand OS URL slot. Deleting that prompt
shifts every later answer by one, so block-indexing lands in intake-mode and so
on, and `init-wiki.sh` writes a silently wrong `wiki.config.json`. That is the
exact failure the skill's own note warns about ("misaligned answers silently
write a wrong wiki.config.json").

**Therefore: repurpose prompt 7 rather than removing it.** It becomes the visual
register question feeding `hero_register`, which keeps the count at 11 and keeps
the slot semantically about visual identity. Update the documented `printf` in
`start-new-wiki/SKILL.md` in the SAME commit, since the slot's meaning changed
even though its position did not.

Note: 7 live wikis carry a copy of `render-page.sh`. They are NOT migrated by
this spec (see Out of scope).

### A4. Fix the reversed law

`wiki-template/illustrations/SPEC.md`: replace the single-focal-scene rule with
the multipanel law, state 3 beats as default, name `--single` as the exception,
and note that beat 2 shows the consequence of beat 1 rather than restating it.
Resolves F4.

### A5. Style-only by default

SPEC.md's recurring-character section becomes explicitly OPTIONAL and
opt-in. The default identity is 2 to 4 blessed style refs, all passed on every
render. The master-first character workflow stays documented for anyone who opts
in, unchanged, since it is correct and hard-won.

### A6. The interview

New phase in `starting-your-own-wiki/GENERATE.md`, invoked from
`gamify-your-learning-wiki/GENERATE.md`:

1. **What a key is.** Two sentences. Images are generated by a paid model and
   billed to his own account, so the key is his, not the wiki's.
2. **Get it.** Walk to `platform.openai.com/api-keys`.
3. **Set it.** Export, then persist to the shell rc. Verify it is readable in a
   fresh shell, because an export that dies with the terminal is the failure
   mode that reads as "it worked."
4. **Prove it.** Render one cheap test image live. He sees an image appear. The
   real charge on his account teaches the cost better than a figure quoted here.
5. **Pick a register.** Three or four presets plus custom.
6. **Bless the refs.** Render 2 to 4 style refs, he approves them, they lock.
7. **First hero.** Render the hero for his first real article.

Also amend `gamify-your-learning-wiki/GENERATE.md`:

- Q4 no longer says visual polish is not the optimization. It sets the register.
- Phase 2 and Phase 4 give each of the five seeded posts a hero.
- The verification block gains the image checks.

Resolves F3 and F5.

## Unit B: the shared form

Lands in `agentic-brand-universe`.

### B1. Shared forms root

Change `forms.py` `survey()` to merge two roots:

- shared: `<abu-repo>/forms/`
- local: `<universe>/forms/`

Rules:

- **Local shadows shared by id.** A universe that wants its own
  `wiki-article-hero` overrides the shared one entirely, never merges with it.
- Each record gains `"source": "shared" | "local"`, and `list` labels it, so no
  one is surprised about where a method came from.
- `resolve` reports the resolved path and its source.

This is the smallest change that makes a form cross-ABU. Resolves F8.

### B2. `forms/wiki-article-hero/`

```
agentic-brand-universe/forms/wiki-article-hero/
  FORM.md      what it is, its goldens, an honest STATUS section
  PROMPT.md    the method (the composer)
  evals/panels.py
```

`PROMPT.md` owns the method: resolve canon, assemble the beat prompt with the
panel law, generate via `on-brand-image`, run `render-readback`, then emit the
five contract artifacts into the target wiki.

Destination follows the precedent already set by `fashion-look/scripts/resolve_out.py`:
the work is recorded canonically under `works/<YYYY-MM-DD>-<slug>/` with every
candidate preserved, and the blessed artifact is installed into the wiki's
`outputDir`. Two locations, one blessed artifact, same shape `add-generator`
uses for its install map.

`evals/panels.py` asserts the render is actually a strip: N panels of roughly
equal width separated by gutters, not one plate. A multipanel law that nothing
checks is how the single-plate default survived for weeks.

### B3. FORM.md states its evidence honestly

Per the framework's own rule, `FORM.md` says how many works it was written
from. The retired composer had 896 lines, 91 tests and zero works, and that is
the failure this must not repeat. The form is authored AFTER Unit A has produced
real heroes, so the count is truthful and greater than zero.

## Sequencing

Unit A and Unit B are independent and Unit A goes first.

The local path does not wait on the form. The form is better written once real
heroes exist, because `FORM.md` has to state its evidence and B3 requires that
number to be honest.

## Verification

Unit A is done when, on a machine with no ABU and no `~/.agents`:

- `git clone` the template, set `OPENAI_API_KEY`, run the door, and a WebP
  appears.
- The output is a 3-panel strip, confirmed by `evals/panels.py` or its local
  equivalent.
- All five contract artifacts exist, including the recipe beside the WebP.
- `grep -r "/img/illustrations/[a-zA-Z0-9_-]*\.png" docs/` returns nothing.
- `grep -rn "\.agents/skills" illustrations/ scripts/` returns nothing.
- `pnpm run build` passes.
- Unsetting `OPENAI_API_KEY` produces an error naming the exact fix.

Unit B is done when:

- `forms.py list <any-universe>` shows `wiki-article-hero (shared)`.
- A universe with a local form of the same id shadows it, proven by a test.
- `make-a-work` against a real wiki produces a hero satisfying the same five
  artifacts as Unit A.
- Existing per-universe forms in `christofuturism` still resolve as `local`.
- Reverting the survey change makes the new tests fail (proving they bite, per
  the repo's own rule).

## Out of scope

- **Migrating the 7 live wikis** off `render-page.sh` (compounding,
  userexperience, christian-integrated-healing, exitstrategy, kingdom-calling,
  politicalstrategy, reallife). The template is fixed at the source first so it
  stops reproducing; the confirmed instances are a separate sweep, and per
  AGENTS.md the source fix comes first. The 5 further copies in the retired
  Imagos and AAS corpuses are not touched at all.
- **Backfilling single-plate heroes.** Family policy is that they age out.
- **`supersuit-org-comic`**, `traction-wiki-strip`, and the politicalstrategy
  wrapper. They keep working. Consolidating them onto the shared form is the
  natural follow-on once B is proven, not part of this spec.
- **Pricing copy.** No per-image cost is quoted anywhere, because the live test
  render shows the real charge.

## Risks

- **The vendored generator drifts from `chatgpt-images`.** Accepted. Portability
  is the whole point, and the vendored copy is deliberately smaller. The header
  names its origin so a future reader knows where to look.
- **Two engines drift on the contract.** Mitigated by the contract being
  explicit here and checkable, rather than living in prose in two scripts.
- **`gpt-image-2` moderation blocks a register.** Already handled by the banned
  vocabulary pre-flight, which is retained. The named-illustrator lesson stays
  in SPEC.md.
