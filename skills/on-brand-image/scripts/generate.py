#!/usr/bin/env python3
"""
generate.py — the framework's PROVIDER ADAPTER. The single generate path.

Every image in an Agentic Story universe/pack goes through here, and it CANNOT
produce an image without also writing its recipe. Provenance is not a separate
step you remember at lock time; it is a side effect of generating. This closes
the gap where candidate renders (everything before a lock) had no provenance.

On success it writes, beside the output, `<output>.recipe.json`:
  { provider, model, prompt, specVersion, stylePack?, refs:[{path}], timestamp, sha256 }
This is the SAME recipe shape `shoot-references` freezes and `compose` emits, so a
generated candidate is already lock-ready and `lint-universe`-auditable.

Skills (on-brand-image, shoot-references, compose) call THIS, never the raw model
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

GPT  = os.path.expanduser("~/.agents/skills/chatgpt-images/scripts/generate_image.py")
NANO = os.path.expanduser("~/.claude/skills/nano-banana-pro/scripts/generate_image.py")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(65536), b""):
            h.update(b)
    return h.hexdigest()

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
    ap.add_argument("--lookbook", default="")
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

    prompt = open(a.prompt_file).read() if a.prompt_file else a.prompt
    if not prompt:
        sys.exit("generate.py: need --prompt or --prompt-file")
    for r in a.ref:
        if not os.path.exists(os.path.expanduser(r)):
            sys.exit(f"generate.py: ref not found: {r}  (the look IS the references; a missing one silently degrades the render)")

    out = os.path.abspath(a.out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    if a.model.startswith("nano"):
        cmd = ["uv", "run", NANO, "--prompt", prompt, "--filename", out, "--resolution", "2K"]
    else:
        cmd = ["uv", "run", GPT, "--prompt", prompt, "--filename", out,
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
    if a.style_pack:
        recipe["stylePack"] = a.style_pack
    if a.lookbook:
        recipe["lookbook"] = a.lookbook
    with open(out + ".recipe.json", "w") as f:
        json.dump(recipe, f, indent=2)
    print(f"[generate] {os.path.basename(out)} + {os.path.basename(out)}.recipe.json  (provenance written)")

if __name__ == "__main__":
    main()
