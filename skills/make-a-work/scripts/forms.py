#!/usr/bin/env python3
"""Discover and resolve the FORMS a universe declares.

A form is a FOLDER, not a skill. That is the whole point: adding a new kind of work
must not require writing new code or a new skill, or the framework has just moved the
hand-rolling up one level.

A form lives at `<universe>/forms/<id>/` and is recognised by:

    FORM.md      REQUIRED. What the form is, its goldens, its status.
    PROMPT.md    REQUIRED. The method. This IS the form's composer.
    evals/       optional. Scripts the method calls at the points it names.

The two required files are required for a reason. A folder with no PROMPT.md is not a
form, it is a note about one: nothing can be made from it, and offering it in a menu
would send an agent looking for a method that does not exist.

    forms.py list <universe>            every form, with status and what it is missing
    forms.py list <universe> --json     the same survey, machine-readable ([] when none)
    forms.py resolve <universe> <id>    paths + the status warning, or a refusal

Legacy note: `forms/<id>/form.json` in the SPEC 4.8 slot encoding was RETIRED in v0.17.
A folder holding only that is reported as retired rather than offered as usable.
"""
import argparse, json, pathlib, re, sys


def _universe(p):
    root = pathlib.Path(p).expanduser().resolve()
    if not (root / "universe.json").exists():
        sys.exit(f"forms.py: not a universe (no universe.json): {root}")
    return root


def _status_line(form_md):
    """The form's own status warning, if it declares one.

    Surfacing this is load-bearing. A form derived from one work is a hypothesis, and an
    agent that reads only the method will follow it with unearned confidence.
    """
    txt = form_md.read_text(errors="replace")
    m = re.search(r"^>\s*#+\s*STATUS[:\s].*$", txt, re.M | re.I)
    if m:
        return m.group(0).lstrip("> #").strip()
    m = re.search(r"^#+\s*STATUS[:\s].*$", txt, re.M | re.I)
    return m.group(0).lstrip("# ").strip() if m else None


def survey(root):
    out = []
    fdir = root / "forms"
    if not fdir.is_dir():
        return out
    for d in sorted(p for p in fdir.iterdir() if p.is_dir()):
        form_md, prompt_md = d / "FORM.md", d / "PROMPT.md"
        missing = [n for n, p in (("FORM.md", form_md), ("PROMPT.md", prompt_md))
                   if not p.exists()]
        rec = {
            "id": d.name,
            "dir": str(d),
            "usable": not missing,
            "missing": missing,
            "evals": sorted(x.name for x in (d / "evals").glob("*.py")) if (d / "evals").is_dir() else [],
            "retiredEncodingOnly": bool(missing) and (d / "form.json").exists(),
            "status": _status_line(form_md) if form_md.exists() else None,
        }
        out.append(rec)
    return out


def cmd_list(a):
    forms = survey(_universe(a.universe))
    if getattr(a, "json", False):
        # A universe with no forms emits [], never the prose below. A brand-new
        # cartridge legitimately declares zero forms, and that is the FIRST thing a
        # GUI consumer sees; making it parse prose to learn "none yet" would push it
        # straight back into regex-scraping this tool's console output.
        print(json.dumps(forms, indent=2))
        return 0
    if not forms:
        print("no forms declared. A form is a folder at forms/<id>/ holding FORM.md + PROMPT.md.")
        return 0
    for f in forms:
        if f["usable"]:
            print(f"  {f['id']:<24} usable" + (f"   evals: {', '.join(f['evals'])}" if f["evals"] else ""))
            if f["status"]:
                print(f"  {'':<24} {f['status'][:96]}")
        elif f["retiredEncodingOnly"]:
            print(f"  {f['id']:<24} RETIRED ENCODING (form.json only, SPEC 4.8 slot model, v0.17)")
        else:
            print(f"  {f['id']:<24} NOT USABLE — missing {', '.join(f['missing'])}")
    return 0


def cmd_resolve(a):
    root = _universe(a.universe)
    hit = next((f for f in survey(root) if f["id"] == a.form), None)
    if hit is None:
        have = [f["id"] for f in survey(root)] or ["(none)"]
        sys.exit(f"forms.py: no form {a.form!r} in {root}. Declared: {', '.join(have)}")
    if not hit["usable"]:
        why = ("it holds only the RETIRED form.json slot encoding"
               if hit["retiredEncodingOnly"] else f"it is missing {', '.join(hit['missing'])}")
        sys.exit(f"forms.py: form {a.form!r} is not usable: {why}.\n"
                 f"  A form needs FORM.md (what it is) and PROMPT.md (the method). Refusing to\n"
                 f"  resolve one that cannot be made from, rather than sending you to look for a\n"
                 f"  method that does not exist.")
    print(json.dumps(hit, indent=2))
    return 0


def main():
    ap = argparse.ArgumentParser(description="Discover the forms a universe declares.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list"); p.add_argument("universe")
    p.add_argument("--json", action="store_true",
                   help="machine-readable: the full survey records, [] when none are declared")
    p.set_defaults(fn=cmd_list)
    p = sub.add_parser("resolve"); p.add_argument("universe"); p.add_argument("form")
    p.set_defaults(fn=cmd_resolve)
    a = ap.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
