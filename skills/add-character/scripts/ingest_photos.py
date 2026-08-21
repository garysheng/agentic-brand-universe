#!/usr/bin/env python3
"""Pull the photos the operator just PASTED into the chat onto disk as an entity's photo stack.

WHY THIS EXISTS
---------------
`add-character` step 2 tells you to "collect a photo stack (aim for 8+ varied real
photos) into reference/<id>/photos/" and ships no way to do it. For a real person
those photos almost never start as files: the operator pastes them into the
conversation, because that is where a human has them. So every real-person build
hand-rolls a base64 scrape of the harness transcript, and the framework's own
demand goes unmet by the framework.

Hand-rolled three times in one session (nation-of-fire, 2026-08-21) for Clarence
Avant, for Rance's smiling references, and for a logo.

THE GUARD IS THE POINT, NOT THE EXTRACTION
------------------------------------------
The extraction is twenty lines. What earned this a script is what went wrong on
the second run: the transcript had not flushed yet, so "the most recent paste"
still resolved to the PREVIOUS person's photos, and four images of Clarence Avant
were written into Rance's photo stack. Nothing errored. A photo stack is passed to
every shot of a matrix, so that would have quietly rewritten one man's face with
another's, and the failure would have surfaced hours later as "this doesn't look
like him" with no trace back to the cause.

So this refuses, by content hash, to write an image that already lives in a
DIFFERENT entity's stack in the same universe. That single check is the difference
between a convenience and something safe to hand a stranger.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import sys
from pathlib import Path

EXT = {"image/jpeg": "jpg", "image/jpg": "jpg", "image/png": "png",
       "image/webp": "webp", "image/gif": "gif"}


def newest_transcript(explicit: str | None) -> Path:
    """The harness transcript to read. Newest by mtime unless one is named."""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            sys.exit(f"REFUSE: no transcript at {p}")
        return p
    root = Path.home() / ".claude" / "projects"
    if not root.is_dir():
        sys.exit(f"REFUSE: no harness transcripts at {root}. Pass --transcript.")
    files = sorted(root.rglob("*.jsonl"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not files:
        sys.exit(f"REFUSE: no .jsonl transcripts under {root}. Pass --transcript.")
    return files[0]


def user_image_batches(path: Path, scan: int):
    """Every user turn carrying images, newest first, as lists of (media_type, bytes)."""
    lines = path.read_text(errors="ignore").splitlines()
    out = []
    for line in reversed(lines[-scan:]):
        try:
            d = json.loads(line)
        except ValueError:
            continue
        msg = d.get("message") or {}
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        imgs = [b for b in content
                if isinstance(b, dict) and b.get("type") == "image" and b.get("source", {}).get("data")]
        if imgs:
            out.append([(b["source"].get("media_type", "image/jpeg"),
                         base64.b64decode(b["source"]["data"])) for b in imgs])
    return out


def existing_hashes(uroot: Path, skip_entity: str) -> dict[str, str]:
    """{sha256: owning-entity-id} for every photo already in the universe."""
    seen: dict[str, str] = {}
    refs = uroot / "reference"
    if not refs.is_dir():
        return seen
    for photos in refs.glob("*/photos"):
        owner = photos.parent.name
        if owner == skip_entity:
            continue
        for f in photos.iterdir():
            if f.is_file():
                seen[hashlib.sha256(f.read_bytes()).hexdigest()] = owner
    return seen


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("universe")
    ap.add_argument("entity", help="entity id, e.g. clarence-avant")
    ap.add_argument("--transcript", help="explicit .jsonl (default: newest under ~/.claude/projects)")
    ap.add_argument("--batch", type=int, default=1,
                    help="which paste back from the end (1 = most recent, default)")
    ap.add_argument("--scan", type=int, default=4000, help="transcript lines to scan back")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="write even if an image already belongs to another entity. Almost "
                         "always the wrong answer; see the module docstring.")
    a = ap.parse_args()

    uroot = Path(a.universe).expanduser().resolve()
    if not (uroot / "universe.json").exists():
        sys.exit(f"REFUSE: no universe.json at {uroot}")

    tpath = newest_transcript(a.transcript)
    batches = user_image_batches(tpath, a.scan)
    if not batches:
        sys.exit(f"REFUSE: no pasted images found in the last {a.scan} lines of {tpath.name}.")
    if a.batch > len(batches):
        sys.exit(f"REFUSE: only {len(batches)} image paste(s) found; --batch {a.batch} is past that.")
    batch = batches[a.batch - 1]

    owned = existing_hashes(uroot, a.entity)
    clashes = []
    for mt, raw in batch:
        h = hashlib.sha256(raw).hexdigest()
        if h in owned:
            clashes.append(owned[h])
    if clashes and not a.force:
        who = ", ".join(sorted(set(clashes)))
        sys.exit(
            f"REFUSE: {len(clashes)} of {len(batch)} image(s) in this paste already belong to "
            f"'{who}'.\n"
            "That almost always means the transcript has not flushed your newest paste yet, so\n"
            "this is still the PREVIOUS person's batch. Writing it would put one person's face\n"
            "into another's photo stack, which is passed to every shot of their matrix.\n"
            "Wait a moment and re-run, or pass --batch 2 to reach further back."
        )

    dest = uroot / "reference" / a.entity / "photos"
    start = 0
    if dest.is_dir():
        nums = [int(f.stem) for f in dest.iterdir() if f.stem.isdigit()]
        start = max(nums) if nums else 0

    print(f"transcript : {tpath.name}")
    print(f"paste      : #{a.batch} of {len(batches)}, {len(batch)} image(s)")
    print(f"destination: reference/{a.entity}/photos/  (existing: {start})")
    if not a.dry_run:
        dest.mkdir(parents=True, exist_ok=True)
    for i, (mt, raw) in enumerate(batch, 1):
        name = f"{start + i:02d}.{EXT.get(mt, 'jpg')}"
        print(f"  {'would write' if a.dry_run else 'wrote'} {name}  {len(raw) // 1024}KB")
        if not a.dry_run:
            (dest / name).write_bytes(raw)
    if a.dry_run:
        print("\ndry run; nothing written. Re-run without --dry-run to apply.")
    else:
        print(f"\n{len(batch)} photo(s) in reference/{a.entity}/photos/. "
              "Pass them to add-entity with --photo, then shoot-references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
