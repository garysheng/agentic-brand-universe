"""The kit (SPEC §13.1, v0.60): a universe's catalog of brand PIECES and NO-GOS.

A piece is a reusable part of the brand with an exact recipe (the selection ring, the six-stripe
thread, the primary button). A no-go is a thing the brand refuses, with the piece to use instead.
Both carry who decided them, when, and in what words, because a refusal with no provenance is an
opinion and gets re-litigated by the next agent that finds it inconvenient.

Before v0.60 a universe had nowhere typed to put either. Pieces lived as sentences inside
register-rule records (or only in site code), and no-gos were scattered across rule prose,
icon notes and project STATE files, so nothing could READ them: no gate refused a surface that
used a refused shape, and a ruling stayed true only for as long as somebody remembered it.

What this module enforces, in `validate` (every defect at once, like `identity.surfaces`):

  - every piece has an id, a name, what it is FOR, and either a `recipe` or a `definedAt`
    pointer into existing canon (a pointer, so a piece already defined is never duplicated);
  - every no-go has an id, what it `refuses`, `why`, and `instead` (a piece id in a kit, or
    null with an `insteadNote` saying why there is no replacement);
  - every item carries `decided` {by, on, verbatim} and, where it was HARVESTED from canon, a
    `source` whose `quote` must still be present at the pointer it cites, so a no-go cannot
    outlive the canon line it was lifted from without the gate saying so;
  - a `supersedes` entry names a live canon line and the words it used to `said`; those words
    must be GONE from that line, because a ruling recorded here while canon still says the old
    thing is two sources of truth disagreeing;
  - a recipe naming tokens is checked against the kit's `tokensFrom` map;
  - every `detect` pattern compiles, because the gate skips what it cannot read.

And `scan`: run every no-go's `detect` patterns over a surface's SOURCE files, which is how a
no-go becomes a refusal rather than a remembered preference (`abu check-kit`).

Earned 2026-10-06 on continental-works: Gary rejected the six stripes run down one edge of a
selected card ("I really don't like it when you ... use the stripes like the way you did it for
Diane") and asked that the replacement "be part of the ABU, as like, I think the ABU should be
cataloging all these different Lego pieces of the brand and no-goes".
"""
from __future__ import annotations

import fnmatch
import json
import os
import re
from pathlib import Path
from typing import Any, Iterable

KIND = "kit"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
# A source in a SIBLING repo is written "<repo>:<path>" (optionally "@<commit>"). It is recorded,
# not checked: the sibling may be on any branch, and a gate that fails on someone else's checkout
# is a gate people learn to skip.
SIBLING = re.compile(r"^[A-Za-z0-9_.-]+:(?!//)")
SKIP_DIRS = {"node_modules", ".git", ".next", "dist", "build", "out", ".docusaurus",
             ".turbo", ".vercel", ".cache", "__pycache__", "coverage"}
DEFAULT_FILES = ["*.css", "*.scss", "*.sass", "*.less", "*.html", "*.htm", "*.js", "*.mjs",
                 "*.cjs", "*.ts", "*.tsx", "*.jsx", "*.vue", "*.svelte", "*.astro"]
MAX_BYTES = 2_000_000


def _ws(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _text(v: Any) -> str:
    """Everything a pointer resolves to, flattened to one searchable string."""
    if isinstance(v, str):
        return v
    if isinstance(v, (list, tuple)):
        return " ".join(_text(x) for x in v)
    if isinstance(v, dict):
        return " ".join(_text(x) for x in v.values())
    return "" if v is None else str(v)


def resolve(root: Path, pointer: str) -> tuple[bool, Any, str]:
    """`<file>#<dot.path>` inside the universe -> (found, value, why-not).

    A numeric segment indexes a list (`rules.4`). No `#` means the whole file. A `.json` file
    is parsed; any other file resolves to its text and takes no path."""
    if not isinstance(pointer, str) or not pointer:
        return False, None, f"pointer must be '<file>#<path>', got {pointer!r}"
    file, _, path = pointer.partition("#")
    f = Path(root) / file
    if not f.is_file():
        return False, None, f"{file} does not exist in the universe"
    if f.suffix != ".json":
        if path:
            return False, None, f"{file} is not JSON, so it takes no '#{path}'"
        return True, f.read_text(errors="replace"), ""
    try:
        obj: Any = json.loads(f.read_text())
    except ValueError:
        return False, None, f"{file} is not valid JSON"
    for seg in [s for s in path.split(".") if s]:
        if isinstance(obj, list) and seg.isdigit() and int(seg) < len(obj):
            obj = obj[int(seg)]
        elif isinstance(obj, dict) and seg in obj:
            obj = obj[seg]
        else:
            return False, None, f"{pointer} does not resolve (no '{seg}')"
    return True, obj, ""


def _as_list(v) -> list:
    if v is None:
        return []
    return v if isinstance(v, list) else [v]


def _check_decided(where: str, item: dict) -> list[str]:
    d = item.get("decided")
    if not isinstance(d, dict):
        return [f"{where}: 'decided' is missing (who ruled, on what date, in what words)"]
    out = []
    if not isinstance(d.get("by"), str) or not d.get("by").strip():
        out.append(f"{where}: decided.by is missing")
    if not isinstance(d.get("on"), str) or not DATE.match(d.get("on", "")):
        out.append(f"{where}: decided.on must be a YYYY-MM-DD date, got {d.get('on')!r}")
    verb = d.get("verbatim")
    has_verbatim = (isinstance(verb, str) and verb.strip()) or (
        isinstance(verb, list) and verb and all(isinstance(x, str) and x.strip() for x in verb))
    if not has_verbatim and not item.get("source"):
        out.append(f"{where}: decided.verbatim is missing and there is no 'source' to cite instead; "
                   "a ruling with neither is an opinion")
    return out


def _check_sources(root: Path, where: str, item: dict) -> list[str]:
    out = []
    for s in _as_list(item.get("source")):
        if not isinstance(s, dict) or not isinstance(s.get("at"), str):
            out.append(f"{where}: each source is {{at, quote}}, got {s!r}")
            continue
        at, quote = s["at"], s.get("quote")
        if not isinstance(quote, str) or not quote.strip():
            out.append(f"{where}: source {at} has no quote; quote the line the no-go was lifted from")
            continue
        if SIBLING.match(at) and not (Path(root) / at.split("#")[0]).exists():
            continue  # a sibling repo's file: recorded, not checked
        ok, val, why = resolve(root, at)
        if not ok:
            out.append(f"{where}: source {why}")
        elif _ws(quote) not in _ws(_text(val)):
            out.append(f"{where}: source {at} no longer says {quote!r}; the canon line moved or "
                       "changed, so re-cite it or retire this item")
    return out


def _check_supersedes(root: Path, where: str, item: dict) -> list[str]:
    out = []
    for s in _as_list(item.get("supersedes")):
        if not isinstance(s, dict) or not isinstance(s.get("at"), str) or not isinstance(s.get("said"), str):
            out.append(f"{where}: each supersedes entry is {{at, said}}, got {s!r}")
            continue
        ok, val, why = resolve(root, s["at"])
        if not ok:
            out.append(f"{where}: supersedes {why}")
        elif _ws(s["said"]) in _ws(_text(val)):
            out.append(f"{where}: supersedes {s['at']}, which STILL says {s['said']!r}; update the "
                       "live line (keep the old words in its own supersession note)")
    return out


def _check_detect(where: str, item: dict) -> list[str]:
    out = []
    for d in _as_list(item.get("detect")):
        if not isinstance(d, dict) or not isinstance(d.get("pattern"), str):
            out.append(f"{where}: each detect entry is {{pattern, files?, note?}}, got {d!r}")
            continue
        try:
            re.compile(d["pattern"], re.I)
        except re.error as e:
            out.append(f"{where}: detect pattern does not compile ({e}): {d['pattern']!r}")
        files = d.get("files")
        if files is not None and not (isinstance(files, list) and all(isinstance(x, str) for x in files)):
            out.append(f"{where}: detect.files must be a list of globs")
    return out


def kits(craft: dict) -> list[dict]:
    """The raw kit records among a store's craft canon, in id order."""
    return [c.raw for c in sorted(craft.values(), key=lambda c: c.id) if c.kind == KIND]


def validate_kits(root: Path, craft: dict) -> list[str]:
    """Every defect across every kit record; empty when there are none (a kit is optional)."""
    root = Path(root)
    records = kits(craft)
    out: list[str] = []
    piece_ids: dict[str, str] = {}
    seen: dict[str, str] = {}
    for k in records:
        for p in k.get("pieces") or []:
            if isinstance(p, dict) and isinstance(p.get("id"), str):
                piece_ids[p["id"]] = k.get("id", "?")
    for k in records:
        kid = k.get("id", "?")
        pieces, nogos = k.get("pieces"), k.get("noGos")
        if not isinstance(pieces, list) or not isinstance(nogos, list):
            out.append(f"kit {kid}: needs 'pieces' and 'noGos' lists (either may be empty)")
            continue
        token_map = None
        if k.get("tokensFrom") is not None:
            ok, val, why = resolve(root, k["tokensFrom"])
            if not ok or not isinstance(val, dict):
                out.append(f"kit {kid}: tokensFrom {why or 'does not name a map of tokens'}")
            else:
                token_map = val
        for kind, items in (("piece", pieces), ("no-go", nogos)):
            for i, it in enumerate(items):
                if not isinstance(it, dict):
                    out.append(f"kit {kid}: {kind} #{i} must be an object")
                    continue
                iid = it.get("id")
                where = f"kit {kid} {kind} '{iid}'" if iid else f"kit {kid} {kind} #{i}"
                if not isinstance(iid, str) or not re.match(r"^[a-z0-9][a-z0-9-]*$", iid):
                    out.append(f"{where}: id must be kebab-case")
                elif iid in seen:
                    out.append(f"{where}: id is already used by {seen[iid]}")
                else:
                    seen[iid] = f"{kind} in kit {kid}"
                out += _check_decided(where, it)
                out += _check_sources(root, where, it)
                out += _check_supersedes(root, where, it)
                if kind == "piece":
                    for f in ("name", "for"):
                        if not isinstance(it.get(f), str) or not it[f].strip():
                            out.append(f"{where}: '{f}' is missing")
                    if not it.get("recipe") and not it.get("definedAt"):
                        out.append(f"{where}: needs a 'recipe' or a 'definedAt' pointer to the canon "
                                   "that already defines it")
                    for ptr in _as_list(it.get("definedAt")):
                        ok, _, why = resolve(root, ptr)
                        if not ok:
                            out.append(f"{where}: definedAt {why}")
                    rec = it.get("recipe")
                    if rec is not None and not isinstance(rec, dict):
                        out.append(f"{where}: recipe must be an object")
                    elif isinstance(rec, dict) and rec.get("tokens"):
                        if token_map is None:
                            out.append(f"{where}: recipe names tokens but the kit has no 'tokensFrom'")
                        else:
                            for t in _as_list(rec["tokens"]):
                                if t not in token_map:
                                    out.append(f"{where}: recipe token '{t}' is not in {k['tokensFrom']}")
                else:
                    for f in ("refuses", "why"):
                        if not isinstance(it.get(f), str) or not it[f].strip():
                            out.append(f"{where}: '{f}' is missing")
                    if "instead" not in it:
                        out.append(f"{where}: 'instead' is missing (a piece id, or null with an insteadNote)")
                    elif it["instead"] is None:
                        if not isinstance(it.get("insteadNote"), str) or not it["insteadNote"].strip():
                            out.append(f"{where}: instead is null, so 'insteadNote' must say why there is no piece")
                    elif it["instead"] not in piece_ids:
                        out.append(f"{where}: instead names '{it['instead']}', which is not a piece in any kit")
                    out += _check_detect(where, it)
    return out


def pieces_by_id(craft: dict) -> dict[str, dict]:
    return {p["id"]: p for k in kits(craft) for p in (k.get("pieces") or [])
            if isinstance(p, dict) and isinstance(p.get("id"), str)}


def nogos(craft: dict) -> list[dict]:
    return [n for k in kits(craft) for n in (k.get("noGos") or []) if isinstance(n, dict)]


def _files(paths: Iterable[str]) -> Iterable[Path]:
    for p in paths:
        p = Path(p)
        if p.is_file():
            yield p
        elif p.is_dir():
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
                for fn in sorted(filenames):
                    yield Path(dirpath) / fn


def scan(craft: dict, paths: Iterable[str]) -> list[dict]:
    """Every place in `paths` (files or directories) that a no-go's `detect` pattern matches.

    Each hit: {nogo, file, line, excerpt, instead}. Patterns run over the WHOLE file, so a rule
    spread across lines is caught; write them with [^}]* rather than .* so one match never
    spans two CSS rules."""
    detectors = []
    for n in nogos(craft):
        for d in _as_list(n.get("detect")):
            if isinstance(d, dict) and isinstance(d.get("pattern"), str):
                try:
                    detectors.append((n, re.compile(d["pattern"], re.I), d.get("files") or DEFAULT_FILES))
                except re.error:
                    continue
    if not detectors:
        return []
    hits = []
    for f in _files(paths):
        try:
            if f.stat().st_size > MAX_BYTES:
                continue
        except OSError:
            continue
        mine = [(n, rx) for n, rx, globs in detectors if any(fnmatch.fnmatch(f.name, g) for g in globs)]
        if not mine:
            continue
        try:
            text = f.read_text(errors="replace")
        except OSError:
            continue
        for n, rx in mine:
            for m in rx.finditer(text):
                line = text.count("\n", 0, m.start()) + 1
                start = text.rfind("\n", 0, m.start()) + 1
                excerpt = text[start:start + 200].split("\n")[0].strip()
                hits.append({"nogo": n.get("id"), "file": str(f), "line": line,
                             "excerpt": excerpt, "instead": n.get("instead")})
    return hits
