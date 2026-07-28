"""Code-built 3D MASSING RENDERER for setting blueprints (SPEC §4.4 setting contract).

WHY THIS EXISTS
---------------
A setting's `contract.blueprint` is the seed the whole reference matrix inherits: every empty
plate, every later spread, every re-render derives its geometry from it. For a long time the
blueprint was drawn as a flat TOP-DOWN PLAN, or worse, described in prose. Both under-specify the
thing the image model actually has to produce, which is a PERSPECTIVE VIEW from a particular
camera. A plan makes the model infer the perspective, and inference is exactly where geometry
drifts: rooms change proportion between angles, handedness flips, furniture migrates.

A massing render removes the inference. You declare the room as boxes and quads once, name the
cameras once, and this renders the ACTUAL perspective each locked camera will see. The image model
is then matching a picture to a picture instead of a picture to a floor plan.

It is deliberately CRUDE: flat-shaded blocks, ink edges, no textures, no materials, no lighting
model beyond one lambert term. Crude is the feature. A blueprint that looks like finished art
invites the model to copy its surface; a blueprint that obviously reads as scaffolding gets used
as scaffolding. The sheet is stamped LAYOUT REFERENCE ONLY and every consumer passes it with the
standard blueprint guard.

Deterministic: same spec in, same pixels out. No seed, no model, no network, no cost.

INPUT
-----
A declarative JSON spec (see `render_sheet` docstring). No universe knows any Python for this.

DEPENDENCY
----------
Pillow only, imported lazily so the rest of the engine stays importable without it.
"""

from __future__ import annotations

import json
import math
import os
from typing import Any, Dict, List, Sequence, Tuple

Vec = Tuple[float, float, float]

# Sheet furniture. Deliberately paper-like so a blueprint never reads as artwork.
BG = (238, 235, 228)
INK = (30, 36, 46)
DIM = (120, 130, 145)
ACC = (176, 110, 52)

TONE = {"rule": ACC, "info": INK, "dim": DIM}

STAMP = "LAYOUT REFERENCE ONLY, NEVER PAINTED"


# --------------------------------------------------------------------------
# vector helpers (pure python on purpose: the engine takes no numpy dependency)
# --------------------------------------------------------------------------

def _sub(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Sequence[float], b: Sequence[float]) -> Vec:
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _dot(a: Sequence[float], b: Sequence[float]) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _norm(a: Sequence[float]) -> Vec:
    m = math.sqrt(_dot(a, a))
    if m < 1e-12:
        return (0.0, 0.0, 0.0)
    return (a[0] / m, a[1] / m, a[2] / m)


def _basis(eye: Sequence[float], target: Sequence[float],
           up: Sequence[float] = (0, 0, 1)) -> Tuple[Vec, Vec, Vec]:
    """Right-handed camera basis. Z-up world, because rooms have floors."""
    f = _norm(_sub(target, eye))
    r = _norm(_cross(f, up))
    u = _cross(r, f)
    return r, u, f


# --------------------------------------------------------------------------
# geometry
# --------------------------------------------------------------------------

def box_quads(lo: Sequence[float], hi: Sequence[float],
              faces: Sequence[str] | None = None) -> List[List[Vec]]:
    """Axis-aligned box as quads. `faces` selects a subset (open rooms want no ceiling)."""
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    f = {
        "bottom": [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0)],
        "top":    [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        "front":  [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
        "back":   [(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)],
        "left":   [(x0, y0, z0), (x0, y1, z0), (x0, y1, z1), (x0, y0, z1)],
        "right":  [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
    }
    keys = list(f.keys()) if not faces else list(faces)
    return [f[k] for k in keys if k in f]


def _solids_to_quads(solids: Sequence[Dict[str, Any]]) -> List[Tuple[List[Vec], Tuple[int, int, int], bool]]:
    """Flatten the declarative solid list into (quad, colour, draw_edges)."""
    out: List[Tuple[List[Vec], Tuple[int, int, int], bool]] = []
    for s in solids:
        colour = tuple(s.get("color", (170, 170, 170)))  # type: ignore[assignment]
        edges = bool(s.get("edges", True))
        kind = s.get("type", "box")
        if kind == "box":
            for q in box_quads(s["min"], s["max"], s.get("faces")):
                out.append((q, colour, edges))  # type: ignore[arg-type]
        elif kind == "quad":
            out.append(([tuple(p) for p in s["pts"]], colour, edges))  # type: ignore[arg-type]
        else:
            raise ValueError(f"unknown solid type {kind!r} (expected 'box' or 'quad')")
    return out


# --------------------------------------------------------------------------
# render one camera
# --------------------------------------------------------------------------

def render_view(solids: Sequence[Dict[str, Any]], camera: Dict[str, Any],
                width: int, height: int, ambient: float = 0.42,
                light: Vec = (0.4, -0.7, 0.8)):
    """Painter's-algorithm flat-shaded render of `solids` from `camera`.

    Returns (PIL.Image, projector) where projector(point3d) -> (x, y) | None,
    so a caller can anchor a leader line to a real world coordinate.
    """
    from PIL import Image, ImageDraw  # lazy: keeps the engine importable without Pillow

    eye = tuple(camera["eye"])
    tgt = tuple(camera["target"])
    fov = float(camera.get("fov", 60))
    r, u, fwd = _basis(eye, tgt, camera.get("up", (0, 0, 1)))
    L = _norm(light)
    f = 1.0 / math.tan(math.radians(fov) / 2.0)
    asp = width / float(height)

    def to_cam(p: Sequence[float]) -> Vec:
        d = _sub(p, eye)
        return (_dot(d, r), _dot(d, u), -_dot(d, fwd))

    def project(p: Sequence[float]):
        c = to_cam(p)
        if c[2] > -0.05:            # at or behind the near plane
            return None
        z = -c[2]
        return (((c[0] * f / asp) / z * 0.5 + 0.5) * width,
                (0.5 - (c[1] * f) / z * 0.5) * height)

    im = Image.new("RGB", (width, height), BG)
    d = ImageDraw.Draw(im)

    prepared = []
    for quad, colour, edges in _solids_to_quads(solids):
        cam = [to_cam(p) for p in quad]
        # Crude near-plane handling: drop any face with a vertex at/behind the eye.
        # A clipper would be more correct; dropping is predictable and never produces
        # the smeared inside-out polygons a naive projection gives.
        if any(c[2] > -0.05 for c in cam):
            continue
        pts = [project(p) for p in quad]
        if any(p is None for p in pts):
            continue
        n = _norm(_cross(_sub(quad[1], quad[0]), _sub(quad[2], quad[0])))
        lam = ambient + (1.0 - ambient) * abs(_dot(n, L))
        col = tuple(min(255, int(c * lam)) for c in colour)
        depth = sum(-c[2] for c in cam) / len(cam)
        prepared.append((depth, pts, col, edges))

    prepared.sort(key=lambda t: -t[0])   # far to near
    for _depth, pts, col, edges in prepared:
        d.polygon(pts, fill=col)
        if edges:
            for i in range(len(pts)):
                d.line([pts[i], pts[(i + 1) % len(pts)]], fill=INK, width=2)

    return im, project


# --------------------------------------------------------------------------
# sheet
# --------------------------------------------------------------------------

def _font(size: int):
    from PIL import ImageFont
    for p in ("/System/Library/Fonts/Supplemental/Courier New.ttf",
              "/System/Library/Fonts/Menlo.ttc",
              "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_sheet(spec: Dict[str, Any], out_path: str) -> str:
    """Render a full blueprint sheet from a declarative massing spec.

    Spec shape::

        {
          "title":    "THE LONG ROOM",
          "subtitle": "3D MASSING SEED / CAMERAS C1 + C2 LOCKED",   # optional
          "sheet":    {"width": 1536, "height": 1024},              # optional
          "solids": [
            {"type":"box",  "min":[0,0,0], "max":[9,4,3.1], "color":[214,206,192],
             "faces":["bottom","back","front"], "edges":true},
            {"type":"quad", "pts":[[0,0,0],[9,0,0],[9,0,3],[0,0,3]], "color":[214,206,192]}
          ],
          "cameras": [
            {"id":"c1","caption":"C1 MASTER - from the door","eye":[0.5,2,1.65],
             "target":[9,2,1.3],"fov":62,"ambient":0.42,
             "labels":[{"at":[1.4,3.9,2.3],"text":"BOOKSHELF WALL = C1-LEFT","screen":[28,40]}]}
          ],
          "notes": [ {"text":"THE ONE CHAIR FACES THE WINDOW.", "tone":"rule"} ]
        }

    `tone` is one of rule | info | dim. Every label draws a leader line from its world
    point `at` to the screen position `screen`, so annotations never collide by accident.

    Returns `out_path`.
    """
    from PIL import Image, ImageDraw

    sheet = spec.get("sheet") or {}
    W = int(sheet.get("width", 1536))
    H = int(sheet.get("height", 1024))
    solids = spec.get("solids") or []
    cams = spec.get("cameras") or []
    if not cams:
        raise ValueError("massing spec needs at least one camera")

    f_title, f_sub, f_cap, f_note = _font(27), _font(14), _font(16), _font(14)

    margin, gap = 44, 24
    avail = W - 2 * margin - gap * (len(cams) - 1)
    vw = max(1, avail // len(cams))
    vh = int(vw * 0.79)

    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    d.rectangle([20, 20, W - 20, H - 20], outline=INK, width=3)
    d.text((margin, 38), spec.get("title", "MASSING"), font=f_title, fill=INK)
    sub = spec.get("subtitle") or "3D MASSING SEED"
    d.text((margin, 76), f"{sub} / {STAMP}", font=f_sub, fill=DIM)

    top = 116
    x = margin
    for cam in cams:
        view, project = render_view(solids, cam, vw, vh,
                                    ambient=float(cam.get("ambient", 0.42)))
        vd = ImageDraw.Draw(view)
        for lab in cam.get("labels") or []:
            p = project(lab["at"])
            if p is None:
                continue
            sx, sy = lab.get("screen", (10, 10))
            colour = TONE.get(lab.get("tone", "rule"), ACC)
            vd.line([p, (sx, sy)], fill=colour, width=1)
            vd.ellipse([p[0] - 3.5, p[1] - 3.5, p[0] + 3.5, p[1] + 3.5], fill=colour)
            tb = vd.textbbox((sx, sy), lab["text"], font=f_cap)
            vd.rectangle([tb[0] - 4, tb[1] - 4, tb[2] + 4, tb[3] + 4],
                         fill=BG, outline=colour, width=1)
            vd.text((sx, sy), lab["text"], font=f_cap, fill=colour)
        im.paste(view, (x, top))
        d.rectangle([x, top, x + vw, top + vh], outline=INK, width=3)
        d.text((x + 4, top + vh + 8), cam.get("caption", cam.get("id", "")),
               font=f_cap, fill=INK)
        x += vw + gap

    y = top + vh + 44
    for note in spec.get("notes") or []:
        d.text((margin, y), note.get("text", ""), font=f_note,
               fill=TONE.get(note.get("tone", "info"), INK))
        y += 24

    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    im.save(out_path)
    return out_path


def write_recipe(out_path: str, spec_path: str, universe: str | None = None,
                 spec_version: str | None = None, entity: str | None = None) -> str:
    """Provenance for a deterministic asset, so a massing sheet is never an unsourced file."""
    rec = {
        "asset": os.path.basename(out_path),
        "generator": "agenticstory.massing (code-built 3D massing render)",
        "deterministic": True,
        "model": None,
        "prompt": None,
        "inputs": [spec_path],
        "universe": universe,
        "entity": entity,
        "specVersion": spec_version,
        "note": ("Blueprint rendered in code from a declarative massing spec, from the entity's "
                 "own locked cameras. Layout reference only; never painted into artwork."),
    }
    p = out_path + ".recipe.json"
    with open(p, "w") as fh:
        json.dump(rec, fh, indent=2)
        fh.write("\n")
    return p
