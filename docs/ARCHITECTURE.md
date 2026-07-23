# Architecture

How a brand universe is put together, what runs it, and why the runtime is what it is.

Every diagram below was emitted by this repository's own `explanatory-plate` skill, deterministically,
from the palette in the spec. None was drawn by hand or by a model.

---

## The six layers

![The six layers](./diagrams/the-layers.svg)

Read it bottom up as a sentence. **Canon** is what is true. **Goldens** are what it looks like once
locked. A **projection** is a kind of thing you can make. A **composition** is one of them. The
**composer** is the agent that makes it and answers to a gate.

The split that matters most is between the middle two. **A projection is a type; a composition is an
instance.** Conflating them is what made this standard storybook-shaped for its first five versions:
the one primitive that existed carried a story's required fields (`logline`, `spine`, `refrain`,
`beats`), so every deliverable had to be a story to be expressible. A flyer has no beats.

## The render step is three parts, not one

![Composer, compiler, gate](./diagrams/composer-compiler-gate.svg)

Collapsing these produces either a rigid template engine (no composer, so nothing new can be
composed) or an unaccountable one (no gate, so whatever the model returned ships).

**The composer** answers an open question and is the only layer where model intelligence belongs.

**The compiler** is deliberately dumb, and that is the point: it assembles the prompt and the
reference list from canon rather than from whatever the operator remembered to type. A rule the brand
already recorded can never be silently dropped.

**The gate** answers a closed question about a specific artifact. It is agentic wherever the rule is
perceptual, so the meaningful split is not agentic versus not, it is **generative versus
adjudicating**. Every invariant is typed accordingly:

| Type | Checkable by | Examples | Cost |
|---|---|---|---|
| `computed` | pure code | palette compliance, content fits its frame, geometry, required metadata | free, runs every time |
| `judged` | a model looking | no text in the image, malformed hands, is this the same person | roughly `judged` rules times slots |

**The judge must not be the maker.** A `judged` invariant is evaluated in fresh context, given the
artifact and the rule and nothing else, never the plan that produced it. An agent shown its own
reasoning defends it instead of inspecting the output. This was earned: a three-element graphic
shipped with one element missing its defining feature, because the maker "knew" the omission was
intentional variety and read its own intent rather than the pixels. An observer with no access to the
plan caught it instantly.

## Why the runtime is Managed Agents

![Why Managed Agents](./diagrams/why-managed-agents.svg)

Composing one illustrated book is not a request. It is tens of slots, each a prompt assembly plus one
or more model calls plus one or more verification passes, running for an hour or more with nobody
watching.

Requirement 2 is the load-bearing one, and it comes straight from the failure model rather than from
preference. When a slot exhausts its re-rolls it is marked DEFECT, **the remaining slots continue**,
and the artifact emits incomplete with a per-slot report. A person then repairs one slot instead of
re-running an hour of work. That behaviour is impossible without per-slot state that survives a
restart.

**The honest scope.** Most work on a model platform is a single call and needs none of this. One
request, one response, no state, no isolation problem, well served by any SDK. The claim here is
narrower and therefore checkable: once a deliverable needs many interdependent generations, held to
rules no single generation can satisfy, over a run long enough that nobody watches it, the workload
has changed kind. At that point you either operate that infrastructure or you rent it. Both are
legitimate.

## The linter

Everything above is only true if it is checked. `skills/lint-universe` runs static checks over a
universe and everything it declares: packs, projections, slots, emitters, generators, goldens, and
provider quirks. No generation, no API, no cost.

```bash
python3 skills/lint-universe/scripts/lint.py <universe-dir>   # 0 clean, 1 warnings, 2 errors
```

Every check corresponds to a failure that actually shipped:

| Check | The failure it prevents |
|---|---|
| `SLOT-NO-EMITTER` | a slot typed `deterministic` that names nothing capable of producing it |
| `SURFACE-INFEASIBLE` | a declared surface no generator can physically make (the 0.333 class) |
| `SLOT-NO-GENERATOR` | a generated slot nothing is assigned to produce |
| `INVARIANT-UNTYPED` | a rule that is neither `computed` nor `judged`, so nobody knows who checks it |
| `EXTENDS-UNRESOLVED` | a fork pointing at a projection that does not exist |
| `REGISTER-UNLOCKED` | a null style anchor, meaning generation should refuse |
| `GOLDEN-MISSING` | a required reference that will crash at render time |
| `PACK-NO-GATE` | a style pack with no read-back rules, which is a mood board |

It earned itself on its first run by finding a generated slot with **no generator declared for it**, a
bug that had been silently parking every cover as a defect. Parking works so well that a real defect
hid behind it, which is an argument for linting rather than against parking.

## Provider quirks

A **quirk** is what a specific model gets reliably wrong regardless of brand. It belongs to the
capability binding, not to the look: it survives a change of brand and dies with a change of provider,
which is the opposite of a style rule. They live in `registry/providers.json`, framework-owned, so one
project learning something benefits every other.

Quirks bind to the provider a slot **resolves to**, not to its pin. Binding them to the pin left the
one projection deliberately kept provider-agnostic as the only unguarded one, which is backwards.

Each quirk carries a `counter` appended automatically to every compiled prompt, and a `check` that
becomes a gate item, because countering something in a prompt is never assumed to have worked.

## Tests

```bash
./run-tests.sh      # no keys, no network, no generation
./sync-plugin.sh    # mirror skills into the packaged plugin, then PROVE they match
```

The sync script exists because the plugin keeps identical copies rather than symlinks, so a silent
copy failure leaves them out of sync with nothing to notice. It found a skill that lived only in the
plugin and was never tracked here, plus two skills whose scripts *and tests* existed on one side only.

## Further reading

- [SPEC.md](../SPEC.md), the normative standard.
- [PROJECTION.json](https://appliedai.wiki/reference/standards/projection-json), the contract format on its own.
- [hyperagentic-age](https://github.com/garysheng/hyperagentic-age), a universe with eight projections and real committed output.
