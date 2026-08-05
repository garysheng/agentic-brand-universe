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

