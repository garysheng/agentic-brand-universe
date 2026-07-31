#!/usr/bin/env python3
"""
generate.py — the framework's PROVIDER ADAPTER. The single generate path.

Every image in an Agentic Brand Universe/pack goes through here, and it CANNOT
produce an image without also writing its recipe. Provenance is not a separate
step you remember at lock time; it is a side effect of generating. This closes
the gap where candidate renders (everything before a lock) had no provenance.

On success it writes, beside the output, `<output>.recipe.json`:
  { provider, model, prompt, specVersion, stylePack?, refs:[{path}], timestamp, sha256 }
This is the SAME recipe shape `shoot-references` freezes and `compose-spread` emits, so
a generated candidate is already lock-ready and `lint-universe`-auditable.

Skills (on-brand-image, shoot-references, compose-spread) call THIS, never the raw model
script. Providers today: gpt-image-2 (chatgpt-images), nano-banana-pro.

Usage:
  python3 generate.py --out <path.png> --prompt "..." [--prompt-file f] \\
    --ref <a.png> [--ref ...] [--model gpt-image-2|nano-banana-pro] \\
    [--size 1536x1024] [--quality high] [--spec-version 0.6] [--style-pack <id-or-path>] \\
    [--timeout 900]   # raise when fanning out; parallel renders queue and time out at the default
"""
import argparse, json, os, subprocess, sys, hashlib, datetime, tempfile, shutil


def shrink_ref(path, max_edge, tmpdir):
    """A reference downscaled for upload. Returns `path` unchanged if it is already small
    enough, if shrinking is disabled, or if Pillow is unavailable (never fail a render over
    an optimization). Alpha is preserved, because a cut-out mark passed as a reference has
    a transparent background and flattening it onto white would teach the model a box."""
    if not max_edge or not tmpdir:
        return path
    try:
        from PIL import Image
    except ImportError:
        return path
    try:
        with Image.open(path) as im:
            if max(im.size) <= max_edge:
                return path
            im = im.copy()
            im.thumbnail((max_edge, max_edge), Image.LANCZOS)
            # Keep alpha lossless; send everything else as JPEG. Re-encoding a downscaled
            # illustration as PNG barely helps (PNG is built for flat color, not painted
            # gradients) and leaves the payload an order of magnitude bigger than it needs
            # to be. Quality 90 is indistinguishable at reference duty.
            has_alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
            stem = os.path.splitext(os.path.basename(path))[0]
            n = len(os.listdir(tmpdir))
            if has_alpha:
                dst = os.path.join(tmpdir, f"{n}-{stem}.png")
                im.save(dst)
            else:
                dst = os.path.join(tmpdir, f"{n}-{stem}.jpg")
                im.convert("RGB").save(dst, quality=90, optimize=True)
            return dst
    except Exception:
        return path


def _abu_root(start=None):
    """The ABU root, found by walking UP for a marker instead of counting parents.

    A fixed `parents[N]` encodes one directory layout. This code runs from at least
    two: a git clone, and a plugin cache under ~/.claude/plugins. Counting worked in
    the clone and would fail silently or wrongly in the other, which is the class of
    bug that made the framework uninstallable in the first place."""
    from pathlib import Path as _PP
    p = _PP(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit(
        "abu: cannot locate the ABU root from " + str(p) + ".\n"
        "  Looked upward for engine/agenticstory. If ABU was installed as a plugin,\n"
        "  reinstall it: /plugin marketplace add garysheng/agentic-brand-universe")


def _engine_on_path():
    """This script lives at <repo>/skills/<name>/scripts/, so the repo root is 3 up.
    `.resolve()` first, because skills are installed by symlinking into
    ~/.claude/skills and an unresolved __file__ points outside the repo."""
    from pathlib import Path
    eng = str(_abu_root() / "engine")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    return eng


def provider_script(provider):
    """Resolved at CALL time rather than import time, so a machine with no
    nano-banana install can still render with gpt-image-2."""
    _engine_on_path()
    from agenticstory.providers import resolve_str
    return resolve_str(provider)


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

ENGINE = None  # resolved lazily by _engine_on_path(); see engine/agenticstory/providers.py


def resolve_entities(specs):
    """Resolve `UNIVERSE:ID[@LOOK]` specs to (refs, invariants, rules, meta).

    REFUSES the render on anything unresolvable. That refusal is the whole point:
    a render that silently proceeds without the subject's locked plates produces a
    plausible picture of the wrong person, which is far more expensive than a hard
    stop, because it passes review.
    """
    eng = _engine_on_path()
    try:
        from agenticstory.store import CanonStore
    except ImportError:
        sys.exit(f"generate.py: --entity needs the engine on disk at {eng}")

    refs, invariants, rules, meta = [], [], [], []
    for spec in specs:
        if ":" not in spec:
            sys.exit(f"generate.py: --entity wants UNIVERSE:ID[@LOOK], got {spec!r}")
        upath, _, rest = spec.rpartition(":")
        eid, _, look = rest.partition("@")
        look = look or None
        upath = os.path.expanduser(upath)

        store = CanonStore(upath)
        ent = store.entity(eid)
        if ent is None:
            sys.exit(f"generate.py: no entity {eid!r} in {upath}")
        try:
            sheets = ent.look_sheets(look)
        except ValueError as e:
            sys.exit(f"generate.py: {e}")
        if not sheets:
            sys.exit(f"generate.py: {eid}"
                     f"{'@' + look if look else ''} resolved ZERO reference sheets. "
                     f"Lock its art first; rendering a canon entity with no plates is "
                     f"exactly the drift this flag exists to prevent.")

        missing = []
        for key, rel in sorted(sheets.items()):
            p = os.path.normpath(os.path.join(str(store.asset_root), rel))
            if not os.path.exists(p):
                missing.append(f"{eid}.{key} -> {rel}")
            else:
                refs.append(p)
        if missing:
            sys.exit("generate.py: locked canon references are MISSING on disk:\n  "
                     + "\n  ".join(missing)
                     + "\nRefusing to render: the result would look fine and be off-canon.")

        invariants.extend(ent.look_invariants(look))
        r = ((ent.raw.get("prose") or {}).get("rules") or "").strip()
        if r:
            rules.append(r)
        meta.append({"universe": upath, "id": eid, "look": look,
                     "sheets": {k: v for k, v in sorted(sheets.items())}})
    # De-dupe, preserving order: two entities may legitimately share a plate.
    seen, uniq = set(), []
    for p in refs:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq, list(dict.fromkeys(invariants)), rules, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--prompt"); ap.add_argument("--prompt-file")
    ap.add_argument("--ref", action="append", default=[])
    ap.add_argument("--model", default="gpt-image-2")
    ap.add_argument("--size", default="1536x1024")
    ap.add_argument("--quality", default="high")
    ap.add_argument("--spec-version", default="0.6")
    ap.add_argument("--style-pack", default="")
    ap.add_argument("--permit", action="append", default=[], metavar="POLE",
                    help="Un-reject one of the style pack's rejectedPoles for THIS render "
                         "(case-insensitive substring, repeatable). Recorded in the recipe. "
                         "Refuses if it matches no pole, so a typo cannot silently do nothing.")
    ap.add_argument("--lookbook", default="")
    # RESOLVE CANON HERE, NOT IN THE CALLER'S HEAD.
    #
    # `canon-resolve` has always been a SKILL: a document instructing whoever is
    # rendering to look up an entity's locked sheets and pass them as --ref. A
    # document is a memory test, not a gate, and it was failed live and repeatedly
    # (gary-sheng-art `jesus`, 2026-07-27): seven batches were rendered passing a
    # hand-picked subset of the entity's plates, the canonical face never reached
    # the model, and the face drifted to the base model's bias every single time.
    # Nothing refused those renders, because nothing was checking.
    #
    # Format: --entity /path/to/universe:entity-id[@look]  (repeatable)
    # It resolves the entity's required sheets through the engine (honouring
    # altLooks, keepSheets, dropSheets and supersedes), prepends them as
    # references, bakes the entity's live invariants into the prompt as positives,
    # and REFUSES the render if a required sheet is missing from disk.
    ap.add_argument("--entity", action="append", default=[], metavar="UNIVERSE:ID[@LOOK]")
    # Per-attempt HTTP timeout, passed through to the gpt-image-2 script. Without this
    # a batch caller is stuck with that script's 300s default, which is fine for one
    # render and NOT fine under concurrency: parallel high-quality 1536x1024 requests
    # queue server-side and every one of them times out at once. Raise it when
    # fanning out. (Earned 2026-07-27: 16 of 18 Society plates died this way.)
    ap.add_argument("--timeout", type=float, default=0.0)
    # Longest edge a reference is uploaded at. A reference carries a LOOK, not detail:
    # nothing about a style anchor survives past ~1024px that changes the render. Uploading
    # masters instead is pure cost, and not a small one: a 6-reference call against full-size
    # 1536x1024 PNG spreads ships ~14MB per request, versus 1.2MB downscaled.
    # This is a throughput/cost knob. It is NOT the fix for renders that hang with no error;
    # that is a stale openai SDK in the uv cache, and generate_image.py pins a floor for it.
    # Set 0 to disable and upload references untouched.
    ap.add_argument("--ref-max-edge", type=int, default=1024)
    a = ap.parse_args()

    recipe_entities = []
    prompt = open(a.prompt_file).read() if a.prompt_file else a.prompt
    if not prompt:
        sys.exit("generate.py: need --prompt or --prompt-file")

    # ------------------------------------------------------------------
    # APPLY the style pack, do not merely record it.
    #
    # --style-pack used to write a label into the recipe and nothing else:
    # the style line was never prepended, the rejected poles were never added
    # as negatives, and the anchor was never uploaded. So a caller passing a
    # pack got a bare-prompt render that silently ignored the look, while the
    # recipe claimed the pack was used. That is worse than no support, because
    # the provenance asserts something untrue.
    #
    # The pack is the definition of the look, so the caller passes a SUBJECT
    # and this compiles the rest. Anchor goes FIRST (a reference outranks
    # words, and the anchor is the content-neutral one).
    # Earned 2026-07-27, first render in gary-sheng-art: an impressionist
    # landscape came back from a neo-expressionist pack, failing its own gate
    # on two assertions.
    # ------------------------------------------------------------------
    # --permit only has meaning against a pack's rejectedPoles. Passed without one it
    # used to be swallowed entirely, because every permit code path lives inside the
    # branch below. That is the same silent no-op the permit's own refusal exists to
    # prevent, so it refuses here instead.
    if a.permit and not a.style_pack:
        sys.exit("generate.py: --permit needs --style-pack. Permits lift a pole from a "
                 "pack's rejectedPoles, and with no pack there are no poles to lift.")

    if a.style_pack:
        pack_dir = os.path.expanduser(a.style_pack)
        pack_file = (pack_dir if pack_dir.endswith(".json")
                     else os.path.join(pack_dir, "pack.json"))
        if not os.path.exists(pack_file):
            sys.exit(f"generate.py: --style-pack has no pack.json: {pack_file}")
        pack_dir = os.path.dirname(pack_file)
        with open(pack_file) as fh:
            pack = json.load(fh)

        style_line = (pack.get("styleLine") or "").strip()
        rejected = [str(r) for r in pack.get("rejectedPoles", []) if r]

        # --permit un-rejects a named pole for THIS render only. A pack's poles are
        # its standing law, but a single work sometimes needs one lifted: a flyer
        # wants text in the field that a page hero must never have. Without this the
        # only ways through are editing the pack (changing the law for every future
        # render) or bypassing the pack (losing the style line, the anchor-first ref
        # order and the recipe). Both are worse than an explicit, recorded exception.
        #
        # Matching is case-insensitive substring, because a caller should be able to
        # say `--permit text` without quoting "any text" exactly. It is recorded in
        # the recipe: a render made under a permit must not be indistinguishable from
        # one that never needed it.
        permitted, lifted = [str(x).strip().lower() for x in (a.permit or [])], []
        if any(not t for t in permitted):
            # An empty permit is a substring of every pole, so the unmatched check
            # below would consider it matched and stay silent while lifting nothing.
            sys.exit("generate.py: --permit was given an empty value. A permit must name "
                     "the pole it lifts; an empty one silently lifts nothing.")
        if permitted:
            keep = []
            for r in rejected:
                if any(t and t in r.lower() for t in permitted):
                    lifted.append(r)
                else:
                    keep.append(r)
            unmatched = [t for t in permitted
                         if not any(t in r.lower() for r in rejected)]
            if unmatched:
                # Fail loudly. A permit that silently matches nothing reads as
                # "text is allowed now" while the negative is still in the prompt.
                sys.exit("generate.py: --permit matched no rejected pole in this pack: "
                         + ", ".join(unmatched)
                         + "\n  the pack's poles are: " + ", ".join(rejected))
            rejected = keep

        parts = [prompt.strip()]
        if style_line:
            parts.append(style_line)
        if rejected:
            parts.append("Do NOT render it in any of these styles: "
                         + ", ".join(rejected) + ".")
        prompt = "\n\n".join(parts)

        # Anchor first, then the rest of the pack's refs, then anything the
        # caller passed explicitly. Never duplicate a ref already given.
        pack_refs, seen = [], set()
        ordered = ([pack["anchor"]] if pack.get("anchor") else []) + list(pack.get("refs", []))
        for rel in ordered:
            p = rel if os.path.isabs(rel) else os.path.join(pack_dir, rel)
            p = os.path.normpath(p)
            if p in seen or not os.path.exists(p):
                continue
            seen.add(p)
            pack_refs.append(p)
        a.ref = pack_refs + [r for r in a.ref
                             if os.path.normpath(os.path.expanduser(r)) not in seen]
        if not pack_refs:
            sys.exit(f"generate.py: style pack {pack_file} resolved zero references. "
                     "The look IS the references; refusing to render a pack-less render "
                     "that would claim the pack in its recipe.")

    # ------------------------------------------------------------------
    # CANON RESOLUTION. Entity refs go in FRONT of everything, including the
    # style pack anchor: a style pack pulls hard toward its own faces, so the
    # subject's own plates must outrank it. Ordering the other way is how a pack
    # wins an argument it should never have been in.
    if a.entity:
        canon_refs, invariants, rules, resolved_meta = resolve_entities(a.entity)
        seen_now = {os.path.normpath(os.path.expanduser(r)) for r in a.ref}
        a.ref = [p for p in canon_refs
                 if os.path.normpath(p) not in seen_now] + a.ref
        blocks = []
        if invariants:
            blocks.append("These are LOCKED canonical traits of the subject(s). "
                          "They are not stylistic suggestions and must survive the "
                          "render exactly: " + "; ".join(invariants) + ".")
        blocks.extend(rules)
        if blocks:
            prompt = prompt.strip() + "\n\n" + "\n\n".join(blocks)
        recipe_entities = resolved_meta

    for r in a.ref:
        if not os.path.exists(os.path.expanduser(r)):
            sys.exit(f"generate.py: ref not found: {r}  (the look IS the references; a missing one silently degrades the render)")

    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if a.model.startswith("nano"):
        cmd = ["uv", "run", provider_script("nano-banana-pro"), "--prompt", prompt, "--filename", out, "--resolution", "2K"]
    else:
        cmd = ["uv", "run", provider_script("gpt-image-2"), "--prompt", prompt, "--filename", out,
               "--size", a.size, "--quality", a.quality, "--no-open"]
        if a.timeout:
            cmd += ["--timeout", str(a.timeout)]
    # Shrink references for UPLOAD ONLY. The recipe below still records every original
    # path, so provenance points at the real reference and never at a temp file.
    tmpdir = tempfile.mkdtemp(prefix="agenticstory-refs-") if a.ref_max_edge else None
    upload = [shrink_ref(os.path.expanduser(r), a.ref_max_edge, tmpdir) for r in a.ref]
    for u in upload:
        cmd += ["--input-image", u]

    try:
        failed = subprocess.run(cmd).returncode != 0 or not os.path.exists(out)
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)
    if failed:
        sys.exit("generate.py: generation FAILED — no image, no recipe")

    recipe = {
        "provider": a.model,
        "model": a.model,
        "prompt": prompt.strip(),
        "specVersion": a.spec_version,
        "refs": [{"path": r} for r in a.ref],
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sha256": sha256(out),
    }
    if recipe_entities:
        recipe["entities"] = recipe_entities
    if a.style_pack:
        recipe["stylePack"] = a.style_pack
        if lifted:
            recipe["permitted"] = lifted
    if a.lookbook:
        recipe["lookbook"] = a.lookbook
    with open(out + ".recipe.json", "w") as f:
        json.dump(recipe, f, indent=2)
    print(f"[generate] {os.path.basename(out)} + {os.path.basename(out)}.recipe.json  (provenance written)")

if __name__ == "__main__":
    main()
