#!/usr/bin/env python3
"""works_board.py — put a batch of WORKS in front of the operator, one batch per page, and record
what they decide about each one (SPEC v0.52, §3.5.1).

WHY THIS EXISTS. The shot board (`shoot-references/scripts/shot_board.py`) is per ENTITY: it
reads one entity's reference folder and approves plates before a lock. A batch of works is a
different shape. Fifty-seven wiki heroes, a set of covers, a run of share cards: each is a
finished candidate with a title, a line saying what it is for, and a recipe that can re-roll it.
Until this board, every such batch was reviewed through a hand-built page per run (2026-09-24 and
2026-09-25 each grew their own), so the verdicts lived in whatever file that page happened to
write and nothing in ABU could read them back.

THE INPUT IS A MANIFEST, and the manifest shape is deliberately loose, because every batch that
already exists wrote its own: a JSON list, or an object holding the list under `items`, `works`,
`heroes`, `slots` or `entries`. Per item it reads the image from `image`/`out`/`path`/`file`, the
title from `title`/`name`/`id`, the context line from `context`/`argues`/`caption`/`description`,
the recipe from `recipe` (else `<image>.recipe.json`) and an optional `batch`. Paths are tried
against the manifest's folder and then each folder above it, so `out` written relative to a
universe root resolves from a manifest two levels down.

ONE BATCH PER PAGE. Items group by their recorded `batch` when any item carries one, else in
manifest order by `--batch-size` (default 5, the size these batches are rendered and composed
in: a batch of five holds at most one desk shot, and the contact sheets are five to a sheet).

THE RECORD IS THE SHOT BOARD'S RECORD. Every write goes through `agenticstory.seen`, into the
`<image>.readback.json` sidecar beside each image: the board a picture was put on, the moment the
page served its bytes, and the verdict tapped against it. A works verdict and a shot verdict are
therefore the same fact in the same place, refused by the same six rules, and `lock-shot` could
read either. What a works board adds is the NOTE: typed or spoken, stored under `seen.note`,
transcript and audio path both, so an agent can re-roll from the recipe with the note applied.

WHAT NEVER GOES ON THE BOARD is decided by `agenticstory.candidates`: nothing under `rejected/`,
`superseded*/`, `candidates/` or `pre-reroll-*/`, and no earlier roll kept as `<slug>.rN.png`.
A manifest that points at one of those is refused for that item, by name, rather than boarded.

Verbs:

    works_board.py open <manifest> [--id ID] [--title T] [--batch-size 5] [--json] [--no-mount]
                        [--restamp]
        Register the board, stamp every current candidate that has no board yet (or whose bytes
        changed since, which is what a re-roll does), mount the page in the Freedom frapp store
        at a stable URL, and print the phone link to text the operator.

    works_board.py boards --json                  every open board, with its progress
    works_board.py batch <id> <n> --json          one batch page's items (the page's only read)
    works_board.py item <id> <key> --json         one item (the page's image route)
    works_board.py served <png> --digest <hex>    the PAGE calls this, from inside the response
    works_board.py tap <png> --verdict keep|reroll [--note TEXT] [--audio F ...]
    works_board.py status <id> [--json]           what is judged, what is not, what came back
    works_board.py rerolls <id> [--json]          every REROLL with its note, and the exact
                                                  `reroll-slot` command that applies it
    works_board.py close <id>                     take a finished board off the page
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _abu_root(start=None) -> Path:
    """Walk up for a marker, never count parents: this runs from a clone and a plugin cache."""
    p = Path(start or __file__).resolve()
    for c in [p, *p.parents]:
        if (c / "engine" / "agenticstory").is_dir():
            return c
    raise SystemExit("works_board: cannot locate the ABU root from " + str(p))


ABU = _abu_root()
sys.path.insert(0, str(ABU / "engine"))
from agenticstory import display  # noqa: E402
from agenticstory.candidates import why_not_candidate  # noqa: E402
from agenticstory.seen import (  # noqa: E402
    _read_doc, _write_doc, digest, read_seen, record_board, record_serve, record_tap,
    sidecar_path,
)

SLUG = "abu-works"             # the store slug, so the phone URL is the same for every board
SOURCE = "abu-works-board"     # the bus source every tap is announced under
FRAPP = HERE.parent / "frapps" / "works-board.mjs"
# The marketplace clone is updated IN PLACE by `/plugin update`; the plugin cache is versioned and
# the old version is pruned on the next update, and a worktree is swept when its branch lands.
MARKETPLACE_FRAPP = (Path.home() / ".claude" / "plugins" / "marketplaces" / "agentic-brand-universe"
                     / "skills" / "approve-works" / "frapps" / "works-board.mjs")


def mount_file(env=None) -> Path:
    """The page file the store should import: one that will still exist after the next update.

    The store keeps the path it was given. A mount made from the versioned plugin cache or from a
    worktree works until an update prunes that directory or the branch lands, and then the phone
    link dies with nothing reporting it (2026-09-25, when the first board was mounted from a
    worktree). `ABU_WORKS_FRAPP` overrides, for iterating on the page itself.
    """
    env = os.environ if env is None else env
    if env.get("ABU_WORKS_FRAPP"):
        return Path(env["ABU_WORKS_FRAPP"]).expanduser().resolve()
    if MARKETPLACE_FRAPP.is_file():
        return MARKETPLACE_FRAPP
    return FRAPP
MOUNT = HERE.parent / "frapps" / "mount.mjs"
REROLL = ABU / "skills" / "reroll-slot" / "scripts" / "reroll_from_recipe.py"

LIST_KEYS = ("items", "works", "heroes", "slots", "entries")
IMAGE_KEYS = ("image", "out", "path", "file")
TITLE_KEYS = ("title", "name", "id")
CONTEXT_KEYS = ("context", "argues", "caption", "description")
DEFAULT_BATCH = 5

KEEP, REROLL_V = "keep", "reroll"
OPTIONS = [KEEP, REROLL_V]
LABELS = ["Approve", "Re-roll"]

# A re-roll with no note is legitimate for a work: "roll it again as it was" is what
# `reroll-slot` does with no `--note`. The engine refuses a reroll with no reason, correctly,
# so the reason is written as what it is, never invented.
NOTELESS = "no note: roll again from the same recipe"


def state_dir() -> Path:
    return Path(os.environ.get("ABU_WORKS_BOARDS")
                or Path.home() / ".freedom" / "frapps" / "abu-works-board")


def boards_dir() -> Path:
    return state_dir() / "boards"


def _now() -> str:
    return _dt.datetime.now().isoformat(timespec="seconds")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(s).lower()).strip("-")
    return s[:60] or "item"


# ── the manifest ────────────────────────────────────────────────────────────────────────────

def load_manifest(path: Path) -> tuple[list[dict], dict]:
    """The item list and the document around it. Refuses a manifest with no list it knows."""
    doc = json.loads(Path(path).read_text())
    if isinstance(doc, list):
        return doc, {}
    for k in LIST_KEYS:
        if isinstance(doc.get(k), list):
            return doc[k], doc
    raise ValueError(f"{path}: no item list. A works manifest is a JSON list, or an object with "
                     f"the list under one of {list(LIST_KEYS)}.")


def _first(item: dict, keys) -> str:
    for k in keys:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""


def resolve_path(rel: str, manifest: Path) -> Path | None:
    """`rel` against the manifest's folder, then each folder above it. None when nowhere."""
    p = Path(rel).expanduser()
    if p.is_absolute():
        return p if p.exists() else None
    for base in [manifest.parent, *manifest.parent.parents][:8]:
        cand = base / p
        if cand.exists():
            return cand.resolve()
    return None


def _take(img: Path) -> int:
    """Which take this is: earlier rolls kept as `.rN` and set-aside rolls in `rejected/`."""
    stem = img.name.rsplit(".", 1)[0]
    n = 1
    try:
        n += sum(1 for f in img.parent.iterdir()
                 if re.fullmatch(re.escape(stem) + r"\.r\d+\.(png|jpe?g|webp)", f.name, re.I))
    except OSError:
        pass
    try:
        n += sum(1 for f in (img.parent / "rejected").iterdir()
                 if f.name.startswith(stem + "-") and re.search(r"\.(png|jpe?g|webp)$", f.name, re.I))
    except OSError:
        pass
    return n


def items_of(manifest: Path, batch_size: int = DEFAULT_BATCH) -> tuple[list[dict], list[str]]:
    """Every boardable item, batched, and the refusals for the ones that are not.

    Each item is `{key, batch, image, title, context, recipe, index}`. A refusal is a sentence
    naming the item and why it is not on the board.
    """
    manifest = Path(manifest).expanduser().resolve()
    raw, _ = load_manifest(manifest)
    out, refused, seen_keys = [], [], set()
    for i, it in enumerate(raw):
        if not isinstance(it, dict):
            refused.append(f"item {i + 1}: not an object")
            continue
        title = _first(it, TITLE_KEYS) or f"item {i + 1}"
        rel = _first(it, IMAGE_KEYS)
        if not rel:
            refused.append(f"{title}: no image (looked for {list(IMAGE_KEYS)})")
            continue
        img = resolve_path(rel, manifest)
        if img is None:
            refused.append(f"{title}: no file at {rel}")
            continue
        why = why_not_candidate(img, manifest.parent)
        if why:
            refused.append(f"{title}: {why}")
            continue
        rec = _first(it, ("recipe",))
        recipe = resolve_path(rec, manifest) if rec else Path(str(img) + ".recipe.json")
        key = slugify(it.get("id") or img.name.rsplit(".", 1)[0])
        while key in seen_keys:
            key += "-x"
        seen_keys.add(key)
        out.append({"key": key, "batchOf": it.get("batch"), "image": str(img), "title": title,
                    "context": _first(it, CONTEXT_KEYS),
                    "recipe": str(recipe) if recipe and Path(recipe).exists() else None,
                    "index": i})
    # ONE BATCH PER PAGE: the recorded batch when the manifest has one, else chunks in order.
    if any(o["batchOf"] not in (None, "") for o in out):
        order: list = []
        for o in out:
            b = o["batchOf"] if o["batchOf"] not in (None, "") else "unbatched"
            if b not in order:
                order.append(b)
            o["batch"] = order.index(b) + 1
    else:
        size = max(1, int(batch_size or DEFAULT_BATCH))
        for n, o in enumerate(out):
            o["batch"] = n // size + 1
    for o in out:
        o.pop("batchOf", None)
    return out, refused


# ── the board registry ──────────────────────────────────────────────────────────────────────

def board_path(bid: str) -> Path:
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", bid or ""):
        raise ValueError(f"not a board id: {bid!r}")
    return boards_dir() / f"{bid}.json"


def read_board(bid: str) -> dict:
    try:
        return json.loads(board_path(bid).read_text())
    except (OSError, ValueError):
        raise ValueError(f"no open board {bid!r}; open it with works_board.py open <manifest>")


def list_boards() -> list[dict]:
    try:
        files = sorted(boards_dir().glob("*.json"))
    except OSError:
        return []
    out = []
    for f in files:
        try:
            out.append(json.loads(f.read_text()))
        except (OSError, ValueError):
            continue
    return sorted(out, key=lambda b: b.get("openedOn", ""), reverse=True)


# ── what the page reads ─────────────────────────────────────────────────────────────────────

def _state(img: Path) -> dict:
    seen = read_seen(img)
    board = seen.get("board") or {}
    now = digest(img)
    boarded = bool(board) and (not board.get("digest") or board.get("digest") == now)
    verdict = seen.get("verdict") if boarded else None
    if verdict and seen.get("digest") and seen["digest"] != now:
        verdict = None
    note = seen.get("note") or {}
    return {"boarded": boarded, "verdict": verdict,
            "why": seen.get("why") if verdict else None,
            "note": note.get("text") if verdict else None,
            "audio": note.get("audio") if verdict else None,
            "served": bool((board.get("display") or {}).get("served")) if boarded else False,
            "on": seen.get("on") if verdict else None}


def _rendered(recipe: str | None) -> str:
    if not recipe:
        return ""
    try:
        r = json.loads(Path(recipe).read_text())
    except (OSError, ValueError):
        return ""
    return str(r.get("timestamp") or r.get("at") or r.get("generatedAt") or "")


def board_view(bid: str) -> dict:
    """The whole board as the page needs it: batches, items and their state, from disk."""
    b = read_board(bid)
    items, refused = items_of(Path(b["manifest"]), b.get("batchSize") or DEFAULT_BATCH)
    for it in items:
        img = Path(it["image"])
        it.update(_state(img))
        it["file"] = img.name
        it["take"] = _take(img)
        it["rendered"] = _rendered(it.get("recipe"))
    nb = max([i["batch"] for i in items] or [0])
    batches = []
    for n in range(1, nb + 1):
        these = [i for i in items if i["batch"] == n]
        batches.append({"n": n, "count": len(these),
                        "judged": sum(1 for i in these if i["verdict"]),
                        "kept": sum(1 for i in these if i["verdict"] == KEEP),
                        "rerolls": sum(1 for i in these if i["verdict"] == REROLL_V)})
    return {"id": bid, "title": b.get("title") or bid, "manifest": b["manifest"],
            "openedOn": b.get("openedOn"), "items": items, "batches": batches,
            "refused": refused,
            "judged": sum(1 for i in items if i["verdict"]), "total": len(items)}


def find_item(bid: str, key: str) -> dict:
    """One item by key, WITHOUT reading every sidecar: the page calls this once per image."""
    b = read_board(bid)
    items, _ = items_of(Path(b["manifest"]), b.get("batchSize") or DEFAULT_BATCH)
    for it in items:
        if it["key"] == key:
            return it
    raise ValueError(f"no item {key!r} on board {bid!r}")


# ── writes ──────────────────────────────────────────────────────────────────────────────────

def stamp(items: list[dict], bid: str, title: str, restamp: bool = False) -> dict:
    """Put every current candidate on its batch's board, unless it already is.

    A picture already boarded with the SAME bytes keeps its board and any verdict on it, so
    re-opening a board costs nothing and never erases a tap. A picture whose bytes changed (a
    re-roll wrote a new image at the same path) is boarded afresh, which `record_board` makes
    supersede the old verdict: the operator's yes to the old picture must not approve the new.
    """
    chan, why = display.resolve_channel()
    if chan != display.FRAPP:
        raise ValueError("a works board is a page that SHOWS the art, and this machine cannot "
                         "serve one: " + why)
    fresh = kept = 0
    for it in items:
        img = Path(it["image"])
        seen = read_seen(img)
        board = seen.get("board") or {}
        # --restamp shows an UNJUDGED picture afresh (its serve is forgotten); a verdict is never
        # thrown away by it, because that would erase the operator's tap.
        if (board and board.get("digest") == digest(img) and board.get("works") == bid
                and not (restamp and not seen.get("verdict"))):
            kept += 1
            continue
        rec = record_board(img, question=f"{it['title']} ({title}, batch {it['batch']})",
                           options=OPTIONS, labels=LABELS, board_id=f"{bid}-b{it['batch']:02d}",
                           shot=it["title"], display=display.pending(chan, why))
        doc = _read_doc(img)
        doc["seen"]["board"]["works"] = bid
        doc["seen"]["board"]["key"] = it["key"]
        _write_doc(img, doc)
        fresh += 1
    return {"fresh": fresh, "kept": kept}


def tap(img: Path, verdict: str, note: str = "", audio: list[str] | None = None) -> dict:
    """Record one verdict, and the note that came with it, beside the picture."""
    verdict = (verdict or "").strip().lower()
    note = (note or "").strip()
    if verdict not in OPTIONS:
        raise ValueError(f"a works board offers {OPTIONS}; {verdict!r} is not one of them")
    why = note or (NOTELESS if verdict == REROLL_V else "")
    seen = record_tap(img, verdict, why=why)
    doc = _read_doc(img)
    if note or audio:
        doc["seen"]["note"] = {"text": note, "audio": list(audio or []), "at": seen.get("on")}
    else:
        doc["seen"].pop("note", None)
    _write_doc(img, doc)
    return doc["seen"]


def reroll_command(img: str, note: str | None) -> str:
    cmd = ["python3", str(REROLL), img]
    if note:
        cmd += ["--note", note]
    return " ".join(shlex.quote(c) for c in cmd)


# ── mounting ────────────────────────────────────────────────────────────────────────────────

def mount(env=None) -> dict:
    """Mount the page in the Freedom frapp store at /abu-works/ and return its links."""
    node = display.node(env=env)
    if not node:
        return {"ok": False, "why": "no `node` on this machine"}
    try:
        r = subprocess.run([node, str(MOUNT), "--slug", SLUG, "--file", str(mount_file(env))],
                           capture_output=True, text=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired) as e:
        return {"ok": False, "why": f"could not run the mount: {e}"}
    try:
        return json.loads(r.stdout.strip().splitlines()[-1])
    except (ValueError, IndexError):
        return {"ok": False, "why": (r.stderr or r.stdout or "no output").strip()[-600:]}


def with_path(url: str | None, path: str) -> str | None:
    """`https://host/abu-works/?k=K` -> `https://host/abu-works/<path>?k=K`."""
    if not url:
        return None
    base, _, q = url.partition("?")
    return base.rstrip("/") + "/" + path.lstrip("/") + ("?" + q if q else "")


# ── verbs ───────────────────────────────────────────────────────────────────────────────────

def cmd_open(a) -> int:
    manifest = Path(a.manifest).expanduser().resolve()
    if not manifest.is_file():
        print(f"works-board: no manifest at {manifest}", file=sys.stderr)
        return 2
    bid = slugify(a.id) if a.id else slugify(manifest.parent.name)
    try:
        items, refused = items_of(manifest, a.batch_size)
    except (ValueError, OSError) as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    if not items:
        print("works-board: nothing to board.\n  " + "\n  ".join(refused), file=sys.stderr)
        return 2
    title = a.title or bid
    board_path(bid).parent.mkdir(parents=True, exist_ok=True)
    prior = {}
    try:
        prior = json.loads(board_path(bid).read_text())
    except (OSError, ValueError):
        pass
    board_path(bid).write_text(json.dumps({
        "id": bid, "title": title, "manifest": str(manifest),
        "batchSize": a.batch_size, "openedOn": prior.get("openedOn") or _now(),
        "reopenedOn": _now() if prior else None}, indent=2))
    try:
        counts = stamp(items, bid, title, restamp=a.restamp)
    except ValueError as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    links = {"ok": False, "why": "--no-mount"} if a.no_mount else mount()
    nb = max(i["batch"] for i in items)
    payload = {"board": bid, "title": title, "items": len(items), "batches": nb,
               "stamped": counts, "refused": refused, "mount": links,
               "phone": with_path(links.get("phone"), f"b/{bid}/1") if links.get("ok") else None,
               "mac": with_path(links.get("local"), f"b/{bid}/1") if links.get("ok") else None,
               "textIt": ("TEXT THE PHONE LINK with freedom:message-myself, without being asked. "
                          "Each tap is announced on the Freedom bus (kind `judged`, source "
                          f"`{SOURCE}`); read the verdicts with `works_board.py status {bid}` "
                          f"and apply the re-rolls with `works_board.py rerolls {bid}`.")}
    if a.json:
        print(json.dumps(payload, indent=2))
        return 0
    print(f"[works-board] {len(items)} work(s) on {nb} page(s) of {a.batch_size}, board `{bid}`.")
    print(f"  stamped {counts['fresh']} new, kept {counts['kept']} already on the board")
    for r in refused:
        print(f"  NOT BOARDED: {r}")
    if links.get("ok"):
        print(f"  phone:  {payload['phone'] or 'NOT AVAILABLE (run /freedom:set-up-frapps once)'}")
        print(f"  Mac:    {payload['mac']}")
    else:
        print(f"  NOT MOUNTED: {links.get('why')}")
    print("[works-board] " + payload["textIt"])
    return 0


def cmd_boards(a) -> int:
    out = []
    for b in list_boards():
        try:
            v = board_view(b["id"])
        except (ValueError, OSError, KeyError):
            continue
        out.append({k: v[k] for k in ("id", "title", "openedOn", "judged", "total")}
                   | {"batches": len(v["batches"])})
    print(json.dumps(out, indent=2) if a.json else
          "\n".join(f"{b['id']}: {b['judged']}/{b['total']} judged" for b in out) or "no boards")
    return 0


def cmd_batch(a) -> int:
    try:
        v = board_view(a.id)
    except (ValueError, OSError) as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    n = max(1, min(int(a.n), max(1, len(v["batches"]))))
    v["n"] = n
    v["items"] = [i for i in v["items"] if i["batch"] == n]
    print(json.dumps(v))
    return 0


def cmd_item(a) -> int:
    try:
        it = find_item(a.id, a.key)
    except (ValueError, OSError) as e:
        print(json.dumps({"ok": False, "error": str(e)}))
        return 2
    print(json.dumps(it))
    return 0


def cmd_served(a) -> int:
    try:
        disp = record_serve(Path(a.png).expanduser().resolve(), sent_digest=a.digest, url=a.url)
    except ValueError as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    print(f"[works-board] served {Path(a.png).name} ({disp.get('digest')})")
    return 0


def cmd_tap(a) -> int:
    img = Path(a.png).expanduser().resolve()
    if a.board and a.key:
        try:
            img = Path(find_item(a.board, a.key)["image"])
        except ValueError as e:
            print(f"works-board: {e}", file=sys.stderr)
            return 2
    try:
        seen = tap(img, a.verdict, note=a.note or "", audio=a.audio or [])
    except ValueError as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps({"ok": True, "image": str(img), "sidecar": str(sidecar_path(img)),
                          "verdict": seen["verdict"], "note": (seen.get("note") or {}).get("text")}))
        return 0
    print(f"[works-board] recorded {seen['verdict']} for {img.name}"
          + (f" ({seen['why']})" if seen.get("why") else ""))
    return 0


def cmd_status(a) -> int:
    try:
        v = board_view(a.id)
    except (ValueError, OSError) as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    if a.json:
        print(json.dumps(v, indent=2))
        return 0
    print(f"{v['title']}: {v['judged']}/{v['total']} judged")
    for b in v["batches"]:
        print(f"  batch {b['n']:>2}: {b['judged']}/{b['count']} judged, {b['kept']} approved, "
              f"{b['rerolls']} re-roll")
    for r in v["refused"]:
        print(f"  NOT BOARDED: {r}")
    return 0 if v["judged"] == v["total"] else 1


def cmd_rerolls(a) -> int:
    try:
        v = board_view(a.id)
    except (ValueError, OSError) as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    rows = [{"key": i["key"], "title": i["title"], "image": i["image"], "note": i["note"],
             "audio": i["audio"], "command": reroll_command(i["image"], i["note"])}
            for i in v["items"] if i["verdict"] == REROLL_V]
    if a.json:
        print(json.dumps(rows, indent=2))
        return 0
    for r in rows:
        print(f"# {r['title']}" + (f"  (note: {r['note']})" if r["note"] else "  (no note)"))
        print(r["command"])
    if rows:
        print(f"\n# then put the new rolls back on the page: works_board.py open {v['manifest']}")
    return 0


def cmd_close(a) -> int:
    try:
        board_path(a.id).unlink()
    except (OSError, ValueError) as e:
        print(f"works-board: {e}", file=sys.stderr)
        return 2
    print(f"[works-board] closed {a.id}; its verdicts stay in the sidecars")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    o = sub.add_parser("open", help="board a manifest of works and mount the page")
    o.add_argument("manifest")
    o.add_argument("--id", default=None, help="board id (default: the manifest's folder name)")
    o.add_argument("--title", default=None)
    o.add_argument("--batch-size", type=int, default=DEFAULT_BATCH)
    o.add_argument("--no-mount", action="store_true", help="stamp and register, do not mount")
    o.add_argument("--restamp", action="store_true",
                   help="board every UNJUDGED work afresh, forgetting its serve (after an agent's "
                        "own screenshot, so the record never claims the operator saw it)")
    o.add_argument("--json", action="store_true")

    b = sub.add_parser("boards", help="every open board")
    b.add_argument("--json", action="store_true")

    p = sub.add_parser("batch", help="one batch page's items, as JSON (the page's read)")
    p.add_argument("id")
    p.add_argument("n", type=int)
    p.add_argument("--json", action="store_true")

    i = sub.add_parser("item", help="one item by key, as JSON (the page's image route)")
    i.add_argument("id")
    i.add_argument("key")
    i.add_argument("--json", action="store_true")

    v = sub.add_parser("served", help="record that a picture's bytes went out (the page calls it)")
    v.add_argument("png")
    v.add_argument("--digest", default=None)
    v.add_argument("--url", default=None)

    t = sub.add_parser("tap", help="record one verdict and its note")
    t.add_argument("png", nargs="?", default="")
    t.add_argument("--board", default=None)
    t.add_argument("--key", default=None)
    t.add_argument("--verdict", required=True, choices=OPTIONS)
    t.add_argument("--note", default="")
    t.add_argument("--audio", action="append", default=[])
    t.add_argument("--json", action="store_true")

    s = sub.add_parser("status", help="what is judged and what is not")
    s.add_argument("id")
    s.add_argument("--json", action="store_true")

    r = sub.add_parser("rerolls", help="every re-roll with its note and the command to apply it")
    r.add_argument("id")
    r.add_argument("--json", action="store_true")

    c = sub.add_parser("close", help="take a board off the page (verdicts stay)")
    c.add_argument("id")

    a = ap.parse_args(argv)
    if a.cmd == "tap" and not a.png and not (a.board and a.key):
        ap.error("tap needs a <png>, or --board and --key")
    return {"open": cmd_open, "boards": cmd_boards, "batch": cmd_batch, "served": cmd_served,
            "tap": cmd_tap, "item": cmd_item, "status": cmd_status, "rerolls": cmd_rerolls,
            "close": cmd_close}[a.cmd](a)


if __name__ == "__main__":
    raise SystemExit(main())
