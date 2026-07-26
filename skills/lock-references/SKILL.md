---
name: lock-references
description: Generate and lock an entity's reference matrix in an Agentic Story universe. For each unlocked or DEFECT matrix slot, generate the shot from the entity's `reference/<id>/prompts.md` (passing `identity.register.anchor` first, plus the photo stack for a real person and any already-locked shots for identity consistency), read it back against the entity's invariants, and lock passers via `agenticstory lock-shot`. Idempotent. Real-person entities stay subject-approval gated after art. Use after `add-*` has scaffolded an entity, to give it its art.
---

# Lock References

Turn a scaffolded entity's null matrix slots into locked reference shots. This is the art step: `add-character` (and siblings) leave an entity at `lock_level: stub` with a `prompts.md`; this skill generates, reads back, and locks until the entity is `locked` (or at least `partial`, once its required shots pass).

## Inputs
- The target universe (a path with `universe.json`) and the entity id.
- Read `identity.register` (anchor + rejectedPoles). If `register.anchor` is null, STOP: the universe's style is not locked. Point the operator at the start-universe style-lock step and do not generate.

## Procedure
1. **Resolve the work.** Read `canon/entities/<id>.json` (its kind, matrix, invariants, and for a real person the `realPerson` photo stack + sensitive list) and `reference/<id>/prompts.md`. Run `agenticstory lock-level <universe> <id>` to see what remains.
2. **For each shot that is missing or was a DEFECT** (skip already-locked passers, so re-runs are cheap):
   a. **Generate** via the `chatgpt-images` skill (gpt-image-2): pass `identity.register.anchor` as the FIRST input image; bake `register.rejectedPoles` as negatives; for a real person pass the photo stack (build from real photos, never a painting-of-a-painting) and honor the sensitive list; pass any already-locked shots of this entity so the face/build stays consistent; use the shot's prompt block from `prompts.md`. Write to `reference/<id>/<shot>.png`.
   b. **Read back** with `render-readback`: crop-zoom each of the entity's invariants, PASS/DEFECT. On any DEFECT, regenerate that shot FROM SCRATCH (never an edit pass), naming the defect as an explicit negative.
   c. **Write the shot's recipe.** Alongside the art, write `reference/<id>/<shot>.recipe.json` capturing what produced it: `{"provider": "gpt-image-2", "prompt": "<the exact prompt sent>", "specVersion": "<universe spec.version>", "refs": [{"path": "<each input image, universe-relative>"}]}`. This is the same recipe shape `compose` emits. Provenance is not optional: a golden locked without it is un-auditable and can never enter a divergence check.
   d. **Lock the passer WITH its recipe:** `python3 -m agenticstory.cli lock-shot <universe> <id> <shot> reference/<id>/<shot>.png --recipe reference/<id>/<shot>.recipe.json`. This sets the sheet path, promotes `requiredForRender` as the required shots lock, and freezes provenance at approval (the golden's own bytes plus each input's bytes now), so `lint-universe` can later tell you if the golden drifts from what Gary blessed.
3. **Verify + commit.** `agenticstory validate <universe>` stays green. `lock-level` should reach `partial` once the required shots pass and `locked` once the full matrix passes. Commit the generated art + the updated entity JSON.

## Locking a DECLARED-FUTURE era look (SPEC v0.10)

An `altLooks.era-<year>` entry declares a body the entity does not have today. Its art
does NOT belong in the default matrix, so lock it into the look:

```bash
python3 -m agenticstory.cli lock-shot <universe> <id> forward-fullbody \
  reference/<id>/era-2030/forward-fullbody.png --look era-2030 \
  --recipe reference/<id>/era-2030/forward-fullbody.recipe.json
```

Two things differ from an ordinary shot, and both are load-bearing:

1. **Generate it from the FACE, never from the body.** Pass the register anchor first, then
   the entity's locked FACE sheets and (for a real person) the photo stack. Do NOT pass
   `forward-fullbody`: that is the present-day silhouette this look supersedes, and a
   reference image outranks a word, so passing it drags the old body into the new one.
2. **`--look` never touches `requiredForRender`.** That is the default look's gate. An era
   plate must not be able to satisfy it.

Read back against the ERA's own invariants (`altLooks.<key>.invariants` plus the base
invariants it does not supersede), not against today's.

## Gates honored
- **Register-first:** every generation leads with the universe style anchor; no anchor means stop.
- **Read-back:** no shot locks without passing every invariant; DEFECT means regenerate from scratch.
- **Subject-approval:** a real person stays `realPerson.approval.state: "gated"` after art. This skill NEVER flips it to "approved"; that is the subject's own blessing, recorded separately.
- **Sensitivity:** the sensitive list is honored on every real-person render.
- **Idempotent:** locked passers are never regenerated.

## Not this skill
- Authoring the entity or its prompts (that is the `add-*` skills).
- Rendering a story's spreads (that is a renderer).
