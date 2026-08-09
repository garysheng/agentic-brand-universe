# Known gaps — the standing register

**What this is.** Framework gaps that have been FOUND and PROVEN by a real run, and NOT yet
closed. One entry per gap, with the evidence, the verb that would close it, and the reason it
is still open. This is the register `pave-the-path` files a DECLINED row into and the first
place `evolve-abu` looks before building anything.

**Why it is a file and not a log entry.** SAVE-LOG.md is chronological and 240KB, and the
framework has already paid for trusting it: the v0.32 changelog records a gap that "had been
FOUND AND FILED in this repo's own save log two days earlier and declined, and the next book
paid for it by hand-negating an oil lamp and a clay jar in all 27 of its spreads." A log
entry is written once and read never. Same rule as `CLAUDE.md`'s job table: discoverability
is a just-in-time problem.

**The bar to be listed here.** Identical to `pave-the-path`'s: a naming sentence with a real
next invocation. "X is missing, and the next invocation that needs X is Y." A gap with no
named next invocation is speculation and does not belong here.

**Leaving is a decision, not a default.** Every open entry says why it is still open. When a
gap is closed, delete its entry and let the SPEC changelog + SAVE-LOG carry the history; a
register of already-fixed things stops being read.

---

## OPEN

### G1. A POSE cannot `dropSheets`; only an altLook can

**What.** `structured.render.poses.<key>` may ADD sheets and prose and (since v0.29)
supersede an invariant, but it has no `dropSheets`. Only `structured.altLooks.<key>` does
(`assemble_prompt.resolve_character`). So a pose that changes the BODY or the WARDROBE is
silently outranked by the base reference image it contradicts, and a reference image outranks
a word every time — the same physics that earned `dropSheets` for alt-looks in the first
place.

**Evidence.** *An Amazing Sex Life*, nation-of-fire, 2026-08-04. Worked around by pairing an
`altLook` of the SAME key onto `jerry-man.elder-eighty`, purely so the drop would happen —
i.e. declaring a second canon object to buy one field.

**Next invocation.** Any pose that changes the body: an age era, a wound, a soaked or torn
garment, a character carrying something that hides a locked sheet's subject.

**Would close it.** `evolve-abu` → `assemble_prompt.py` (honour `dropSheets` on a selected
pose, same semantics as an alt-look) + SPEC §12.

**Still open because.** It touches the resolver every interior of every book runs through,
and the v0.32 `pose-without-look` refusal already redirects the sharpest version of this to
`altLooks`. Land it on a quiet framework day, not with seven sessions mid-render.

### G2. `chain_matrix`'s prompts.md heading parser cannot read a nested alt-look path

**What.** `parse_prompts_full` keys a shot by the file its heading points at, via
`re.search(r"reference/[^/]+/([A-Za-z0-9._-]+)\.png", head)` (`chain_matrix.py:437`).
`[^/]+` cannot cross a directory separator, so the nested path `build_plan` itself prescribes
for an alt-look shoot — `reference/<id>/<look>/<shot>.png` — never matches. The parser falls
back to the heading TEXT, so the per-shot `(WxH)` size declaration silently does not bind and
every alt-look shoot has to pass `--size` on the command line for the whole matrix.

**Evidence.** *An Amazing Sex Life*, 2026-08-04, shooting `jerry-man@elder-eighty`. Two rules
in one script disagree: `build_plan` writes the nested path and the parser cannot read it.

**Next invocation.** Every alt-look shoot whose shots do not all want one aspect — which is
most of them, since a full-body wants portrait and an expressions row wants landscape.

**Would close it.** `evolve-abu` → one regex (`reference/(?:[^/]+/)+([A-Za-z0-9._-]+)\.png`)
plus a test that an alt-look heading's `(WxH)` binds.

**Still open because.** Small and probably safe, but the same function grew a REFUSE on
duplicate output keys this week (uncommitted at the time of writing, from a sibling session)
and two edits to one parser landing blind against each other is how a shoot starts refusing
valid matrices. Land it in one pass, with both changes visible.

### G3. The alt-look face fallback is hardcoded to three matrix keys and does not refuse

**What.** When an alt-look declares no `anchorPhoto`, `chain_matrix` seeds from the entity's
face plates by looking for exactly `face-neutral`, `face-3q`, `expressions`
(`chain_matrix.py:805`). SPEC §12 permits the legacy key `face`, which `jerry-man` uses, so
the fallback resolved NOTHING, printed a note, and proceeded to shoot the look off the style
anchor alone. That is the framework generating a stranger's face and calling it an era of a
locked character.

**Evidence.** *An Amazing Sex Life*, 2026-08-04, `jerry-man@elder-eighty`.

**Next invocation.** Any alt-look on any entity locked before the `face-neutral`/`face-3q`
key set existed.

**Would close it.** `evolve-abu` → read the face keys from the entity's own sheet map (the
same `FACE_SHEET_KEYS` `assemble_prompt` already uses) and REFUSE when none resolves, exactly
as `resolve_character` refuses a look with no identity reference. A note is the wrong
severity: the run continues and spends.

**Still open because.** The fix is a refusal on a path that currently succeeds, so it will
stop in-flight alt-look shoots in universes with legacy face keys. That is the RIGHT outcome
and the wrong week.

### G4. `lock-shot`'s `master` alias is keyed on the literal shot name

**What.** `authoring.py:336`: `if kind == "visual-metaphor" and shot == "master": slot =
"turnaround"`. A visual-metaphor whose anchor plate carries a DESIGNED state name (`sealed`,
`present-night`, whatever the object's own vocabulary calls its base state) can never reach
`contract.turnaround` through the tool, so it files into `emptyPlates`, never clears
`setting_contract_gaps`, and sits at `status: unlocked` with no error anywhere.

**Evidence.** Fourth instance of the alias defect class SPEC v0.29 opened with `scale` and
v0.31 continued with `master`: the word the spec and the scaffolder give the author is not
the word the locker accepts. Each instance so far was repaired by hand-editing canon JSON to
match an already-hand-edited sibling.

**Next invocation.** The next visual-metaphor whose base state is not spelled `master` — and
the scaffolder positively invites this, since `add-entity visual-metaphor --state` lets the
author name every state.

**Would close it.** `evolve-abu` → let the entity DECLARE which shot is its anchor
(`contract.anchorShot`, defaulting to `master`) rather than matching a string, so the alias
class is closed by data instead of by adding a fifth literal.

**Still open because.** It is an engine + SPEC change (a new contract field), which is the
heaviest kind, and it wants doing once for the whole alias class rather than four times.

### G5. Nothing protects the framework repo's single CHECKOUT from concurrent paves

**What.** `land-work` classifies a target BRANCH as free/idle/busy so a merge never moves
one out from under a live sibling worktree. Nothing does the equivalent for the working copy
itself. The framework repo has ONE checkout and no worktrees, so two `pave-the-path` runs
firing at once share a HEAD: one session can create a branch, commit, `reset`, and re-commit
while another is mid-edit in the same files, and the second session's commit silently lands
on top of the first session's feature branch instead of where it meant to go.

**Evidence.** 2026-08-04. A sibling session created `fix/prompt-prose-hygiene`, committed,
reset to `HEAD~1`, and re-committed as `773e618`, all inside another session's build of
v0.33. The v0.33 commit therefore has `773e618` as its parent and sits on a branch it never
chose, sharing two files with work that is not its own. Nothing errored, nothing warned, and
the collision was only visible because the committing session read `git log` afterwards.

**Next invocation.** Immediate and recurring: a fleet of book runs ends in `pave-the-path`,
and `make-a-book` wires that in as the last step of every book. Seven sessions were live in
nation-of-fire the day this was found.

**Would close it.** `evolve-abu` → `land-work` (or a small sibling of it) gains a
START-OF-PAVE claim on the framework repo: report the current branch and any uncommitted
sibling work BEFORE editing, take a worktree per pave rather than sharing the checkout, and
refuse to commit onto a branch this session did not create. The framework already owns the
right primitive for this; it is simply pointed at the universe repo and not at itself.

**Still open because.** It wants designing with the parallel fleet in mind rather than
patching mid-fleet, and the wrong version of it (an over-eager refusal) would stop paves
outright. Recorded the day it bit, with the exact commit ids, so the design starts from
evidence.

---

### G6. The visual-metaphor location gate hard-requires a `blueprint` the authoring skill calls optional

**What.** `setting_contract_gaps` lists `blueprint` in `SETTING_GATE_FILE_FIELDS`, so any
visual-metaphor cast as a beat LOCATION blocks `assert-story` on `blueprint is null`, while
add-visual-metaphor treats the blueprint as advisory for organic forms.

**Evidence.** 2026-08-04, all-the-data-in-the-world beat 22: `the-city-of-threads` (organic
aerial city, honestly no massable geometry) blocked the story gate. The run declined to
falsify a blueprint; the beat was re-homed from `location` to cast, which is honest for a
portrait-of-the-metaphor but is a workaround where the metaphor truly stages a scene.

**Next invocation.** Any book staging a beat INSIDE an organic locked metaphor.

**Would close it.** Make `blueprint` advisory for kind=visual-metaphor when the entity
declares `blueprintWaived: "<reason>"`, keeping the hard gate for architecture.

**Still open because.** Wants a spec decision (which kinds owe which files), not a mid-fleet
patch.

---

### G7. `compose_prompts` and `chain_matrix` disagree about scaffold TODO stubs

**What.** compose_prompts treats the scaffolder's `TODO(author)` stub bodies as authored and
composes 0 shots, while chain_matrix refuses on the same stubs; plus `-> None` headings and
character-shaped warm-studio boilerplate on non-character kinds.

**Evidence.** 2026-08-04, shooting `the-archive-of-everything`: hand-unblocked once.

**Next invocation.** Every new non-character entity shot from a fresh scaffold.

**Would close it.** One shared stub predicate both scripts call; kind-aware prompt
boilerplate in the scaffolder.

**Still open because.** Touches two skills' scripts and the scaffolder together; wants one
deliberate change, not three drive-bys.

---

### G8. The code-drawn blueprint is dropped from non-seed conditioning while --print-plan promises it

**What.** chain_matrix's plan output lists the blueprint on every shot, but recipes prove
only the seed received it — the v0.29 "surface that looks like it enforces and doesn't"
class.

**Evidence.** 2026-08-04, the-archive-of-everything: plates passed read-back because the
seed carried the geometry, but the plan lied.

**Next invocation.** Any multi-state chain where a late state drifts geometry and the
operator trusts --print-plan.

**Would close it.** Either pass the blueprint on every shot or make the plan print what is
actually passed.

**Still open because.** Recorded same-day with recipes as evidence; fix is small but sits in
the same script as G7's refactor.

---

### G9. Beats -> manuscript sync is hand-rolled every book (third occurrence)

**What.** The invariant beats == manuscript == captions is enforced by book-doctor, but no
script GENERATES the manuscript from beats or re-syncs after an edit; make-a-book already
records two runs doing it by hand, and all-the-data-in-the-world did it twice more inline
(initial write, then a one-word beat-8 fix re-mirrored by hand).

**Evidence.** 2026-08-04, all-the-data-in-the-world: two inline python heredocs whose whole
job was title + mark + `## n` + beat text + closing verse.

**Next invocation.** Every book, twice (first write and every caption edit).

**Would close it.** `compose-spec/scripts/sync_manuscript.py <universe> <story>`: emit the
manuscript from the StorySpec deterministically; `--check` mode for book-doctor parity.

**DIRECTION CORRECTION, 2026-08-05 (keep-god-out-of-the-state, fourth occurrence).** The
proposed fix above emits the MANUSCRIPT FROM THE BEATS, and that is backwards for a book
written manuscript-first. voice-gate blesses the MANUSCRIPT, so the manuscript is the
authority and the beats are the derivative; generating the manuscript from beats would mean
the blessed artifact is regenerated from an unblessed one. That run built the arrow the other
way (`build_story.py`: parse `## n` sections out of the blessed manuscript, emit beat `text`
verbatim, so beats == manuscript by CONSTRUCTION rather than by care) and it worked first try.

**So the closing verb needs BOTH directions and a declared authority**, not one:
`sync_beats.py --from-manuscript` (manuscript-first books, the common case) and
`--from-beats` (beats-first books), plus `--check` for book-doctor parity. Building only the
filed direction would have shipped a tool this run could not have used.

**Still open because.** Filed during a live seven-session fleet under G5; building it means
touching the shared checkout, so it is queued for the next quiet window. Re-confirmed open
2026-08-05 for the same reason: a sibling session was committing to nof-universe minutes
before this entry was written.

---

### G10. `render_cover.py` cannot express the two closing-plate decisions

**What.** compile_cover has `--no-text`; render_cover does not, so the working convention is
`--title ""` (discovered only by reading a prior book's recipe). And the hero is auto-cast
from the story, so a plate whose scene wants NO figure quietly renders the hero into it.

**Evidence.** 2026-08-04, all-the-data-in-the-world plate-0: `--no-text` errored; the
sky-and-sparrows scene came back with Jerry standing in it. The result was kept because the
verse made it work, which is luck, not control.

**Next invocation.** Every book's closing plate.

**Would close it.** Pass `--no-text` through to render_cover and add `--no-hero`.

**Still open because.** Same G5 fleet constraint; a two-flag change queued for the quiet
window.

---

### G11. `compose_prompts --all` deletes the code-drawn section that `chain_matrix`'s detection is keyed on

**What.** `compose_prompts.py` prints "code-drawn, not composed (deterministic art): blueprint"
and writes a prompts.md with NO `## blueprint` section — but `chain_matrix.py` builds its
code-drawn set from the shots parsed out of prompts.md sections (`code_drawn_shots(refdir,
shots)`), so a blueprint with a perfect `agenticstory.elevation` recipe on disk is simply not
in the plan: not printed, not passed, no refusal anywhere. The v0.31 promise ("found and
passed automatically... you do not pre-declare anything") holds only while the scaffolder's
section survives, and the compose step removes it. Same family as G7/G8 (the two scripts
disagree about what prompts.md means), but this variant loses the geometry ENTIRELY on the
seed too.

**Evidence.** 2026-08-05, nation-of-fire `the-liberty-bell`: fresh scaffold, `abu elevation`
blueprint with recipe, `compose_prompts --all`, then `--print-plan` showed no code-drawn line
and both shots conditioned on anchor/seed only. Hand-restored the `## blueprint` heading with
a fallback body and the plan immediately carried the blueprint on every shot.

**Next invocation.** Every blueprint-seeded visual-metaphor or prop whose prompts are
composed rather than hand-typed — which is the recommended flow for both.

**Would close it.** Either detect code-drawn assets from `contract.states` /
`structured.sheets` + recipes on disk (not from prompts.md sections), or have
compose_prompts KEEP the section with a generated "code-drawn, never generated" body.

**Still open because.** Sits in the same two scripts as the G7/G8 refactor; filed to be
closed with them in one deliberate change.

---

### G12. `--bless-seed` hardcodes `blessedBy: "human"`, so a delegated agent-readback blessing must falsify or hand-amend the marker

**What.** `chain_matrix.py --bless-seed` writes `master.golden.json` with `"blessedBy":
"human"` unconditionally. A supervised chain run by an agent under an operator's direction
(the normal make-a-book / steward-subagent case, and the exact case the-sealed-spring's
authority note records) has no way to record what actually happened; the tool writes a false
attestation on its behalf. That is the class the framework's own provenance invariants name:
"when a record can state either what canon SAYS or what the run DID, and they can differ, it
must say which one it is saying."

**Evidence.** 2026-08-05, nation-of-fire `the-liberty-bell`: seed blessed after a crop-zoom
readback pass by the steward subagent; the marker's `blessedBy` was hand-amended to honest
attribution because the alternative was an attestation claiming a person looked at it.

**Next invocation.** Every autonomous or fleet book run that shoots a new entity (crank-blessing-book
runs seed blessings on every new spine-object).

**Would close it.** `--bless-seed <shot> --by "<who>"` (default remains "human"), written
verbatim into the marker; optionally a distinct `agent-readback` value the chain still
accepts, since the gate's existence check is unchanged.

**Still open because.** One-flag change, but the blessing gate's semantics (what counts as a
golden) deserve a deliberate SPEC sentence, not a drive-by; queued for evolve-abu.

---

### G20. There is no `renditions` axis: a register conversion of a locked master cannot be declared

**What.** SPEC v0.37 gives an entity a register-neutral MASTER matrix. It gives it nothing for
the other half of that architecture: the per-register CONVERSIONS derived from the master. There
is no field saying "this plate set is `<master sheets>` rendered in `<style pack>`", no selector
that picks a rendition per render, and no check that a rendition was derived from the master
rather than re-shot from the source photographs. The one layer that CAN express the derivation
today is the recipe sidecar's `derivedFrom`, which no compiler reads.

The consequence is not cosmetic. A rendition added to `structured.sheets` lands in
`requiredForRender` and is then passed on EVERY render of that entity, which is the reference
pollution SPEC v0.34 documents for `the-stronghold`; keeping renditions OUT of `sheets` means
canon cannot name them at all, so choosing one per render is a hand-typed path.

**Evidence.** 2026-08-06, proof-of-vibes `russ-ballard`. Its own
`structured.renditionPolicyNote` already writes the wanted shape out in prose and opens with
"PROPOSED SHAPE, READ BY NOTHING TODAY": `structured.renditions.<register-id> = {derivedFrom:
[<master sheet keys>], sheets: {...}, medium: <style-pack-id>}`, selected per render, never in
`requiredForRender`, face sheets KEPT by default (the inverse of `altLooks`, which auto-drops
them). A universe writing the framework's next field into a note is the same signal that earned
v0.37 itself: `reference/russ-ballard/prompts.md` had written the register-neutral rule in prose
first.

**Next invocation.** The first Proof of Vibes work that renders Russ: a field-log editorial
plate, a halftone-pop flyer, a cutout sticker. That is the moment a rendition must be selected,
and today it is selected by typing a path.

**Would close it.** `evolve-abu` → `structured.renditions` on an entity + a `@rendition`
selector in the cast entry, resolving like `altLooks` but keeping the face sheets, plus a
`shoot-references` mode that derives a rendition FROM the master's plates (never from the photo
stack again, because two independent shoots of one subject produce two subjects).

**Still open because.** v0.37 deliberately shipped the half that was BLOCKING work (the master
could not be shot at all) and not the half that is merely inconvenient (a rendition can be made
by hand with `on-brand-image --entity` and a recipe). The renditions axis wants designing against
two real universes rather than one, and Proof of Vibes has not yet rendered its first work.

### G21. Register-neutrality is whole-matrix only, so `face-neutral-color` still has no home

**What.** `structured.registerNeutral` (v0.37) declares that an entity's WHOLE matrix carries no
register. The framework's own vocabulary also contains a PER-SLOT version of the same idea and
has since v0.21: `matrix.py` documents `face-neutral-color` as "a full-colour, register-neutral
face plate", an optional slot that exists because a face sheet in a non-photographic medium
carries facial architecture and no complexion. That slot sits inside an otherwise in-register
matrix, and nothing declares it neutral, so it is shot against the register anchor like every
other shot and the thing it exists to supply (a real complexion) is exactly what the anchor
overrides.

**Evidence.** The comment itself records the cost: seven render batches on gary-sheng-art's
`jesus` (2026-07-27) before anyone opened the plates and saw they were monochrome. v0.37 did not
touch that case.

**Next invocation.** The next character defined from non-photographic references whose renders
come back with the wrong complexion, which is every character in every non-photoreal universe
that has a real skin tone to get right.

**Would close it.** Not by adding a per-slot flag to the same declaration. The chain conditions
each shot on its accepted siblings, so a half-neutral matrix walks the anchor into the neutral
plates through the golden chain regardless of what the flagging says. The honest shape is a
SECOND small matrix (a look, or its own prompts.md folder) shot register-neutral and locked back
onto the entity, which is the same move `--look` already makes for an era.

**Still open because.** It needs the chain topology question answered (a neutral sub-matrix is a
separate chain, not a flagged shot inside one), and v0.37 was scoped to the deadlock that was
blocking a live universe.

### G22. A register declaring only a `stylePack` can be SHOT but not RENDERED

**What.** SPEC v0.33 made `identity.register.stylePack` load-bearing in the reference shooter: a
register declaring a pack and no inline `anchor` resolves from the pack. No render path learned
the same thing. `assemble_prompt` raises "no anchor: identity.register.anchor is null and
render-spec has no anchorRef", and the cover compiler is the same. So a universe can shoot its
entire reference matrix against its declared pack and then be unable to render a single spread.

**Evidence.** Read directly off the two files, 2026-08-06 (`chain_matrix.resolve_register` vs
`assemble_prompt` line 1467). Not yet paid for by a run, because every universe that declares a
pack today also declares an inline anchor.

**Next invocation.** proof-of-vibes, and its own `stylePackNote` names the date: "When register
A's images exist and Gary has blessed them, set `identity.register.stylePack` to the pack id ...
so the anchor moves INTO the pack rather than sitting beside it." The first spread rendered after
that move refuses.

**Would close it.** `evolve-abu` → one shared register resolver both the shooter and the spread
compiler call, instead of two implementations that already disagree.

**Still open because.** Filed the day it was found, with no run behind it yet; it wants landing
with the resolver extracted once rather than patched into the compiler as a second copy.

---

### G27. `pick_caption_pos` measures busyness, which cannot see a face or a word

**What.** `compose-spread/scripts/pick_caption_pos.py` (landed 2026-08-08) scores each anchor
by gradient energy and picks the calmest band. That is the right shape and the wrong sensor.
Energy answers "how much detail is here", and the actual question is "is the thing here
important" — which is a question about what the objects ARE. The two come apart in exactly the
places that matter: a plain-lit face scores LOW and is the worst possible thing to cover, while
a wall of pinned photographs or a foliage canopy scores HIGH and is free real estate. In-art
lettering is invisible to it as a category.

**Evidence.** the-introducer, 2026-08-08, graded against Gary's own hand placements on the same
book. He named a target on seven spreads; a fresh reimplementation of the same energy method
agreed on three, and all four misses were decided by a hand-tuned bottom-preference constant at
margins of 0.001-0.04, i.e. noise with a constant on top. Two failures were categorical, not
close calls: on spread 8 it ranked `top-left` first, which is the hero's face beside a lit lamp,
while the correct `bottom-right` is a table of papers; the runner-up `bottom-left` sits squarely
on the "MEETSUNDAY" lettering drawn into the art. Spread 16 shipped with its caption on the
ANTHROPIC door plaque and no measurement noticed, because a brass plaque and the stucco around
it are the same gradient story.

**Next invocation.** Every book. `--apply` writes `pos` into the render-spec, so a wrong pick is
not advisory — it lands in the manifest the reader and any print export both read.

**Would close it.** Keep the script as the cheap always-on floor and add a READBACK pass above
it, following `judge-slot`'s own doctrine that the judge is a ROLE first and a script second:
code computes each anchor's REAL footprint from the real caption text at the real size (a
four-line caption is a different box from a two-line one) and hands the model those rectangles;
the model says what is under them and returns protected regions plus a ranking. Geometry is
arithmetic and belongs in code; "that is the hero's face" is not. Cache the verdicts beside the
render-spec so it is one call per spread ever, and let `--apply` refuse when the readback and
the energy pick disagree.

**Still open because.** Found while building a print export in the platform repo, with the
energy script only hours old; it wants closing once, above the existing script, rather than by
tuning its constants a third time.

---

### G28. `detect_handroll` only runs inside a chain, so it misses hand-rolls outside one

**What.** `pave-the-path/scripts/detect_handroll.py` has the right signatures and names the
verb that owns each one, but the only thing that invokes it is `pave-the-path`, at the end of
an ABU chain run. Book work does not stop at the universe: a finished book is consumed by a
platform repo, a site, a print pipeline, and those sessions touch the same plates, manuscripts
and recipes with no chain to close and no reason to read this repo's docs.

**Evidence.** 2026-08-08, garysheng-books, judging caption placement on the-introducer: a PIL
contact-sheet montage hand-rolled in a heredoc, with `render-readback/contact_sheet.py`
installed. The detector's own docstring already records two prior occurrences and concludes
"the detector has to carry the pointer" — this third one shows the pointer never gets read
when the detector never runs. The same session also hand-rolled a caption scorer that
duplicated `pick_caption_pos.py` (see G27).

**Next invocation.** Any session in a consuming repo that touches ABU output: the books
platform, a print export, a site build. That is most sessions that are not themselves a render.

**Would close it.** Make it runnable from anywhere with no chain: `detect_handroll.py .`
defaulting to the cwd, plus a `--since <ref>` mode that scans a git diff rather than a
scratchpad, so a consuming repo can run it as a pre-commit or a CI step. Then name it in the
places that work happens rather than only in `pave-the-path`.

**Still open because.** The stopgap landed the same day (a pointer in the consuming repo's
CLAUDE.md naming the four scripts reached for most from there), and the real fix wants doing
once, for the whole class of consuming repos, rather than one CLAUDE.md at a time.

---

## Filing a gap here

Append an entry with the five headings above (**What / Evidence / Next invocation / Would
close it / Still open because**). If you cannot write the **Next invocation** line, do not
file it. If you cannot write **Still open because**, you are not filing a gap — you are
deferring work, and the honest move is to build it.


---

### G14. The uncast-name guard false-positives on common English words that are also entity given-names

**What.** `_cast_name_tokens` matches a CAST entity's name tokens against scene text, but an
entity whose id contains an ordinary English word makes that word un-writable in any scene.
`miss-odessa` makes "impossible to MISS" a refusal; `roman-witness` makes "Roman capitals" and
"a Roman ruler's head" a refusal. The guard is right to be conservative and its escape hatch
(`allowUncast`) works, but the escape is per-spread and blanket: it disables the whole check
for that spread, including the real uncast-person case it exists to catch.

**Evidence.** 2026-08-05, keep-god-out-of-the-state: three spreads (23, 25, 29) needed
`allowUncast` purely for this, and two of them cost a refused render batch to discover. Note
the cartridge's own standing lesson: when a tool's false positive becomes a WRITING rule, the
universe has started working for the tooling.

**Next invocation.** Any universe with an entity named after a common word, which is most of
them (`the-boy`, `charon`, `victory`, `selah`, `josh`, `drew`, `abbie`).

**Would close it.** Require a match on a DISTINCTIVE token rather than any token: skip tokens
that are common English words unless the full multi-token name matches, or gate single-token
matches on capitalisation in the source text. Failing that, a scoped
`allowUncast: ["miss-odessa"]` list so one false positive does not disarm the whole guard.

**Still open because.** Touches a load-bearing refusal that several live books depend on;
wants doing once for the class, with tests, not patched per book.

---

### G15. `render_cover.py --hero-pose` is silently ignored when the hero is not a character

**What.** A cover can name any entity as `--hero`. If that entity is a visual-metaphor or a
prop, `--hero-pose` is accepted without complaint and the DEFAULT plate is passed instead of
the named one. This is the same `plate`-vs-`pose` selector split that `audit_spec_refs.py`
REFUSES on for spreads (SPEC 12), except the cover path neither refuses nor honours it.

**Evidence.** 2026-08-05, keep-god-out-of-the-state: `--hero the-house-of-three-rooms
--hero-pose the-sealed-roof` printed `Editing with ... the-house-of-three-rooms/as-built.png`
and rendered the wrong state. It cost one cover render to notice, and it was only noticed
because the ref list is printed; a book whose two states look similar would ship the wrong one.

**Next invocation.** Any cover whose hero is a multi-state spine object, which is the normal
shape of a thesis book.

**Would close it.** Give `render_cover.py` the same selector guard the spread compiler already
has: honour `--hero-plate` for non-characters, and REFUSE `--hero-pose` on a non-character
naming the available plates, exactly as `_selector_bake_guard` does.

**Still open because.** Cover path change during a live fleet; sits naturally with G10, which
is the other pair of render_cover expressiveness gaps.

---

### G16. A setting cannot declare WHO may be cast into it

**What.** A setting entity can declare its geometry, its dressing and its house rules, but it
cannot declare its OCCUPANTS. Nothing refuses a spread that stages an unrelated character in
a named real person's home. The failure is silent and it is worse than a normal miscast,
because the room is dressed with a specific family's belongings, so the render contradicts
its own reference plate while looking perfectly competent.

**Evidence.** 2026-08-05, keep-god-out-of-the-state spread 9: `wade-unseen`, canon's white
American everyman, and an anonymous wife were staged in `vegas-home`, which canon describes
as the "REAL FAMILY HOME of real living people" and dresses with a Chinese brush-painting
scroll, terracotta rice bowls and chopsticks. It rendered cleanly, passed book-doctor, and
shipped. Gary caught it on the published book: "preserve the Sheng household only for the
Sheng family... this is also not an Asian family being depicted, so spread nine is
ridiculous." The guard now lives as prose in the entity's invariants, which is exactly the
"prose does not bind, refusals bind" failure mode make-a-book already names.

**Next invocation.** Every universe with a real person's home in canon, which is every
universe that has done a testimony book. nation-of-fire alone has vegas-home, reyes-home,
daniels-house, shibata-rose-farm, miriams-household, kenzies-denver-apartment,
humming-heart-homestead and colins-apartment.

**Would close it.** `structured.occupants` on a setting: a list of entity ids plus an
`allowGuests` flag. `audit_spec_refs.py` refuses a spread casting anyone outside it, naming
the setting's declared occupants, in the same pass that already catches the plate/pose split.
A story that legitimately shows a visitor sets `allowGuests` or lists them.

**Still open because.** Same shared-checkout window as G5/G9/G13; filed the day it was found,
with the prose guard landed in the universe meanwhile so the specific case cannot repeat.


### G17. `add-entity character` births an entity its own linter hard-ERRORs on

**What.** `add-entity <u> character <id>` writes no `structured.render` block, and
`lint-universe` immediately reports `ERROR [CAST-UNRENDERABLE] <id>.json: kind 'character' has
no structured.render block, so the render compiler cannot cast it at all.` v0.31 fixed exactly
this for `visual-metaphor` (the scaffolder emits one pose per declared state) and did not
generalize to `character`. Every character in every universe is born failing its own lint.

**Evidence.** 2026-08-06, nation-of-fire: `josh-howerton`, `jana-howerton` and `bob-russell`
all three ERRORed the moment they were scaffolded, before an author had touched them. Not
blocking, because the author was about to write the render blocks anyway, but the linter's
signal is worthless on a fresh entity and an author who trusts it learns to ignore it.

**Next invocation.** Every `add-character` in every universe.

**Would close it.** Emit `structured.render: {"always": "", "poses": {}}` as a stub, and
downgrade the lint to a WARNING while `always` is empty. The ERROR should mean "this entity is
cast in a story and cannot render", not "this entity is new".

### G18. There is no verb that AUTHORS an altLook; every age era is hand-edited JSON

**What.** `structured.altLooks` (with `supersedes`, `dropSheets`, `keepSheets`, `anchorPhoto`,
`validFor`) is fully specified in SPEC §12 and fully load-bearing in the compiler, and both of
its consumers REFUSE to create one. `lock-shot --look` raises "has no altLook <key>. Author the
look first"; `chain_matrix --look` shoots into an existing look only. There is no `abu add-look`
and no `--look` on `add-entity`. `add-character` step 4b's instruction is literally "add
`structured.altLooks.era-<year>`", i.e. edit the JSON by hand.

This matters more than it looks because the shape has a known inverted trap the spec spends four
paragraphs on: an era look chained off a photo stack auto-drops the base face sheets, so without
`keepSheets`/`keepPhotos` you render a stranger with the right build. A hand-editor gets no
scaffolder to get that right, and nothing checks the SHOOT ORDER either (the era with
photographs must be shot first and the others chained off it).

**Evidence.** 2026-08-06, nation-of-fire's `josh-howerton`: three age eras (sixteen, eighteen,
mid-twenties) over a present-day photo stack, all three hand-authored, including a hand-set
`anchorPhoto` so `sixteen` chains off `eighteen` rather than off the forty-three-year-old face.
SPEC §12 names the documented-past case (Kenneth Hagin at fifteen, no photograph) as identical
in shape, so this is at least the second universe to hand-roll it.

**Would close it.** `abu add-look <universe> <id> <key> [--era FROM-TO] [--chain-from <look>]
[--keep-sheets ...] [--supersedes ...]`, emitting the correct-by-construction shape plus the
look's own `prompts.md` skeleton, and a lint check that a look with an `anchorPhoto` pointing
into a sibling look is shot after it.

### G19. A "NOT USED" stub heading in prompts.md is a LIVE SHOT that renders garbage

**What.** A code-drawn plate (`abu elevation` / `abu massing`) has no business being prompted,
and the scaffolder's own prompts.md says the blueprint section "is never used". That is only
true while the file already exists on disk: `--skip-existing` skips it. Delete or never create
the PNG and the chain happily sends the stub body to the model. A two-sentence stub plus the
style anchor is precisely the alias-clobber failure the parser's own comments describe, and it
returns a confident finished picture that is not a blueprint.

**Evidence.** 2026-08-06, nation-of-fire's `the-lunch-booth`. Its prompts.md carried
`## blueprint -> .../blueprint.png` with the body "NOT USED. Code-drawn by `abu elevation`...".
No blueprint.png existed (the code-drawn plan was written to `dummies.png`), so the chain
rendered the stub and produced a full painted restaurant-booth scene with two invented people
in it, filed as the setting's geometry blueprint. It was caught by eye, not by any check.

**Would close it.** Two moves. (1) `add-entity` should not scaffold a heading for a slot it
documents as code-drawn. (2) `parse_prompts_full` should REFUSE a shot body shorter than N
characters or matching /^NOT USED/i, on the same reasoning as the existing TODO(author)
refusal: a body that says it is not a prompt is not a prompt.

### G23. Commission photos pasted in chat have no route onto disk

**What.** A real-person entity needs a `photoStack` of on-disk files, and the photos routinely
arrive as images PASTED INTO THE CONVERSATION, which no framework verb can reach. The
workaround that worked: parse the harness session transcript JSONL and base64-decode the image
blocks into `reference/<id>/photos/`.

**Evidence.** the-introducer, 2026-08-08: five photos of David Kobrosky arrived inside the
commission message. Hand-rolled a JSONL extractor twice in one session; the second run silently
grabbed a STALE image because mid-turn pastes append to the transcript only after the turn ends,
and the "new" anchor extracted was byte-identical to an already-saved photo (caught by size).

**Next invocation.** The next commissioned book about a real person whose photos arrive as chat
pastes, which is how every commission so far has arrived.

**Would close it.** A small `shoot-references/scripts/extract_chat_photos.py <session-jsonl>
<universe> <entity>` that decodes image blocks, dedupes by hash against the existing stack,
names files by order, and REFUSES (or warns) when the newest paste is not yet in the transcript.

### G24. The ABU book layout and the platform stager disagree about names

**What.** `render_spread.py --out-dir` writes `spreads/spread-01..NN.png` beside `cover.png` and
`closing-plate.png`; garysheng-books' `stage-book-assets.py` expects composer naming
(`cover-0.png`, `spread-0..N-1.png`, `plate-0.png`). Every publish hand-builds a `.stage-in/`
bridge dir of renamed copies.

**Evidence.** the-introducer, 2026-08-08 (17-file rename bridge). The same bridge is implied by
every prior hyperagentic-age publish.

**Next invocation.** The next ABU book published to books.garysheng.com.

**Would close it.** Teach `stage-book-assets.py` to detect the ABU layout (it lives in the
platform repo, so coordinate there), or give the book chain a `stage` substep that emits
composer naming directly.

### G25. The closing plate has no platform-copy publisher; the cover does

**What.** `render_cover.py` publishes `cover-raw.png -> cover.png` with a derived recipe
(v0.33) precisely because the hand copy kept failing book-doctor provenance. The closing plate
has the same shape (gen -> conform -> platform copy) and no equivalent, so the final copy +
recipe is hand-written per book.

**Evidence.** the-introducer, 2026-08-08: hand-authored `closing-plate.png.recipe.json`.
nobody-labeled-the-door's copy was written by reroll-slot's replay, which only exists after a
first hand-rolled publish.

**Next invocation.** Every book, at the closing-plate step.

**Would close it.** A `--closing-plate` mode (or sibling script) in the cover skill that runs
conform + platform copy + recipe in one verb, mirroring `render_cover.py`'s publish step.


### G26. An altLook's photoStack APPENDS to the base stack instead of replacing it

**What.** A look that declares its own `photoStack` (SPEC: "a look's own anchorPhoto and
photoStack outrank the base face sheets") still gets the BASE realPerson stack passed first at
shoot time, with the look's photos appended after. For an age era this is exactly backwards:
five present-day photos lead the conditioning and the young-era anchor arrives sixth of eight,
so the young face averages toward the adult one.

**Evidence.** david-kobrosky@college, 2026-08-08: three seed rolls fought adult-face drift and
residual stubble until the BASE stack was hand-swapped to young-only (stash key in the entity,
restored after), which is a workaround that falsifies nothing but that nobody will remember.

**Next invocation.** The next age-era or wardrobe-era look on any realPerson entity.

**Would close it.** chain_matrix's look branch passes look.photoStack INSTEAD of the base stack
when the look declares one (anchorPhoto first), matching the outrank language the spec already
uses for sheets. The base stack still rides along only when the look declares `keepPhotos`.

### G27b. CLOSED 2026-08-09. `--shoot-seed` and `--seed` deadlocked any blueprint-first entity

**What.** An entity whose only plate on disk was its CODE-DRAWN blueprint had no legal first
shot. `--shoot-seed` refused ("already has 1 plate(s) on disk, so 'master' is not this
entity's first painted thing") and named `--seed <blueprint>` as the fix; `--seed <blueprint>`
then refused ("is CODE-DRAWN. It is already the seed: it is passed as conditioning to every
shot in this matrix"). The two guards contradicted each other, and the second one is right:
`_shoot` passes `plan["codeDrawn"]` as an `--input-image` on every shot INCLUDING the seed
(v0.31), so the "locked place will NOT ride along" premise is false for code-drawn geometry.

This bit every entity built the way the framework itself instructs: `add-setting`,
`add-visual-metaphor` and `make-a-book` all say to draw the blueprint in code FIRST.

**Evidence.** nation-of-fire, 2026-08-09, `addisons-walk` and `the-splintered-light`, both
scaffolded blueprint-first. Neither could be shot at all until the guard was fixed.

**Closed by.** `painted_plates_on_disk()` extracted as a pure predicate in `chain_matrix.py`
and made to exclude plates whose own recipe names a deterministic generator. Code-drawn is
read from the RECIPE and never from the filename, so a painted plate merely named `blueprint`
still blocks the seed. Three tests, mutation-checked (reverting the condition fails two).

**Note for whoever tests near this.** The guard sits inside `main()` AFTER the `--dry-run`
early return, so a `--dry-run` subprocess test passes whether the fix is present or not. The
first version of these tests did exactly that and proved nothing. Test the predicate.

### G28b. prompts.md invites a shared description block the parser never sends

**What.** The scaffolded `prompts.md` template, and the filled files across this universe,
carry header blocks headed "THE MAN, restated in full on every shot" and "Shared negatives on
every shot". `parse_prompts_full` uses ONLY the text under each `## <shot>` heading, so those
blocks reach the model on no shot at all. A shot body written as "the full signature wardrobe
described above" therefore ships with no description in it, and the seed render is conditioned
on the register anchor plus a sentence about camera framing.

The one header form that IS parsed is `**Negatives (every shot):** a, b, c`, which is
undocumented anywhere the author is looking while filling the file in.

**Evidence.** nation-of-fire, 2026-08-09: four character seeds (c-s-lewis, j-r-r-tolkien,
hugo-dyson, reid-one-more) came back as four generic period men, none matching a single
invariant, because every body deferred to a shared block. Four renders, diagnosed only by
reading the emitted `.recipe.json`.

**Next invocation.** The next entity anybody authors prompts for by hand.

**Would close it.** Either (a) have the parser prepend a header block explicitly marked as
shared, in the same spirit as `**Negatives (every shot):**`, or (b) change the scaffold so its
header blocks are labelled as author notes and each shot body is stamped SELF-CONTAINED. (b)
is cheaper and loses nothing, since the entity's own `structured.render.always` is the real
home for a description that must apply everywhere.

### G29. audit_spec_refs cannot tell "improvised on purpose" from "forgot to cast"

**What.** The bare-anchor check fires on `len(refs) <= 1` and says "Cast the entities this
spread is actually about." For a book with genuinely one-off imagined plates there is nothing
to cast: the picture is a dragon, an empty tomb, a hall of suitors, a bow on a threshold. Each
appears ONCE, so making each a canon entity is overengineering by the framework's own
abstract-from-the-second-instance rule. There is no way to say so, and eight standing warnings
train an author to skim the audit, which is the exact failure the audit exists to prevent.

The leak the check is really worried about is already closable: `identity.register`'s own
`stylePackNote` prescribes a purpose-made CONTENT-NEUTRAL swatch as the anchor for "any render
that casts nothing else", and a spread can set it per-spread via `anchorRef`. The audit does
not look at whether the anchor it is warning about HAS a subject.

**Evidence.** the-story-underneath-the-story, 2026-08-09: eight `imagined` plates, all pointed
at `reference/register-neutral-swatch/hero.png`, all still flagged.

**Next invocation.** Any book with argued/imagined plates rather than only staged scenes. That
is most teaching books in this universe.

**Would close it.** Downgrade the finding to a NOTE when the spread's resolved anchor is the
register's declared content-neutral swatch (or any anchor with no `anchorSubject`), and keep it
a problem when the anchor is a subject-bearing one. That reads the actual risk rather than a
proxy for it. A per-spread `improvised: true` opt-out is the cheaper alternative and worse: it
is a flag an author sets to silence a check, which is the thing this register keeps warning
about elsewhere.

### G30. pick_caption_pos is structurally biased toward `top`, and cannot see a face

**What.** Two defects in the same scorer, both of which put captions in the wrong place on a
shipped book, and neither of which the tool can detect about itself.

1. **The top bias is arithmetic.** A bottom candidate scores `0.82*E_bottom + 0.45*E_top`
   (BOTTOM_BONUS, then the short-viewport FLIP penalty); a top candidate scores `E_top` and
   pays no flip penalty, because top does not flip. So bottom wins only when
   `E_bottom < 0.67*E_top`. The docstring states "a small BOTTOM PREFERENCE, because bottom
   is the book's typographic norm" and the arithmetic contradicts it.
2. **Gradient energy is backwards about faces.** Skin is smooth, so a face scores CALM and
   reads as an excellent place for a plate; foliage is busy, so leaves score badly when
   covering leaves is free. The defect that produced this tool was "the caption landed on a
   face", and the proxy it chose cannot see one.

**Evidence.** the-story-underneath-the-story, 2026-08-09: 27 top / 9 bottom across 36
spreads, which is a tilt rather than 36 judgements. The Introducer, 2026-08-08: agreed with
Gary on 3 of 7 spreads, per caption-vision.ts's own header.

**Next invocation.** Any book that runs the prior without the vision pass.

**Would close it.** The vision pass already closes it in practice and is now mandatory in
make-a-book step 4b, so this stays open only as a defect in the FALLBACK. If the fallback is
ever load-bearing again: score the flip penalty symmetrically (or drop it and let the reader's
own flip rule handle short viewports), and add a skin-tone-plus-low-gradient penalty so a
smooth face stops reading as calm. Do NOT hand-tune the constant; a constant is what made the
misses photo finishes in the first place.
