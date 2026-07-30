# Glossary

The vocabulary, in the order it becomes load-bearing. Terms are defined by what they *refuse*
wherever possible, because in this framework the refusal is usually the feature.

For the formal definitions see [`../SPEC.md`](../SPEC.md); this page is the plain-language map.

---

**Universe** (also **cartridge**) — one brand or story world as version-controlled data: typed
entities, typed relations, locked assets, craft rules. It lives in its **own** git repo. The
framework holds no universe's canon.

**Canon** — the living contents of a universe. Entities and relations, each a typed record in its
own file, so two concurrent runs touch disjoint paths and cannot silently collide.

**Entity** — one named thing in canon. Kinds: `character`, `setting`, `prop`, `motif`,
`visual-metaphor`. Each is scaffolded with a **reference matrix** and stays `unlocked` until that
matrix is filled with real art.

**Relation** — a typed edge between two ids: `crossover-with`, `appears-in`, `derived-from`,
`contradicts`, `supersedes`. Makes contradictions explicit records rather than silent edits to
history.

**Reference matrix** — the set of shots an entity owes before it may be rendered (for a character,
eight; for a setting, a turnaround plus per-angle empty plates plus a blueprint). The list of
questions the art has to answer before anyone draws the entity into a scene.

**Golden** — a locked reference asset. The visual answer of record, **passed** to the model rather
than described to it. Prose drifts; a golden does not.

**Lock** — promoting a generated shot to golden, with its provenance frozen. An entity is
`unlocked` until its `requiredForRender` slots are locked, and the gate refuses it until then.

**Gate** — a check that **refuses** rather than warns. The pre-render gate (`assert-story`,
`assert-spread`) blocks a render whose cast lacks real art on disk. A read-back gate checks the
finished pixels against declared assertions. Failing closed is the whole design: a render that
proceeds without its references produces a plausible picture of the wrong thing, which is far more
expensive than a hard stop, because it passes review.

**Invariant** — the specific, checkable thing about an entity that must be true in every render
(a scar, a hand count, a silhouette). What `render-readback` crop-zooms and grades, one at a time.

**Register** — a universe's paint language: the anchor image plus the poles it rejects. Passed
first on every render, because a reference outranks negative words.

**Style Pack** — a register extracted into a portable folder (`pack.json` + `refs/` + a gate) that
works with **no universe**. The framework's lightweight front door: "here is a folder of images,
make more that look like them."

**Lookbook** — the complement of a Style Pack. Where a pack enforces *sameness* of look, a lookbook
defines a curated but deliberately **varied** vocabulary (a wardrobe, a range of faces) with a rule
that says vary, never clone.

**Rejected pole** — a look baked in as a negative. Reject a specific *failure*, never a whole
visual mode: a pole broad enough to name a capability deletes that capability, and the model cannot
tell you it did.

**Anchor** — the reference passed first, defining the look. Must be **content-neutral** (palette,
light, finish, no subject), or its content leaks into every render.

**Form** — the typed contract for a KIND of deliverable: surface, required kinds, slots,
invariants, emitted outputs. Called *Projection* before v0.14.

**Work** — ONE instance of a form, binding a brand's actual ids into its slots. Called *Composition*
before v0.14.

**Composer** — the agentic layer that plans, compiles, generates and repairs, answering to a gate.
Refuses an undeliverable surface at plan time, and parks a defective slot rather than halting.

**Generator** — code that **draws** an asset instead of prompting for one, for anything whose
correctness is a number rather than a judgement: marks, favicons, grids, scale rules, massing
renders. Deterministic, free, and identical every run.

**Provenance** (**recipe**) — the `.recipe.json` written beside every generated asset recording
provider, model, prompt, refs and hashes. Written as a *side effect of generating*, never as a
step at the end, because provenance you have to remember is not provenance.

**Craft canon** — a universe's recorded rules of craft (spine, genre, register rules), as records
rather than as advice in a prompt.

**Spine** — what a story argues, declared per story: `obedient-servant`, `thesis`, `primer`,
`testimony`, and others. Open set. A story is never assumed to be a hero journey.

**Casting sweep** — before naming any new entity, searching canon for one that already fits.
Reuse wins by default: it skips the whole matrix build, and every reuse is a crossover receipt.

**Derived artifact** — a file generated from a source of truth and regenerated on demand, fenced by
`BEGIN GENERATED` / `END GENERATED` markers, with a `--check` mode that fails when it is stale.
`CANON.md` in a universe, and this repo's own `README.md` and `REFERENCE.md`. The cure for prose
that was true when it was typed and rotted afterward.

**Hand-rolling** — doing framework-shaped work by hand instead of improving the framework so it
produces the result. Fine once, to keep momentum. Twice is a bug in the framework, and
`evolve-agentic-story` is the fix.
