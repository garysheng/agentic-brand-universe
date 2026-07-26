#!/usr/bin/env python3
"""book_doctor.py — grade a RENDERED book on local disk against what its spec declares.

This is the LOCAL, PRE-DELIVERY half of the doctor pattern. It answers one question:
"is this book finished and internally consistent BEFORE anything is uploaded anywhere?"

It deliberately knows NOTHING about any delivery surface: no bucket, no CDN, no reader
URL, no cloud SDK, no network, no API key. A delivery platform's own doctor (probing
whatever storage it uses) is a separate, platform-owned tool, and the two do not
overlap. Two of the checks here are ones a bucket probe CANNOT do at all, because the
evidence never leaves the machine:

  * PROVENANCE. Every generated asset must carry its recipe (model, exact prompt, every
    input by path). Recipes are build artifacts and are not shipped, so the only place
    this is checkable is here.
  * NO SELF-REFERENCE. A spread must never be generated from another spread render;
    editing a prior render lets a defect survive into its own "fix". The evidence is the
    recipe's input list, which again never ships.

The check that earned this tool: a book shipped with its closing plate rendered at
LANDSCAPE interior aspect when the reader composes it as a single-page BACK COVER at
3:4, so the reader cropped it. Nothing in the pre-render gates covers output shape,
because at gate time there is no output yet.

Usage:
    book_doctor.py <book-dir> [--universe <path>] [--json]

Exit 0 = healthy. Exit 1 = at least one problem. Exit 2 = could not read the book.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Aspect contract. A book may override via render-spec "doctor": {...}.
COVER_ASPECT = 0.75  # 3:4 portrait: front cover AND closing plate (both are endcaps)
TOLERANCE = 0.02


def _load_json(p: Path):
    try:
        return json.loads(p.read_text())
    except Exception:
        return None


def _size(p: Path):
    """Width/height without a hard Pillow dependency at import time."""
    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - environment guard
        return None
    try:
        with Image.open(p) as im:
            return im.size
    except Exception:
        return None


def _aspect_ok(size, want: float) -> bool:
    if not size or not size[1]:
        return False
    return abs(size[0] / size[1] - want) <= TOLERANCE


def _find(book: Path, stem: str):
    """A rendered asset may be .png or .webp; the doctor accepts either."""
    for ext in (".png", ".webp", ".jpg", ".jpeg"):
        for sub in ("spreads", "cover", ""):
            c = book / sub / f"{stem}{ext}" if sub else book / f"{stem}{ext}"
            if c.exists():
                return c
    return None


def _recipe_for(asset: Path):
    for c in (asset.with_suffix(asset.suffix + ".recipe.json"),
              asset.with_suffix(".recipe.json")):
        if c.exists():
            return c
    return None


def diagnose(book_dir: str, universe: str | None = None) -> dict:
    book = Path(book_dir)
    spec_path = book / "render-spec.json"
    spec = _load_json(spec_path)
    if spec is None:
        return {"fatal": f"no readable render-spec.json at {spec_path}"}

    cfg = spec.get("doctor") or {}
    cover_aspect = float(cfg.get("coverAspect", COVER_ASPECT))
    size_str = spec.get("size", "1536x1024")
    try:
        w, h = (int(x) for x in str(size_str).lower().split("x"))
        interior_aspect = float(cfg.get("interiorAspect", w / h))
    except Exception:
        interior_aspect = float(cfg.get("interiorAspect", 1.5))

    declared = [s["id"] for s in spec.get("spreads", []) if "id" in s]
    rows: list[dict] = []

    def row(role, path, ok, note=""):
        rows.append({"role": role, "path": str(path) if path else None,
                     "ok": bool(ok), "note": note})

    # 1. front cover: an endcap, so portrait
    cover = _find(book, "spread-00-cover")
    if cover is None:
        row("front cover", None, False, "missing")
    else:
        s = _size(cover)
        row("front cover", cover, _aspect_ok(s, cover_aspect),
            "" if _aspect_ok(s, cover_aspect)
            else f"aspect {round(s[0]/s[1], 2) if s else '?'} (want {cover_aspect})")

    # 2. every declared interior exists, at interior aspect
    for sid in declared:
        p = _find(book, sid)
        if p is None:
            row(sid, None, False, "missing")
            continue
        s = _size(p)
        ok = _aspect_ok(s, interior_aspect)
        row(sid, p, ok, "" if ok
            else f"aspect {round(s[0]/s[1], 2) if s else '?'} (want {interior_aspect})")

    # 3. closing plate at N+1 is a BACK COVER: portrait, not an interior
    if declared:
        try:
            last = max(int(str(x).rsplit("-", 1)[-1]) for x in declared)
        except ValueError:
            last = len(declared)
        plate_id = f"spread-{last + 1:02d}"
        plate = _find(book, plate_id)
        if plate is None:
            row("closing plate (back cover)", None, False, f"missing {plate_id}")
        else:
            s = _size(plate)
            ok = _aspect_ok(s, cover_aspect)
            row("closing plate (back cover)", plate, ok, "" if ok
                else f"aspect {round(s[0]/s[1], 2) if s else '?'} (want {cover_aspect}); "
                     "the closing plate is an ENDCAP, not an interior")

    # 4. provenance: every rendered asset carries its recipe
    for r in [x for x in rows if x["ok"] and x["path"]]:
        a = Path(r["path"])
        if _recipe_for(a) is None:
            row(f"provenance {a.name}", a, False, "no recipe.json beside the asset")

    # 5. no self-reference: no rendered asset generated from another spread render.
    # Scans EVERY asset, not just the numbered interiors. The closing plate is the
    # likeliest offender of all (the legacy migration recipe literally says "copy the
    # final spread as the plate file"), and keying this off a role name beginning
    # "spread-" skipped exactly that asset. Caught by its own test.
    for r in [x for x in rows if x["path"]]:
        a = Path(r["path"])
        rec = _recipe_for(a)
        if rec is None:
            continue
        data = _load_json(rec) or {}
        inputs = data.get("input_images") or data.get("inputImages") or []
        if isinstance(inputs, str):
            inputs = [inputs]
        for src in inputs:
            name = Path(str(src)).name
            if name.startswith("spread-") and name != a.name:
                row(f"self-reference {a.name}", a, False,
                    f"generated from another render ({name}); regenerate from canon only")

    # 6. optional: every cast entity resolves in canon and is locked
    if universe:
        ents = Path(universe) / "canon" / "entities"
        cast: set[str] = set()
        for sp in spec.get("spreads", []):
            for c in sp.get("characters", []) or []:
                if isinstance(c, dict) and c.get("entity"):
                    cast.add(c["entity"])
            for e in sp.get("extras", []) or []:
                if isinstance(e, dict) and e.get("entity"):
                    cast.add(e["entity"])
            st = sp.get("setting")
            if isinstance(st, dict) and st.get("entity"):
                cast.add(st["entity"])
            elif isinstance(st, str):
                cast.add(st)
        for eid in sorted(cast):
            f = ents / f"{eid}.json"
            if not f.exists():
                row(f"cast {eid}", f, False, "not registered in canon")
                continue
            d = _load_json(f) or {}
            if d.get("status") == "unlocked":
                row(f"cast {eid}", f, False, "status is unlocked")

    problems = [r for r in rows if not r["ok"]]
    return {"book": str(book), "rows": rows, "problems": problems,
            "healthy": not problems}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="book_doctor")
    ap.add_argument("book")
    ap.add_argument("--universe", default=None,
                    help="also check that every cast entity is registered and locked")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)

    res = diagnose(a.book, a.universe)
    if res.get("fatal"):
        print(f"cannot read book: {res['fatal']}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(res, indent=2))
    else:
        for r in res["rows"]:
            mark = "ok  " if r["ok"] else "FAIL"
            note = f"  {r['note']}" if r["note"] else ""
            print(f"  [{mark}] {r['role']:<32}{note}")
        print()
        if res["healthy"]:
            print("healthy: every declared asset is rendered, at the right aspect, "
                  "with provenance, and no spread was built from another spread.")
        else:
            print(f"PROBLEM: {len(res['problems'])} issue(s):")
            for p in res["problems"]:
                print(f"  - {p['role']}: {p['note'] or 'missing'}")
    return 0 if res["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
