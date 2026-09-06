---
name: explore
description: Render a comparison SET that isolates one variable, so a human can decide a visual question by looking instead of by reading a description. Use when the answer is a matter of taste rather than canon: what material, which register, how much shine, which form factor, which of several readings of a vague brief. Fans out N variants of one subject in parallel through the provider adapter, stages every roll with its prompt beside it, and hands back a labelled set. Trigger phrases: "explore what X could look like", "give me visual options", "I'm not sure, show me", "what are the ways this could go", "5-6 different ways", or any moment you are about to build your best guess and ask whether it is right. NOT for producing a finished asset (on-brand-image), NOT for an entity's reference matrix (shoot-references), NOT for re-running a recorded recipe (reroll-slot).
---

# Explore

The framework had verbs for making a thing you had already decided on (`on-brand-image`,
`shoot-references`, `compose-spread`) and no verb for **deciding**. That gap is why every
taste question got improvised: write some prompt files, fan out a loop, stage the outputs,
open them. Four times in one session before it got built.

## When you are in this skill

The tell is that you are about to type a hedge: *I think he means*, *this should be what
you want*, *let me know if this is the right direction*. A wrong guess costs a full render
cycle plus the correction, and a second wrong guess reads as not listening.

Ship the comparison instead. Two variants side by side settle in one round what three
sequential attempts do not.

Also reach for it when the operator says outright that they do not know. "Idk" and "give me
visual options" are not stalls, they are a request for this verb.

## The one law: isolate the variable

**Everything except the axis under study must be identical across the set.** Same subject,
same framing, same light, same material, same everything. If two things change between
rolls, the operator cannot attribute the difference and the set has told them nothing.

That is what `--subject-file` is for: it holds the INVARIANT half of the prompt and is
concatenated in front of every variant. Put the axis in the variants file and everything
else in the subject.

Corollary worth stating because it is counterintuitive: when exploring **form**, hold the
material constant, even if the material is also unsettled. When exploring **material**, hold
the form constant. Two open questions get two passes, never one grid.

## Run it

```bash
python3 skills/explore/scripts/explore.py \
  --subject-file subject.txt \
  --variants variants.txt \
  --out-dir ~/scratch/explore-<question> \
  --style-pack <path/to/pack> \
  [--ref <locked-plate> ...] [--ref-first] \
  [--size 1536x1024] [--quality high] [--concurrency 3]
```

`variants.txt` is one variant per line, `id: text`. Ids become filenames, so make them
readable (`A-ducted-sphere`, not `v1`), because the id is how the operator will answer.

Each roll writes `<id>.png`, `<id>.prompt.txt` and `<id>.log` into the out-dir. Use
`--dry-run` to print the assembled commands and spend nothing.

**Concurrency 3.** Higher queues server-side and times rolls out together, and a timeout
means no image AND no recipe.

## Once one is chosen, EDIT it. Do not re-roll it.

Exploring ends the moment the operator picks a frame. Everything after that is a targeted
change to THAT image, and a targeted change is an edit rather than a fresh generation:

```bash
uv run <providers>/gpt-image-2/generate_image.py \
  --input-image <the chosen roll>.png --filename <out>.png \
  --size 1536x1024 --quality high --no-open \
  --prompt "Edit this photograph. Change only <the one thing>. Leave everything else
            identical: the same face, the same expression, the same light, the same
            wardrobe, the same background."
```

**A render is not reproducible, so re-rolling spends what was already approved.** The
operator picked that frame for its face, its light, its colour and its composition. A fresh
generation re-rolls all of them alongside the one thing being fixed, so every pass trades a
solved problem for a new one and the set never converges. The tell is an operator repeating
a correction they already gave, because the thing they fixed two rounds ago came back.

Earned across roughly a dozen rounds on one photograph, ending with the operator saying it
plainly: *"Try again dude you didn't follow my instructions ... just modify this image."* The
edit landed both changes on the first attempt with the rest of the frame untouched.

**Say what stays, not just what changes.** An edit prompt that names only the change invites
the model to reinterpret everything it was not told to keep. List the invariants explicitly.

## Showing the set

- **Send the images, do not just open them.** If the operator is on Remote Control they are
  not at the machine, and a Preview window on their desktop is useless. `SendUserFile` with
  all of them in one call.
- **Name the order in the same message**, in id order, one clause each. The operator answers
  with an id, so the ids have to be legible from the caption alone.
- **Look at the leading candidates yourself first.** You are the one who can catch a defect
  that has nothing to do with the axis (a missing limb, invented lettering, a broken
  reflection). Do not hand over a set with a fatal flaw in it and make the operator find it.

## Every roll is kept

A render is not reproducible: `gpt-image-2` has no seed, so a candidate that is deleted is
gone. Stage them all, and prune only after a winner is locked. Losing a good roll to
tidiness is a real and permanent loss.

When a winner is chosen, **the chosen file IS the golden**. Do not regenerate "a clean
version" of it from the same prompt; you will get a different image and the operator's
approval will not transfer to it. Copy the blessed file into canon as-is.

## After the pick

An explore that ends in a picture and no canon change was a conversation, not a decision.
Close it:

1. Copy the winner into the entity's sheet, or into a style pack's refs.
2. Write what won into the entity's `invariants` and `render.always`, so the next render
   inherits it instead of depending on someone remembering this thread.
3. Add a gate assertion for anything that could silently regress (a finish, a proportion, a
   material) so the losing direction fails read-back rather than shipping quietly.

## Not this skill

- Making a finished asset in a settled look: `on-brand-image`.
- Filling an entity's reference matrix: `shoot-references`.
- Re-running an existing recipe with a small delta: `reroll-slot`.
