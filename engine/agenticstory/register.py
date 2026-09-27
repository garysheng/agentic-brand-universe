"""The ONE reader of a universe's register, for every tool that passes an anchor.

SPEC 4.7 lets `identity.register` source its `anchor`, `rejectedPoles` and
`anchorSubject` from a Style Pack (`identity.register.stylePack`) instead of
inlining them. The reference shooter learned that in v0.33; the spread compiler and
the cover compiler did not, so a universe declaring a pack and no inline anchor could
SHOOT its whole matrix and then not RENDER one spread ("no anchor:
identity.register.anchor is null"). Two implementations of one contract disagree
within a release; this module is the one both ends read (gap G22, issue #16).

Deliberately stdlib-only and exception-typed, so a script that turns every problem
into its own refusal type can wrap `RegisterError` without importing anything else.
"""
from __future__ import annotations

import json
from pathlib import Path


class RegisterError(ValueError):
    """The register cannot supply an anchor. The message says why and what to do."""


def pack_dir(spec: str) -> Path:
    """A pack is named by ID (`nof-soft-painterly`) or universe-relative PATH
    (`reference/style/nof-soft-painterly`); both resolve here."""
    return Path(spec) if "/" in spec else Path("reference") / "style" / spec


def load_style_pack(uroot: Path, spec: str, why: str) -> dict:
    """`{anchor, rejectedPoles, name, anchorSubject, pack}` from a Style Pack.

    `anchor` is returned UNIVERSE-RELATIVE (a pack's own `anchor` is relative to the
    pack dir), because every other path a compiler handles is universe-relative.
    """
    uroot = Path(uroot)
    rel = pack_dir(spec)
    pf = uroot / rel / "pack.json"
    if not pf.exists():
        raise RegisterError(f"{why}: no Style Pack at {pf}")
    try:
        pack = json.loads(pf.read_text())
    except (OSError, ValueError) as e:
        raise RegisterError(f"{why}: {pf} is not readable JSON ({e})")
    a = pack.get("anchor")
    if not a:
        raise RegisterError(f"{why}: {pf} declares no anchor")
    anchor = str(rel / a)
    if not (uroot / anchor).exists():
        raise RegisterError(f"{why}: anchor not on disk: {uroot / anchor}")
    return {
        "anchor": anchor,
        "rejectedPoles": list(pack.get("rejectedPoles") or []),
        "name": pack.get("styleLine") or pack.get("name") or pack.get("id") or Path(spec).name,
        "anchorSubject": pack.get("anchorSubject"),
        "pack": spec,
    }


def render_register(uroot: Path, uni: dict) -> dict:
    """The register a RENDER passes: `{anchor, rejectedPoles, name, anchorSubject, pack}`.

    * inline `anchor` declared: it wins, exactly as every render has always read it.
      (A universe declaring BOTH is left on its inline anchor here; the shooter refuses
      that ambiguity because a sparse shoot returns an anchor's subject wholesale, while
      a render is dense and its canon renders already agree on the inline one.)
    * no inline anchor, `stylePack` declared: the pack IS the register (SPEC 4.7).
      Inline `rejectedPoles` / `anchorSubject`, when present, still win over the
      pack's, since they are the universe speaking about itself.
    * neither: RegisterError, naming both ways to lock the style.
    """
    reg = ((uni or {}).get("identity") or {}).get("register") or {}
    anchor, spec = reg.get("anchor"), reg.get("stylePack")
    if anchor:
        return {"anchor": anchor, "rejectedPoles": list(reg.get("rejectedPoles") or []),
                "name": reg.get("name"), "anchorSubject": reg.get("anchorSubject"),
                "pack": None}
    if spec:
        got = load_style_pack(uroot, spec, f"identity.register.stylePack {spec!r}")
        if reg.get("rejectedPoles"):
            got["rejectedPoles"] = list(reg["rejectedPoles"])
        if reg.get("anchorSubject"):
            got["anchorSubject"] = reg["anchorSubject"]
        if reg.get("name"):
            got["name"] = reg["name"]
        return got
    raise RegisterError(
        "identity.register declares neither an `anchor` nor a `stylePack`: the universe "
        "style is not locked. Set identity.register.stylePack to a Style Pack (SPEC 4.7) "
        "or identity.register.anchor to a content-neutral image.")
