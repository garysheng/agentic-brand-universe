---
name: book-doctor
description: Grade a RENDERED book on local disk against what its render-spec declares, BEFORE it is delivered anywhere. Checks that every declared spread exists, that the endcaps (front cover and closing plate) are portrait while interiors are landscape, that every generated asset carries its provenance recipe, that no spread was generated from another spread render, and optionally that every cast entity is registered and locked. Deliberately knows nothing about any delivery surface: no bucket, no CDN, no reader URL, no network, no API key. Use when Gary says "book doctor", "is this book done", "check the book", "grade this book", "/book-doctor", or before declaring ANY rendered book finished. Complements assert-story (pre-render gate, no output yet to measure), lint-universe (static warnings) and universe-doctor (grades the whole universe); a delivery platform's own doctor probing its storage is a separate, platform-owned tool and the two do not overlap.
---

> `$ABU` below is wherever ABU is installed. Find it with `ABU=$(python3 -c "import agenticstory,pathlib;print(pathlib.Path(agenticstory.__file__).resolve().parents[2])" 2>/dev/null || echo ~/.claude/plugins/cache/garysheng/abu/*/)`, or just ask the harness; never hardcode a home directory.


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
python3 $ABU/skills/book-doctor/scripts/book_doctor.py \
  <book-dir> [--universe <universe-path>] [--json]
```

`<book-dir>` holds `render-spec.json`, `spreads/` and `cover/`. Exit `0` healthy, `1` problems, `2` unreadable. `--json` for machine output.

Per-book overrides live in the spec under `"doctor": {"coverAspect": 0.75, "interiorAspect": 1.5}`; the defaults are the contract and you should need them rarely.

### An ENDCAP MAY BE DECLARED IN `spreads`, and it is not an interior

`compose-spec` emits the endcaps as ordinary members of the `spreads` array, with the ids
`cover` and `closing-plate`. Until 2026-07-31 the interior list was taken from `spreads`
verbatim, so a declared endcap was graded TWICE: once correctly as an endcap (portrait), then
again as an interior (landscape), and **the second grade can never pass.** The report read
`aspect 0.75 (want 1.5)` on a cover that was exactly right.

Two more defects compounded it. `max(int(id.rsplit("-")[-1]))` raised on the non-numeric id
`cover`, and the fallback counted the endcaps in, so a 69-spread book was told its closing
plate was `missing spread-72`. And check 6 read `characters`/`extras`, a dialect nothing in
the chain emits, while `compose_spec.py` writes and `assemble_prompt.py` reads `cast`, so the
cast-registered-and-locked check had been a silent no-op on every real book since it shipped.

The net effect was that **this tool failed every book, on both endcaps, while agreeing with
the platform's staging script about what the right answer was.** That is worse than having no
doctor: it teaches its operator that the doctor is wrong, so the run it finally catches
something real is the run nobody reads. Caught by the-power-of-obeying-book, 69 spreads, which
was correct and graded as three FAILs.

Accepted endcap names, in either naming convention:

| role | composer names (pre-conform, PORTRAIT enforced) | staged names (post-conform, exact 3:4) |
|---|---|---|
| front cover | `cover`, `cover-0` | `spread-00-cover` |
| closing plate | `closing-plate`, `plate-0` | `spread-<N+1>` |

## The boundary (read this before extending it)

**This tool is local and delivery-agnostic on purpose.** A delivery platform that stores assets in a bucket has its own health check, coupled to that bucket's SDK, its registry, and its reader URLs, and sharing that platform's frozen-tested aspect helper is what makes it correct. Pulling that logic in here would fork a tested check into an untested copy, which is the exact bug those platforms tend to have already had once.

So the split is: **book-doctor answers "is this book finished and internally consistent," the platform's doctor answers "did it arrive."** Run both. Neither replaces the other, and checks 4 and 5 here are structurally impossible for a delivery probe because the evidence never leaves the machine.

## Gates honored

- **Provenance coverage**: an asset with no recipe is a defect, not a style choice.
- **No self-reference**: canon references only, never a prior render.
- **Endcaps are portrait**: the shape contract that pre-render gates cannot see.

## Not this skill

- Grading a whole universe's completeness → `universe-doctor`.
- Static pre-flight checks with no output yet → `lint-universe`.
- Refusing a render whose canon is not ready → `assert-story` / `assert-spread`.
- Confirming assets actually reached a delivery surface → that platform's own publish/doctor command.
