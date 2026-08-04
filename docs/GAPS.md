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

## Filing a gap here

Append an entry with the five headings above (**What / Evidence / Next invocation / Would
close it / Still open because**). If you cannot write the **Next invocation** line, do not
file it. If you cannot write **Still open because**, you are not filing a gap — you are
deferring work, and the honest move is to build it.
