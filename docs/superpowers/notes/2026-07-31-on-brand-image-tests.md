# Testing `on-brand-image` — the proven path was the untested one

**Date:** 2026-07-31
**Target:** `skills/on-brand-image/scripts/generate.py` (380 lines)
**Tests:** `skills/on-brand-image/tests/test_generate.py` (98 tests)
**Before:** 545 tests across 28 files. **After:** 643 tests across 29 files. ALL GREEN.

## Why

`generate.py` is the framework's single generate path: every image in every universe
and every style pack goes through it, 293 works and counting. It had zero tests. The
composer deleted the day before had 91 tests and zero works. That inversion is the
whole point of this session: coverage had accumulated where the code was cheap to
test, not where it was load-bearing.

## The seam: no API calls, no network, no generation

`run-tests.sh` opens with "No API keys, no network, no generation," so the entire
suite stops at the provider boundary:

- `subprocess.run` is replaced by a fake that **records the argv it was handed** and
  writes the bytes the real provider would have written. It asserts `cmd[0] == "uv"`,
  so a test that stopped intercepting a real shell-out fails loudly instead of
  quietly passing.
- `provider_script` is stubbed to `/nonexistent/never-executed-provider.py`, which is
  never executed and would fail if it were.
- The tests therefore exercise the **real `main()`** — real prompt compilation, real
  ref ordering, real recipe write — rather than a refactored shadow of it.
- `TestCliRefusals` additionally runs the CLI as a **real child process**, but only on
  paths that exit before a provider is ever resolved, with `OPENAI_API_KEY` and
  `GEMINI_API_KEY` stripped from the child env.
- Every fixture pack, universe, reference and output lives in `tempfile` temp dirs.

Verified by running the suite with `socket.socket.connect`, `connect_ex`,
`create_connection` and `getaddrinfo` all monkeypatched to raise: 98 tests, OK.

## No refactor

Nothing in `generate.py` was extracted or changed. The permit and pack-compilation
logic stayed inline in `main()` where 293 works have proven it, and the stubbed
`subprocess.run` made it testable as-is. So the "does the CLI still emit the identical
prompt string" question is trivially yes — there is no second code path to drift.

## What is covered

| Area | Tests | Notes |
| --- | --- | --- |
| `--permit` | 18 | The newest code, added 2026-07-30 with zero coverage |
| Style-pack compilation | 11 | style line, poles clause, missing/empty packs |
| Ref ordering | 11 | anchor-first, de-dup, skip-missing, entity-outranks-pack |
| The recipe | 18 | shape, sha256, no machine leakage, never skippable |
| `resolve_entities` refusals | 14 | every path must REFUSE, never proceed |
| `shrink_ref` | 10 | alpha as PNG, non-alpha as JPEG, never fails a render |
| `_abu_root` | 5 | walks up for the marker, helpful `SystemExit` without one |
| CLI boundary (real subprocess) | 6 | refusals reachable through argparse |
| Suite self-guards | 5 | proves the provider stub is real |

Highlights worth naming:

- **The permit's loud refusal** is tested from four angles: a permit matching nothing
  refuses; the message names the pack's actual poles; nothing is generated and no
  recipe is written; and one bad permit refuses even when a sibling permit matched.
  A silent no-op would read as "text is allowed now" while the negative sat in the
  prompt, so this is the property that matters most.
- **`permitted` in the recipe** records the pack's own wording (`Any Text Or
  Lettering`) rather than the operator's permit string (`text`), and is absent
  entirely when nothing was lifted.
- **Anchor-first ordering** is asserted against a pack whose manifest lists the anchor
  in the middle of `refs`, which is exactly what `create-style-pack` writes.
- **Entity plates outrank the pack anchor**, per the comment explaining that a pack
  pulls hard toward its own faces.
- **The recipe points at real references, never the shrunk upload temp files** — a
  recipe naming a deleted temp copy is provenance that cannot be re-run.
- **A provider that returns 0 but writes nothing still refuses.** No image, no recipe,
  and specifically no recipe describing an image that does not exist.

### Mutation-checked

The suite was validated by breaking `generate.py` five ways and confirming failures:
disable the permit refusal (5 failures), put the anchor last (2), redirect the recipe
write (1 failure + 26 errors), flatten alpha in `shrink_ref` (1), append entity refs
instead of prepending (1). All reverted; the file is byte-identical to `4a3c860`.

## Bugs found — reported, not fixed

Both are the same class the `--permit` loud refusal exists to prevent, reached by
different doors. Both are pinned by tests suffixed `_KNOWN_DEFECT`, so a fix is a
deliberate, visible change to an assertion rather than an accident.

1. **`--permit` without `--style-pack` is a silent no-op.** Every permit code path
   lives inside `if a.style_pack:`. A permit passed without a pack neither lifts
   anything nor refuses, and leaves no `permitted` key in the recipe. The operator
   believes they granted an exception; nothing happened and nothing said so.
   *Suggested fix (not applied): refuse at argument-parse time if `--permit` is given
   without `--style-pack`.*

2. **`--permit ""` matches everything and lifts nothing.** The lift loop guards
   `if t and t in r.lower()`, but the unmatched check does not — and `""` is a
   substring of every pole, so an empty permit always "matches" and can never be
   reported as unmatched. Silent no-op again.
   *Suggested fix (not applied): drop empty permits at parse time, or refuse them.*

Neither was fixed here because this is a path with 293 real works behind it and the
brief was tests, not behavior. Neither is trivial in the "obviously safe" sense: both
fixes turn a currently-succeeding invocation into a hard exit, which is a CLI
behavior change that deserves its own commit.

## Deliberately not covered, and why

- **Any real image generation, provider HTTP, or model behavior.** Out of bounds by
  the runner's own contract. `gpt-image-2` and `nano-banana-pro` are separate scripts
  with their own ownership; this file is an adapter and is tested as one.
- **`provider_script` / `resolve_str` resolution.** It belongs to
  `engine/agenticstory/providers.py` and is covered by the engine suite. Stubbing it
  is what keeps this suite offline.
- **`_engine_on_path` sys.path mutation in isolation.** It is exercised transitively
  by every `--entity` test, and asserting on global `sys.path` mutation across tests
  is order-dependent and worse than the coverage is worth.
- **Concurrency and the `--timeout` knob's actual effect.** The pass-through is
  asserted (present only when set, correct value); whether 900s beats server-side
  queueing is a property of the provider under load, not of this file.
- **Pillow's downscaling quality.** The tests assert the max edge, the format
  decision, alpha survival, and that the original is untouched. Whether LANCZOS at
  q90 is visually indistinguishable at reference duty is a taste judgement that was
  already made and recorded in the source comment.
- **`--lookbook` beyond recipe recording.** The flag currently only annotates the
  recipe; there is no compilation behavior to test yet.

## Follow-ups worth someone's time

- Fix the two permit defects above, together, in one commit with the refusal tests
  flipped from `_KNOWN_DEFECT` to positive assertions.
- The zero-refs pack check (`style pack ... resolved zero references`) fires *after*
  the prompt has already been compiled with the pack's style line. Harmless today
  because it exits, but it means the failure message cannot mention how far it got.
