---
name: book-doctor
description: Grade a RENDERED book on local disk against what its render-spec declares, BEFORE it is delivered anywhere. Checks that every declared spread exists, that the endcaps (front cover and closing plate) are portrait while interiors are landscape, that every generated asset carries its provenance recipe, that no spread was generated from another spread render, and optionally that every cast entity is registered and locked. Deliberately knows nothing about any delivery surface: no bucket, no CDN, no reader URL, no network, no API key. Use when Gary says "book doctor", "is this book done", "check the book", "grade this book", "/book-doctor", or before declaring ANY rendered book finished. Complements assert-story (pre-render gate, no output yet to measure), lint-universe (static warnings) and universe-doctor (grades the whole universe); a delivery platform's own doctor probing its storage is a separate, platform-owned tool and the two do not overlap.
---

# Book Doctor

The Doctor Pattern applied to one rendered property: a fixed rubric, a punch-list, and an exit code. Run it before you call a book finished.

`assert-story` gates BEFORE a render, when there is no output to measure. `book-doctor` grades AFTER, when there is.

## What it checks

| # | Check | Why it exists |
| --- | --- | --- |
| 1 | Every spread declared in `render-spec.json` has a rendered file | A book can look done because the spreads you looked at exist. |
| 2 | Interiors are at the spec's `size` aspect | A stray portrait interior gets letterboxed. |
| 3 | **Front cover AND closing plate are PORTRAIT (3:4)** | Both are ENDCAPS, composed by the reader as single pages. The closing plate living at `spread-<N+1>` describes where it lives, not what shape it is; building it like an interior gets it cropped. |
| 4 | Every rendered asset has a `recipe.json` beside it | Provenance is a non-negotiable (model, exact prompt, every input by path) and recipes are build artifacts that never ship, so this is the only place it is checkable. |
| 5 | No asset was generated from another spread render | Editing a prior render lets a defect survive into its own "fix". The evidence is the recipe's input list, which also never ships. |
| 6 | (with `--universe`) every cast entity is registered and locked | A spread naming an unlocked or unregistered entity renders a stranger. |

## Usage

```bash
python3 ~/Documents/github-repos/agenticstory/skills/book-doctor/scripts/book_doctor.py \
  <book-dir> [--universe <universe-path>] [--json]
```

`<book-dir>` holds `render-spec.json`, `spreads/` and `cover/`. Exit `0` healthy, `1` problems, `2` unreadable. `--json` for machine output.

Per-book overrides live in the spec under `"doctor": {"coverAspect": 0.75, "interiorAspect": 1.5}`; the defaults are the contract and you should need them rarely.

## The boundary (read this before extending it)

**This tool is local and delivery-agnostic on purpose.** A delivery platform that stores assets in a bucket has its own health check, coupled to that bucket's SDK, its registry, and its reader URLs, and sharing that platform's frozen-tested aspect helper is what makes it correct. Pulling that logic in here would fork a tested check into an untested copy, which is the exact bug those platforms tend to have already had once.

So the split is:

| Tool | Question | Reads |
| --- | --- | --- |
| `agenticstory:book-doctor` (this skill) | **IS IT FINISHED?** | local disk vs the render-spec. No network, ever. |
| `npm run book:probe` (garysheng-books) | **DID IT ARRIVE?** | Firebase Storage + Firestore, from the consumer's side. |

**Run both. Neither replaces the other.** Checks 4 and 5 here are structurally impossible for a delivery probe, because recipe.json files never ship; equally, this skill has no idea whether an upload succeeded.

The platform command was called `npm run book:doctor` until 2026-07-26. Two tools with the same name, run twenty minutes apart in the same build, cost real confusion in reading back what had actually been verified, so the delivery one was renamed to `book:probe` after what its own header already called it: a probe from the consumer's side. If you find `book:doctor` in an older log or SAVE-LOG entry, it means today's `book:probe`.

## Gates honored

- **Provenance coverage**: an asset with no recipe is a defect, not a style choice.
- **No self-reference**: canon references only, never a prior render.
- **Endcaps are portrait**: the shape contract that pre-render gates cannot see.

## Not this skill

- Grading a whole universe's completeness → `universe-doctor`.
- Static pre-flight checks with no output yet → `lint-universe`.
- Refusing a render whose canon is not ready → `assert-story` / `assert-spread`.
- Confirming assets actually reached a delivery surface → that platform's own publish/doctor command.
