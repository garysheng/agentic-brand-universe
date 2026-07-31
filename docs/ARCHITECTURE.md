# Architecture

How a brand universe is put together, what runs it, and why the runtime is what it is.

Every diagram below was emitted by this repository's own `explanatory-plate` skill, deterministically,
from the palette in the spec. None was drawn by hand or by a model.

---

## The six layers

![The six layers](./diagrams/the-layers.svg)

Read it bottom up as a sentence. **Canon** is what is true. **Goldens** are what it looks like once
locked. A **form** is what makes a work the kind of thing it is. A **work** is one made thing, canon
given form. A **composer** is the agent that makes it and answers to a gate.

The split that matters most is between the middle two. **A form is a kind; a work is one made
thing.** Conflating them is what made this standard storybook-shaped for its first five versions:
the one primitive that existed carried a story's required fields (`logline`, `spine`, `refrain`,
`beats`), so every deliverable had to be a story to be expressible.

> **The ENCODING of those two layers is retired, and nothing has replaced it yet.** From v0.6 to
> v0.16 a form and a work were typed documents (surface, required kinds, slots, generators,
> invariants) executed by a single universal composer. That composer was deleted in v0.17 having
> produced zero works. The concepts survive; the schema does not, and no replacement is written
> until a second composer is proven. SPEC §4.8, §4.9 and §4.10 are the record. Read everything below
> about *how* a work gets planned as description of what was tried, not of a contract you can build
> against today. A flyer has no beats.

## The render step is three parts, not one

![Composer, compiler, gate](./diagrams/composer-compiler-gate.svg)

Collapsing these produces either a rigid template engine (no composer, so nothing new can be
composed) or an unaccountable one (no gate, so whatever the model returned ships).

**A composer** answers an open question and is the only layer where model intelligence belongs. There
is one *per form*, not one universal one (§4.10): a storybook, a diptych series and a deck plan
genuinely differently. What they share is everything underneath the plan.

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

**The judge is a subagent, and that is the whole implementation.** Independence is a property of
context, not of vendor or billing account. A fresh subagent inside the runtime that is already
composing has never seen the plan, which is the only thing the rule asks for, and it needs no second
credential. An earlier implementation required an API key and shelled out to a separate process; with
no key present every slot parked as unjudgeable, which made the correct architecture look like a
blocked one. It was neither. It was the cheapest judge being unreachable.

So the maker does not judge. Per generated unit, whoever composed it writes a **brief** naming exactly
what a judge is shown, and exactly what it is not:

```jsonc
{ "artifact": "...", "reference": "...", "mode": "identity" | "style",
  "checklist": ["no-text-in-art", "hands-loopy-non-anatomical, four fingers plus a thumb"],
  "withheld": "the plan, the beats, the compiled prompt, and the intent" }
```

The brief is the enforcement. Asking an agent to disregard what it already knows is not a control;
handing a different agent a bounded brief is. `mode` matters because there are two different
questions: `identity` judges against a character golden (*is this the same subject?*), `style` judges
against a pack anchor whose subject is irrelevant (*is this the same visual voice?*).

**The gate fails closed** (§4.10). A unit whose judged invariants could not be checked is *unjudged*,
never PASS: the artifact exists and is sound, and one check has not run. Re-running never regenerates
it, because re-rolling something nobody has judged pays twice and throws away the artifact the judge
was about to inspect. The retired executor spelled this state `NEEDS-JUDGMENT`; the rule outlived the
implementation.

## Where hosted execution is headed

![Why Managed Agents](./diagrams/why-managed-agents.svg)

> **ASPIRATIONAL, NOT DESCRIPTIVE** (SPEC §14). Nothing in this framework runs on Managed Agents.
> The composer this argument was written for was deleted in v0.17 having never run, and the pipeline
> that does the work (`make-a-book`) runs locally. The claim about the SHAPE of the workload is still
> believed; treat local execution as the only reality today.

Composing one illustrated book is not a request. It is tens of generated units, each a prompt assembly
plus one or more model calls plus one or more verification passes, running for an hour or more with
nobody watching.

Durable per-unit state is the load-bearing requirement, and it comes from the failure model rather
than from preference: when a unit exhausts its re-rolls it is marked DEFECT, **the remaining units
continue**, and the artifact emits incomplete with a per-unit report, so a person repairs one unit
instead of re-running an hour of work. That behaviour is impossible without state that survives a
restart. It is also, honestly, unbuilt here — the deleted executor implemented it, and §4.10 now lists
it among the open candidates for what belongs *under* a composer rather than inside one.

**The honest scope.** Most work on a model platform is a single call and needs none of this. One
request, one response, no state, no isolation problem, well served by any SDK. The claim here is
narrower and therefore checkable: once a deliverable needs many interdependent generations, held to
rules no single generation can satisfy, over a run long enough that nobody watches it, the workload
has changed kind. At that point you either operate that infrastructure or you rent it. Both are
legitimate.

## The linter

Everything above is only true if it is checked. `skills/lint-universe` runs static checks over a
universe and everything it declares: packs, entities, goldens, provenance, and provider quirks.
No generation, no API, no cost.

```bash
python3 skills/lint-universe/scripts/lint.py <universe-dir>   # 0 clean, 1 warnings, 2 errors
```

Every check corresponds to a failure that actually shipped:

| Check | The failure it prevents |
|---|---|
| `REGISTER-UNLOCKED` | a null style anchor, meaning generation should refuse |
| `GOLDEN-MISSING` | a required reference that will crash at render time |
| `PACK-NO-GATE` | a style pack with no read-back rules, which is a mood board |

There is one more check that runs at **compose time** rather than in the linter, because it needs the
work and not just the universe: a scene may not *name* something its style pack rejects. A beat
described a grid as "receding" for a pack that rejects perspective, and the compiler dutifully
appended "no perspective" to the same prompt, so the model received both instructions and picked one.

### Risk compounds per instance, so compose around the fragile rule

Not everything is a check. One finding from the same run is guidance rather than code, and it saved
more re-rolls than any check did.

A per-slot invariant is evaluated over the whole artifact, so **every instance of the risky element in
a scene is an independent chance to fail it**. On the hardest invariant in this universe, a hand with
exactly five digits, the plates asking for one hand passed quickly. The plate asking for two hands
failed three consecutive rolls, because it had to get the same fragile thing right twice in a row.
Rewriting that scene to use one hand was worth more than any amount of prompt strengthening, and it
cost nothing.

The general rule: when a judged invariant has a known failure rate, the work controls its own
exposure. Invoke the fragile element fewer times and the expected number of re-rolls drops with it.
That is an authoring decision, not a contract change, and it is the cheapest lever available before
anyone reaches for relaxing the rule or repinning the provider.

## Provider quirks

A **quirk** is what a specific model gets reliably wrong regardless of brand. It belongs to the
capability binding, not to the look: it survives a change of brand and dies with a change of provider,
which is the opposite of a style rule. They live in `registry/providers.json`, framework-owned, so one
project learning something benefits every other.

Quirks bind to the provider a job **resolves to**, not to its pin. Binding them to the pin left
anything deliberately kept provider-agnostic as the only unguarded thing, which is exactly backwards.

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
- [PROJECTION.json](https://appliedai.wiki/reference/standards/projection-json) — the v0.6–v0.16
  contract format, published separately. **Retired encoding** (SPEC §4.8); kept here as a pointer to
  what was tried, not as something to build against. That page lives in another repo and still
  describes it as live.
- [hyperagentic-age](https://github.com/garysheng/hyperagentic-age), a universe with eight forms and real committed output.
