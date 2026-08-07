---
name: pave-the-path
description: The retrospective sweep at the END of a chain run. Read what the session actually wrote, find the hand-rolled code and manual steps that WILL recur on the next invocation, and pave them into deterministic substeps the framework owns. Fires after the deliverable ships, not mid-flinch: the whole point is that the path has already been walked, so you are paving a real desire path instead of speculating about one. Use when a book/work/universe run is finishing, when Gary says "pave the path", "what did we hand-roll", "memorialize this", "turn that into a step", "audit this run for reusable pieces", or as the last step of make-a-book, render-book, or any other chain run. NOT the in-the-moment reflex (that is fix-the-generator) and NOT the mechanics of editing the framework (that is evolve-abu, which this skill dispatches to).
---

# Pave The Path

A desire path is the line worn into the grass because people actually walk it. You do not
plan a desire path; you **discover** it, and then you decide whether to pave it.

This skill is the end-of-run walk around the lawn. It reads what a completed run actually
did, finds the places where the agent improvised code or repeated a manual step, and
promotes the ones that will certainly recur into **deterministic substeps of the chain**.

**The distinction from its two neighbours, because all three get confused:**

| Skill | Fires | Answers |
| --- | --- | --- |
| `fix-the-generator` | mid-flinch, the moment you reach for a one-off | "Should I be hand-rolling this at all?" |
| `pave-the-path` | **after the run ships** | "What did I hand-roll that I will hand-roll again?" |
| `evolve-abu` | once a decision is made | "How do I actually land it, version it, deliver it?" |

`pave-the-path` decides WHAT to pave. `evolve-abu` does the paving. Always
dispatch to it rather than editing the framework here.

## The bar (this is the whole skill)

Pave a thing **only** when you can complete this sentence with a specific, named case:

> I hand-rolled X, and the next invocation that needs X is **Y**.

If you cannot name Y, do not pave. Write it down as an observation and move on.

**INTEGRATE BY DEFAULT. The bar is the only gate.** If a candidate clears the naming
sentence, you BUILD it, in this session, through `evolve-abu`. You do not file it
as a suggestion and move on.

This is the correction that matters most in this file, and it was earned by this skill's own
first run failing at it (Gary, 2026-07-29: *"how am I supposed to integrate the pave-the-path
suggestions that are in SAVE-LOG.md? I feel like the default should be to integrate. Am I
crazy?"*). He was not crazy. That first run wrote six ranked proposals into a log and shipped
none of them, which is precisely the failure `fix-the-generator` already names: **writing down
a hazard is not removing it.** A suggestion in a log is a to-do nobody does, and a sweep whose
output is a list has simply moved the hand-rolling into the future and added paperwork.

So the caution in this skill lives in the BAR and nowhere else. The bar is genuinely strict:
most improvised things fail it, and DECLINING is the common outcome. But once something passes,
"proposed" is not a state it is allowed to rest in.

**Paving the wrong thing is still worse than hand-rolling twice.** A hand-roll costs one
session; a bad abstraction calcifies into every future run. That is what the bar is for. It is
not a reason to defer a candidate that already cleared it.

**The two things you may legitimately stop and ask about**, and they are exceptions, not the
default:
- A pave that changes behaviour for work ALREADY SHIPPED by someone else, where a human has to
  weigh the churn.
- A pave large enough to be its own project, where landing it half-done is worse than not
  starting. Say so plainly, name the size, and get a decision.

Anything else that clears the bar: build it, test it, land it, and report what you BUILT.

## Procedure

### 1. Gather the evidence, do not recall it

Memory of a long run is unreliable and flattering. Read the artifacts.

```bash
git -C <repo> status --porcelain          # what this run touched
git -C <repo> diff --stat HEAD            # and how much
ls <scratchpad>                           # EVERY throwaway script is a candidate
```

The highest-yield sources, in order:

1. **The scratchpad.** Every `*.sh` / `*.py` you wrote to get unstuck is, by definition, a
   hand-roll. This is the single richest signal and it is usually ignored because the files
   feel disposable. They are disposable; the PATTERN in them is not.
2. **Retry loops and sleeps.** Any loop you wrote around a provider call encodes a failure
   mode the framework does not yet model.
3. **Verification you wrote by hand.** A script that checks the output is correct is a TEST
   the framework is missing. These are the cheapest, safest paves in the whole catalogue.
4. **Anything you did N times by hand** (renamed N files, cropped N images, re-typed N
   entries). N > 2 means the loop belongs in code.
5. **Rules you enforced by being careful.** If correctness depended on you remembering
   something, it will fail the run where you forget.

### 1b. SEARCH BEFORE YOU CLASSIFY. A hand-roll is not proof of a gap.

```bash
find <framework>/skills -path '*/scripts/*' -name '*.py' | xargs -n1 basename | sort -u
grep -rl "<the-thing-you-wrote-by-hand>" <framework>/skills <framework>/engine
```

Run this on EVERY candidate before deciding it is missing. This skill was written on the
assumption that hand-rolled work means the framework lacks the tool, and that assumption is
wrong often enough to be dangerous: on 2026-08-01 a session hand-rolled the same PIL
contact-sheet montage roughly FIFTEEN times while `render-readback/scripts/contact_sheet.py`
sat in the repo the whole session, along with `crop_zoom.py` for the crop checks it also
hand-rolled. Nobody noticed, because a hand-roll feels like evidence of absence.

**The two cases have OPPOSITE fixes and confusing them is expensive:**

| | It does not exist | It exists and was not found |
|---|---|---|
| The fix | BUILD it (step 3) | Add a POINTER where the work happens |
| Building anyway costs | nothing | a duplicate that will drift from the original |

**A tool nobody finds at the moment of need is indistinguishable from a missing tool, and
the fix is not more documentation.** The pointer belongs in the file that is READ DURING THE
TASK: the skill's own method, the form's PROMPT.md, the repo's CLAUDE.md. A catalog read at
session start loses to an instruction read at the point of use, and on a long session it
loses badly.

Two structural causes worth checking for while you are in there:

- **Filed by OWNER rather than by JOB.** `contact_sheet.py` lives under `render-readback/`,
  so it is only visible to someone who has already decided to run render-readback. Anyone who
  merely needs a contact sheet never opens that folder.
- **Named for its mechanism rather than its outcome.** If you would not think to search the
  word, the name is wrong.

### 2. Classify each candidate, because they do not all get paved the same way

- **PAVE (deterministic substep).** Mechanical, verifiable, no taste required: a crop, a
  rename, an aspect conform, a retry policy, a budget check. These become code.
- **GATE (a check that refuses).** Correctness you enforced by attention. These become an
  assertion in the chain, and they should FAIL CLOSED.
- **BUG (the framework is wrong, not missing).** A cap that does not cap, a guard that
  misfires, a default that is unsafe. File and fix; do not build a workaround on top.
- **GUIDANCE (prose, not code).** Judgment calls, taste, "prefer X when Y." These go in the
  relevant SKILL.md and nowhere else. Resist coding a judgment call: that is how a
  framework becomes a straitjacket.
- **LEAVE.** Genuinely one-off. Say so explicitly, so the next reader knows it was
  considered and declined rather than missed.

**A PAVE / BUG / GATE row you are not building TODAY goes in `docs/GAPS.md`,** the standing
register of known-open gaps, with its evidence, its next invocation, and why it is still
open. Not SAVE-LOG, and not only your report: both are chronological, and this framework has
already lost a filed gap that way once (SPEC v0.32's changelog names the book that paid for
it). "Not yet" is a legitimate answer here; "not written down anywhere anyone will look" is
not.

### 3. Build it. Do not merely route it.

- PAVE / BUG → `evolve-abu`, and see it THROUGH: the edit, the test that proves it,
  the version bump, the plugin re-sync, the log. Invoking the verb is not the finish line;
  a green test on the new behaviour is.
- GATE → the same, plus name which existing gate list it joins.
- GUIDANCE → route by scope, exactly as `make-a-book` already specifies: universal to the
  base skill, universe-specific to the cartridge. **If two cartridges would say the same
  thing, that is the signal to promote it.**
- Anything touching the engine, spec or CLI → the `agenticstory` repo, same session.

### 4. Report what you BUILT, then what you declined

One table, most-valuable first, and its rows are PAST TENSE. Every row carries its "next
invocation that needs it," or it does not belong in the table. A row that is still a
suggestion has to say why it was not built, in the two allowed shapes above; if it cannot,
it was not really above the bar and belongs in DECLINED.

## Worked example (the run that earned this skill)

`she-had-everything-but-peace`, 2026-07-29, a 40-spread Nation of Fire book with two new
real-person entities. The end-of-run sweep found six things:

| Hand-rolled | Class | Next invocation | Where it goes |
| --- | --- | --- | --- |
| Retry loop on `moderation_blocked` from the image provider | PAVE | any real-person book | a typed retry policy in `render_spread.py` |
| `[:2]` photo cap silently defeated by a DIRECTORY photoStack (6 refs passed, 2 of them group shots, on 17 spreads) | BUG | every real-person entity | `assemble_prompt.py` |
| Head-and-shoulders crop of source photos so the ref carries identity and not stage wardrobe | PAVE | every real person | a crop step in `shoot-references` |
| Verifying manifest captions are byte-identical to the blessed manuscript | GATE | every book | platform test / `book:probe` |
| Column-budget check (subtitle 52, tagline 90, closingNote 450 chars, silent clipping) | GATE | every book | same lint |
| `export -f` + `xargs -P` batch render harness (and its zsh-vs-bash failure) | PAVE | every multi-spread book | the renderer's own batch mode |

And two things it deliberately declined to pave:

- **"Chain a known-good sibling in as the control when regenerating a drifted plate."**
  GUIDANCE, not code. It is a judgment call about which sibling is trustworthy, and
  `make-a-book` already says it.
- **The one-off Wikimedia Commons photo fetch.** LEAVE. Every real person needs different
  sources under different licences, and a generic fetcher would encourage using whatever it
  happened to return.

The tell that the sweep was worth running: **five of the six rows were invisible from
inside the run.** Each one felt like "just getting unstuck" at the time.

## Anti-patterns

- **Paving while the run is still going.** You cannot see a path you are still walking, and
  editing a shared framework file mid-render can break the render. Ship first, sweep after.
- **Paving from memory instead of from the diff.** You will remember the interesting
  problems and forget the repetitive ones, which is exactly backwards.
- **Coding a judgment call.** If the right answer depends on taste, it is GUIDANCE.
- **A table row with no named next invocation.** That is speculation wearing a table's
  clothes.
- **Silently swallowing a BUG as a PAVE.** Building a helper on top of a broken cap leaves
  the cap broken for everyone else.
- **Shipping a list instead of a change.** The single worst outcome available to this skill,
  because it looks like diligence. If the sweep's artifact is a log entry and the repo is
  otherwise unchanged, the sweep did not run; it rehearsed.

## Gates honored
- Evidence before proposal (read the diff and the scratchpad, never recall).
- Naming sentence required per row (no unnamed next invocation, no paving).
- Cautious by default (propose ranked, never auto-merge; "not yet" is a valid answer).
- Route, do not edit (all framework edits go through `evolve-abu`).
- Declines are recorded, so a later reader knows they were considered.

## Skill improvement
If a paved step later gets ripped out, record WHY here: a bad pave is the most valuable
evidence this skill can carry, because the bar above exists to prevent exactly that.

## Run the detector first. Do not rely on remembering the run.

```
python3 <skill>/scripts/detect_handroll.py <scratchpad-dir> [--universe DIR]
```

It looks for the mechanical signatures of a run that routed around a framework verb: a
script calling a provider generate script directly, a script hardcoding the register line
canon already owns, and art sitting beside a `prompts.md` that still says `TODO(author)`,
which means the prompt that made it is recorded nowhere. Exit 1 on any finding, so a chain
step can gate on it.

**First run, 2026-07-30: 79 findings, across at least SEVEN different sessions.** That was
the real result. The assumption going in was "I hand-rolled five scripts today"; what the
scan showed was `shoot.py`, `gen.sh`, `shoot-r1.sh`, `shoot-r2.sh` and `room_variants.py`
sitting in the scratchpads of sessions weeks apart. Hand-rolling was not an incident, it was
the framework's normal usage pattern, invisible the entire time because nothing looked.

Treat every finding as a GAP, never as a scolding. Each one means the verb does not exist,
or it exists and was harder to reach than writing the script. Both are the framework's
problem to fix, and both route to `evolve-abu`.

## Score the run itself, not only what it wrote

When the run left a transcript (`runs/<id>/transcript.jsonl`, stream-json), score HOW it
spent its calls before deciding what to pave:

```
python3 <skill>/scripts/review_run.py runs/<id> [--json]
```

Total tool calls, per-tool histogram, the first call that TOUCHED the render machinery
versus the first that EXECUTED a generation (a `--help` on a render script is
orientation, not work), duration, cost, and a one-line verdict. An **orientation-heavy**
verdict ("71/85 calls before the first generation") is itself a finding: the run spent
its budget reconstructing context, so the gap to pave is usually a missing DIRECT ROUTE
to the answer, not a missing capability. That exact verdict on the 2026-08-07
closing-plate run is what earned `reroll-slot`: the reproduction context sat in the
slot's own `.recipe.json` the whole time and no verb read it back.

