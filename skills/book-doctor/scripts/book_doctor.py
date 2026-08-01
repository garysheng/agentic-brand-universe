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

# An ENDCAP MAY BE DECLARED IN `spreads`, and it is not an interior.
#
# `compose-spec` emits the endcaps as ordinary members of the `spreads` array,
# with the ids below. Until 2026-07-31 this file derived its interior list from
# `spreads` verbatim, so every declared endcap was graded TWICE: once correctly
# as an endcap (portrait) and then again as an interior (landscape), and the
# second grade can never pass. That failed every book compose-spec has ever
# produced, on both endcaps, and a doctor that always fails teaches its operator
# to ignore it. Caught by the-power-of-obeying-book, which was correct.
COVER_IDS = ("cover", "cover-0", "spread-00-cover", "spread-00")
CLOSING_IDS = ("closing-plate", "plate-0", "closing", "back-cover")


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


def _numeric_suffix(sid) -> int | None:
    """The interior number in `spread-07`, or None for `cover` / `closing-plate`.

    A non-numeric id used to raise ValueError out of the `max(...)` that derives
    the closing plate's number, and the `except` fell back to `len(declared)`,
    which counted the endcaps in. On a 69-spread book that demanded `spread-72`.
    """
    tail = str(sid).rsplit("-", 1)[-1]
    return int(tail) if tail.isdigit() else None


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

    # Resolve the ENDCAPS out of `declared` BEFORE anything grades an interior,
    # so no asset is graded against two contradictory aspect rules.
    declared_cover = next((d for d in declared if d in COVER_IDS), None)
    declared_closing = next((d for d in declared if d in CLOSING_IDS), None)
    endcap_ids = {x for x in (declared_cover, declared_closing) if x}
    interiors = [d for d in declared if d not in endcap_ids]

    rows: list[dict] = []

    def row(role, path, ok, note=""):
        rows.append({"role": role, "path": str(path) if path else None,
                     "ok": bool(ok), "note": note})

    # 1. front cover: an endcap, so portrait.
    #
    # TWO NAMING CONVENTIONS, and the difference decides which aspect rule applies
    # (corrected 2026-07-26 after an earlier patch here got it wrong).
    #
    #   COMPOSER names  cover-0.png / plate-0.png      pre-conform, native portrait
    #   STAGED names    spread-00-cover / spread-<N+1>  post-conform, exact 3:4
    #
    # A composer-emitted endcap is legitimately 1024x1536 (0.667): `stage-book-assets.py`
    # owns the aspect contract and pads it to 3:4 by edge replication on the way to webp.
    # So demanding exact 3:4 of a COMPOSER-named file is a FALSE POSITIVE, and an earlier
    # version of this comment wrongly accused a shipped book of a defect it never had.
    # What IS a real defect at composer stage is a LANDSCAPE endcap, because padding
    # cannot rescue that: the reader would crop it. So enforce PORTRAIT there, and exact
    # 3:4 only once the name says the conform has already happened.
    cover, cover_staged = _find(book, "spread-00-cover"), True
    if cover is None:
        cover, cover_staged = (
            _find(book, "cover-0") or _find(book, "cover")
            or (_find(book, declared_cover) if declared_cover else None)), False
    if cover is None:
        row("front cover", None, False,
            "missing (looked for spread-00-cover, cover-0, cover)")
    else:
        s = _size(cover)
        if cover_staged:
            ok, want = _aspect_ok(s, cover_aspect), f"want {cover_aspect}"
        else:
            ok, want = (bool(s) and s[0] < s[1]), "want PORTRAIT (staging pads it to 3:4)"
        row("front cover", cover, ok,
            "" if ok else f"aspect {round(s[0]/s[1], 2) if s else '?'} ({want})")

    # 2. every declared interior exists, at interior aspect.
    #    `interiors` excludes the endcaps, which checks 1 and 3 own.
    for sid in interiors:
        p = _find(book, sid)
        if p is None:
            row(sid, None, False, "missing")
            continue
        s = _size(p)
        ok = _aspect_ok(s, interior_aspect)
        row(sid, p, ok, "" if ok
            else f"aspect {round(s[0]/s[1], 2) if s else '?'} (want {interior_aspect})")

    # 3. the closing plate is a BACK COVER: portrait, not an interior.
    #
    # Two ways it is named, and BOTH are legitimate:
    #   DECLARED     the spec names it `closing-plate` (what compose-spec emits,
    #                and what stage-book-assets.py accepts). Composer name, so
    #                the PORTRAIT rule applies and staging conforms it to 3:4.
    #   POSITIONAL   it is not in the spec at all and sits at interior N+1.
    if declared:
        nums = [n for n in (_numeric_suffix(x) for x in interiors) if n is not None]
        last = max(nums) if nums else len(interiors)
        plate_id = declared_closing or f"spread-{last + 1:02d}"
        if declared_closing:
            plate, plate_staged = _find(book, declared_closing), False
        else:
            plate, plate_staged = _find(book, plate_id), True
        if plate is None:
            plate, plate_staged = (
                _find(book, "closing-plate") or _find(book, "plate-0")), False
        if plate is None:
            row("closing plate (back cover)", None, False,
                f"missing {plate_id} (or closing-plate, plate-0)")
        else:
            s = _size(plate)
            if plate_staged:
                ok, want = _aspect_ok(s, cover_aspect), f"want {cover_aspect}"
            else:
                ok, want = (bool(s) and s[0] < s[1]), "want PORTRAIT (staging pads it to 3:4)"
            row("closing plate (back cover)", plate, ok, "" if ok
                else f"aspect {round(s[0]/s[1], 2) if s else '?'} ({want}); "
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
        # STALE CAPTIONS ARE A DEFECT, AND AN INVISIBLE ONE.
        #
        # A render-spec's `_caption` is copied from the story's beat text when the
        # spec is scaffolded, and NOTHING re-syncs it afterwards. Edit a beat later
        # and the art follows the new text while the caption keeps the old, so the
        # book ships a picture of one thing under the words for another.
        #
        # Earned 2026-08-01 on will-there-be-ice-cream: beats 1 and 2 were rewritten
        # from an ice cream counter to a park bench AFTER the spec was scaffolded,
        # and the manifest generator, which correctly reads `_caption` so captions
        # are never hand-typed, faithfully emitted "a small creamery on a warm
        # evening" to sit under a painting of a park bench. It was caught by hand.
        # Nothing in the chain would have caught it.
        story_id = spec.get("story")
        sp_dir = Path(universe) / "stories"
        story_path = sp_dir / f"{story_id}.json" if story_id else None
        if story_path and story_path.exists():
            story = _load_json(story_path) or {}
            beats = {b.get("n"): b.get("text") for b in story.get("beats", []) or []}
            by_id = {s.get("id"): s for s in spec.get("spreads", []) or []}
            stale = []
            for n, text in beats.items():
                if n is None:
                    continue
                sp = by_id.get(f"spread-{n:02d}") or by_id.get(f"spread-{n}")
                if sp is None:
                    continue
                cap = sp.get("_caption")
                if cap is not None and cap != text:
                    stale.append(n)
            if stale:
                shown = ", ".join(str(n) for n in stale[:8])
                more = f" (+{len(stale) - 8} more)" if len(stale) > 8 else ""
                row("captions", str(story_path), False,
                    f"{len(stale)} caption(s) disagree with the blessed manuscript: "
                    f"beat(s) {shown}{more}. The art followed the new beat text and the "
                    f"caption kept the old, so the book would ship the wrong words under "
                    f"the right picture. Re-sync _caption from the story before delivering.")
            else:
                row("captions", str(story_path), True,
                    f"all {len(beats)} match the blessed manuscript verbatim")

        ents = Path(universe) / "canon" / "entities"
        cast: set[str] = set()

        def _add(v):
            """`cast` entries are `{"id": ...}` or a bare id string; the legacy
            `characters`/`extras` entries are `{"entity": ...}`."""
            if isinstance(v, str) and v:
                cast.add(v)
            elif isinstance(v, dict):
                for k in ("id", "entity"):
                    if v.get(k):
                        cast.add(v[k])
                        break

        for sp in spec.get("spreads", []):
            # `cast` is the live dialect: what compose_spec.py EMITS and what
            # assemble_prompt.py READS. This check read only `characters`/
            # `extras`, which nothing in the chain emits, so it was a silent
            # no-op on every real book from the day it shipped.
            for c in sp.get("cast", []) or []:
                _add(c)
            for c in sp.get("characters", []) or []:
                _add(c)
            for e in sp.get("extras", []) or []:
                _add(e)
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
