# Agentic Brand OS — Engine Spec

**v0.1 — 2026-07-19. EARLY DRAFT.** The runtime/engine spec: the deployed console that **loads a
brand universe (a cartridge) and generates any on-brand deliverable from it** — in plain language,
with provenance, held to the brand's rules, and getting sharper every time it runs. Home:
`agenticbranduniverse.com`. Reference implementation: the **AITX Brand OS** (`garysheng/aitx`),
built for the AITX × NVIDIA hackathon.

> **Read this first — honesty note.** This is **v0.1 and explicitly early.** The *cartridge* format —
> the Agentic Brand Universe, [`SPEC.md`](./SPEC.md) (currently v0.5) — is spec'd and comparatively
> stable. The *engine* — the Agentic Brand OS, this document — is **still being figured out.** This
> spec **codifies what the AITX Brand OS reference implementation actually does today** and **names
> the open questions**; it is not a frozen standard. Field names, interfaces, and the conformance list
> below will change. Treat the *shape and the invariants* as the commitment and everything else as
> provisional. Do not read this as a finished standard.

> **Thesis, in one line:** *A brand is a cartridge; the OS is the console that plays it — load a
> universe, ask in plain language, get an on-brand deliverable with a recipe, and the mistakes it
> makes become durable rules the whole brand inherits.*

---

## 1. Where this sits (the ontology — locked)

There are **two specs** in this standard. This is the **second** one.

1. **Agentic Brand Universe** = the **cartridge** (data). A portable, version-controlled brand: its
   canon (characters, settings, motifs, doctrines, rules) + its blessed golden assets. Forkable,
   rentable, evolvable. This is what [`SPEC.md`](./SPEC.md) defines. **This spec does not redefine it.**
2. **Agentic Brand OS** = the **console/runtime** (software). A deployed engine that *loads* a brand
   universe and *generates* any on-brand deliverable (a **projection**) from it, in plain language,
   with provenance, held to the rules. **This is what this document specs, at v0.1.**

```
   cartridge (universe)   +   console (Brand OS)   →   anything you want
   canon + goldens + rules      the running engine       book · flyer · meme · merch · thank-you
   (Agentic Brand Universe)     (Agentic Brand OS)        (a projection / deliverable)
```

A **projection** (a.k.a. deliverable) is the *output* — medium-neutral. Agentic *storytelling* (the
picture-book renderer of the cartridge spec) is **one** projection; agentic brand *management* — the
flyer, the meme, the sponsor thank-you, the sticker, the speaker card — is the rest.

An OS instance may present as a **named agent** — a persona that is itself a projection of the OS,
carrying the brand's voice and audio DNA. AITX's is **Chip**, the brand czar. (§8.)

## 2. What an Agentic Brand OS is — and is not

**It is:** a deployed runtime that (a) loads a conforming brand universe, (b) turns plain-language
intent into an on-brand projection by composing the universe's blessed atoms, (c) scores its own
output against the brand's rules with a deterministic critic, (d) distills each brand mistake into a
durable general rule and persists it *through a human-merged pull request*, (e) attaches a
reproducible provenance recipe to every output, and (f) exposes all of this through permissioned
faces (view / generate / modify) over one shared, version-controlled source of truth.

**It is NOT:**
- **Not the cartridge.** It *consumes* a universe; it does not *contain* one. Swap the cartridge, keep
  the console. (AITX is one cartridge; the same OS pattern runs a personal brand, a church, a company,
  a franchise.)
- **Not a static brand guide.** A PDF cannot generate, cannot score itself, cannot learn. The OS is a
  living, interactable product.
- **Not a one-off script or a bare model wrapper.** A wrapper generates and stops. An Agentic Brand OS
  closes the loop — critic, learned rule, human gate, provenance — so the brand's knowledge compounds.
- **Not a replacement for human taste.** The gates (the golden gate, subject approval) are
  load-bearing by design; the human blesses, the agent proposes.

## 3. The cartridge ⇄ OS contract (the input)

The OS loads a brand universe conforming to the **Agentic Brand Universe** spec ([`SPEC.md`](./SPEC.md)).
At a high level, it expects to find and read:

- **An identity block** — the universe's constants (mark, palette id, platform id, voice terms,
  subject-approval policy, register). See cartridge SPEC §11. The OS reads these instead of hardcoding
  the brand. *(AITX: the `aitx` group entity + `identity` block; exact palette `#ff4201 / #010101 /
  #ffffff`.)*
- **Canon** — the typed, git-versioned graph of entities + relations (characters, settings, motifs,
  props, doctrines, stories). Source of truth is the structured record; prose is a field on it.
  *(AITX: `universe/` — `michael-daigler`, `jake-oshea`, the `founders` two-shot, `aitx-mark`,
  `antler-venue`, `aitx-skylark`, `aitx-merch`, `aitx-agent`/Chip.)*
- **Goldens** — the blessed asset library: the **atoms** (Golden Atomic Brand References — the mark,
  the founders, the venue, the products) plus finished **molecules** (flyers, posts, memes, stickers)
  composed from them. A file is golden *only after a human blesses it.* *(AITX: `goldens/`, staged from
  `explorations/`.)*
- **The rules** — the enforceable brand law the OS holds the line on:
  - **Visual identity rules** — the mark, co-branding, palette. *(AITX: `universe/brand-os/BRAND-RULES.md`
    — e.g. the cardinal rule "one asset carries one mark, and it is ours"; never a logo lockup.)*
  - **Voice** — how the brand sounds. *(AITX: `universe/brand-os/VOICE.md` — warm, plain-spoken, no
    em dashes, no corporate filler, no hype/fear, no foreign slogans.)*
  - **Learned rules** — the durable corrections the OS has distilled and a human has merged. *(AITX:
    `universe/brand-os/LEARNED-RULES.md`.)*

**The contract, minimally:** the OS is handed a path to a universe repo; it MUST be able to load the
identity block, resolve the canon and its load-bearing references, read the rule files, and refuse to
run against a universe whose required references do not resolve. *(AITX loads via the shared engine:
`python3 -m agenticstory.cli validate|list|assert-spread <universe>`.)*

> **Where the boundary is still soft (open).** The cartridge spec today types the *canon* and the
> load-bearing refs. It does **not yet** formally type the goldens library, the generation/skill
> layer, the permissions model, or the human-language edit surface — the OS reads those from
> convention (the `brand-os/` folder, `goldens/`), not from a locked schema. Formalizing that input
> contract is v0.2 work (§9).

## 4. Core capabilities (the MUSTs, grounded in AITX Brand OS)

Each capability below is a **MUST** for a system to call itself an Agentic Brand OS. Each is grounded
in a real path in the reference implementation.

### 4.1 Load a universe
The OS MUST load a conforming universe — its identity block, canon, goldens, and rule files
(BRAND-RULES + VOICE + any LEARNED-RULES) — and hold them as the live source of truth for the session.
References are load-bearing: **a missing reference is a hard error, not a silent guess.**
*Grounded in:* the shared engine's load + `assert-spread` gate; `universe/brand-os/*`.

### 4.2 Generate a projection from plain-language intent
The OS MUST turn a plain-language request ("I need a flyer for the Dallas meetup on the 14th") into an
on-brand projection, **composing atoms into molecules** — passing the relevant blessed atoms in as
references so the mark is always the real mark and the founders always read as themselves. **A
reference is load-bearing:** if a required atom is missing, the build fails loudly rather than
inventing one. *Grounded in:* `goldens/README.md` (atoms→molecules); `portal/app/api/agent/route.ts`
(plain request → structured asset); `portal/app/studio/*` (event-flyer, meme studios).

### 4.3 Self-critique with a deterministic brand-rule critic
The OS MUST score its own output against the brand's rules with a **deterministic** critic that turns
"on-brand" into a **number** — so improvement is *measured*, not claimed. The same rules a human reads
in the rule files are what the critic enforces, and the score is stable for the same input.
*Grounded in:* `portal/lib/agent/critic.ts` — `scoreText()` returns `{ score: 0–100, violations[] }`,
each violation a `{ rule, label, match, penalty }` (em dash −15, logo-mixing −40, corporate filler
−15, hype/fear −20, foreign slogan −15, exclamation spam −10). The critic is the metric the generator
optimizes against.

### 4.4 Recursive intelligence — distill mistakes into durable rules
When the critic flags a violation, the OS MUST **distill that specific mistake into ONE durable,
*general* rule** (not a patch for the one incident) and persist it so every future generation obeys
it. Crucially, the OS MUST persist it by **opening a pull request that a human merges — never a silent
commit** (§4.5, the golden gate). No model retraining; every rule the OS ever learned is a git diff.
*Grounded in:* the learn step in `portal/app/api/agent/route.ts` (distills a general imperative,
explicitly stripping the company/event/wording of the incident); `portal/app/api/learn-pr/route.ts`
(branches, appends to `universe/brand-os/LEARNED-RULES.md`, opens a real GitHub PR); the loop diagram
in the AITX `README.md`.

> This is the **recursive-intelligence loop**: generate → deterministic critic scores → distill a
> general rule → open a PR → **human merges (the golden gate)** → the merged rule grounds every future
> request. The knowledge base is the intelligence, and it persists honestly.

### 4.5 The golden gate — the agent proposes, a human blesses
The OS MUST enforce a **human-approval gate** before anything becomes "golden." Agent output is a
**candidate**, staged (AITX: `explorations/`), never written straight into the blessed library. A
learned rule is a **proposed PR**, never a direct commit. Promotion to golden — an asset, a rule, a
locked reference — **requires a human blessing.** *Grounded in:* `goldens/README.md` ("Golden means
human-approved… If it wasn't blessed, it isn't golden"); `BRAND-RULES.md` §Approval; the PR flow in
`learn-pr/route.ts`.

### 4.6 Provenance / reproducibility — every output carries a recipe
The OS MUST attach a **provenance recipe** to every generated output, sufficient to reproduce it:
the **model**, the **exact prompt**, and the **references pinned by hash**, plus params, template, and
rule-set versions. Nothing is a mystery; everything is reproducible. *Grounded in:* `generator/recipe.ts`
— the `Recipe` type (`model`, `prompt`, `params`, `references[]` where each `Reference` is
`{ path, sha256, role }`, `template`, `ruleSet`) written as a `.recipe.json` sidecar; the home gallery's
"How it was made" provenance sidebars.

### 4.7 Permissioned faces over one shared source of truth
The OS MUST expose **permissioned faces** — at minimum **view/download**, **generate**, and **modify
guidelines** — all reading and writing the **same** version-controlled canon. *Grounded in:* AITX
VISION.md §3 — three faces:
- **Partner** (public / sponsor / collaborator): browse and **download** on-brand assets; read the
  brand at a glance; self-serve, zero back-and-forth.
- **Creator** (chapter leaders, organizers): **generate** new on-brand assets in plain language,
  composed from the atoms, guardrails baked in.
- **Admin** (brand owners): **modify** the brand OS itself in plain language — canon, voice,
  guidelines, wardrobe, standing corrections — every edit a commit.

Permissions are configurable per person/role (view / generate / modify guidelines). *(The exact
permission model and UX is open — §9.)*

## 5. The recursive-intelligence loop (the heart of it)

```
   plain-language request
            │
            ▼
   ┌──────────────────┐        clean         ┌────────────────────────────┐
   │ generate asset   │ ───────────────────▶ │ on-brand projection        │
   │ (compose atoms,  │                      │ + provenance recipe        │
   │  strict output)  │                      │ (model · prompt · refs@sha)│
   └──────────────────┘                      └────────────────────────────┘
            │ violation
            ▼
   ┌──────────────────┐
   │ deterministic    │  turns "on-brand" into a numeric score
   │ brand-rule critic│
   └──────────────────┘
            │ distill the mistake into ONE general, reusable rule
            ▼
   ┌──────────────────┐   human merges (the golden gate)   ┌────────────────────┐
   │ open a PULL      │ ─────────────────────────────────▶ │ version-controlled  │
   │ REQUEST          │                                    │ LEARNED-RULES.md    │
   └──────────────────┘                                    └─────────┬──────────┘
                                                                     │ grounds every
                                                                     ▼ future request
                                                            (back to generate)
```

The load-bearing property is that **improvement is captured, not re-taught**: a correction becomes
standing, version-controlled canon that everyone who touches the brand next inherits for free. No
silent commits; no model retraining; the diff is the brand's learning.

## 6. Conformance

> **v0.1 caveat:** this list is derived from *one* reference implementation (AITX Brand OS). It marks
> what distinguishes an Agentic Brand OS from a bare AI wrapper. Expect it to tighten as a second
> implementation appears.

**MUST** (a system is not an Agentic Brand OS without these):
1. **MUST load a conforming universe** — identity block + canon + goldens + rule files — as the live
   source of truth.
2. **MUST treat references as load-bearing** — a missing required reference is a hard error, never a
   silent guess.
3. **MUST generate projections from plain-language intent** by composing blessed atoms into molecules.
4. **MUST self-critique with a deterministic critic** that produces a numeric on-brand score from the
   brand's own rules.
5. **MUST distill each brand mistake into a durable, general rule** (not an incident-specific patch).
6. **MUST enforce the golden gate** — human approval is required to promote anything (asset, rule,
   locked reference) to golden.
7. **MUST NOT silently commit learned rules** — learned rules persist via a human-reviewed pull
   request (or an equivalent explicit human-merge gate).
8. **MUST emit provenance** — every output carries a recipe pinning model, exact prompt, and
   hash-pinned references, sufficient to reproduce it.
9. **MUST expose permissioned faces** — at minimum view/download, generate, and modify-guidelines —
   over one shared version-controlled source of truth.

**SHOULD:**
- SHOULD present as a **named agent persona** carrying the brand's voice/audio DNA (§8).
- SHOULD keep the critic's rules in sync with the human-readable rule files, so a person and the agent
  hold the same line from the same source.
- SHOULD stage candidates in an explorations area distinct from the blessed goldens library.
- SHOULD make the whole loop measurable (a before/after delta on the critic score).

**MAY:**
- MAY offer multiple renderers/projection types beyond the first (picture-book, flyer, meme, merch…).
- MAY run the generator on any model/provider behind a swappable adapter (AITX uses Nemotron via NIM
  for copy and gpt-image-2 for images).
- MAY carry an **audio atom** (a brand voice-DNA sidecar) so external tools generate on-brand audio.

**Disqualifying (this is just an AI wrapper, not a Brand OS):** generates but does not load a
conforming universe; guesses past missing references; has no deterministic score (only vibes); learns
by silent commit or by fine-tuning with no human gate; emits no reproducible provenance; is a single
role with no permission surface.

## 7. Non-goals (for v0.1)

- Not a spec of the cartridge — that is [`SPEC.md`](./SPEC.md); this consumes it.
- Not a portable-runtime binary standard yet — AITX is a Next.js portal + a shared Python engine + a
  provenance generator; the OS's portable interface is explicitly open (§9).
- Not a plugin API for new projection/deliverable types yet — new renderers are added by hand today.
- Not a permissions/identity product — the role model is named, not yet formally specified.
- Not multi-universe — one OS instance runs one cartridge in the reference implementation.

## 8. The agent persona (Chip)

An OS instance MAY present as a **named agent** — a persona that is itself a **projection of the OS**,
not a separate thing bolted on. The persona holds the canon, the goldens, and the rules; people talk
to *it* instead of pinging the brand owner for assets. It carries the brand's **voice and audio DNA**.

*Grounded in:* AITX's **Chip**, the brand czar — a canon `character` (`aitx-agent`) with the brand's
**audio atom**: an ElevenLabs voice id (`brand-voice.json`: `mascot_name`, persona,
`elevenlabs_voice_id`). Chip's voice is the brand's real voice DNA; the same sidecar lets external
tools generate on-brand audio (e.g. the keynote is narrated by Chip in his own voice). The persona is
the human-facing face of the console; the cartridge supplies who it is and how it sounds.

## 9. Open / not-yet-specified questions (the v0.2+ roadmap)

Named honestly, because the engine is still being figured out:

- **The portable runtime interface.** AITX is a specific Next.js portal + shared engine + generator.
  What is the *portable* contract a conforming OS implements, independent of that stack? (The single
  biggest open question.)
- **The projection / skill plugin interface.** How does a new deliverable type (a novel renderer, a
  merch generator, a slide deck) plug in without editing the core? The cartridge spec's renderer
  interface (SPEC §4.5) is a start; the OS-side skill/projection registry is unspecified.
- **The permissions model shape.** Roles, grants, how modify-rights are configured and enforced, and
  whether the faces are one role-gated app or separate surfaces (AITX VISION §5).
- **The formal input contract beyond canon.** Typing the goldens library, the generation/skill layer,
  and the human-language edit surface as schema rather than convention.
- **Multi-universe.** One console running (or switching between) many cartridges; shared vs.
  per-universe knowledge.
- **The marketplace.** Create / fork / rent / earn on universes and OS instances — "GitHub for brand
  universes" (AITX `/platform`). Entirely unspecified here.
- **How the critic generalizes beyond hand-written rules.** Today the deterministic critic is a
  hand-authored rule set (banned phrases, penalties). How does it grow to catch violations no one
  pre-listed — and how do learned rules feed back into the *scorer*, not just the *generator*?
- **Determinism ceiling.** As in the cartridge spec, the critic makes the *check* deterministic; model
  *output* stays stochastic. The human gate remains load-bearing; that is a feature, not a gap to
  close.

## 10. Version note

- **v0.1 — 2026-07-19. Early draft.** First articulation of the engine/console half of the standard.
- **Reference implementation:** the **AITX Brand OS** (`garysheng/aitx`), built for the AITX × NVIDIA
  Claw Agent Hackathon (Recursive Intelligence track). Nemotron via NIM for copy, gpt-image-2 for
  images, a deterministic critic, real GitHub PRs for learned rules, hash-pinned provenance recipes.
- **Companion spec:** the cartridge format, [`SPEC.md`](./SPEC.md) (Agentic Brand Universe, v0.5) —
  spec'd and comparatively stable. This engine spec is **expected to change** as the portable runtime,
  the projection plugin interface, and the permissions model are worked out. The cartridge is the
  stable half; the console is the moving half.

## 11. Glossary

- **Agentic Brand Universe / cartridge** — the version-controlled brand *data* (canon + goldens +
  rules). Defined by [`SPEC.md`](./SPEC.md). The OS consumes it.
- **Agentic Brand OS / console** — the deployed *runtime* that loads a cartridge and generates
  projections from it. Defined by this document.
- **Projection / deliverable** — an OS *output* in a medium (book, flyer, meme, merch, thank-you).
- **Atom (GABR)** — a Golden Atomic Brand Reference: a blessed, locked, load-bearing reference (the
  mark, a founder, the venue, a product).
- **Molecule** — a finished deliverable composed by passing atoms in as references.
- **Deterministic brand-rule critic** — the scorer that turns "on-brand" into a stable number from the
  brand's rules (AITX `critic.ts`).
- **Recursive-intelligence loop** — generate → critic scores → distill a general rule → PR → human
  merges → grounds future requests.
- **The golden gate** — the human-approval gate: the agent proposes, a human blesses; only then is an
  asset/rule/reference golden. No silent commits.
- **Provenance recipe** — the reproducibility record on every output: model, exact prompt, hash-pinned
  references, params, template/rule-set versions (AITX `recipe.ts`).
- **Faces** — the permissioned views over one shared source of truth: partner (view/download), creator
  (generate), admin (modify guidelines).
- **Persona / Chip** — a named agent that is a projection of the OS, carrying the brand's voice/audio
  DNA (AITX's brand czar).
- **Audio atom** — a portable voice-DNA sidecar (e.g. an ElevenLabs voice id) that lets tools generate
  on-brand audio in the persona's voice.
