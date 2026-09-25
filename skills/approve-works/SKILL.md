---
name: approve-works
description: Put a BATCH OF WORKS in front of the operator for approval on their phone, one batch per page, and record what they decide about each. Large images, the title and the line saying what each work is for, and per work APPROVE or RE-ROLL with an optional note, typed or spoken. The default for ANY batch of finished works (wiki heroes, covers, share cards, flyers, a run of on-brand images): never hand-build a review page for a run again. Verdicts land in the same seen sidecars the shot board writes, every tap is announced on the Freedom bus, and every re-roll's note comes back as the exact `reroll-slot` command that applies it. Use when a batch of works is rendered and needs the operator's eye, or when someone says "let me approve these", "put them on my phone", "review the heroes", "which ones should I redo", "approval board". NOT for an entity's reference matrix before a lock (that is shoot-references' shot board).
---

# Approve works

A batch of works gets judged on ONE page per batch, from the phone, at a link that keeps
working across sittings. This is the shot board's sibling: same record, same refusals, a
different shape of input.

| Board | Input | Page | When |
|---|---|---|---|
| shot board (`shoot-references`) | one entity's reference folder | one-shot, cards | before `lock-shot` |
| **works board (this)** | a manifest of finished works | mounted, one batch per page | after a batch renders |

## Input: a manifest

A JSON list, or an object holding the list under `items`, `works`, `heroes`, `slots` or
`entries`. Per item:

| Field | Read from (first that exists) |
|---|---|
| image | `image`, `out`, `path`, `file` (relative to the manifest, or any folder above it) |
| title | `title`, `name`, `id` |
| context line | `context`, `argues`, `caption`, `description` |
| recipe | `recipe`, else `<image>.recipe.json` |
| batch | `batch` (optional) |

Batches follow the recorded `batch` when any item has one, else chunks of five in manifest
order (the size batches are rendered and composed in). A manifest written for a run already
works: `works/2026-09-25-supersuit-heroes/heroes.json` needed nothing added.

## Steps

**1. Open it.**

```bash
python3 skills/approve-works/scripts/works_board.py open <manifest> --id <slug> --title "<Title>"
```

It stamps every current candidate onto its batch's board, mounts the page in the Freedom frapp
store at `/abu-works/` (a stable URL; opening a second board costs no restart), and prints the
phone link. Re-running it is safe: a tap is never erased, and a work whose bytes changed (a
re-roll written to the same path) is put back on the board for a fresh look.

**2. Prove it serves, WITHOUT looking for them.** `curl -I` each image route: HEAD answers
without recording a serve. A GET, or a screenshot, records one, and then the record says the
operator saw a picture only you saw. If you screenshot a page, run `open ... --restamp`
afterwards, which forgets the serve on every UNJUDGED work (never a verdict).

**3. Text the phone link** through `freedom:message-myself`, without being asked.

**4. Hear the taps.** Each one is announced on the Freedom bus (`kind: judged`,
`source: abu-works-board`), so a session that ends its turn still learns of it. Read the state
with `works_board.py status <id>`; it exits 1 while anything is unjudged.

**5. Apply the re-rolls.** `works_board.py rerolls <id>` prints, per re-roll, the note (typed,
and the transcript of anything spoken, with the audio path) and the exact
`reroll_from_recipe.py <image> --note "..."` command. Run those, read each result back
(`render-readback`), then `open` the manifest again so the new rolls go back on the page.

## What the page will not do

- **Show anything that is not a current candidate.** Nothing under `rejected/`,
  `superseded*/`, `candidates/`, `pre-reroll-*/`, and no earlier roll kept as `<slug>.rN.png`.
  The rule is `engine/agenticstory/candidates.py`, shared with the shot board; a manifest item
  pointing at one is listed as "not on the board" by name.
- **Take an approval for a picture it never served.** The engine refuses it (`seen.record_tap`)
  and the card shows the refusal instead of advancing.
- **Advance on a failed save.** The card stays with the error on it.

## Files

- `scripts/works_board.py` the verbs (`open`, `boards`, `batch`, `item`, `served`, `tap`,
  `status`, `rerolls`, `close`). The page reads and writes only through it.
- `frapps/works-board.mjs` the page. Freedom's shell, recorder and notify bus, resolved from the
  newest installed Freedom at every start.
- `frapps/mount.mjs` puts the page in the store and prints its links.
- State: `~/.freedom/frapps/abu-works-board/` (`boards/`, waiting `takes/`, saved spoken
  `notes/`, cached phone `previews/`); `ABU_WORKS_BOARDS` overrides it. Verdicts live beside
  each image in `<image>.readback.json`, under `seen`.
