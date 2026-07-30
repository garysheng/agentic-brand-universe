"""Code-built 2D ELEVATION renderer for object blueprints (SPEC §4.4 / §12 contracts).

WHY THIS EXISTS
---------------
`massing` solves this problem for SETTINGS: a room is a perspective view, so it declares
solids and cameras and renders what each locked camera sees. But the other thing a universe
constantly needs a blueprint for is not a room. It is an OBJECT: a door, a key, a lamp, a
cellar hatch, a boat, a book. Those are argued flat and head-on, and a perspective massing
render is the wrong tool for them, so every object blueprint got hand-written instead.

Nine separate hand-rolled blueprint scripts accumulated in one universe before this existed
(nation-of-fire, 2026-07-30, counted at the pave). They total ~1300 lines and they agree
almost entirely on what they draw: rectangles, lines, ellipses, polygons and a great deal of
text. Eight of the nine re-implement the SAME `font()` fallback chain. Several re-implement
dimension lines and dashed strokes. That is duplication, and duplication is the cheap part.

The expensive part is that only FOUR of the nine stamped "LAYOUT REFERENCE ONLY" on the
sheet. The other five shipped a blueprint that does not say it is a blueprint, into a
pipeline whose entire blueprint convention is that the guard is present and every consumer
passes it. A rule that depends on each author remembering it is a rule that fails the run
where they forget, and it had already failed five times out of nine. This renderer stamps
the guard unconditionally and there is no flag to turn it off.

THE OTHER WIN: DECLARED UNITS
-----------------------------
Geometry is stated in the object's OWN units (feet, inches, millimetres), not pixels,
because that is how an entity contract states it: "about three feet wide by seven feet tall",
"a rectangle about fourteen inches by twelve". A hand-rolled script converts those to pixels
by hand, once, silently, and every later edit has to redo the arithmetic in the author's
head. Here the spec carries the numbers the contract already carries, and `scale` converts.

Deterministic: same spec in, same pixels out. No seed, no model, no network, no cost.

INPUT
-----
A declarative JSON spec (see `render_sheet`). No universe knows any Python for this.

DEPENDENCY
----------
Pillow only, imported lazily so the rest of the engine stays importable without it.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Sequence, Tuple

# Sheet furniture, matched to massing.py so the two blueprint kinds read as one family.
BG = (238, 235, 228)
INK = (30, 36, 46)
DIM = (120, 130, 145)

PALETTE: Dict[str, Tuple[int, int, int]] = {
    "paper": BG,
    "ink": INK,
    "dim": DIM,
    "wood": (150, 112, 68),
    "iron": (52, 55, 62),
    "stone": (196, 192, 184),
    "glass": (150, 178, 196),
    "accent": (176, 66, 52),   # callouts: the thing the sheet is pointing AT
    "guide": (176, 66, 52),
}

GUARD = "LAYOUT REFERENCE ONLY. Never paint these lines, dashes, dimensions or labels into a spread."


def _color(v: Any, default: Tuple[int, int, int] = INK) -> Tuple[int, int, int]:
    """Accept a palette name, an [r,g,b] triple, or None."""
    if v is None:
        return default
    if isinstance(v, str):
        if v in PALETTE:
            return PALETTE[v]
        s = v.lstrip("#")
        if len(s) == 6:
            try:
                return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
            except ValueError:
                pass
        raise ValueError(f"unknown colour {v!r}: use a palette name {sorted(PALETTE)} or #rrggbb")
    if isinstance(v, (list, tuple)) and len(v) == 3:
        return (int(v[0]), int(v[1]), int(v[2]))
    raise ValueError(f"unknown colour {v!r}")


def _font(size: int):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Supplemental/Courier New Bold.ttf",
              "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


class _Scale:
    """Declared units -> pixels, with the drawing origin at the sheet's content area."""

    def __init__(self, spec: Dict[str, Any], sheet: Dict[str, Any]):
        sc = spec.get("scale") or {}
        self.unit = sc.get("unit", "px")
        self.k = float(sc.get("pxPerUnit", 1.0))
        if self.k <= 0:
            raise ValueError("scale.pxPerUnit must be > 0")
        self.ox = float(sc.get("originPx", [sheet["margin"], sheet["margin"] + 120])[0])
        self.oy = float(sc.get("originPx", [sheet["margin"], sheet["margin"] + 120])[1])

    def p(self, pt: Sequence[float]) -> Tuple[float, float]:
        return (self.ox + float(pt[0]) * self.k, self.oy + float(pt[1]) * self.k)

    def d(self, v: float) -> float:
        return float(v) * self.k


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(v, hi))


def _dashed(draw, p0, p1, fill, width, on=12, off=9) -> None:
    """PIL has no dashed-line primitive and every hand-rolled sheet re-wrote this."""
    x0, y0 = p0
    x1, y1 = p1
    dx, dy = x1 - x0, y1 - y0
    ln = max(1e-6, (dx * dx + dy * dy) ** 0.5)
    ux, uy = dx / ln, dy / ln
    t = 0.0
    while t < ln:
        e = min(t + on, ln)
        draw.line([(x0 + ux * t, y0 + uy * t), (x0 + ux * e, y0 + uy * e)], fill=fill, width=width)
        t = e + off


def _stroke(draw, p0, p1, fill, width, dashed: bool) -> None:
    if dashed:
        _dashed(draw, p0, p1, fill, width)
    else:
        draw.line([p0, p1], fill=fill, width=width)


def _expand(parts: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Flatten `repeat` parts.

    Almost every object sheet has a run of identical members: five planks, two ledges,
    two hinges, four nails, six pickets. Hand-rolled scripts write a for-loop each time,
    which is where an off-by-one lives.
    """
    out: List[Dict[str, Any]] = []
    for p in parts:
        if p.get("kind") != "repeat":
            out.append(p)
            continue
        proto = p.get("of")
        if not isinstance(proto, dict):
            raise ValueError("repeat.of must be a part object")
        count = int(p.get("count", 0))
        if count < 0:
            raise ValueError("repeat.count must be >= 0")
        step = p.get("step") or [0, 0]
        for i in range(count):
            c = json.loads(json.dumps(proto))
            dx, dy = float(step[0]) * i, float(step[1]) * i
            for key in ("at", "from", "to", "center", "leaderTo"):
                if key in c and c[key] is not None:
                    c[key] = [float(c[key][0]) + dx, float(c[key][1]) + dy]
            if "points" in c and c["points"]:
                c["points"] = [[float(a) + dx, float(b) + dy] for a, b in c["points"]]
            if isinstance(c.get("text"), str) and "{i}" in c["text"]:
                c["text"] = c["text"].replace("{i}", str(i + int(p.get("startAt", 1))))
            out.append(c)
    return out


def _draw_part(draw, s: _Scale, part: Dict[str, Any], fonts, bounds) -> None:
    f_label, f_small = fonts
    kind = part.get("kind")
    stroke = _color(part.get("stroke") or part.get("outline"), INK)
    fill = _color(part["fill"], INK) if part.get("fill") else None
    w = int(part.get("width", 3))
    dashed = bool(part.get("dashed"))

    if kind == "rect":
        x, y = s.p(part["at"])
        ww, hh = s.d(part["size"][0]), s.d(part["size"][1])
        if fill and not dashed:
            draw.rectangle([x, y, x + ww, y + hh], fill=fill,
                           outline=stroke if part.get("outline") or part.get("stroke") else None,
                           width=w)
        else:
            corners = [(x, y), (x + ww, y), (x + ww, y + hh), (x, y + hh)]
            for i in range(4):
                _stroke(draw, corners[i], corners[(i + 1) % 4], stroke, w, dashed)

    elif kind == "line":
        _stroke(draw, s.p(part["from"]), s.p(part["to"]), stroke, w, dashed)

    elif kind == "ellipse":
        cx, cy = s.p(part["center"])
        rx, ry = s.d(part["r"][0]), s.d(part["r"][1])
        draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry],
                     fill=fill, outline=stroke, width=w)

    elif kind == "polygon":
        draw.polygon([s.p(pt) for pt in part["points"]], fill=fill,
                     outline=stroke if not fill else None)

    elif kind == "dim":
        _draw_dim(draw, s, part, f_small, bounds)

    elif kind == "note":
        _draw_note(draw, s, part, f_label, f_small)

    else:
        raise ValueError(f"unknown part kind {kind!r}: "
                         "use rect, line, ellipse, polygon, repeat, dim or note")

    # Any geometric part may carry an inline label.
    if kind in ("rect", "line", "ellipse", "polygon") and part.get("text"):
        anchor = part.get("at") or part.get("center") or part.get("from") or part["points"][0]
        tx, ty = s.p(anchor)
        draw.text((tx + 8, ty + 6), str(part["text"]), font=f_small,
                  fill=_color(part.get("textColor"), INK))


def _draw_dim(draw, s: _Scale, part: Dict[str, Any], f, bounds: Tuple[int, int, int]) -> None:
    axis = part.get("axis", "h")
    a, b = s.p(part["from"]), s.p(part["to"])
    off = float(part.get("offset", 40))
    col = _color(part.get("stroke"), DIM)
    label = str(part.get("label", ""))
    W, _H, margin = bounds
    if axis == "h":
        y = max(a[1], b[1]) + off
        draw.line([(a[0], y), (b[0], y)], fill=col, width=2)
        for x in (a[0], b[0]):
            draw.line([(x, y - 9), (x, y + 9)], fill=col, width=2)
        if label:
            tw = draw.textlength(label, font=f)
            draw.text((_clamp((a[0] + b[0]) / 2 - tw / 2, margin, W - margin - tw), y + 12),
                      label, font=f, fill=col)
    else:
        x = min(a[0], b[0]) - off
        draw.line([(x, a[1]), (x, b[1])], fill=col, width=2)
        for y in (a[1], b[1]):
            draw.line([(x - 9, y), (x + 9, y)], fill=col, width=2)
        if label:
            tw = draw.textlength(label, font=f)
            # A vertical dim's label sits to the LEFT of its rule, so a generous offset
            # silently pushes it off the sheet and the measurement is simply absent.
            draw.text((_clamp(x - tw - 14, margin, W - margin - tw),
                       (a[1] + b[1]) / 2 - 10), label, font=f, fill=col)


def _draw_note(draw, s: _Scale, part: Dict[str, Any], f_label, f_small) -> None:
    at = s.p(part["at"])
    col = _color(part.get("stroke"), INK)
    if part.get("leaderTo"):
        draw.line([at, s.p(part["leaderTo"])], fill=col, width=2)
    lines = part.get("text")
    lines = [lines] if isinstance(lines, str) else list(lines or [])
    y = at[1]
    for i, ln in enumerate(lines):
        f = f_label if i == 0 and part.get("heading", True) else f_small
        draw.text((at[0], y), str(ln), font=f, fill=col)
        y += (26 if f is f_label else 22)


def render_sheet(spec: Dict[str, Any], out_path: str) -> str:
    """Render a declarative 2D elevation sheet.

    SPEC SHAPE
    ----------
        {
          "title": "THE LITTLE DOOR",
          "subtitle": "ELEVATION",
          "sheet":  {"width": 1536, "height": 1024, "margin": 60},
          "scale":  {"unit": "ft", "pxPerUnit": 84, "originPx": [300, 200]},
          "parts":  [ ...see below... ],
          "laws":   ["THE FLAP NEVER CHANGES SIZE OR SHAPE in any state.", ...]
        }

    All part coordinates are in `scale.unit`, with the origin at `scale.originPx`.

        {"kind":"rect",    "at":[0,0], "size":[3,7], "fill":"wood", "stroke":"ink"}
        {"kind":"line",    "from":[0,0], "to":[3,0], "stroke":"ink", "dashed":true}
        {"kind":"ellipse", "center":[2.8,4], "r":[0.25,0.25], "stroke":"iron", "width":7}
        {"kind":"polygon", "points":[[0,1],[1.8,1.1],[1.8,1.3],[0,1.4]], "fill":"iron"}
        {"kind":"repeat",  "of":{...}, "count":5, "step":[0.6,0], "startAt":1}
        {"kind":"dim",     "axis":"h", "from":[0,7], "to":[3,7], "offset":38, "label":"3 ft"}
        {"kind":"note",    "at":[-2.6,4], "text":["FLAP FOOTPRINT","14 in x 12 in"],
                           "leaderTo":[1.4,5.8], "stroke":"accent"}

    `laws` are the standing rules printed in the footer block. The LAYOUT REFERENCE ONLY
    guard is ALWAYS stamped and cannot be disabled: five of the nine hand-rolled sheets
    this replaces forgot it.

    Returns `out_path`.
    """
    from PIL import Image, ImageDraw

    sheet = dict(spec.get("sheet") or {})
    W = int(sheet.get("width", 1536))
    H = int(sheet.get("height", 1024))
    margin = int(sheet.get("margin", 60))
    sheet["margin"] = margin

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    f_title, f_label, f_small = _font(32), _font(20), _font(16)

    title = str(spec.get("title", "ELEVATION"))
    sub = str(spec.get("subtitle", "ELEVATION"))
    d.text((margin, 40), f"{title}  /  {sub}  /  LAYOUT REFERENCE ONLY", font=f_title, fill=INK)
    d.line([(margin, 84), (W - margin, 84)], fill=INK, width=3)

    s = _Scale(spec, sheet)
    for part in _expand(spec.get("parts") or []):
        _draw_part(d, s, part, (f_label, f_small), (W, H, margin))

    laws = [str(x) for x in (spec.get("laws") or [])]
    laws.append(GUARD)
    block_h = 26 * len(laws) + 20
    y0 = H - block_h - 8
    d.line([(margin, y0), (W - margin, y0)], fill=INK, width=2)
    for i, ln in enumerate(laws):
        d.text((margin, y0 + 16 + i * 26), ln, font=f_small, fill=INK)

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    img.save(out_path)
    return out_path


def write_recipe(out_path: str, spec_path: str, universe: str | None = None,
                 spec_version: str | None = None, entity: str | None = None) -> str:
    """Freeze provenance beside the sheet, matching massing's signature and shape."""
    rec: Dict[str, Any] = {
        "asset": os.path.abspath(out_path),
        "generator": "agenticstory.elevation",
        "mode": "deterministic-2d-elevation",
        "spec": os.path.abspath(spec_path),
        "inputs": [],
        "model": None,
    }
    if universe:
        rec["universe"] = os.path.abspath(universe)
    if spec_version:
        rec["specVersion"] = spec_version
    if entity:
        rec["entity"] = entity
    p = out_path + ".recipe.json"
    with open(p, "w") as fh:
        json.dump(rec, fh, indent=2)
        fh.write("\n")
    return p
