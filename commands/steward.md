---
description: Hand a framework-shaped task to the abu-steward subagent instead of hand-rolling it
argument-hint: [the task, e.g. "add the forge setting to nation-of-fire"]
allowed-tools: Agent, Read, Grep, Glob
---

Dispatch the `abu-steward` subagent for this task:

**$ARGUMENTS**

Use the Agent tool with `subagent_type: "abu:abu-steward"`. Do not do the work inline.
Dispatching IS the point of this command: the main context is carrying momentum and is
therefore the worst judge of "should I write a quick script here." A fresh context whose
only question is "which framework verb is this" has no such incentive.

If `$ARGUMENTS` is empty, ask what the task is in one sentence, then dispatch. Do not
turn the question into an interview.

## What to hand it

Give the steward, in the prompt:

- **The universe path** if one is in play (resolve it: an explicit path, else the one you
  are standing in, else ask). `on-brand-image` and `create-style-pack` need a Style Pack
  rather than a universe, so a pack path is a valid answer here.
- **The step**, named as the outcome the user wants rather than a verb you already picked.
  Let the steward select the verb; that selection is its entire job.
- **The entities involved**, by id where you know them.
- **What was already tried**, especially anything hand-rolled this session. A script you
  wrote ten minutes ago is exactly the evidence the steward exists to act on.

## What to expect back

One of two things, and both are successful runs:

- **The verb it used** plus what changed on disk.
- **A FLAGGED GAP**: the framework cannot yet do this sensibly. This is a real finding,
  not a failed run. Route it to `evolve-abu` and keep going.

Report the outcome to the user in plain language. You still own any operator gates and
the final report; the steward owns verb selection.
