---
name: make-a-playable-deck
description: Build a mobile-friendly PLAYABLE slide deck from slides declared as data, for sending someone an argument they can sit with on their phone. Use when the operator says deck, slides, present this, walk someone through it, send it to X for feedback, or asks for an artifact someone should reflect on rather than read as a document. Emits ONE self-contained HTML file with fit-to-viewport scaling so nothing scrolls, swipe, deep-linked slides, a draggable scrub bar across the whole argument, and a palette read from the universe's own tokens. NOT for a printed PDF and NOT for a document; a deck is a sequence someone moves through.
---

# Make a playable deck

```bash
python3 skills/make-a-playable-deck/scripts/build_deck.py <deck.json> \
    --out <dir> [--palette <universe>/canon/craft/palette.json] [--assets <dir>] \
    [--repo-root <universe>]
```

**A deck is DATA plus a shell.** You write `deck.json`; the shell is the same every time and
is not yours to edit per deck. If the shell cannot express something, that is a gap in the
shell and it gets fixed there, because the second deck is where a per-deck edit silently
diverges from the first.

## Why this exists rather than hand-writing HTML

Everything that makes a deck good on a phone is mechanism, not content, and all of it is
tedious and easy to get subtly wrong: measuring a slide unscaled and transform-scaling it so
nothing ever scrolls, re-measuring when an image finally loads and reports a height, `100dvh`
because iOS `vh` hides the footer behind the address bar, horizontal-intent-only swipe so a
vertical drag can still scroll, `replaceState` so the back button leaves the deck instead of
walking back through twelve slides.

**Extracted 2026-09-12 from one deck that had already been used in front of a real audience on
real phones.** That deck is the whole evidence base, and the comments in `shell/deck.js` that
explain WHY are carried over verbatim, because each records a failure that is invisible in
working code.

## The slide kinds

Ten, and they are a hypothesis rather than a vocabulary. Unknown keys are **refused by name**,
because a mistyped key is the one defect a deck cannot show you: the content is simply absent,
on one slide, and the deck still looks finished.

| kind | for | payload |
|---|---|---|
| `cover` | the opening | `heading`, `lede`, `image` |
| `statement` | a claim with room around it | `heading`, `body` (string or list) |
| `image` | the artwork IS the point | `image`, `caption`, `plain` |
| `pair` | a rejected candidate beside the pick | `images: [{image, caption}]` |
| `split` | prose next to a picture | `body`, `image` |
| `quote` | somebody's own words | `quote`, `who` |
| `chat` | a recreated exchange | `turns: [{from: me\|them, text}]` |
| `table` | where taste became a number | `columns`, `rows`, `pick` |
| `list` | a short enumeration | `items`, `ordered` |
| `handoff` | a prompt the reader takes away | `paste`, `label`, `footnote` |

`**bold**`, `*italic*` and `[text](https://...)` work in any text field. Nothing else does, on
purpose: a slide is a sentence or two, and a markdown parser would let a slide carry headings
and tables that the kinds exist to decide. **Links are https only**, and that is the security
boundary rather than a style rule: `javascript:` and `data:` would otherwise become live
handlers on a page that escapes everything else it is handed.

## The method

1. **Decide the SPINE before writing a slide.** A deck is not a document with page breaks. It
   is one argument, in order, and the order is the work. Write the spine as a list of one-line
   claims first; if two adjacent claims are the same claim, you have a slide to cut.
2. **Lead with the result when the deck is for FEEDBACK.** A reader cannot evaluate a journey
   until they know what it arrived at. Put the finished thing first with almost no words, then
   the decisions behind it.
3. **Every claim carries its alternative.** This is the difference between a deck that gets
   "looks great" and one that gets critique. A `pair` slide showing the rejection beside the
   pick invites a real reader to disagree with the pick; a gallery of finals does not.
4. **Surface the flaws early, and name them.** A reader who finds a weakness you hid stops
   trusting the rest. A reader who meets it on slide three reads the whole deck as an audit.
5. **Pass `--palette`** so the deck carries the universe's own tokens. Without it the shell's
   neutral defaults apply and the deck SAYS SO in its own provenance comment, so nobody can
   mistake an unthemed deck for a themed one.
6. **`--assets` copies the images beside the HTML**, so the folder travels and the deck works
   offline. Reference them by plain filename in the slides.
7. **OPEN IT ON A PHONE BEFORE SENDING IT.** The fit is measured at run time against a real
   viewport, so a desktop window proves almost nothing about the device most people will read
   it on. This is the step that gets skipped and it is the only one the generator cannot do.
8. **Sending it to a person is a separate, gated act.** Hand the URL to `freedom:send-message`,
   which shows the draft and waits for a human yes. Never send unasked.

## A deck built to be REVIEWED declares a `review` block

A deck is the worst possible artifact to receive feedback on through an agent. The argument is
in pictures, the pictures are resized copies with invented filenames, and a comment like
"slide 2, this image feels off" hands the reviewer's agent a caption and nothing else. It
cannot open the plate, cannot read the prompt that made it, and cannot see which canon rule the
picture is evidence for, so it either asks the reviewer questions the deck already answered or
it fills the gap with a plausible guess that reads exactly like a fact.

Declare `review` and the build emits **`llms.txt`** beside the HTML: the deck as an index an
agent can read, with every image carrying its absolute URL (for an agent holding only the link)
AND the repo-relative path of the source plate (for an agent holding the repo, which can then
open the `.recipe.json` beside it and read the exact prompt that made the picture).

```json
"review": {
  "baseUrl": "https://<where-it-is-served>",
  "repo": "org/universe",
  "clone": "git clone git@github.com:org/universe.git",
  "assetRoot": "works/<work>/assets",
  "author": "who made it", "reviewer": "who is reading it",
  "boomerang": "BOOMERANG.md",
  "returns": "one line naming the document that comes back",
  "protocol": ["how to name a slide", "what kind of comment is useful"],
  "canon": [{"path": "canon/entities/x.json", "what": "one line"}]
}
```

Then every image carries its `source`, beside a single image or inside each `images` entry:

```json
"source": {
  "path": "reference/<entity>/<roll>/<plate>.png",
  "depicts": "what the plate is, in one line",
  "governs": ["canon/entities/<entity>.json"],
  "status": "blessed|rejected|superseded|candidate|proof|generated",
  "note": "anything a reviewer would otherwise have to ask"
}
```

**Declaring `review` is declaring that every image is traceable, and the build refuses until
that is true.** A review file with holes is worse than no review file: the one image with no
source is the one the reviewer's agent quietly guesses about.

**Pass `--repo-root <universe>` and every `source.path`, every `governs` entry and every
`review.canon` path is checked to exist.** Paths rot for ordinary reasons: a plate gets
promoted out of `rejected/`, a roll is renamed, a generator's output folder is cleaned. None of
those announce themselves, and a dead path is worse than no path, because the agent goes
looking, finds nothing, and has to decide whether the deck is lying.

Pair it with a `handoff` slide at the end carrying a conforming
[BOOMERANG.md](https://appliedai.wiki/reference/standards/boomerang-md) prompt, and the review
becomes one paste for the reviewer instead of a list of instructions they have to follow.

## Refusals

- A deck with no slides.
- An unknown `kind`, naming the ones that exist.
- An unknown key on a known kind, naming the key and what is allowed there.
- An unknown key inside an entry of `images`, or inside a `source`.
- A kind missing its payload (`pair` with no `images`, `table` with no `columns`,
  `handoff` with no `paste`).
- A `source` whose `status` is not one of the known six.
- `review` with no `baseUrl`, since every URL it emits is absolute.
- `review` declared while any image lacks a `source` with both `path` and `depicts`.
- `review.boomerang` naming a file that does not exist beside the deck, rather than shipping a
  dead link on the one slide whose whole job is to be pasted.
- With `--repo-root`, any `source.path`, `governs` or `review.canon` path that does not resolve.

## Where the work goes

The deck folder is a WORK, so it belongs with the universe's other works rather than in a
scratch directory, and its slides file is the authored artifact worth keeping: re-running the
builder reproduces the HTML byte-for-byte, so `deck.json` plus the assets ARE the deck.

A universe that makes decks repeatedly should declare a FORM (`create-form`) recording its own
register: which kinds it uses, what its covers look like, how much evidence the method rests
on. The form carries the taste; this skill carries the mechanism.
