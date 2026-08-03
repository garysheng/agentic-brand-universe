#!/usr/bin/env python3
"""scaffold.py: stamp the skeleton of a NEW form at <universe>/forms/<id>/.

A form is a FOLDER (FORM.md + PROMPT.md + optional evals/), discovered by
make-a-work/scripts/forms.py. This scaffolder owns three refusals and one stamp:

  1. It validates the id (lowercase slug, the same grammar every form so far uses).
  2. It REFUSES on zero evidence. A form is written FROM works actually made, and a
     form with zero works is the failure this framework spent a day removing: the
     retired universal composer had 896 lines, 91 tests and ZERO works (SPEC 4.8,
     retired v0.17). If the work does not exist yet, make it first, then extract.
  3. It refuses to clobber an existing form folder, including one holding only the
     retired form.json encoding, which is kept as a record rather than overwritten.
  4. It stamps FORM.md + PROMPT.md skeletons with the evidence base already counted
     and listed. Below THREE works the STATUS section carries the hypothesis warning
     (the fashion-look / event-flyer precedent: one work is legal, and it is a
     hypothesis); at three or more it states the records-win rule instead (the
     living-diorama precedent: the works' own records remain the ground truth).

It also checks each evidence work for a work.json declaring this form, and prints
backfill guidance for any that lack one. It never writes work.json itself: the
retrofit note is an authored record about a specific work, not boilerplate.

Usage:
  python3 scaffold.py <universe> <form-id> \
    --work <path-to-finished-work-dir> [--work ...] \
    [--name "<Display Name>"] [--what "<one line>"] [--evals]
"""
import argparse, datetime, json, pathlib, re, sys

ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$")

COUNT_WORDS = {1: "ONE", 2: "TWO", 3: "THREE", 4: "FOUR", 5: "FIVE", 6: "SIX"}

HYPOTHESIS = """\
Treat it as a hypothesis, not a standard: below three works there is not enough
evidence to know which rules are true of the FORM and which are only true of those
works. The next work is the experiment, and whatever it has to fight or work around
is a defect in this file, not in the work: fix the form rather than the work."""

RECORDS_WIN = """\
The works' own READMEs, recipes and raw/candidate folders remain the ground truth
this file was distilled from; where this file and a shipped work's records disagree,
the records win. If a new work has to fight a step here, that is a defect in this
file: fix the form rather than the work."""


def fail(msg):
    sys.exit(f"create-form scaffold: {msg}")


def main():
    ap = argparse.ArgumentParser(description="Scaffold a new form from existing works.")
    ap.add_argument("universe")
    ap.add_argument("form_id")
    ap.add_argument("--work", action="append", default=[],
                    help="path to a FINISHED work this form is extracted from (repeatable)")
    ap.add_argument("--name", help="display name (default: derived from the id)")
    ap.add_argument("--what", help="one line: what the form is")
    ap.add_argument("--evals", action="store_true", help="also create evals/")
    a = ap.parse_args()

    root = pathlib.Path(a.universe).expanduser().resolve()
    if not (root / "universe.json").exists():
        fail(f"not a universe (no universe.json): {root}")

    if not ID_RE.match(a.form_id):
        fail(f"bad form id {a.form_id!r}: a form id is a lowercase slug "
             "([a-z0-9] and hyphens), like fashion-look or living-diorama")

    # The evidence gate. This is the heart of the skill and it fails closed.
    if not a.work:
        fail("REFUSING to scaffold a form with ZERO works.\n"
             "  A form is written FROM works actually made. The retired universal composer\n"
             "  is the cautionary tale: 896 lines, 91 tests, zero works, authored from one\n"
             "  imagined example (SPEC 4.8, retired v0.17). Make the first work by hand\n"
             "  through the ordinary tools, then come back with --work <path>.")

    works = []
    for w in a.work:
        p = pathlib.Path(w).expanduser()
        if not p.is_absolute():
            p = (root / p)
        p = p.resolve()
        if not p.is_dir():
            fail(f"evidence work is not a directory on disk: {p}\n"
                 "  The gate is that the work ACTUALLY EXISTS. A path that resolves to\n"
                 "  nothing is speculation with a filename.")
        works.append(p)

    fdir = root / "forms" / a.form_id
    if fdir.exists() and any(fdir.iterdir()):
        has = ", ".join(sorted(x.name for x in fdir.iterdir()))
        fail(f"forms/{a.form_id}/ already exists and is not empty ({has}).\n"
             "  Refusing to clobber. If it is a live form, edit it in place; if it holds\n"
             "  only the retired form.json encoding, it is kept as a record: pick another\n"
             "  id, or clear the folder deliberately yourself.")

    name = a.name or a.form_id.replace("-", " ").title()
    what = a.what or "TODO: one paragraph a stranger could act on."
    today = datetime.date.today().isoformat()
    n = len(works)
    count_word = COUNT_WORDS.get(n, str(n))

    def rel(p):
        try:
            return str(p.relative_to(root))
        except ValueError:
            return str(p)

    work_lines = "\n".join(f"- `{rel(p)}` (TODO: what this work established)" for p in works)
    plural = "work" if n == 1 else "works"
    status_tail = HYPOTHESIS if n < 3 else RECORDS_WIN

    form_md = f"""# {name}

{what}

## STATUS: read this before trusting the method

**This form rests on {count_word} finished {plural}**, scaffolded {today} by
`create-form`:

{work_lines}

{status_tail}

## Why this form exists

TODO: what recurring need this form answers, and why the existing primitives
(motif, prop, style pack, lookbook, another form) are the wrong instrument for it.

## The family laws (gate criteria, not suggestions)

TODO: the testable claims a candidate is judged against, each earned by a real work.
A candidate that violates one is a DEFECT regardless of how good it looks.

## Where the work goes

TODO. The `make-a-work` default is `works/<id>/`. Override it only with a stated
reason (fashion-look files entity-scoped; living-diorama files register-scoped).

## Goldens

{work_lines}

## What a good one looks like

TODO.

## Known debts (named, not hidden)

TODO: anything the method still hand-rolls. Each one is flagged to `evolve-abu`,
never silently worked around.
"""

    prompt_md = f"""# Method: {name}

Follow this exactly. Every step should exist because a work needed it, not because
it seemed prudent. The family laws in FORM.md are gate criteria at every step.
`<abu>` below means the agentic-brand-universe repo root.

## 1. Words before art

TODO: what is decided and WRITTEN DOWN before any render, so a render can be judged
against it.

## 2. Resolve where the work goes

TODO (see FORM.md). Create the work folder and its candidates/ (or raw/) up front.

## 3. Render through the provider adapter

Every generated image goes through `<abu>/skills/on-brand-image/scripts/generate.py`,
which writes the `.recipe.json` on every render. There is no other legal render path.

TODO: the per-asset briefs, references, and flags this form needs.

## 4. Verify before you look, judge before you re-roll

```bash
python3 <abu>/skills/render-readback/scripts/verify_render.py <out>.png
python3 <abu>/skills/render-readback/scripts/contact_sheet.py --out _contact.png --cols 3 *.png
python3 <abu>/skills/render-readback/scripts/crop_zoom.py ...   # BEFORE calling any defect
```

TODO: what this form specifically checks. A miss is a re-roll FROM SCRATCH (never
stack an edit pass) or an accepted deviation recorded in the work's records.
Rejected candidates are never deleted.

## 5. Measure (only if the method measures anything)

TODO: name the eval script in `evals/` here, at the step that uses it. An eval must
be VERIFIED against the goldens it claims to reproduce before the form lands: run it
on a golden and confirm it reproduces the recorded measurements.

## 6. The requester blesses. You do not.

Show every candidate. Only the requester moves a work to blessed. Record who
blessed it, when, and in their own words.
"""

    fdir.mkdir(parents=True, exist_ok=True)
    (fdir / "FORM.md").write_text(form_md)
    (fdir / "PROMPT.md").write_text(prompt_md)
    if a.evals:
        (fdir / "evals").mkdir(exist_ok=True)

    # Backfill check: a work the form was extracted from should DECLARE the form.
    undeclared = []
    for p in works:
        wj = p / "work.json"
        declared = False
        if wj.exists():
            try:
                declared = json.loads(wj.read_text()).get("form") == a.form_id
            except (json.JSONDecodeError, OSError):
                declared = False
        if not declared:
            undeclared.append(p)

    print(f"[create-form] OK  {a.form_id}  ({count_word} evidence {plural})  -> {fdir}")
    if n < 3:
        print(f"  STATUS stamped as a HYPOTHESIS ({n} < 3 works). The next works are the experiment.")
    if undeclared:
        print(f"  BACKFILL NEEDED: {len(undeclared)} evidence work(s) do not declare this form:")
        for p in undeclared:
            print(f"    {rel(p)}/work.json")
        print("  Each gains a work.json with \"form\": \"" + a.form_id + "\" and a formNote"
              " stating the retrofit\n  (added the day the form was extracted; the work"
              " predates the form and is one of its\n  goldens). NEVER rewrite the work's"
              " historical README, recipes, or attestations:\n  they are what the form was"
              " distilled from.")
    print("  Next: distill FORM.md and PROMPT.md from the works' records (see the"
          " create-form SKILL),\n  then prove discovery:  python3 "
          "<abu>/skills/make-a-work/scripts/forms.py resolve "
          f"{root} {a.form_id}")


if __name__ == "__main__":
    main()
