#!/usr/bin/env python3
"""
generate.py — the framework's PROVIDER ADAPTER. The single generate path.

Every image in an Agentic Story universe/pack goes through here, and it CANNOT
produce an image without also writing its recipe. Provenance is not a separate
step you remember at lock time; it is a side effect of generating. This closes
the gap where candidate renders (everything before a lock) had no provenance.

On success it writes, beside the output, `<output>.recipe.json`:
  { provider, model, prompt, specVersion, stylePack?, refs:[{path}], timestamp, sha256 }
This is the SAME recipe shape `lock-references` freezes and `compose` emits, so a
generated candidate is already lock-ready and `lint-universe`-auditable.

Skills (on-brand-image, lock-references, compose) call THIS, never the raw model
script. Providers today: gpt-image-2 (chatgpt-images), nano-banana-pro.

Usage:
  python3 generate.py --out <path.png> --prompt "..." [--prompt-file f] \\
    --ref <a.png> [--ref ...] [--model gpt-image-2|nano-banana-pro] \\
    [--size 1536x1024] [--quality high] [--spec-version 0.6] [--style-pack <id-or-path>]
"""
import argparse, json, os, subprocess, sys, hashlib, datetime

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
    for r in a.ref:
        cmd += ["--input-image", os.path.expanduser(r)]

    if subprocess.run(cmd).returncode != 0 or not os.path.exists(out):
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
    with open(out + ".recipe.json", "w") as f:
        json.dump(recipe, f, indent=2)
    print(f"[generate] {os.path.basename(out)} + {os.path.basename(out)}.recipe.json  (provenance written)")

if __name__ == "__main__":
    main()
