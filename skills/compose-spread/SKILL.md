---
name: compose-spread
description: Render ONE spread of an Agentic Brand Universe book as an atomic unit — resolve canon, deterministically ASSEMBLE the prompt + refs from canon (register-anchor-first, each in-frame entity's block for its SELECTED look including alt-looks, auto-disambiguation, and negatives COMPUTED from the selected looks so a blanket negative can never fight a canon alt-look), generate, then read back. This is the atomic step render-book and update-book used to describe in prose and every book re-hand-rolled as its own gen-spread.py. Character/setting truth is read from canon/entities, never retyped per book. Generic and universe-parameterized.
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
4. **Archived-entity refusal (SPEC v0.16).** An entity whose `lifecycle` is `archived` has been
   retired from NEW work. The assembler refuses before spending and names `archived.supersededBy`
   when there is one. This gate lives HERE and deliberately NOT in `assert-story`, because archiving
   must never retroactively break a book that already shipped: history keeps rendering and its
   provenance stays honest. Re-rendering a pre-archive book is legitimate and opts out per spread
   with `allowArchived`, which leaves an auditable trace of that choice.

5. **Anonymous figures (`anonymous`).** The cast closure is fail-closed, which is right, but
   it had no way to say *there ARE people here and none of them is canon*. A crowd, a stranger,
   a class of children seen from behind, a widow at her own kitchen table: all are deliberately
   NOT entities, because promoting every passer-by to canon is the bug rule 7 prevents in the
   other direction. Without an escape hatch the failure is **silent and expensive**: the scene
   describes a person, the closure says there is nobody, the model obeys the closure, and the
   render comes back as a tasteful still life of the room they were supposed to be in. Nothing
   refuses and nothing warns; it surfaces only at read-back.

   So a spread may set `"anonymous": "one widow in her eighties at her table"` — a short phrase
   naming who the unnamed figures are. It widens the closure from *nobody* to *these, and nobody
   else*. It never grants canon identity and it never relaxes the uncast-NAME refusal, so a real
   entity mentioned by name is still refused before spend. **Reach for it whenever a scene's
   subject is a person the story deliberately leaves unnamed**, and reach for `add-character`
   instead the moment that person recurs. (Earned 2026-07-29 on *Atlas Surrendered*: three
   spreads whose subject was an unnamed stranger each rendered as an empty room.)

6. **Per-spread preamble override.** A book may carry MORE THAN ONE visual register when the change is **diegetic**: a game world on a screen, a vision blooming out of a canon device, a memory, a dream. A spread may override `style`, `negatives`, `guardedNegatives`, `anchorRef`, `size`, `allowMultiPanel`, `allowUncast`. Anything it does not name falls back to the book preamble. Do NOT reach for a second render-spec to get a second register: that duplicates the whole preamble and drifts the moment one copy is edited. The universe's own `rejectedPoles` are identity and are never shed by a spread.

### Declare the SIZE of anything that recurs, not just its look

An entity file happily describes a thing's form, its colour, its materials and its
rules, and never once says HOW BIG IT IS. Nothing catches that: every gate here
checks identity, register and composition, and a thing can satisfy all of them at
any scale. The result is a recurring object that is a different size on every
page, which a reader notices immediately and no check ever will.

Earned on what-a-book-is-made-of, 2026-07-29. The supercharged laptop appears in
most of twenty-one spreads and ranged from a notebook to a small television.
Colour was meaning in that universe and scale was a guess.

Any entity of ANY kind may carry `structured.scale`:

    "scale": {
      "absolute": "a 14-inch notebook, 33cm wide, its open screen about twice the
                   height of a mug beside it and about a quarter of the desk width",
      "relativeTo": {"other-entity-id": "several inches shorter than"}
    }

`absolute` is emitted as a TRUE SIZE line whenever that entity is in frame, alone
or not, for every kind. `relativeTo` still emits the RELATIVE SCALE line and still
requires both entities to be in frame. Before this, scale was read only off
CHARACTERS and only fired when two of them related to each other, so a prop could
not state its size at all.

**Pin the size to things a render already contains.** "33cm wide" is unverifiable
in a painting; "about twice the height of the mug beside it" is checkable at
read-back by looking. Write the ratio, then the measurement.

**A code-drawn scale plate is the cheapest way to get the ratios right.** Model
the object beside a desk, a mug and a spread hand in a `massing` spec and render
it: deterministic, free, and it gives you a reference image to pass as well as the
numbers to write down. See `reference/supercharged-laptop/scale.png`.

### The book `style` must describe the BOOK, never the CAST

**The assembler now enforces this**, because documenting it did not work: the same
mistake was made three times in one session by the same author who had just written
the warning below. Every render now carries a CAST CLOSURE line derived from the
cast (`THE ONLY CHARACTERS IN THIS IMAGE ARE: ...`, or a flat statement that there
are none), so a preamble can no longer smuggle a figure into a spread that did not
cast one. The guidance below still matters for prompt hygiene; it is no longer the
only thing standing between you and an invented stranger.


A book-wide `style` string is prepended to EVERY spread, so anything it names is
present on every spread whether or not that spread cast it. Naming the cast there
manufactures the exact defect the uncast-character guard exists to prevent, and it
sails straight past that guard, because the guard reads the SCENE text and the
invention is coming from the preamble.

Earned on it-only-has-to-fly, 2026-07-29. Its style read "a children's picture
book about two children and a small hand-made helper who build a little factory in
a garden shed". Five of the seventeen spreads did not cast the helper, and the
model dutifully invented one on each: a different robot every time, none of them
matching the canon entity, one of them three spreads before the character is
introduced in the story, and one of them rendered twice in the same frame at two
different sizes. All five had to be re-rendered.

Write the style as MEDIUM, PALETTE, REGISTER and SUBJECT MATTER. If it helps to
say what the book is about, say it without an inventory of who appears:

    BAD:  "...about two children and a small hand-made helper who build a factory"
    GOOD: "...about building a factory in a garden shed"

and it is worth appending, once, at book level:

    "Each spread contains ONLY the figures its own scene description names."

### Put a load-bearing exclusion FIRST, not last

A rule at the end of a long scene is a rule the model has stopped reading. Two
spreads kept rendering a seated figure through two rolls with an explicit
"ABSOLUTELY NOBODY IS IN THE ROOM" appended at the end of a two-hundred-word scene.
Moving that same sentence to the FRONT and tightening the camera so there was no
room in frame for a figure fixed it on the next roll, with no new words added.

Order the scene: hard exclusions, then camera, then subject, then dressing.

### Do not compose for the read-back

Side-on three-quarter shots show a face, and a face is easy to verify against
invariants, so they quietly become the default. On what-a-book-is-made-of every
interior spread came out side-on and the blueprint's own over-the-shoulder camera
was never referenced once, in a book whose entire thesis is that the man is OUTSIDE
the machine looking in. Gary caught it: side-on turns that into a man chatting with
a gadget, and over-the-shoulder puts the reader where he stands.

Choose the camera the argument needs, then work out how to check it. If a setting
declares a camera you have not used, ask why not before you finish.

### Never fork this into a universe-local compiler

A per-universe `compile_render.py` / `gen-spread.py` is the failure this skill exists to prevent, and it is not hypothetical: Nation of Fire ran one for months (SPEC v0.5 even named it the reference impl). The two implementations drifted into **disjoint** feature sets. The fork held all four guards above; the framework held alt-looks, auto-disambiguation, guarded negatives and `anchorRef`. Neither could see the other's, so every guard earned in one universe was invisible to every other, and every framework capability was invisible to the universe doing the most rendering. If the assembler is missing something you need, add it HERE with a test (`evolve-abu`), never in a universe.

## Procedure

1. **Resolve (gate).** Invoke `canon-resolve` on the spread's cast + setting: it resolves each entity's locked references + invariants and runs `assert-spread`. A non-zero exit BLOCKS the render — lock the missing reference, never render around it.

2. **Assemble (deterministic software).** Run `scripts/assemble_prompt.py <universe> <render-spec.json> <spread-id>`. It returns `{prompt, refs, size, qa}` as a pure function of canon + descriptor:
   - `identity.register.anchor` first (or the book's `anchorRef` override when the universe anchor is unsuitable, e.g. a photo in a painterly universe);
   - each in-frame entity's block from canon for its SELECTED look (an alt-look supersedes the base look's superseded invariants and swaps in the alt anchor photo — the default sheets are NOT passed, so they can't fight it);
   - auto-disambiguation naming what makes each castmate distinct when ≥2 share the frame;
   - negatives = `rejectedPoles` + book `negatives` + `guardedNegatives` **kept only when no in-frame look positively declares the guarded feature** (a negatively-phrased invariant like `…never-a-mustache` does not count as declaring it).
   Do not edit the assembled prompt by hand. If it is wrong, the fix is in canon or the descriptor, never a one-off patch to the prompt string (that reintroduces drift).

3. **Generate.** Pass the assembled `prompt` + `refs` (anchor first) + `size` to the image model. `scripts/render_spread.py <universe> <render-spec.json> <spread-id> --out <path>` does assemble+generate in one call (3 retries); use `--print-prompt` to inspect.

   **A whole book goes through the SAME script, in batch.** Do not write a driver.

   ```bash
   render_spread.py <universe> <render-spec.json> --all --out-dir spreads/ --jobs 4 --skip-existing
   render_spread.py <universe> <render-spec.json> spread-07 spread-12 --out-dir spreads/
   ```

   `--jobs` defaults to 1, so single-spread behaviour is unchanged. A per-spread failure never
   aborts the batch, because a 69-spread render is expensive and a driver that stops at the
   first refusal throws away every spread that would have landed after it; the run exits
   nonzero and names what failed. Pair `--all` with `--dry-run` as a FREE pre-flight over the
   whole book: refusals are pure text checks, so every uncast character, wrong-era look, bad
   plate key and missing ref is caught before a cent is spent.

   Added 2026-07-31 because every book had been writing the same ThreadPoolExecutor wrapper
   around this script, twice after `pave-the-path` first flagged it.

4. **Read back.** Invoke `render-readback` on the output: crop-zoom every invariant in the returned `qa` list. Any DEFECT regenerates FROM SCRATCH (re-run render_spread.py; the model is stochastic), never an edit pass. Loop until all invariants PASS.

## Wrong-era selection is refused PRE-SPEND (SPEC v0.18)

A variant is a body a thing wears for part of its life: a character's `altLook`, a setting's
era plate. Nothing used to gate which one a spread could select, so every variant was legal on
every spread. On a book spanning three ages of one man, nothing stopped a 1933 beat picking
the `elder` look, and nothing stopped a 1990 beat silently falling through to the default
young face. **Both are silent**: the render succeeds, it passes read-back (the wrong era's
invariants all hold), it is beautiful and internally consistent, and it is of the wrong person.

Declare the window in canon and the date on the spread:

```jsonc
// canon/entities/kenneth-hagin.json
"structured": {
  "validFor": {"from": 1935, "to": 1973},              // the DEFAULT look
  "altLooks": {
    "bedfast": {"validFor": {"from": 1933, "to": 1934}, ...},
    "elder":   {"validFor": {"from": 1974}, ...}       // open-ended
  }
}
// canon/entities/the-broken-arrow-ground.json — a setting's era axis is its PLATES
"contract": {"plates": {"era-farm-empty-pasture": {"validFor": {"to": 1930}}}}
// render-spec.json
{"id": "spread-01", "when": 1933, "cast": [{"id": "kenneth-hagin", "look": "bedfast"}]}
```

The refusal NAMES the variant that is legal at that date, which is where the saving is: a gate
that only says no still sends you to read canon. `when` is a plain number, so a universe may
count in years or in beat indices. Both ends are opt-in: no `when`, or no declared windows, and
the spread compiles exactly as before.

**Window the WHOLE set or none of it.** An undeclared variant stays legal at every date, so a
partially windowed set has a hole precisely where it looks closed. `lint-universe` warns
`VALIDFOR-PARTIAL` for this and errors on `VALIDFOR-INVERTED` / `VALIDFOR-MALFORMED`.

## Gates honored
- **Canon-resolve before the prompt:** no render except from a resolved, asserted record.
- **Era gate:** a look or plate selected outside its declared `validFor` window is refused
  before any spend, naming the variant that is legal at the spread's `when`.
- **Unregistered cast:** an id canon has never heard of REFUSES by name, rather than raising a
  FileNotFoundError that names a path instead of the spread and, in a batch, took every
  remaining spread down with it.
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
- Authoring/altering an entity or adding an alt-look → the `add-*` skills (an alt-look is `structured.altLooks.<key>` with `anchorPhoto`, `supersedes`, `invariants`, and the two suppression fields below). A **declared-future/prophetic** look additionally sets `keepSheets`/`keepPhotos` (SPEC v0.10): its face is continuous and the future has no photograph, so without a kept face source only the superseded body sheets reach the model. The assembler refuses that rather than render a stranger.
- Stating how tall one character is beside another → `structured.scale` on each entity (SPEC v0.10). The assembler emits a `RELATIVE SCALE` line automatically when two in-frame characters declare a relation; never write heights into a spread's `scene`.
- Locking a reference matrix → `shoot-references`.
- The cover (portrait + baked title) → `cover` (may share the assembler).
- Whole-book orchestration (worktrees, manuscript gate, delivery) → `render-book`; editing a shipped book → `update-book`. Both invoke THIS skill for the per-spread step.

## State a device's orientation RELATIONALLY, never camera-relative

The generator already injects a device guard: *the glowing display is on the screen side, and that
side FACES ITS USER.* A scene can still defeat it, and the way it defeats it looks like good
camera direction: **"over his shoulder from behind, so we see the back and edge of his laptop."**

That sentence asserts a CAMERA-RELATIVE fact. It is only true when the camera sits exactly behind
the user, and the camera almost never lands exactly there. Put it a few degrees to one side and the
model still obeys the words: it turns the lid away from the viewer, which now means turning it away
from the USER too. The screen ends up facing a wall, or facing the reader while the character
stares past it, and the character is using a machine he cannot see.

Say instead what is true from every camera:

    BAD:   over his shoulder so we see the BACK and edge of his laptop
    GOOD:  the open lid tilts BACK TOWARD HIM so the screen points at his face and the keyboard
           lies between the screen and his hands; we read it only by the light thrown up onto him

Then describe the camera separately, and do not tell the model what it will see of the device.
If you want the screen CONTENT visible, that is a different composition: put the camera behind the
user and say the screen is visible over their shoulder, which is consistent rather than in conflict.

The same trap applies to anything with a front and a back that belongs to a character: a phone, a
book, a hand mirror, a photograph being shown to someone. Orient it to its owner, never to the lens.

Earned 2026-07-29 on *Atlas Surrendered*, twice from one copied sentence: spread 11 rendered the
screen facing the viewer and spread 29 rendered the lid opening away from the man toward the wall.
Both scenes ALSO contained a correct relational clause ("the screen faces him"); the camera-relative
sentence won because it was more specific.

## Reading material faces the reader, never the camera

A book, notebook, page, ledger, letter or document that a character is reading or writing belongs to THEM, so it is oriented for them: top edge away from them, text running the direction they read, and therefore foreshortened, tilted or partly upside down from the camera. Image models default to squaring the page up to the lens so the viewer can read it, because that is what stock illustration does, and the result reads as staged the instant you notice it. If the camera cannot see the page clearly, that is correct.

DO NOT bake this as a per-book negative. It is enforced for you, on every render, by the shared prompt guard in
`~/.agents/skills/chatgpt-images/scripts/prompt_guards.py`, which both image generators import. A per-book restatement
is worse than nothing: the guard's own signature is what makes re-application idempotent, and an earlier version of the
probe list matched paraphrases, so a book's weaker restatement SUPPRESSED the authoritative rule.

History, because it took three passes to land: prose in a SKILL.md (ignored), then a per-book negative plus a guard
whose word list had no entry for "card" and which simultaneously demanded "NO real readable letters" — so on a scene
that specified exact designed text the model had to choose, and it chose legible-by-rotating-to-the-lens. Caught by Gary
on `it-was-not-broken` spread 36 ("you continuously flip the book", 2026-07-25) and again on
`she-had-everything-but-peace` spread 16 (2026-07-29). The guard now names the resolution: legibility is a CAMERA
problem. Move the camera to the reader's side; never turn the page.

The one exception is a page the scene explicitly presents TO the viewer as a designed element under CANON rule 6, which is a deliberate composition and not a character reading.
