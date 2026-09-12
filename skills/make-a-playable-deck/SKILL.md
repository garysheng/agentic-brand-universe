---
name: make-a-playable-deck
description: Build a mobile-friendly PLAYABLE slide deck from slides declared as data, for sending someone an argument they can sit with on their phone. Use when the operator says deck, slides, present this, walk someone through it, send it to X for feedback, or asks for an artifact someone should reflect on rather than read as a document. Emits ONE self-contained HTML file with fit-to-viewport scaling so nothing scrolls, swipe, deep-linked slides, a draggable scrub bar across the whole argument, and a palette read from the universe's own tokens. NOT for a printed PDF and NOT for a document; a deck is a sequence someone moves through.
---

# Make a playable deck

```bash
python3 skills/make-a-playable-deck/scripts/build_deck.py <deck.json> \
    --out <dir> [--palette <universe>/canon/craft/palette.json] [--assets <dir>]
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

Nine, and they are a hypothesis rather than a vocabulary. Unknown keys are **refused by name**,
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

`**bold**` and `*italic*` work in any text field. Nothing else does, on purpose: a slide is a
sentence or two, and a markdown parser would let a slide carry headings and tables that the
kinds exist to decide.

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

## Refusals

- A deck with no slides.
- An unknown `kind`, naming the ones that exist.
- An unknown key on a known kind, naming the key and what is allowed there.
- A kind missing its payload (`pair` with no `images`, `table` with no `columns`).

## Where the work goes

The deck folder is a WORK, so it belongs with the universe's other works rather than in a
scratch directory, and its slides file is the authored artifact worth keeping: re-running the
builder reproduces the HTML byte-for-byte, so `deck.json` plus the assets ARE the deck.

A universe that makes decks repeatedly should declare a FORM (`create-form`) recording its own
register: which kinds it uses, what its covers look like, how much evidence the method rests
on. The form carries the taste; this skill carries the mechanism.
