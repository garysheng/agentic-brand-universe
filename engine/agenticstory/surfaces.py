"""Surface roles (SPEC §11 `identity.surfaces`, v0.59): which canon tokens a renderer outside
the universe paints each surface in.

A universe's colors live wherever its canon put them: Continental Works keeps tokens as
`{hex}` objects in `canon/craft/palette.json`, Christofuturism keeps bare hexes in
`universe.json` `brand.chrome`. Token NAMES do not travel either: Christofuturism's `ink` is
its text color, Continental Works' `ink` is its ground. So a consumer (Freedom's deck builder
and artifacts host, freedom#163) never reads a name. It reads this declaration, which says,
per surface, which record holds the tokens and which token is the ground, the text and the
accent. `validate` checks it, so a declaration that has stopped resolving fails here, in the
universe's own gate, rather than as a deck that quietly renders in someone else's colors.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

ROLES = ("ground", "text", "accent")
HEX = re.compile(r"^#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def _dig(obj, path: str):
    for k in [p for p in path.split(".") if p]:
        if not isinstance(obj, dict):
            return None
        obj = obj.get(k)
    return obj


def _check(root: Path, name: str, decl) -> list[str]:
    where = f"identity.surfaces.{name}"
    if not isinstance(decl, dict):
        return [f"{where}: must be an object"]
    ref = decl.get("tokens")
    file, _, path = (ref if isinstance(ref, str) else "").partition("#")
    if not file:
        return [f"{where}: tokens must be '<file>#<path>', got {ref!r}"]
    f = root / file
    if not f.is_file():
        return [f"{where}: {file} does not exist in the universe"]
    try:
        rec = json.loads(f.read_text())
    except ValueError:
        return [f"{where}: {file} is not valid JSON"]
    tokens = _dig(rec, path) if path else rec
    if not isinstance(tokens, dict):
        return [f"{where}: {ref} does not name a map of tokens"]
    roles = decl.get("roles") if isinstance(decl.get("roles"), dict) else {}
    out = []
    for role in ROLES:
        tok = roles.get(role)
        if not tok:
            out.append(f"{where}: roles.{role} is missing")
            continue
        if tok not in tokens:
            out.append(f"{where}: {role} names token '{tok}', which {ref} does not have")
            continue
        v = tokens[tok]
        hexv = v if isinstance(v, str) else v.get("hex") if isinstance(v, dict) else None
        if not isinstance(hexv, str) or not HEX.match(hexv):
            out.append(f"{where}: {role} ('{tok}') is not a hex color: {hexv!r}")
    if "display" in decl and not isinstance(decl["display"], str):
        out.append(f"{where}: display must be a font family string")
    return out


def validate_surfaces(root: Path, manifest: dict) -> list[str]:
    """Every defect in `identity.surfaces`, empty when it is sound or absent (it is optional)."""
    s = (manifest.get("identity") or {}).get("surfaces")
    if s is None:
        return []
    if not isinstance(s, dict):
        return ["identity.surfaces: must be an object"]
    out = []
    if "default" not in s:
        out.append("identity.surfaces: has no 'default', so a surface it does not name has nothing to fall back to")
    for name, decl in s.items():
        if not name.startswith("_"):
            out += _check(Path(root), name, decl)
    return out
