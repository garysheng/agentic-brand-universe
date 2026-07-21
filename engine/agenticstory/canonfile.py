"""CANON.md as a DERIVED artifact.

The properties registry and the crossover log were hand-appended markdown tables
in a single file that every concurrent render wrote to. That produced two failure
modes that git could not catch:

  1. SILENT ID COLLISION. Crossover numbers were assigned "read the last, add
     one". Two runs both read N and both wrote N+1. The rows land on different
     lines, so git merges them cleanly and canon ends up with duplicate ids and
     no conflict ever raised. (Ten numbers were already duplicated when this
     module was written.)
  2. STRUCTURAL DRIFT. Repeated appends left stray separator rows mid-table and
     a header with no separator under it.

The fix is to make the shared file a projection of per-record files. Two runs
adding records touch disjoint paths, so they cannot collide, and display numbers
are assigned ONCE at build time instead of guessed independently by each run.

Records:
  canon/properties/<id>.json   {id, property, form, status, home, cast, order}
  canon/crossovers/<id>.json   {id, n, summary, properties, status}

`n` is a DISPLAY ORDINAL, not identity. It is preserved for records that already
have one (existing prose cites "crossover #88"), and assigned + persisted by
build for records that do not. That single assignment point is what removes the
race: a run authors a record with no `n` and never has to guess.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

PROPS_BEGIN = "<!-- BEGIN GENERATED: properties -->"
PROPS_END = "<!-- END GENERATED: properties -->"
XOVER_BEGIN = "<!-- BEGIN GENERATED: crossovers -->"
XOVER_END = "<!-- END GENERATED: crossovers -->"

PROPS_HEADER = ["| Property | Form | Status | Home | Cast |", "|---|---|---|---|---|"]
XOVER_HEADER = ["| # | Crossover | Properties | Status |", "|---|---|---|---|"]

_SEP = re.compile(r"^\|(\s*-+\s*\|)+\s*$")


def slugify(text: str, fallback: str = "record") -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    s = re.sub(r"-{2,}", "-", s)
    return (s or fallback)[:70].strip("-")


def _uniq(base: str, taken: set[str]) -> str:
    if base not in taken:
        taken.add(base)
        return base
    i = 2
    while f"{base}-{i}" in taken:
        i += 1
    out = f"{base}-{i}"
    taken.add(out)
    return out


# ---------------------------------------------------------------- parsing

def parse_property_rows(text: str) -> list[dict]:
    """Rows of the 5-column properties registry, in document order."""
    out = []
    for line in text.splitlines():
        if _SEP.match(line):
            continue
        m = re.match(r"^\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
        if not m:
            continue
        prop, form, status, home, cast = m.groups()
        if prop in ("Property", "#"):
            continue
        if not form or not status:
            continue
        out.append({"property": prop, "form": form, "status": status, "home": home, "cast": cast})
    return out


def parse_crossover_rows(text: str) -> list[dict]:
    """Rows of the 4-column crossover log, in document order."""
    out = []
    for line in text.splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*$", line)
        if not m:
            continue
        out.append({
            "n": int(m.group(1)),
            "summary": m.group(2),
            "properties": m.group(3),
            "status": m.group(4),
        })
    return out


# ---------------------------------------------------------------- store

def props_dir(uroot: Path) -> Path:
    return uroot / "canon" / "properties"


def xover_dir(uroot: Path) -> Path:
    return uroot / "canon" / "crossovers"


def load_properties(uroot: Path) -> list[dict]:
    d = props_dir(uroot)
    recs = [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.is_dir() else []
    # newest first: higher order sorts earlier
    recs.sort(key=lambda r: (-int(r.get("order", 0)), r.get("id", "")))
    return recs


def load_crossovers(uroot: Path) -> list[dict]:
    d = xover_dir(uroot)
    recs = [json.loads(p.read_text()) for p in sorted(d.glob("*.json"))] if d.is_dir() else []
    # numbered first in numeric order, then unnumbered (they get numbers at build)
    recs.sort(key=lambda r: (r.get("n") is None, r.get("n") or 0, r.get("id", "")))
    return recs


def assign_numbers(recs: list[dict]) -> list[dict]:
    """Give every record a stable display ordinal. Existing `n` is preserved;
    missing ones are appended after the current max, deterministically by id.
    This is the ONLY place a number is assigned, which is what kills the race."""
    used = {r["n"] for r in recs if r.get("n") is not None}
    nxt = (max(used) + 1) if used else 1
    for r in sorted([r for r in recs if r.get("n") is None], key=lambda r: r.get("id", "")):
        while nxt in used:
            nxt += 1
        r["n"] = nxt
        used.add(nxt)
        nxt += 1
    return recs


def duplicate_numbers(recs: list[dict]) -> list[int]:
    seen, dupes = set(), set()
    for r in recs:
        n = r.get("n")
        if n is None:
            continue
        (dupes if n in seen else seen).add(n)
    return sorted(dupes)


# ---------------------------------------------------------------- rendering

def render_properties(recs: list[dict]) -> list[str]:
    rows = [f"| {r['property']} | {r['form']} | {r['status']} | {r['home']} | {r['cast']} |" for r in recs]
    return PROPS_HEADER + rows


def render_crossovers(recs: list[dict]) -> list[str]:
    rows = [f"| {r['n']} | {r['summary']} | {r['properties']} | {r['status']} |" for r in recs]
    return XOVER_HEADER + rows


def _replace_block(text: str, begin: str, end: str, body: list[str]) -> str:
    block = "\n".join([begin, *body, end])
    if begin in text and end in text:
        pre, rest = text.split(begin, 1)
        _, post = rest.split(end, 1)
        return pre + block + post
    raise ValueError(f"markers not found: {begin}")


def build(uroot: Path, persist_numbers: bool = True) -> str:
    """Regenerate CANON.md's two generated blocks from the record store."""
    props = load_properties(uroot)
    xovers = assign_numbers(load_crossovers(uroot))
    if persist_numbers:
        for r in xovers:
            p = xover_dir(uroot) / f"{r['id']}.json"
            if p.exists():
                cur = json.loads(p.read_text())
                if cur.get("n") != r["n"]:
                    cur["n"] = r["n"]
                    p.write_text(json.dumps(cur, indent=2) + "\n")
    canon = uroot / "CANON.md"
    text = canon.read_text()
    text = _replace_block(text, PROPS_BEGIN, PROPS_END, render_properties(props))
    text = _replace_block(text, XOVER_BEGIN, XOVER_END, render_crossovers(xovers))
    return text


def check(uroot: Path) -> list[str]:
    """Problems that make the projection untrustworthy."""
    problems = []
    xovers = load_crossovers(uroot)
    for n in duplicate_numbers(xovers):
        ids = [r["id"] for r in xovers if r.get("n") == n]
        problems.append(f"duplicate crossover number {n}: {', '.join(ids)}")
    canon = uroot / "CANON.md"
    if canon.exists() and PROPS_BEGIN in canon.read_text():
        if canon.read_text() != build(uroot, persist_numbers=False):
            problems.append("CANON.md is stale: run `agenticstory build-canon <universe>`")
    return problems


def adopt(uroot: Path) -> list[str]:
    """Create records for rows sitting in CANON.md with no backing record.

    This is the rescue path for a concurrent run that hand-appended a row the
    old way: its work is ingested instead of being silently overwritten by the
    next build."""
    canon = (uroot / "CANON.md").read_text()
    created = []

    def block(text, begin, end):
        if begin not in text:
            return ""
        return text.split(begin, 1)[1].split(end, 1)[0]

    pd, xd = props_dir(uroot), xover_dir(uroot)
    pd.mkdir(parents=True, exist_ok=True)
    xd.mkdir(parents=True, exist_ok=True)

    have_props = {json.loads(p.read_text())["property"] for p in pd.glob("*.json")}
    taken = {p.stem for p in pd.glob("*.json")}
    rows = parse_property_rows(block(canon, PROPS_BEGIN, PROPS_END) or canon)
    order = max([int(json.loads(p.read_text()).get("order", 0)) for p in pd.glob("*.json")] or [0])
    for row in reversed(rows):  # document order is newest-first
        if row["property"] in have_props:
            continue
        order += 1
        rid = _uniq(slugify(row["property"]), taken)
        (pd / f"{rid}.json").write_text(json.dumps({"id": rid, "order": order, **row}, indent=2) + "\n")
        created.append(f"properties/{rid}.json")

    have_x = {json.loads(p.read_text())["summary"] for p in xd.glob("*.json")}
    takenx = {p.stem for p in xd.glob("*.json")}
    for row in parse_crossover_rows(block(canon, XOVER_BEGIN, XOVER_END) or canon):
        if row["summary"] in have_x:
            continue
        rid = _uniq(slugify(row["properties"]) or f"crossover-{row['n']}", takenx)
        (xd / f"{rid}.json").write_text(json.dumps({"id": rid, **row}, indent=2) + "\n")
        created.append(f"crossovers/{rid}.json")
    return created
