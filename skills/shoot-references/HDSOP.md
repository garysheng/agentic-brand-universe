---
title: "Give a scaffolded entity a body: shoot the matrix, read it back, lock what passes"
id: HDSOP-ABU-033
version: 0.1
skill: shoot-references
doc_status: drafting
tags: [art, canon, gate, provenance, golden]
frequency: "once per new entity, plus re-shoots when a seed changes"
est_time_per_run: "30-90 min per entity"
automation_potential: "medium"
related_skills: [add-character, add-setting, add-visual-metaphor, render-readback, create-style-pack, lint-universe, open-in-preview, judge-slot, create-or-manage-frapp]
related_workflows: []
concepts: [canon, entity, golden, invariant, register, style pack, provenance, gate]
---

# Purpose

A scaffolded entity gets a body. Three things happen in order: SHOOT, READ BACK, LOCK. Locking is
the last of the three, not the point of them.

The name was `lock-references` until 2026-07-26, and agents reaching for "make the art for this
character" did not find it, because locking sounds like a metadata operation on art that already
exists.

# When to use (Trigger)

After an `add-*` skill has scaffolded an entity and you want to SEE it: "shoot the references",
"make the art for X", "generate X's sheets", "give X its body", "X is still unlocked".

# Inputs / Prerequisites

- The universe and the entity id.
- `identity.register`. If `register.anchor` is null, STOP: the style is not locked. **Unless** the
  entity declares `structured.registerNeutral`, which is the one legitimate exception.
- `identity.register.stylePack` and the notes beside it. A universe that declares a pack usually
  declares it BECAUSE its inline anchor misbehaved, and the note says how.
- `reference/<id>/prompts.md` with every shot body filled. `chain_matrix.py` REFUSES while a body
  still says `TODO(author)`.
- For a real person, the photo stack, pointed at as a FOLDER.

# Roles

| Role | Responsibility |
|---|---|
| **The subject, when real** | Owns the approval. This skill NEVER flips `realPerson.approval.state` from gated; that is the subject's own blessing, recorded separately. |
| **Human operator** | SEES every shot. No shot locks until a person has actually seen it, and that delivery has to reach them wherever they are. |
| **Agent executor** | Resolves what remains, composes prompt bodies from the entity rather than typing them, shoots only what is missing, reads back every invariant, and locks passers WITH their recipes. |

# Procedure

Steps say WHAT happens. The flowchart says who; Automation Opportunities holds the ROI.

1. Resolve the work. Read the entity and `prompts.md`, and run `abu lock-level` to see what
   remains. Compose any unwritten prompt body with `scripts/compose_prompts.py`, which builds each
   body out of the entity's OWN strings, then READ what it wrote.
2. For each shot missing or previously DEFECT, generate with `chain_matrix.py`: register anchor
   first, rejected poles as negatives, the photo stack for a real person, and any already-locked
   shots so the face and build stay consistent. Locked passers are skipped, so re-runs are cheap.
3. Read back with `render-readback`, crop-zooming each invariant. On any DEFECT regenerate that
   shot FROM SCRATCH with the defect named, never an edit pass.
4. SHOW THE OPERATOR EVERY SHOT, by sending the files with the harness's own file-delivery tool. A
   batch of four or more goes as one contact sheet plus individual files for anything being
   approved. Build the sheet with `contact_sheet.py --cover <the reference dir>`, which REFUSES
   unless every shot in that batch is on it; `chain_matrix.py` prints the exact invocation when a
   chain completes, so the artifact is not something to remember.
4b. OPEN THE BOARD, WHICH SHOWS THE ART. `shot_board.py board` starts a frapp that serves every
   shot and records both the serve and the tap, then prints a phone link: TEXT that link to the
   operator through `freedom:message-myself`. A tap is what SEEN means (v0.50) and the picture has
   to be in front of them for the tap to mean it (v0.51). With no Freedom install it falls back to
   `AskUserQuestion` cards (four per call, a preview on every option, the off-list answer in the
   question text because a preview costs the visible `Other` row) and records every approval as
   `unshown` with the reason, because a card cannot carry a picture.
5. Lock each passer WITH its recipe: `lock-shot <universe> <id> <shot> <path> --recipe <path>`.
   This sets the sheet, promotes `requiredForRender` as the required shots lock, and freezes
   provenance at approval. It REFUSES a shot with no approving verdict, one whose bytes have
   changed since the verdict, and one approved on a frapp board that never served the picture.
6. Validate and commit. `lock-level` reaches `partial` once the required shots pass and `locked`
   once the full matrix does.

# Process Flowchart

Amber = irreducibly human. Blue = agent-executed or agent-proposed.

```mermaid
flowchart TD
    A[An entity is scaffolded and has no art] --> B{Is the register anchor locked?}
    B -->|No| C{Does the entity declare registerNeutral?}
    C -->|No| D[STOP. The style is not locked]
    C -->|Yes| E[Shoot with NO anchor at all. --register is refused]
    B -->|Yes| F{Does the register declare BOTH a pack and an inline anchor?}
    F -->|Yes| G[REFUSES at plan time. Read the anchorNote, then answer with --register]
    F -->|No| H[Compose any unwritten prompt body from the entity's own strings]
    G --> H
    E --> H
    H --> I{Is this a state set, or an angle matrix?}
    I -->|States| J[--star: every state conditions on the seed and the blueprint, not a sibling]
    I -->|Angles| K[Chain cumulatively, master to face to the rest]
    J --> L[Shoot only what is missing or was a DEFECT]
    K --> L
    L --> M[render-readback every invariant]
    M --> N{All PASS?}
    N -->|No| L
    N -->|Yes| R[Deliver the files, then compose the AskUserQuestion board]
    R --> O{Operator TAPS a verdict on each shot}
    O -->|Re-roll| L
    O -->|Keep| P[lock-shot with its recipe. Provenance frozen at approval]
    P --> Q[Validate, commit, report lock-level]
    classDef human fill:#fde68a,stroke:#b45309,color:#111827;
    classDef agent fill:#bfdbfe,stroke:#1e40af,color:#111827;
    class A,I,O human;
    class B,C,D,E,F,G,H,J,K,L,M,N,P,Q,R agent;
```

# Done / Verification

`abu validate` is green. `lock-level` reports `partial` or `locked`. Every locked sheet has a
single `<asset>.recipe.json` beside it, never two. A real person's entity is still `gated`. The
operator has received the files, not just had them opened on one machine, and every locked shot
carries a recorded tap: `shot_board.py status <png>...` exits non-zero while anything is
unlockable and names why.

**The tell that delivery was skipped: a session that generated a dozen images and whose transcript
contains no delivery, only reads the agent made to itself.**

# Exceptions & Troubleshooting

- **A reference shoot is the sparsest render there is**, which is exactly where an anchor's own
  SUBJECT comes back wholesale. A universe declaring both a pack and an inline anchor refuses at
  plan time; the refusal is free and fires before any generation, while a wrong seed is a paid
  image and a blessed wrong seed is a whole matrix.
- **The identity master owes the register nothing.** A photoreal master from which every register
  rendition is DERIVED cannot wait for a blessed register, because it is what the conversions are
  made FROM. Declare it on the ENTITY, never at the command line: a flag cannot refuse a re-shoot
  it is not passed, and a plate cannot be un-baked.
- **Shoot the RENDITIONS from the master, never from the photographs again.** Two independent
  shoots of one subject produce two subjects.
- **The photographs decide the SHOOTING ORDER, and the order is load-bearing.** When the
  photographs cover a NON-default era, shoot that era FIRST and chain the others off it. One
  entity runs fully inverted: elder from the two public photographs, the young default chained off
  elder, and bedfast chained off young. Shooting three in parallel from prose returns three
  different men who merely share a description.
- **Never write the prompt into a throwaway script.** Faced with a stub, an agent wrote its prompts
  inline in five throwaway bash scripts and called the provider directly; the tool it needed
  already existed and already did chaining, the register and skip-existing. A prompt in
  `prompts.md` is versioned, reviewable and reused; the same prompt in a temp file is gone when
  the session ends.
- **A hand-typed prompt paraphrases the invariants slightly, and read-back then checks the art
  against the OTHER wording.** A composed prompt cannot diverge from the rule it will be judged by,
  because it is the same string.
- **Never write a second recipe sidecar.** Two for one asset can diverge, and did.
- **ONE recipe, and never a bare `--star` on an angle matrix.** Use `--star` when shots are STATES
  rather than angles: a cold night plate and a warm-gold noon plate chained serially walk the night
  into the noon, and a negative cannot undo a reference image.
- **The blueprint holds the OBJECT, not the FRAMING.** Two states seeded off one blueprint came back
  with different cover proportions and read as two different books. Pin the shared dimensions as
  NUMBERS in every state's prompt and put it on the entity as an invariant.
- **Replacing the seed invalidates the whole matrix, and it is not bookkeeping.** The temptation is
  to edit each recipe's input digest to today's bytes, which is laundering: it turns "nobody has
  re-judged these" into "these were all approved", silently. Re-shoot instead; nine plates cost
  nine calls and under a minute. And check whether the staleness is real: the same swap changed a
  character's jewellery, visible in six of the nine plates.
- **`open-in-preview` alone is NOT delivery.** Half the time the operator is remote or on a phone.
  This is also why the board is a frapp rather than a viewer on this machine: a page on their
  tailnet goes where they are, and a window here reports success against a screen nobody is at.
- **Never attest to a display.** There is no verb for "I showed them". `shot_board.py served` is
  called by the page from inside the response that sent the bytes, and an agent calling it about a
  picture no browser requested is the forgery the whole mechanism exists to remove.
- **A cross-entity selector can only ADD.** The field that lets you say more must not become a way
  to skip a plate the entity's own gate demands.

# Automation Opportunities

**Already automated:** prompt composition from the entity's own strings, the both-anchors refusal,
the register-neutral shoot with a recipe that records the absence as a statement, automatic
discovery and passing of a code-drawn blueprint, the star topology, `--print-plan` for a free
pre-flight, skip-existing idempotence, provenance merged into the single sidecar, the prompts
backfill and scaffold for old entities, and the multi-character scale plate as a verb.

**Irreducibly human:** the approval, both the subject's and the operator's look at every shot. A
golden IS human judgement frozen, so a shoot that locks without one has frozen nothing.

**Partly built, v0.49.** The sheet can no longer be SHORT: `contact_sheet.py --cover` refuses a
sheet that does not cover its batch, which is the refusal this skill's own method already claimed
the script performed and which no code performed. And the command that builds it is printed where a
shoot ends, so it is a step rather than a technique.

**Closed, v0.50.** The refusal this section called the strongest next candidate is built:
`lock_shot` refuses a slot with no recorded verdict. Both halves of the definition it was waiting
on were settled by the owner on 2026-09-14 -- what COUNTS as shown is a tap on an
`AskUserQuestion` card, and an absent operator is a `waived` verdict with a written reason, which
is never a board option because a waiver is by definition not a tap. It does change the cost of
every shoot: a matrix now costs two or three boards of four questions each, and that is the price
of a golden meaning what it says.

**Closed, v0.51.** The question this section left open -- whether the board should carry the
picture itself rather than its path -- is answered, and the answer generalises: **a choice that
requires LOOKING at an artifact goes to a frapp; one answerable from WORDS stays an
`AskUserQuestion` card.** `shot_board.py board` opens a page that serves each shot and takes each
verdict, so the display stops being something an agent claims and becomes something the page
knows, and the link reaches the operator's phone rather than this machine's screen. An approving
tap on a frapp board that never served is refused.

**Still open, and it is a LIMIT rather than a gap.** Nothing proves a human looked at the screen;
eyes are not addressable. What the record now says is that the bytes reached the browser the
verdict came from, which is the strongest thing a machine can know about a look and is strictly
stronger than a filename. Do not build ceremony on top of it that looks like more proof than that.

**And one step is still prose:** texting the phone link. ABU cannot invoke `freedom:message-myself`
from Python -- the Skill tool belongs to the agent -- so `shot_board.py board` prints the
instruction at the moment of use and this map repeats it. The frapp itself is unaffected, because
the Mac URL works without it; what is lost when it is skipped is the remote operator.

# Related

- [add-character](../add-character/SKILL.md) and siblings: author the entity and its prompts.
- [render-readback](../render-readback/SKILL.md): step 3, and the crop and measure tooling.
- [create-style-pack](../create-style-pack/SKILL.md): the pack a declared `stylePack` resolves to.

# Revision History

| Version | Date | Changes |
|---|---|---|
| 0.1 | 2026-09-14 | Written from the skill file, read rather than recalled. |
| 0.2 | 2026-09-14 | v0.50: the board is the delivery record, and `lock-shot` refuses without a tap. |
