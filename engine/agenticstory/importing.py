"""Bringing an asset made OUTSIDE this universe INTO it, with its provenance intact.

A universe absorbs assets it did not generate. It happens constantly: a retired brand
repo is folded in, a blessed render is cut out of a product repo and installed as a
photo-stack reference, a client hands over photographs. Until v0.21 the framework had no
verb for it, and every path available was a lie or a hand-roll:

  * `backfill-provenance` classifies an unrecipe'd image as `source` ("there is no
    generating call to record"), `reconstructed`, `attested` ("nothing about the
    generating call survives") or `deterministic`. For a CROP of a known gpt-image-2
    render whose source hash, crop box and original prompt are all in hand, every one of
    those four is false. Recording a knowable fact as unknowable is the exact failure
    that module was written to prevent, pointed the other way.
  * Writing the `.recipe.json` by hand is provenance saved by memory, which the provider
    adapter exists to abolish.

So: `abu import-asset` copies the file in and writes the recipe as a SIDE EFFECT of the
copy, the same way `generate.py` writes one as a side effect of generating. It adds one
provenance class, `derived`, whose whole content is the chain: where the bytes came from,
what was done to them, and (when known) the call that made the SOURCE.

`derived` is deliberately NOT `unrecorded`. The generating call is recorded; it simply
happened in another repo, and this asset is a stated transform of its output. That is a
stronger claim than `attested` and a different one from `reconstructed`, which recovers a
prompt for an asset generated HERE.

Manifest mode exists because these arrive in batches (a twelve-crop photo stack cut from
one source repo in one sitting) and twelve hand-typed invocations is the hand-roll wearing
a different hat.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

RECIPE_SUFFIX = ".recipe.json"
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()


class ImportRefusal(Exception):
    """A refusal to import. Always about a fact that is missing or wrong, never style."""


def _norm_derived_from(d: dict | None, src: Path, default_repo: str | None) -> dict | None:
    if not d:
        return None
    out = dict(d)
    if default_repo and not out.get("repo"):
        out["repo"] = default_repo
    # A 16-char prefix is what a hand-cut manifest usually carries; keep it under its own
    # key rather than pretending it is a full digest, so nothing downstream compares a
    # prefix to a digest and calls them different.
    if out.get("sha256") and len(str(out["sha256"])) < 64:
        out["sha256_16"] = out.pop("sha256")
    return out


def build_record(dst: Path, src: Path, *, spec_version: str,
                 provenance: str = "derived",
                 derived_from: dict | None = None,
                 transform: dict | None = None,
                 prompt: str | None = None,
                 blessed_by: str | None = None,
                 note: str | None = None,
                 default_repo: str | None = None) -> dict:
    """The recipe for one imported asset. Pure; writes nothing."""
    if provenance not in ("derived", "source"):
        raise ImportRefusal(
            f"provenance must be 'derived' (a stated transform of a known asset) or "
            f"'source' (an original input, e.g. a photograph), got {provenance!r}")
    df = _norm_derived_from(derived_from, src, default_repo)
    if provenance == "derived" and not df:
        raise ImportRefusal(
            "a 'derived' import must say what it is derived FROM (--from-repo/--from-path/"
            "--from-sha, or a manifest item's derivedFrom). An import with no chain is not "
            "provenance; use --provenance source if it genuinely has no antecedent.")
    rec: dict = {
        "asset": str(dst),
        "provenance": provenance,
        "unrecorded": False,
        "imported": True,
        "specVersion": spec_version,
        "sha256": sha256(dst),
        "generator": "abu import-asset",
        "importedFrom": str(src),
        "note": note or {
            "derived": "Imported from outside this universe. The bytes are a stated "
                       "transform of a known asset; `derivedFrom` records that asset and "
                       "the call that made it, so the chain is auditable across repos.",
            "source": "Imported from outside this universe as an ORIGINAL input (not "
                      "generated output). There is no generating call to record.",
        }[provenance],
    }
    if df:
        rec["derivedFrom"] = df
    if transform:
        rec["transform"] = transform
    if prompt:
        # The prompt that made the SOURCE, not this file. Named so nothing mistakes it
        # for a call that produced these exact bytes.
        rec["sourcePrompt"] = prompt
    if blessed_by:
        rec["blessedBy"] = blessed_by
    return rec


def import_one(universe: Path, src: Path, dest_rel: str, *, spec_version: str,
               force: bool = False, **kw) -> dict:
    """Copy ONE asset in and write its recipe beside it. Returns the record."""
    universe = Path(universe).expanduser().resolve()
    src = Path(src).expanduser()
    if not src.is_file():
        raise ImportRefusal(f"source is not a file: {src}")
    dst = (universe / dest_rel).resolve()
    if universe not in dst.parents:
        raise ImportRefusal(
            f"destination {dest_rel} lands outside the universe. A universe is "
            f"SELF-CONTAINED: every referenced asset resolves under assetRoot.")
    if dst.exists() and not force:
        raise ImportRefusal(f"{dest_rel} already exists (pass --force to overwrite)")
    dst.parent.mkdir(parents=True, exist_ok=True)

    # PERFORM THE CROP, OR REFUSE TO CLAIM IT (v0.29).
    #
    # This used to `shutil.copy2` unconditionally while `build_record` wrote
    # `transform.crop` into the recipe from the caller's argument. The bytes were the
    # untouched original and the provenance asserted an edit that never happened, which
    # is strictly worse than recording nothing: a false record passes an audit. Found on
    # 2026-08-01, where a plate's recipe claimed crop [824,25,1638,1112] and the file was
    # the full uncropped original.
    #
    # A crop is now applied or the import REFUSES. It never silently degrades to a copy,
    # because a silent degrade is exactly how the false record got written.
    crop = (kw.get("transform") or {}).get("crop")
    if crop:
        if len(crop) != 4:
            raise ImportRefusal(
                f"transform.crop must be [x0,y0,x1,y1]; got {crop!r}")
        try:
            from PIL import Image
        except ImportError:
            raise ImportRefusal(
                "transform.crop was requested but Pillow is not installed, so the crop "
                "cannot be performed. Refusing rather than copying the original and "
                "recording a crop that did not happen: a recipe that asserts an edit it "
                "never made is worse than one that records nothing.")
        try:
            with Image.open(src) as im:
                x0, y0, x1, y1 = (int(v) for v in crop)
                if not (0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height):
                    raise ImportRefusal(
                        f"crop {crop} does not fit inside the source image "
                        f"({im.width}x{im.height})")
                im.crop((x0, y0, x1, y1)).save(dst)
        except ImportRefusal:
            raise
        except Exception as e:
            raise ImportRefusal(f"could not crop {src}: {e}")
    else:
        shutil.copy2(src, dst)

    rec = build_record(dst, src, spec_version=spec_version, **kw)
    (dst.parent / (dst.name + RECIPE_SUFFIX)).write_text(json.dumps(rec, indent=2) + "\n")
    return rec


def load_manifest(path: Path) -> dict:
    """An import manifest: a batch of items sharing a source repo.

        {
          "sourceRepo": "<label, e.g. a repo name; per-item derivedFrom.repo wins>",
          "dest": "<optional universe-relative directory for every item>",
          "items": [
            {"file": "crops/face-3q.png",        // relative to the MANIFEST, or absolute
             "as": "face-3q.png",                // optional destination name
             "provenance": "derived",            // default: derived
             "derivedFrom": {"repo","path","sha256","dimensions"},
             "cropBox": [x0,y0,x1,y1],           // sugar for transform.crop
             "transform": {...},                 // anything else done to the bytes
             "generator": "gpt-image-2",         // what made the SOURCE
             "prompt": "…" | "promptKey": "…",   // the SOURCE's prompt, or a key into --prompts
             "blessedBy": "…", "note": "…"}
          ]
        }
    """
    path = Path(path).expanduser().resolve()
    try:
        m = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as e:
        raise ImportRefusal(f"cannot read manifest {path}: {e}")
    if not isinstance(m, dict) or not isinstance(m.get("items"), list) or not m["items"]:
        raise ImportRefusal(f"{path}: a manifest needs a non-empty `items` array")
    m["_dir"] = str(path.parent)
    return m


def import_manifest(universe: Path, manifest: Path, *, spec_version: str,
                    dest: str | None = None, prompts: Path | None = None,
                    force: bool = False, dry_run: bool = False) -> dict:
    """Import every item in a manifest. Refuses the WHOLE batch before copying anything.

    Fail-closed on the batch, not per item: half an imported photo stack is worse than
    none, because the entity then declares a stack whose provenance is inconsistent and
    nothing says which half is which.
    """
    m = load_manifest(manifest)
    mdir = Path(m["_dir"])
    default_repo = m.get("sourceRepo")
    dest_dir = dest or m.get("dest")
    prompt_map: dict = {}
    if prompts:
        try:
            prompt_map = json.loads(Path(prompts).expanduser().read_text())
        except (OSError, json.JSONDecodeError) as e:
            raise ImportRefusal(f"cannot read prompts file {prompts}: {e}")

    planned = []
    for i, it in enumerate(m["items"]):
        f = it.get("file")
        if not f:
            raise ImportRefusal(f"manifest item {i} has no `file`")
        src = Path(f)
        if not src.is_absolute():
            src = mdir / f
        if not src.is_file():
            raise ImportRefusal(f"manifest item {i}: source not on disk: {src}")
        name = it.get("as") or src.name
        rel = str(Path(dest_dir) / name) if dest_dir else name
        transform = dict(it.get("transform") or {})
        if it.get("cropBox"):
            transform["crop"] = it["cropBox"]
        prompt = it.get("prompt")
        key = it.get("promptKey") or ((it.get("derivedFrom") or {}).get("path"))
        if not prompt and prompt_map:
            # A key may name the source path or its stem, because a prompt archive is
            # normally keyed by the thing it generated rather than by where it landed.
            for cand in filter(None, [it.get("promptKey"), key,
                                      Path(key).stem if key else None]):
                if cand in prompt_map:
                    prompt = prompt_map[cand]
                    break
        df = it.get("derivedFrom")
        prov = it.get("provenance", "derived")
        # Build the record against the SOURCE path now so a refusal (a `derived` item
        # with no chain) fires before any bytes are copied.
        if prov == "derived" and not df:
            raise ImportRefusal(
                f"manifest item {i} ({name}) is 'derived' but declares no `derivedFrom`")
        planned.append({
            "src": src, "rel": rel, "provenance": prov, "derivedFrom": df,
            "transform": transform or None, "prompt": prompt,
            "blessedBy": it.get("blessedBy"), "note": it.get("note"),
            "generator": it.get("generator"),
        })

    if dry_run:
        return {"universe": str(universe), "planned": len(planned),
                "items": [{"from": str(p["src"]), "to": p["rel"],
                           "provenance": p["provenance"],
                           "hasPrompt": bool(p["prompt"])} for p in planned],
                "written": 0}

    written = []
    for p in planned:
        df = dict(p["derivedFrom"] or {})
        if p["generator"] and not df.get("generator"):
            df["generator"] = p["generator"]
        rec = import_one(universe, p["src"], p["rel"], spec_version=spec_version,
                         force=force, provenance=p["provenance"],
                         derived_from=df or None, transform=p["transform"],
                         prompt=p["prompt"], blessed_by=p["blessedBy"],
                         note=p["note"], default_repo=default_repo)
        written.append(rec)
    return {"universe": str(universe), "planned": len(planned),
            "written": len(written), "items": [r["asset"] for r in written],
            "withSourcePrompt": sum(1 for r in written if r.get("sourcePrompt"))}
