---
name: make-a-book
description: The base orchestrator for making an illustrated, narrated picture book in ANY Agentic Brand Universe universe. Runs the full chain in the load-bearing order (story -> cast -> lock -> render -> cover -> narrate -> deliver -> publish -> land -> pave), delegates every step to the matching abu:* skill, and AUTO-ADVANCES between steps instead of asking what to do next. Universe-parameterized: a per-universe CARTRIDGE skill (make-a-nof-book, make-a-hyperagent-book) supplies the universe path, register, mark, delivery wiring and universe law, then invokes this. Use directly when making a book in a universe that has no cartridge yet. NOT for a brand-new universe (start-new-story-universe) and NOT for editing an existing book (update-book).
---

> `$ABU` below is wherever ABU is installed. Find it with `ABU=$(python3 -c "import agenticstory,pathlib;print(pathlib.Path(agenticstory.__file__).resolve().parents[2])" 2>/dev/null || echo ~/.claude/plugins/cache/garysheng/abu/*/)`, or just ask the harness; never hardcode a home directory.


# Make a Book (base orchestrator)

The single door over the agenticstory pipeline for **any** universe. The engine is a pipeline,
not one skill; `render-book` is deliberately LAST. This skill sequences the chain and never
reimplements a step.

**The order is load-bearing: story -> cast -> lock -> render -> cover -> narrate -> deliver ->
publish -> land -> pave.** Invoking `render-book` first cannot work; nothing is cast or locked yet.

## How this is used

A **cartridge** skill supplies the universe facts and invokes this. If you are reading this
because a cartridge sent you here, that cartridge has already given you the universe path, the
register, the mark, the delivery wiring, and the universe's own law. If there is no cartridge for
the universe, run this directly and read `universe.json` for those facts yourself.

**Everything in this file is universal.** Anything true of only one universe belongs in that
universe's cartridge, never here. See "The cartridge contract" at the end.

## AUTO-ADVANCE — the whole point of this skill

**Default to CONTINUE. Do the next step without asking.** The failure this fixes is turning every
hand-off into a "should I proceed to narration?" checkpoint. Run the chain end to end, **through
publish**, and surface the operator at the **two real gates only**:

1. **Voice-gate FAILS** on the manuscript (a words-before-art violation the author must resolve).
2. **A readback defect where the fix is a judgment call** (re-render vs accept a known defect). A
   clear defect with an obvious fix (wrong side, invented character, register break) you
   regenerate from scratch and keep going. Only a genuine taste call stops for the operator.

Everything else (casting, locking, per-spread rendering, cover, narration, staging, **and the
public publish**) is auto-advanced and reported, not asked. When torn between asking and
continuing, continue and report.

### Ask with the TOOL, not with prose (Gary, 2026-07-30: "use it a lot more")

**Any question that has options is an `AskUserQuestion` call, not a paragraph.** This rule
already existed and was still under-used four separate times in one session: the glow
reading, the beat budget, Lorraine's likeness, and the book-thickness invariant were all
asked in prose. Two of them went unanswered for hours because a question buried at the end
of a long report is easy to scroll past, and a tappable option is not.

The bar is low on purpose. If you are about to write "let me know which you prefer", "your
call", "want me to X or Y", or a bulleted list of choices, that is the tool. Reserve prose
for questions with genuinely no option set, which are rare.

Lead with a recommendation marked "(Recommended)", and attach a `preview` whenever the
options are concrete: candidate art, a beat budget drawn movement by movement, two versions
of a defective spread. He should compare artifacts, not adjectives.

### When you DO surface him, use `AskUserQuestion`

Auto-advance says **how often** to stop. This says **what stopping looks like**: tappable options,
never a wall of prose to answer in free text. Applies to the two gates, to the story-shaping calls
delegated to `add-story` (spine object, title, beat-count, how far the book reaches), and to
anything else that genuinely needs him.

- **`preview` is mandatory when the options are concrete.** A candidate title beside the source
  quote it came from; a beat budget drawn movement by movement; the two versions of a defective
  spread. He should compare artifacts, not adjectives.
- **Lead with a recommendation**, first in the list, marked "(Recommended)". You did the reading.
- **A readback-defect gate is a two-option question, not an essay**: regenerate vs accept, with
  the actual crop as the preview.
- **Never use it to ask permission for something this skill auto-advances.** A nicely formatted
  "should I publish?" is still asking, and still wrong.

### Publish is auto-advanced too

A finished, readback-clean book **ships without asking**. Do not stage-and-hold, do not describe
publishing as a decision waiting on him. He commissioned the book; shipping it is the deliverable.

**Publish anyway when the run was imperfect.** A re-rolled spread, an accepted known defect, a
compromise you already reported is NOT a major concern. Ship and say what you settled for.

**HOLD only on a MAJOR concern**, meaning one of these and nothing softer:
- A real person is depicted or named in a way that could **dishonor** them, unresolvable in craft.
- A **doctrinal** claim you are genuinely unsure the universe holds.
- A **defect you could not fix**: art still failing a canon invariant after re-rolls, a garbled
  cover title, an asset that will not verify.
- The book **contradicts or duplicates a shipped sibling** in a way that needs his call.

If one is live, say so in a sentence or two, publish nothing, and wait. Otherwise ship.

## DISPATCH THE STEWARD. It ships with the plugin and nobody uses it.

`abu-steward` is a subagent in this plugin whose entire job is "reach for the RIGHT framework
verb instead of hand-rolling, and FLAG any gap rather than silently working around it." On
2026-07-30 it was invoked **zero times** across a full book session in which the main agent
hand-rolled five shoot scripts, a photo-stack extraction, and prompt assembly the framework
already owned. The countermeasure was installed and unused for the entire run.

**So dispatch it, do not merely have it.** For each chain step that touches canon or art
(cast, lock, render, cover), hand the step to `abu-steward` via the Agent tool rather than
doing it inline.

Why a separate context and not more instructions to yourself: the main agent is carrying the
book's momentum and is therefore the WORST judge of "should I write a quick script here." It
has a reason to keep moving. A fresh context whose only question is "which framework verb is
this" has no such incentive, and it has not spent an hour becoming attached to a plan.

Give it: the universe path, the step, and the entities involved. Expect back: the verb it
used, or an explicit FLAGGED GAP. **A gap it flags is a real finding, not a failure of the
run** — route it to `evolve-abu` and keep going.

You still own the two operator gates and the final report. The steward owns verb selection.

## Prose does not bind. Refusals bind.

Every rule this chain BROKE on 2026-07-30 existed as prose in a skill file: use
`AskUserQuestion` at a gate (ignored four times), angels are light beings (a European man was
rendered), show the operator every shot (written that same session, then not done). Every
rule it OBEYED was a refusal in code: `assert-story` on unlocked references, `build-docs
--check` failing the suite, the uncast-character guard, and the `prompts.md` TODO refusal,
which ended a five-times-repeated workaround the moment it existed.

**So when you catch a rule being broken, do not restate it more emphatically. Move it into
something that stops you**, and put the refusal at the choke point every path already goes
through. A rule that lives only in prose is a suggestion with good intentions.

## Environment

- **The engine is NOT pip-installed.** Run the CLI from its repo dir:
  ```bash
  ENG=$ABU/engine
  (cd "$ENG" && python3 -m agenticstory.cli <cmd> ...)
  ```
- **Precheck the style lock.** `universe.json` `identity.register.anchor` must be non-null. If it
  is null, STOP: the style is not locked and every render will drift.
- **Every paid image call goes through `uv run`, never bare `python3`.**
  `~/.agents/skills/chatgpt-images/scripts/generate_image.py` is a PEP 723 inline-deps file and
  plain `python3` dies on `ModuleNotFoundError: openai`. Piping to `tail` masks the failure, so
  use `set -o pipefail` and confirm the output file exists.
- **Give the renderer a long Bash timeout and batch it.** It fires spreads in parallel; a batch of
  6+ blows past the default 2-minute limit and the killed children leave a partial set (landed
  PNGs are fine, missing ones just re-run). Pass `timeout: 600000`, batch ~7 spreads.
- **Do NOT background the renderer with `nohup ... &`.** The parent exits instantly, the harness
  reaps the process group, and you get empty logs and zero PNGs. Run it in the FOREGROUND of a
  single tracked background task.
- **`validate` is universe-wide, `assert-story` is yours.** With sibling sessions mid-flight,
  `validate` reports problems belonging to other books. Filter to your own ids; the gate that must
  be green for you is `assert-story <your-story-id>`.

## The chain

### 1. Story -> `abu:add-story`
Author `stories/<id>.json`: logline, the **spine** (a primer explains, a thesis argues, a testimony
recounts; never assume hero-journey), the **refrain**, and the **beats** (each with `text`,
`characters`, optional `location`, and **provenance** — every beat traces to a real source). Then
the **casting sweep** (`abu:casting-sweep`): reuse-first. Every reuse is a crossover
receipt; only genuinely new names become new entities.

### 2. Cast -> `add-character` / `add-setting` / `add-visual-metaphor` / `add-motif` / `add-prop`
Scaffold via `add-entity <universe> <kind> <id> --name --origin`, then fill invariants + prose.
Leave `requiredForRender: []` until `shoot-references` locks the sheets.

- **A `kind: character` entity with no `structured.render` block does not crash the framework
  compiler. It silently loses its prompt-craft, which is worse.** `compose-spread` falls back to
  the entity's `requiredForRender` sheets plus its deslugged invariants and renders happily. What
  goes missing is the `always` prose: the sentence that actually steers the model, as opposed to
  the kebab QA key that only checks it afterwards. An invariant reading
  `north-star-pendant-front` does not tell the model "a faceted four-point STAR, NOT a Latin
  cross"; the render block does. This is the documented cause of signature wardrobe and a
  star-versus-crucifix pendant regressing across whole batches.
  **So dry-run the cast before writing the render-spec and check `structured.render.poses` on
  every character.** Where it is missing, REPAIR the entity (additive only: restate its locked
  invariants and prose as `always` + poses, invent no design). Do not demote it to an extra, which
  drops the QA invariants too. (A universe-local fork of the compiler may HARD-CRASH on the same
  entity instead of degrading. That is a difference between implementations, not a reason to keep
  a fork.)
- **A reusable environment is a SETTING, built once.** A recurring place is a locked `setting`
  with fixed geometry and multiple camera-angle sheets, not re-described per spread (that drifts
  geometry and flips seating). Cast the right angle per beat.
- **Any entity whose real-world shape a reader already knows** (a book, a lamp, a boat, a badge)
  needs at least one GEOMETRY invariant and a filled `contract.blocking` naming proportions and
  scale. Colour invariants do not constrain shape, and read-back cannot catch what canon never
  specified.
- **A prop that appears in two states needs both sheets.** When a beat shows an object in a state
  no locked sheet depicts, generate the state; do not let the model derive it.
- **A load-bearing "always pass X with Y" rule must live in `sheets` + `poses`, not prose.** Prose
  cannot make the compiler pass a file.
- **When you add a pose, add its sheet key in the same edit**, or the compiler hard-exits on a
  pose naming a sheet that does not exist.

### 3. Lock -> `abu:shoot-references`
Generate, read back, and lock each new entity's reference matrix (register-anchor-first, rejected
poles as negatives, regenerate-from-scratch on defect). Set `requiredForRender` to the locked
shots. Idempotent, so a re-run only shoots what is missing.

- **Independent renders run PARALLEL; a reference matrix runs CHAINED.** Chain master -> face ->
  the rest, so every plate inherits one identity.
- **A code-drawn massing seed is right for ARCHITECTURE and wrong for an ORGANIC SILHOUETTE.**
  Boxes ARE the truth of a boat, a street or a walled city, and seeding those off a massing sheet
  returned one consistent vessel across open, shut and afloat. Seeding a colossal HUMAN-FORM
  figure off the same crude boxes made the boxes the DESIGN: blocky limbs, a floating cube head,
  glowing seams that read as neon piping, a video-game asset instead of a dread-object. The
  blueprint guard says paint none of its surface, but it cannot stop the model inheriting a
  silhouette that was only ever scaffolding. For anything whose correct shape is organic,
  describe the form in prose and let the model find the silhouette.
- **Seed a multi-state object's chain on a CODE-DRAWN BLUEPRINT, not a state plate.** A schematic
  fixing geometry and arguing nothing leaves the model the least to invent, so every state
  inherits one shape. Three states generated in parallel come back as three different objects.
- **Build a multi-state study plate by COMPOSITING the locked plates in code**, never by
  generating it. A generated study sheet can drift from the states it claims to summarize; a
  composite cannot. It is also free.
- **For a locked SETTING, verify the EMPTY plates first**, then populate people one at a time.
  That is how the geometry stays honest.
- **For a state defined by ABSENCE, generate from the anchor alone**, never chained off a sibling
  state. A reference image outranks any number of words, so the thing that is supposed to be gone
  comes back. Negate the missing thing by name.

### 4. Words + render -> `abu:render-book` (per spread: `compose-spread`)
Words-before-art: run `abu:voice-gate` on the manuscript FIRST. Then:
```bash
(cd "$ENG" && python3 -m agenticstory.cli validate "$U")            # must be OK
(cd "$ENG" && python3 -m agenticstory.cli assert-story "$U" <id>)   # the load-bearing gate
```

**Render through the framework compiler, `abu:compose-spread`.** It assembles the prompt
from canon so a per-book prompt can never drop a rule, and it carries the guards below. **Never
fork it per universe.** A universe-local compiler cannot see guards earned elsewhere and drifts
into a disjoint feature set; that failure is documented and cost real books.

Then `abu:render-readback` every image.

**The compiler already enforces these. Read what it prints and you get them free:**
- **Uncast characters named in scene text.** A scene mentioning a person the spec does not cast
  does not get a tasteful anonymous shoulder; it gets a whole different human, confidently
  rendered. It refuses before spending. An over-the-shoulder single still needs BOTH people cast,
  because the shoulder is a person. Quoted spans are stripped first, since a name in designed
  lettering is not a body in frame.
- **Single-image guard.** Several canon references are multi-panel study sheets, and the model
  copies their LAYOUT, returning a contact sheet instead of a scene.
- **Anchor style guard.** The register anchor is passed FIRST on every render, so on a spread that
  casts nothing else it is the only content signal and its subject leaks into the scene.
- **Per-spread overrides** (`style`, `negatives`, `anchorRef`, `size`, `settingRule`,
  `allowMultiPanel`, `allowUncast`) so one book can carry a second diegetic register, and so the
  3:4 cover and closing plate render portrait inside a landscape book.

**Prompt and spec discipline:**
- **NEVER write a blanket no-text negative.** In-art text is a first-class design element; a
  blanket ban renders a real book or sign as a blank slab. Forbid **stray or invented** text only
  and carve out the exception: text a scene specifies as an exact quoted string is designed and
  must be spelled exactly.
- **A scene must not contradict itself.** A beat requiring a partial figure (a hand, a shoulder)
  while the negatives say "no people in this image" resolves by DELETING the required subject.
  State the subject positively and at size, and scope the negative.
- **Cast by POSITIVE description; naming a thing to exclude plants it.** Describe who IS in frame.
- **Negate the anchor's own subject on a bare spread.** A dry-run showing only one ref is casting
  nothing but the anchor.
- **A multi-state entity needs a per-spread `bake` naming ONE state**, plus "render exactly one
  state and no other". Handed the entity's whole rules, the model draws a chart of all of them.
- **An emotion the caption depends on must be stated as a negative too.** "Quietly asking a hard
  question" reads as serene unless you also say what the face is NOT.
- **An "undefended" or "open" face needs the anatomy spelled out**, not just the adjective: brow
  smooth, eyebrows level or raised, eyes fully open, mouth relaxed, plus what he is NOT.

**Camera and pose:**
- **Camera geometry must be physically possible.** Never show interior detail from an exterior
  camera. An establishing exterior angle is establishing-only.
- **A left-hand-drive vehicle seen from the front is MIRRORED**: the driver appears on the
  viewer's RIGHT. State viewer-relative sides explicitly.
- **People in vehicle seats face FORWARD**, heads turning to talk; torsos do not rotate. Drivers
  keep hands on the wheel, seatbelt on, eyes on the road.
- **A POSE IS A WARDROBE SELECTOR, so it must match the camera you will get.** Any scene reading
  as "walking away", "climbing", or "being turned around" WILL render as a back view, and a front
  pose then bakes front-only markings onto a back. Decide the camera first, then the pose.
- **A character seen from behind on a cover is a `back` pose**, with its sheet.
- **Re-framing a two-person scene can silently swap the blocking.** Name the furniture beside each
  person, not viewer-left/right.

**Process:**
- **A contact sheet of four is the right read-back unit.** It catches composition, wrong
  character, invented people, panels, photoreal drift and gross canon breaches. Crop-zoom only
  what a beat actually depends on.
- **Back up every roll when two failure axes are live.** Each roll fixes one and breaks the other,
  and without copies there is nothing to compare. Park rejects in `<book>/candidates/` under names
  stating what is wrong, never as `spread-*` (the render guard would accept them as inputs).
- **Correct a WRONG INVARIANT rather than re-rolling good art.** When a plate is right and the
  rule is impossible, fix the rule and record why in `authority.note`.
- **Fix the ENTITY, not the spreads.** Ten wrong spreads from one bad sheet is one entity rewrite
  plus a re-render, not ten re-rolls. Chain a known-good sibling in as the control.
- **Classify beat states by READING them, not by regex.** A `\bopen\b` sweep matches "open hand".
- **Do not re-roll good art over a sub-legible detail.** A badge or pendant too small to read is
  correctly just a shape; read it back only where the beat frames it legibly.

### 5. Cover -> `abu:cover`
Portrait 3:4, register anchor first, the universe mark, and the title baked as integrated
lettering with the exact string quoted. Read the cover back and check spelling letter by letter;
regenerate from scratch on any typo.

- **Conform the aspect with the framework tool, never a hand-rolled pad.** Models emit a
  producible 2:3; the reader wants 3:4. Flat side bars seam visibly against textured art. Use
  `conform_cover.py --mode pad` (blurred self-bleed).
- **The closing plate needs its OWN title-free art.** A baked-title cover leaves no untitled
  version to fall back on, and the plate sits behind the overlaid closing verse. Generate a
  dedicated clean plate with a calm, open lower half.

### 6. Narrate -> 7. Deliver -> 8. Publish
Cartridge-specific wiring. The universal parts:
- **Words changed means narration is re-cut.** TTS spend is unconstrained; a stale clip is not.
- **Verify at the reader's own path, then at the live page.** A storage probe proves the bucket
  has the assets; it does not prove the page renders. Poll the live URL for 200 and confirm the
  title is present before reporting a link.
- **Captions may not be server-rendered.** Grepping the live HTML for caption text is an invalid
  check on a client-rendered reader. Verify against the deployed bundle or the reader itself.

## Land the work -> `abu:land-work` (ALWAYS, never "parked")

The run is not over until every branch it opened is merged or queued. Never end a report with
"committed but parked". Parking is an unfinished job that compounds into stale worktrees.

```bash
(cd "$ENG" && python3 -m agenticstory.cli land "$U" --drain-only)         # FIRST, drain prior runs
(cd "$ENG" && python3 -m agenticstory.cli land "$U" --branch <branch>)    # LAST, once per repo
```
Safe by construction: merges only when the target is checked out nowhere or held by a clean
worktree, QUEUES when a live session holds it dirty, and never uses `git update-ref` or
`git branch -f`. A queued merge is a SUCCESS worth one line. Surface only a genuine CONFLICT.

**Repo hygiene, because these repos usually have other sessions live in them:**
- `git add` your paths explicitly, never `-A`. Never revert or commit another session's work.
- **Re-check `git worktree list` immediately before touching any ref**, not once at session start.
- Clean only your own entity's directory by name; a glob like `reference/*/*.log` matches other
  books' tracked provenance.
- **Historical provenance keeps its pre-rename paths.** A recipe records what was actually passed
  at generation time; rewriting it to match a later move falsifies it.

## 9. Pave the path -> `abu:pave-the-path` (ALWAYS, the real last step)

**Run it after the book ships and the branches land, on every book, without being asked.**

This step exists because the skill it calls is retrospective, and a retrospective skill that
depends on somebody REMEMBERING it does not run. Its first outing had to be requested by hand,
and its output was a list of suggestions nobody would have actioned. Both failures had the same
root: nothing invoked it. Now the chain does.

It reads the run's diff and the scratchpad (never your memory of the run), finds the hand-rolled
code and repeated manual steps that will certainly recur, and BUILDS the ones that clear its bar.
It integrates by default; it does not file suggestions. Expect most candidates to be declined and
a small number to be paved.

The signal that this step is being skipped: a scratchpad full of `*.sh` files at the end of a run
and a framework that is byte-identical to how it started. Every one of those scripts is a thing
you will write again on the next book.

## Every image reaches the human, or the step is not done

Applies to every art step in this chain: `shoot-references`, `compose-spread`, `cover`.

**Send the art to the operator with the harness's file-delivery tool, every time.** Opening
it in a local viewer is not delivery: they are frequently not at that machine, and "opened
12 images" then reports success for something nobody saw. Reading an image back yourself is
QA, and QA is not delivery.

Batch of four or more: one contact sheet plus individual files for anything being approved.

## Gates honored
Words-before-art + voice-gate; casting reuse-first; register-anchor-first on every render;
readback-from-scratch on any defect; spine declared not assumed; provenance per beat; render only
against locked references; publish proven at the reader's own path; the run's hand-rolled work swept and paved.

## The cartridge contract

A per-universe cartridge is thin. It supplies **only** what is not true of every universe:

1. **Universe path** (the dir holding `universe.json`) and where book folders live.
2. **Register**: its name, its rejected poles, and the anchor path, with any note about what the
   anchor is (a content-neutral swatch is safer than a character portrait, which leaks a face).
3. **The mark**, and whether it is applied by the platform layer or typed into the render.
4. **Format default** (landscape full-spread vs portrait art-and-text) and why.
5. **Delivery + publish wiring**: the platform skill, the manifest path, the publish command.
6. **Universe LAW**: doctrine, real-people policy, palette discipline, anything a render must obey
   because of what this universe believes.
7. **Entity calibrations**: per-character quirks that cost real re-rolls.
8. **A worked example**: the reference instance to imitate.

Anything a cartridge writes that would be true in another universe belongs HERE instead. If two
cartridges ever say the same thing, that is the signal to promote it.

## Skill improvement
When a run earns a lesson, route it by scope: universal to this file, universe-specific to the
cartridge. If the engine schema or a CLI verb changes, fix it here in the same session.
