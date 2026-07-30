# Welcome

You talk. It builds. That is the whole interface.

Agentic Brand Universe runs inside your AI harness. You describe what you want in
plain language and the harness operates the machinery: it makes the images, holds the
look steady across everything, remembers what your characters and places look like,
and refuses to render something it does not have the references for.

**You are not expected to learn any commands.** There are none in this file on
purpose. An earlier version of this page was a list of things to type, which is the
wrong shape: in this model you state intent and the console does the operating.

## Starting from scratch

Open your harness in this folder and say:

> **set me up**

It installs everything, checks what is missing, and tells you in plain sentences what
is ready and what is blocked. Two things it cannot do for you, because both are
credentials rather than chores: installing the harness itself, and holding an image
API key. It will tell you if either is missing.

Then say what you are making. If you already have images you like, say so, because
that is the fastest path to a first result.

## Once you are running

Say:

> **abu**

That is the front door. Hand it nothing and it tells you where your universe stands,
what the single highest-leverage next thing is, and a ten-minute version if you are
just browsing. It scores your universe out of 100 and remembers the last score, so it
can tell you what moved since Tuesday rather than only where you are today.

Everything else is a wish said out loud:

> *make more images that look like these*
> *this character keeps changing between pictures*
> *the room is a different shape on every page*
> *make a zine cover*
> *is this any good yet*
> *what should I do next*
> *I'm bored*

You never need to know which verb handles which wish. That is the harness's job.

## The one idea worth knowing up front

Most AI image work drifts. You get something great, then the next one is subtly
different, and by the tenth you cannot get back to the first. This exists to stop
that.

The look and the characters live in **locked reference images**, not in words you
retype. When something must appear the same everywhere, the framework refuses to draw
it until it actually has the reference on disk, because a picture of the wrong
character is far more expensive than a hard stop. It looks fine, so it passes review,
and you find out ten pages later.

You do not need this on day one. If you are making a zine and only the *style* has to
stay consistent, a style pack plus a gate is enough, and the harness will set that up
for you when you ask.

## Where the details live

You should not need these, but they are here.

- [`docs/REFERENCE.md`](./docs/REFERENCE.md) every skill, verb, form and provider,
  generated from the code so it cannot go stale.
- [`docs/GLOSSARY.md`](./docs/GLOSSARY.md) the vocabulary, each term defined by what
  it refuses.
- [`SPEC.md`](./SPEC.md) the contract.
- [`docs/ARCHITECTURE.md`](./docs/ARCHITECTURE.md) how the six layers fit.
