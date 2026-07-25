---
name: universe-doctor
description: Grade how COMPLETE and how HIGH-QUALITY an Agentic Story / Agentic Brand Universe is, then work the punch-list. Runs a self-contained scorecard over the universe (identity, entity reference matrices, setting size-contracts, provenance coverage, craft-canon, stories, self-containment), returns a letter grade + per-dimension scores + a prioritized list of what to fix and which framework verb to reach for, and then tackles the top issues by dispatching those verbs. The rubric IS the framework's definition of "a done, good universe." Use when Gary says "grade this universe", "how complete is X", "universe checkup / health check / doctor", "what's left to do on this universe", "/universe-doctor", or when you want to know if a universe is ready to render/ship. Complements validate (schema pass/fail) and lint-universe (static warnings): this is the holistic completeness + quality report.
---

# Universe Doctor

A universe is never "done" by feel. This skill replaces the vibe with a **scorecard**: a
letter grade, a score per dimension, and a punch-list ordered by impact, each item naming the
exact framework verb that closes it. It answers two questions at once — *how good is this
universe, and what do I do next to make it better* — and the rubric it grades against is the
framework's working definition of success.

Where its neighbors stop short:
- **`agenticstory validate`** answers *is the canon schema-valid?* (pass/fail gate).
- **`lint-universe`** answers *are there static best-practice warnings?* (advisory list).
- **`universe-doctor`** answers *is it complete and high-quality, and what's the next highest-leverage fix?* (a graded report you can act on).

## The rubric (what a complete, good universe is — weights sum to 100)

| Dimension | Max | What it measures |
|---|---|---|
| **Validity** | 15 | universe.json + every entity parses and carries id/kind. A broken universe caps the grade. |
| **Identity** | 15 | `register.name`, a resolving `register.anchor`, a `mark`, `voice` term rules, a resolving `stylePack`. The constants every render reads. |
| **Entity matrices** | 25 | For each renderable entity, the fraction of its reference matrix that is filled AND resolves on disk (character sheets; setting/visual-metaphor contract plates + descriptor prose). The heaviest weight: unlocked references are the thing the whole framework exists to prevent. |
| **Setting size (v0.9)** | 10 | Every setting/visual-metaphor has a `scalePlate` file + a `scale` descriptor, so its size is checkable (an empty plate cannot prove its own size). |
| **Provenance** | 10 | Every generated image under `reference/` has a sibling `.recipe.json`. Provenance is a property, not a memory. |
| **Craft-canon** | 10 | `canon/craft/*.json` exists: the universe's invariants (spines, genres, register-rules like a lookbook binding) are encoded, not tacit. |
| **Stories** | 10 | Stories are composed over the canon (stub scores partial, full scores complete). A canon with no story is scaffolding, not a universe in use. |
| **Self-contained** | 5 | `assetRoot` is `.` so every ref resolves inside the repo (SPEC §3a). |

Grade: A ≥90, B ≥80, C ≥70, D ≥60, F <60.

## Procedure

1. **Grade it.**
   ```bash
   python3 ~/.../skills/universe-doctor/scripts/grade.py <universe-dir>        # human report
   python3 ~/.../skills/universe-doctor/scripts/grade.py <universe-dir> --json # machine-readable
   ```
   The script is self-contained (reads the universe's files directly, no engine import, no
   generation, no cost). It prints the letter grade, the per-dimension bars, and the punch-list.

2. **Read the punch-list top-down.** It is already sorted by impact (points recoverable). Each
   line names the fix and the framework verb that delivers it (`add-story`, `lock-references`,
   `add-setting`, `create-lookbook`, `on-brand-image`, …).

3. **Work the issues with the RIGHT verb — never hand-roll a fix.** For each item, invoke the
   named skill against this universe. Common closers:
   - matrix `X% filled` on a scaffolded entity → **`lock-references`** (generate + read-back + lock its remaining slots).
   - a renderable entity that doesn't exist yet → **`add-character` / `add-setting` / `add-visual-metaphor` / `add-motif` / `add-prop`**, then `lock-references`.
   - a setting that "cannot prove its size" → **`add-setting`** (fill `scalePlate` + `scale`).
   - "no stories" → **`add-story`**.
   - "no craft-canon" → **`create-lookbook`** (+ a register-rule) or author a spine/genre record.
   - images without a recipe → regenerate them through **`on-brand-image`** (the provider adapter writes provenance on every render).
   For a batch of framework-shaped fixes, dispatch the **`agenticstory-steward`** agent with the
   punch-list; it reaches for these verbs and flags anything the framework can't yet do.

4. **Re-grade after a work session** to confirm the score moved and nothing regressed. The grade
   is the definition of done: aim to raise it deliberately, not to "feel finished."

## Notes on reading a grade

- A **low grade is a report, not a failure** — a young universe SHOULD grade low; the punch-list is the plan. The script always exits 0.
- The heaviest weight is **entity matrices** on purpose: a universe whose references aren't locked will drift on every render, which is the exact failure the framework exists to kill.
- Do not "fix" a low sub-score by hand-editing a JSON to look complete (e.g. writing a plate path that doesn't resolve). The grader checks that files actually resolve; faking it just moves the lie downstream. Close the gap with the real verb.
