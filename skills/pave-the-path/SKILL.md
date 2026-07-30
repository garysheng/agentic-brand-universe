---
name: pave-the-path
description: The retrospective sweep at the END of a chain run. Read what the session actually wrote, find the hand-rolled code and manual steps that WILL recur on the next invocation, and pave them into deterministic substeps the framework owns. Fires after the deliverable ships, not mid-flinch: the whole point is that the path has already been walked, so you are paving a real desire path instead of speculating about one. Use when a book/work/universe run is finishing, when Gary says "pave the path", "what did we hand-roll", "memorialize this", "turn that into a step", "audit this run for reusable pieces", or as the last step of make-a-book / compose / add-work. NOT the in-the-moment reflex (that is fix-the-generator) and NOT the mechanics of editing the framework (that is evolve-agentic-story, which this skill dispatches to).
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
| `evolve-agentic-story` | once a decision is made | "How do I actually land it, version it, deliver it?" |

`pave-the-path` decides WHAT to pave. `evolve-agentic-story` does the paving. Always
dispatch to it rather than editing the framework here.

## The bar (this is the whole skill)

Pave a thing **only** when you can complete this sentence with a specific, named case:

> I hand-rolled X, and the next invocation that needs X is **Y**.

If you cannot name Y, do not pave. Write it down as an observation and move on.

**Paving the wrong thing is worse than hand-rolling twice.** A hand-roll costs one session.
A bad abstraction calcifies into every future run, and every later author has to work
around it or is silently constrained by it. This is why the skill is CAUTIOUS by default:
its output is a ranked proposal, and the operator's default answer may legitimately be "not
yet."

**Corollary: two occurrences beat one prediction.** A step you performed once and can
imagine repeating is a candidate. A step you performed twice IN THE SAME RUN, or once in
each of two runs, is a decision. Prefer evidence over foresight.

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

### 3. Route it, do not do it here

- PAVE / BUG → `evolve-agentic-story` (it owns the edit, the test, the version bump, the
  plugin re-sync and the log).
- GATE → the same, plus name which existing gate list it joins.
- GUIDANCE → route by scope, exactly as `make-a-book` already specifies: universal to the
  base skill, universe-specific to the cartridge. **If two cartridges would say the same
  thing, that is the signal to promote it.**
- Anything touching the engine, spec or CLI → the `agenticstory` repo, same session.

### 4. Report, ranked, with the naming sentence attached

One table, most-valuable first. Every row carries its "next invocation that needs it," or
it does not belong in the table.

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

## Gates honored
- Evidence before proposal (read the diff and the scratchpad, never recall).
- Naming sentence required per row (no unnamed next invocation, no paving).
- Cautious by default (propose ranked, never auto-merge; "not yet" is a valid answer).
- Route, do not edit (all framework edits go through `evolve-agentic-story`).
- Declines are recorded, so a later reader knows they were considered.

## Skill improvement
If a paved step later gets ripped out, record WHY here: a bad pave is the most valuable
evidence this skill can carry, because the bar above exists to prevent exactly that.
