---
name: compose-spread
description: Render ONE spread of an Agentic Story book as an atomic unit — resolve canon, deterministically ASSEMBLE the prompt + refs from canon (register-anchor-first, each in-frame entity's block for its SELECTED look including alt-looks, auto-disambiguation, and negatives COMPUTED from the selected looks so a blanket negative can never fight a canon alt-look), generate, then read back. This is the atomic step render-book and update-book used to describe in prose and every book re-hand-rolled as its own gen-spread.py. Character/setting truth is read from canon/entities, never retyped per book. Generic and universe-parameterized.
---

# Compose Spread

The atomic per-spread unit: turn one spread descriptor into a read-back-clean render. `render-book` and `update-book` invoke this once per touched spread; do NOT re-describe "resolve → generate → read back" in prose and do NOT hand-roll a per-book `gen-spread.py` — that reimplementation is where drift bugs live (a book's retyped character prose silently overriding the character's canon).

**The rule this skill enforces:** the composition is DETERMINISTIC SOFTWARE, not a fresh improvisation each render. Everything load-bearing about a character or setting — including which LOOK it is in — comes from `canon/entities/<id>.json`. The per-book `render-spec.json` carries only per-spread COMPOSITION and book-wide style/negatives.

## Inputs
- The target universe (a path with `universe.json`).
- The book's `render-spec.json` (book-wide `style`/`negatives`/`guardedNegatives`/`anchorRef`, plus one descriptor per spread).
- The spread id to render, and the output PNG path.

### Spread descriptor shape (in render-spec.json `spreads[]`)
```
{ "id": "spread-07",
  "cast": [ {"id":"yan-zhang"}, {"id":"tony-sheng","look":"mustache-wavy"}, {"id":"gary-sheng"} ],
  "setting": "vegas-home", "plate": "empty-c1-kitchen",
  "scene": "<the composition/action — the ONE free-text field; identity comes from canon>" }
```
`look` is omitted for a character's default look, or names a `structured.altLooks.<key>` in that character's canon. No character description is ever written here.

### The four guards the assembler enforces for you (SPEC v0.8)

Each was paid for with defective renders. You do not write any of them into a book's style text; the assembler emits or enforces them on every job, which is the point of having a compiler at all.

1. **Anchor-style guard.** The register anchor is ref[0] on every render, so on a spread that casts nothing its *subject* leaks as content (a pure-vision beat once came back as a room full of period strangers holding the anchor's own props). The guard is always emitted alongside the anchor.
2. **Single-image guard.** Canon legitimately supplies multi-panel references (a turnaround, a states sheet) and the model copies their *layout*. Emitted by default; set `allowMultiPanel` on the book or one spread to opt out.
3. **Uncast-character refusal.** A character NAMED in the scene text but not cast is rendered as a confident invented stranger. The assembler matches every character entity's given name against the scene and **refuses before spending**. An over-the-shoulder single needs BOTH people cast: the shoulder is a person. Set `allowUncast` when the mention is genuinely not an in-frame person.
   - **False positives are expected, and this is why `allowUncast` is PER-SPREAD.** The check matches a bare given-name token, so an ordinary word that happens to be some entity's head token trips it: a scene naming a character class "the Elder" matched the unrelated entity `elder-lee` and refused. That is the guard being cheap and fail-closed, which is correct. What is NOT acceptable is waiving it for a whole run: set `allowUncast` on the ONE spread whose mention is innocent, and every other spread in the batch keeps its protection. A book-level waiver to unblock a single false positive silently disarms the most expensive defect class this pipeline has.
   - **Order the batch so a refusal is cheap.** The refusal aborts the entire invocation before any spend (right), which means one false positive blocks every other spread in that call. Cost is zero dollars and one round trip, but on a long batch it is wasted wall-clock. Run a `--dry` pass first on a new book, or expect to re-fire.
4. **Per-spread preamble override.** A book may carry MORE THAN ONE visual register when the change is **diegetic**: a game world on a screen, a vision blooming out of a canon device, a memory, a dream. A spread may override `style`, `negatives`, `guardedNegatives`, `anchorRef`, `size`, `allowMultiPanel`, `allowUncast`. Anything it does not name falls back to the book preamble. Do NOT reach for a second render-spec to get a second register: that duplicates the whole preamble and drifts the moment one copy is edited. The universe's own `rejectedPoles` are identity and are never shed by a spread.

### Never fork this into a universe-local compiler

A per-universe `compile_render.py` / `gen-spread.py` is the failure this skill exists to prevent, and it is not hypothetical: Nation of Fire ran one for months (SPEC v0.5 even named it the reference impl). The two implementations drifted into **disjoint** feature sets. The fork held all four guards above; the framework held alt-looks, auto-disambiguation, guarded negatives and `anchorRef`. Neither could see the other's, so every guard earned in one universe was invisible to every other, and every framework capability was invisible to the universe doing the most rendering. If the assembler is missing something you need, add it HERE with a test (`evolve-agentic-story`), never in a universe.

## Procedure

1. **Resolve (gate).** Invoke `canon-resolve` on the spread's cast + setting: it resolves each entity's locked references + invariants and runs `assert-spread`. A non-zero exit BLOCKS the render — lock the missing reference, never render around it.

2. **Assemble (deterministic software).** Run `scripts/assemble_prompt.py <universe> <render-spec.json> <spread-id>`. It returns `{prompt, refs, size, qa}` as a pure function of canon + descriptor:
   - `identity.register.anchor` first (or the book's `anchorRef` override when the universe anchor is unsuitable, e.g. a photo in a painterly universe);
   - each in-frame entity's block from canon for its SELECTED look (an alt-look supersedes the base look's superseded invariants and swaps in the alt anchor photo — the default sheets are NOT passed, so they can't fight it);
   - auto-disambiguation naming what makes each castmate distinct when ≥2 share the frame;
   - negatives = `rejectedPoles` + book `negatives` + `guardedNegatives` **kept only when no in-frame look positively declares the guarded feature** (a negatively-phrased invariant like `…never-a-mustache` does not count as declaring it).
   Do not edit the assembled prompt by hand. If it is wrong, the fix is in canon or the descriptor, never a one-off patch to the prompt string (that reintroduces drift).

3. **Generate.** Pass the assembled `prompt` + `refs` (anchor first) + `size` to the image model. `scripts/render_spread.py <universe> <render-spec.json> <spread-id> --out <path>` does assemble+generate in one call (3 retries); use `--print-prompt` to inspect.

4. **Read back.** Invoke `render-readback` on the output: crop-zoom every invariant in the returned `qa` list. Any DEFECT regenerates FROM SCRATCH (re-run render_spread.py; the model is stochastic), never an edit pass. Loop until all invariants PASS.

## Gates honored
- **Canon-resolve before the prompt:** no render except from a resolved, asserted record.
- **Register-anchor-first:** every render leads with the register anchor.
- **Canon is the single source:** character/setting identity and look come from canon; the per-book file cannot contradict it, because the block, its refs, and the guarded negatives are computed from the SAME look.
- **Read-back after every render:** any DEFECT regenerates from scratch.

## Show the render

**Every image this skill produces is shown via the `open-in-preview` skill, never a raw `open`.**
Invoke it with the paths in viewing order and name that order in the same message so the human can
point by name. It groups the set into ONE window and hard-fails before opening if any path is
missing, instead of silently dropping the whole batch. Describing an image is not showing it: a
reader who cannot see the render cannot catch what the read-back missed.

## An alt look must SUPPRESS the base look, in all three channels

`supersedes` only removes base INVARIANTS. Two other channels still carry the base look to the
model, and both outrank an invariant list: **a reference image beats a word, and canon prose beats
a slug.** An alt look that suppresses only invariants ships the base look's signature anyway.

When authoring an alt look, walk all three:

1. **`supersedes: [...]`** — the base invariants this look contradicts (QA keys).
2. **`dropSheets: [...]`** — the base SHEETS this look contradicts. Face sheets drop automatically;
   everything else (a pendant sheet, a signature-jacket body sheet, a shoes sheet) does not.
3. **`render: {...}`** — an alt look's own render block REPLACES the base `structured.render` for
   that look. Needed whenever the base block's prose asserts the thing the look denies. Omit it and
   the look inherits the base block, which is right for a look that only changes one feature.

The failure is silent and it is the worst shape available: the plate comes back internally
consistent, and the readback key that would have caught it was superseded, so nothing flags it.
Earned on jerry-man's age eras — a twenty-year-old rendered wearing the adult faith-marker pendant
he does not own yet, first because the pendant SHEET still rode along, then again because
`render.always` still said "his gold NORTH STAR pendant" and the front pose still baked the adult
jacket.

**Test an alt look before rendering a batch with it:** assemble one spread and read the `refs` list
and the prompt back. Every ref and every sentence should belong to the look you selected.

## The model fills silence with cliché

Anything a spread's scene text leaves unsaid gets filled from the nearest cultural stock image, and
near sacred material that is reliably the wrong thing. Observed, each on a first render: a scene
saying "a figure in holy fire, singing" produced Christ, because every training image matching that
description is Christ or a martyr and the prompt never said WHAT KIND of person; a warm domestic
interior grew framed family photographs, violating a sensitive list that forbade a subject's children,
because the prompt banned a child in the scene and said nothing about pictures OF children; and an
ordinary kitchen spontaneously grew a divine hand of light that belonged to a later payoff spread.

Two rules follow. **Close the gap explicitly** rather than trusting a negative to hold: say the
ordinary thing you DO want (an ordinary present-day person in modern clothes). And **a motif reserved
for a book's payoff must be forbidden by name in every earlier spread that could attract it** — an
unrequested divine element is a DEFECT even when it breaks no law, because it spends an image the
book was saving.

## Two things the model volunteers, and both are DEFECTS

Measured across one 8-book run: **7 of 9 read-back defects were one of these two.** Put both in the
preamble negatives of every render spec, not just in the spreads you think are at risk.

**It volunteers divine elements into ordinary frames.** Hands of light, shafts of gold, and glows
appear in scenes that asked for none, including a frame whose whole argument was that God is visibly
NOT acting there. A negative alone does not hold: on any spread that must carry none, ALSO say it
positively in the scene text ("there is no divine light and no hand of light anywhere in this frame;
the sky is empty"). And a motif reserved for a book's payoff must be forbidden by name in every
earlier spread that could attract it, because spending it early costs the payoff.

**It DEPICTS the style anchor.** The anchor is passed as a style reference and the model draws its
contents as props: a character handing the anchor's brass goggles across a table, set-down luggage
growing goggle lenses. Every spec's negatives need a clause like: *the first reference image is a
STYLE anchor only; nothing drawn in it may appear in this scene.*

Related: when a passed reference is a MULTI-PANEL sheet, name what you want from it and exclude the
rest. A hand-of-light plate leaked a literal loaf of bread because the sheet's fourth panel holds
bread, and it argued the wrong thing for that beat.

## Not this skill
- Authoring/altering an entity or adding an alt-look → the `add-*` skills (an alt-look is `structured.altLooks.<key>` with `anchorPhoto`, `supersedes`, `invariants`, and the two suppression fields below).
- Locking a reference matrix → `lock-references`.
- The cover (portrait + baked title) → `cover` (may share the assembler).
- Whole-book orchestration (worktrees, manuscript gate, delivery) → `render-book`; editing a shipped book → `update-book`. Both invoke THIS skill for the per-spread step.

## Reading material faces the reader, never the camera

A book, notebook, page, ledger, letter or document that a character is reading or writing belongs to THEM, so it is oriented for them: top edge away from them, text running the direction they read, and therefore foreshortened, tilted or partly upside down from the camera. Image models default to squaring the page up to the lens so the viewer can read it, because that is what stock illustration does, and the result reads as staged the instant you notice it. If the camera cannot see the page clearly, that is correct.

Bake this as a book-level negative rather than hoping per spread. It recurs on every spread with a desk, a Bible, a report card or a ledger, and it is invisible in a thumbnail and obvious at full size (caught by Gary on `it-was-not-broken` spread 36, 2026-07-25: "you continuously flip the book").

The one exception is a page the scene explicitly presents TO the viewer as a designed element under CANON rule 6, which is a deliberate composition and not a character reading.
