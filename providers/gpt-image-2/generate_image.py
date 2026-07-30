#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["openai>=2.48", "pillow"]
# ///
"""
Generate or edit images using OpenAI's gpt-image-2 model.

The openai FLOOR above is load-bearing, not tidiness. An unpinned `openai` let uv keep
reusing a months-old cached environment (openai 2.32.0), and that SDK version HANGS on a
multi-image `images.edit` call: the request goes out, the socket stays ESTABLISHED, and the
process sits at 0% CPU until the timeout fires, then burns a retry and does it again. The
same call on 2.48.0 returns in ~58s.

That failure is nasty because it looks like a slow API rather than a broken client, and the
instinct it provokes (raise --timeout) makes it strictly worse. If renders ever start
hanging with no error again, check the resolved SDK version FIRST:
    uv run --refresh <this script> ...
and if --refresh fixes it, raise the floor here rather than living on --refresh.
"""

import argparse
import base64
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


# --------------------------------------------------------------------------
# AUTO-INJECTED PROMPT GUARDS
#
# The rules themselves now live in prompt_guards.py, imported below, because
# `nano-banana-pro` is a SECOND generator that had NO guards at all: a rule kept
# here was invisible to it, so any render routed through it silently lost every
# guard. One definition, both generators.
#
# ADD A RULE TO prompt_guards.py, never here and never in a caller.
# --no-guards opts out for the rare deliberate case (a product shot OF a device,
# an exploded diagram).
# --------------------------------------------------------------------------

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_guards import apply_prompt_guards  # noqa: E402


def get_api_key(provided: str | None) -> str:
    key = provided or os.environ.get("OPENAI_API_KEY")
    if not key:
        print("Error: OPENAI_API_KEY not set. Pass --api-key or set the env var.")
        sys.exit(1)
    return key


def save_b64(b64: str, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(base64.b64decode(b64))
    print(f"Saved: {path}")


def write_recipe(path: Path, args, image_paths: list[str] | None) -> None:
    """Freeze the provenance recipe beside every generated asset.

    AGENTS.md non-negotiable: every generated asset carries its provenance recipe
    (model, exact prompt, every input by path). This used to be left to each caller,
    so most assets shipped with no recipe at all and the rule was unenforceable.
    Writing it here means no caller can forget it.

    ALWAYS REWRITES. The recipe must describe the bytes currently on disk, so when
    an asset is regenerated its sidecar is regenerated with it. The old
    skip-if-exists guard meant a re-roll overwrote the image and left provenance
    pointing at the DISCARDED one, which is worse than no recipe: it reads as
    audited while describing art nobody ever saw. That silently broke the single
    hottest path in the pipeline, since render-readback's whole contract is
    "on any DEFECT, regenerate that shot FROM SCRATCH" (found 2026-07-26 on the
    given-ark master, whose recipe still described a stone-looking first pass).
    Freezing provenance at APPROVAL is a locking step's job and not this
    function's: `abu lock-shot --recipe` snapshots the bytes' digests
    into the entity, and that frozen copy is what a divergence check reads.
    """
    recipe_path = path.with_suffix(path.suffix + ".recipe.json")
    recipe = {
        "asset": str(path),
        "model": args.model,
        "mode": "edit" if image_paths else "generate",
        "prompt": args.prompt,
        "inputs": [str(Path(p).resolve()) for p in (image_paths or [])],
        "size": args.size,
        "quality": args.quality,
        "background": args.background,
        "mask": str(args.mask) if args.mask else None,
        "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "generator": "chatgpt-images/scripts/generate_image.py",
    }
    try:
        recipe_path.write_text(json.dumps(recipe, indent=2) + "\n")
        print(f"Recipe: {recipe_path}")
    except OSError as e:
        # never fail a good render over its sidecar
        print(f"Warning: could not write recipe {recipe_path}: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate or edit images with OpenAI gpt-image-2")
    parser.add_argument("--prompt", required=True, help="Image description or editing instructions")
    parser.add_argument("--filename", required=True, help="Output file path (PNG)")
    parser.add_argument("--input-image", action="append", help="Path to input image for editing. Pass multiple --input-image flags for multi-reference editing with gpt-image-2 (e.g. one for face, one for style anchor).")
    parser.add_argument("--mask", help="Path to mask PNG for inpainting (DALL-E 2 only)")
    parser.add_argument("--model", default="gpt-image-2", help="Model: gpt-image-2 (default), gpt-image-1.5, gpt-image-1, gpt-image-1-mini, dall-e-3, dall-e-2")
    parser.add_argument("--size", default="1536x1024", help="Output size, e.g. 1024x1024, 1536x1024, 1024x1536")
    parser.add_argument("--quality", default="high", help="Quality: high (default), medium, low, auto")
    parser.add_argument("--background", default="auto", choices=["auto", "transparent", "opaque"],
                        help="Background: auto (default), transparent (PNG alpha, gpt-image models only), opaque. "
                             "Transparent requires medium/high quality.")
    parser.add_argument("--api-key", help="OpenAI API key (or set OPENAI_API_KEY env var)")
    parser.add_argument("--timeout", type=float, default=300.0,
                        help="Per-attempt HTTP timeout in seconds (default 300). The OpenAI SDK "
                             "defaults to 600s with 2 retries, so a stalled image call burns ~30 "
                             "minutes producing NO output and looking identical to slow-but-working.")
    parser.add_argument("--no-guards", dest="guards", action="store_false", default=True,
                        help="Skip the auto-injected prompt guards (device anatomy, readable "
                             "surfaces, no-UI). Only for a deliberate product shot OF a device or "
                             "an exploded diagram; the guards exist because callers forget them.")
    parser.add_argument("--max-retries", type=int, default=1,
                        help="Retries after the first attempt (default 1). SDK default is 2, which "
                             "triples worst-case wall time on a stall.")
    parser.add_argument("--open", dest="open", action="store_true", default=True,
                        help="Open the output in Preview after saving (macOS). On by default.")
    parser.add_argument("--no-open", dest="open", action="store_false",
                        help="Do NOT open Preview after saving. Use this in batch loops to avoid spawning many windows, then open the curated set yourself.")
    args = parser.parse_args()

    args.prompt, _guards = apply_prompt_guards(args.prompt, args.guards)
    if _guards:
        print(f"[guards] auto-appended: {', '.join(_guards)}", file=sys.stderr)


    from openai import OpenAI
    # EXPLICIT timeout + retry cap. Constructing OpenAI() bare inherits a 600s timeout
    # and 2 retries, so one stalled image call blocks for ~30 minutes while printing
    # nothing, which is indistinguishable from "slow but working" and cost a real
    # session 25+ idle minutes on 2026-07-26. Fail loudly and early instead.
    client = OpenAI(api_key=get_api_key(args.api_key),
                    timeout=args.timeout, max_retries=args.max_retries)
    print(f"[timeout {args.timeout:.0f}s/attempt, {args.max_retries} retr"
          f"{'y' if args.max_retries == 1 else 'ies'}]", flush=True)

    output_path = Path(args.filename)

    if args.input_image:
        image_paths = args.input_image  # list (action='append' produces a list)
        print(f"Editing with {len(image_paths)} reference image(s): {image_paths}", flush=True)
        files = [open(p, "rb") for p in image_paths]
        try:
            kwargs = dict(
                model=args.model,
                image=files if len(files) > 1 else files[0],
                prompt=args.prompt,
                size=args.size,
            )
            if args.background != "auto" and args.model.startswith("gpt-image-"):
                kwargs["background"] = args.background
            if args.mask:
                with open(args.mask, "rb") as mask_file:
                    kwargs["mask"] = mask_file
                    result = client.images.edit(**kwargs)
            else:
                result = client.images.edit(**kwargs)
        finally:
            for f in files:
                f.close()
    else:
        print(f"Generating image with {args.model}...", flush=True)
        generate_kwargs = dict(
            model=args.model,
            prompt=args.prompt,
            size=args.size,
            quality=args.quality,
            n=1,
        )
        if args.background != "auto" and args.model.startswith("gpt-image-"):
            generate_kwargs["background"] = args.background
        if not args.model.startswith("gpt-image-"):
            generate_kwargs["response_format"] = "b64_json"
        result = client.images.generate(**generate_kwargs)

    b64 = result.data[0].b64_json
    save_b64(b64, output_path)
    write_recipe(output_path, args, args.input_image)
    if args.open:
        subprocess.run(["open", str(output_path)], check=False)


if __name__ == "__main__":
    main()
