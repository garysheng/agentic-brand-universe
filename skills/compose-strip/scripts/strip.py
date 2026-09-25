#!/usr/bin/env python3
# /// script
# dependencies = ["pillow"]
# ///
"""strip.py — compose a STRIP: two to four panels, each rendered through the entity route, read
back, re-rolled on a defect, then assembled in CODE into one image with ONE composite recipe that
a wiki's provenance gate accepts (SPEC v0.53, §4.15).

WHY THIS EXISTS. Four wiki-hero strips were built by hand on 2026-09-25, each from a long prose
brief, and each repeated the same steps: render a panel through `on-brand-image --entity`, read it
back, re-roll it, keep the rejects somewhere, crop the panels into a canvas with cream gutters in a
one-off `compose.py`, write a recipe, stamp the result on the works board. Every one of those
`compose.py` files wrote a recipe the supersuit.wiki provenance gate REFUSED: `provider: "code"`,
no prompt, no refs, no model, no timestamp the gate reads, and an asset path the gate cannot match.
They were fixed by hand in the wiki worktree. This script owns all of it, so a strip is a spec file
and a handful of verbs, and its recipe is right by construction.

THE SPLIT, AND WHY IT IS NOT ONE `run` VERB. Code does everything a machine can check: it
assembles each prompt from the spec's blocks, renders through the provider adapter (which writes
the panel's recipe), checks the canon binding with `verify_render.py`, counts rolls against the cap,
moves a rejected roll into `rejected/` with its reason, composes, validates the recipe, exports the
wiki copy and stages the board. The one thing it cannot do is LOOK. A panel is judged by an agent
reading the pixels (render-readback), and `judge` is where that verdict is recorded. A verb that
rendered, "judged" and composed in one go would be a verb that approves its own work.

Verbs (paths in the spec resolve against the universe; `out` against the spec's own folder):

    strip.py plan    <spec> [--json]                 validate the spec; per panel: prompt size, refs,
                                                      entities, rolls so far, and the next move
    strip.py prompt  <spec> --panel ID               print the exact prompt the next roll will send
    strip.py render  <spec> --panel ID [--dry-run]   one roll: generate.py, then the binding check
    strip.py judge   <spec> --panel ID --roll N --verdict pass|defect
                            [--reason "..."] [--counter "..."] [--guard NAME=VERDICT[:why]]...
    strip.py reopen  <spec> --panel ID --reason "..." [--counter "..."]   un-keep a kept panel
    strip.py compose <spec> [--export PATH.webp --export-asset static/img/.../x.webp] [--json]
    strip.py stage   <spec> --manifest PATH [--board-id ID] [--title T] [--context "..."]
                            [--no-mount]
    strip.py check-recipe <recipe.json> [--asset REL]   the wiki gate's rules, in Python

State lives beside the spec in `strip-state.json`; panel rolls in `panels/`, rejects (image, recipe,
readback and a `.reject.json` with the reason) in `panels/rejected/`. Nothing is ever deleted.
"""
from __future__ import annotations

import argparse
import contextlib
import datetime as _dt
import fcntl
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ABU = Path(__file__).resolve().parents[3]
GENERATE = ABU / "skills" / "on-brand-image" / "scripts" / "generate.py"
VERIFY = ABU / "skills" / "render-readback" / "scripts" / "verify_render.py"
WORKS_BOARD = ABU / "skills" / "approve-works" / "scripts" / "works_board.py"

MIN_PANELS, MAX_PANELS = 2, 4
DEFAULT_MAX_REROLLS = 4          # the first roll plus four re-rolls
DEFAULT_CANVAS = {"size": "1536x1024", "margin": 16, "gutter": 16, "colour": "#F0ECE5"}
DEFAULT_EXPORT = {"maxEdge": 1600, "quality": 82}
ID_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PENDING_GUARD = "has no recorded verdict"


class StripError(Exception):
    """A refusal. The message says what is wrong and what to do instead."""


def _now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat()


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def abu_version() -> str:
    try:
        return json.loads((ABU / ".claude-plugin" / "plugin.json").read_text())["version"]
    except (OSError, ValueError, KeyError):
        return "unknown"


# ---------------------------------------------------------------------------------------------
# The spec
# ---------------------------------------------------------------------------------------------

def load_spec(path: Path) -> dict:
    path = Path(path).resolve()
    try:
        spec = json.loads(path.read_text())
    except (OSError, ValueError) as e:
        raise StripError(f"{path}: not a readable JSON strip spec ({e})")
    spec["_path"] = path
    spec["_dir"] = path.parent
    uni = Path(spec.get("universe") or "").expanduser()
    if not str(uni):
        raise StripError(f"{path}: no `universe`. A strip renders canon entities, so it names the "
                         f"universe they live in (absolute, or relative to the spec).")
    spec["_universe"] = (uni if uni.is_absolute() else (path.parent / uni)).resolve()
    if not (spec["_universe"] / "universe.json").exists():
        raise StripError(f"{path}: `universe` resolves to {spec['_universe']}, which has no "
                         f"universe.json.")
    validate_spec(spec)
    return spec


def canvas(spec: dict) -> dict:
    c = {**DEFAULT_CANVAS, **(spec.get("canvas") or {})}
    try:
        w, h = (int(x) for x in str(c["size"]).lower().split("x"))
    except ValueError:
        raise StripError(f"canvas.size {c['size']!r} is not WxH")
    c["w"], c["h"] = w, h
    return c


def panel_widths(spec: dict) -> list[int]:
    c, panels = canvas(spec), spec["panels"]
    n = len(panels)
    avail = c["w"] - 2 * c["margin"] - (n - 1) * c["gutter"]
    given = [p.get("width") for p in panels]
    if all(isinstance(g, int) for g in given):
        if sum(given) != avail:
            raise StripError(f"panel widths {given} sum to {sum(given)}; this canvas leaves exactly "
                             f"{avail} ({c['w']} - 2x{c['margin']} margin - {n - 1}x{c['gutter']} "
                             f"gutter). Widths that do not fill it leave a stripe of gutter colour.")
        return given
    if any(g is not None for g in given):
        raise StripError("give every panel a `width`, or none (none = equal split)")
    base, rem = divmod(avail, n)
    return [base + (1 if i < rem else 0) for i in range(n)]


def validate_spec(spec: dict) -> None:
    path = spec["_path"]
    sid = spec.get("id")
    if not isinstance(sid, str) or not ID_RE.match(sid):
        raise StripError(f"{path}: `id` must be a lowercase slug, got {sid!r}")
    if not isinstance(spec.get("out"), str) or not spec["out"].endswith(".png"):
        raise StripError(f"{path}: `out` must name the composite PNG (relative to the spec)")
    panels = spec.get("panels")
    if not isinstance(panels, list) or not MIN_PANELS <= len(panels) <= MAX_PANELS:
        raise StripError(f"{path}: a strip has {MIN_PANELS} to {MAX_PANELS} panels (three by "
                         f"default); got {len(panels) if isinstance(panels, list) else panels!r}. "
                         f"One panel is a single hero: use on-brand-image.")
    blocks = spec.get("promptBlocks") or {}
    seen = set()
    for i, p in enumerate(panels, 1):
        pid = p.get("id") or f"p{i}"
        p["id"] = pid
        if not ID_RE.match(pid) or pid in seen:
            raise StripError(f"{path}: panel {i} id {pid!r} is not a unique slug")
        seen.add(pid)
        for k in ("beat", "scene"):
            if not isinstance(p.get(k), str) or not p[k].strip():
                raise StripError(f"{path}: panel {pid} has no `{k}`. Words before art: the beat "
                                 f"says what the panel argues and the scene says what is in it.")
        if not p.get("entities"):
            raise StripError(f"{path}: panel {pid} names no `entities`. Every panel renders "
                             f"through the entity route, so canon arrives as plates and "
                             f"invariants rather than as a description.")
        for b in p.get("blocks") or []:
            if b != "scene" and b not in blocks:
                raise StripError(f"{path}: panel {pid} names block {b!r}, which is not in "
                                 f"`promptBlocks` ({', '.join(sorted(blocks)) or 'none'})")
        for r in p.get("refs") or []:
            if not (spec["_universe"] / r).exists():
                raise StripError(f"{path}: panel {pid} ref {r!r} does not resolve under the "
                                 f"universe. A missing ref is a silent downgrade to prose.")
        shift = p.get("shift", 0)
        if not isinstance(shift, (int, float)) or not -1 <= shift <= 1:
            raise StripError(f"{path}: panel {pid} shift {shift!r} must be in [-1, 1]")
    panel_widths(spec)


def panel(spec: dict, pid: str) -> dict:
    for p in spec["panels"]:
        if p["id"] == pid:
            return p
    raise StripError(f"no panel {pid!r}; panels are {', '.join(p['id'] for p in spec['panels'])}")


def entity_args(spec: dict, p: dict) -> list[str]:
    return [f"{spec['_universe']}:{e}" for e in p["entities"]]


# ---------------------------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------------------------

def state_path(spec: dict) -> Path:
    return spec["_dir"] / "strip-state.json"


def load_state(spec: dict) -> dict:
    sp = state_path(spec)
    st = json.loads(sp.read_text()) if sp.exists() else {}
    st.setdefault("id", spec["id"])
    st.setdefault("panels", {})
    for p in spec["panels"]:
        st["panels"].setdefault(p["id"], {"rolls": [], "kept": None, "counters": []})
    return st


def save_state(spec: dict, st: dict) -> None:
    tmp = state_path(spec).with_suffix(".json.tmp")
    tmp.write_text(json.dumps(st, indent=1) + "\n")
    tmp.replace(state_path(spec))


@contextlib.contextmanager
def locked(spec: dict):
    """Every read-modify-write of the state holds this lock. Panels render in PARALLEL (three at
    once is the working number), and before the lock each render loaded the state, waited minutes
    on the model, and saved: the last one to finish erased the other panels' rolls (2026-09-25,
    the first strip made through this script)."""
    lp = spec["_dir"] / "strip-state.lock"
    with open(lp, "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def panels_dir(spec: dict) -> Path:
    return spec["_dir"] / "panels"


def max_rolls(spec: dict) -> int:
    return 1 + int(spec.get("maxRerolls", DEFAULT_MAX_REROLLS))


# ---------------------------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------------------------

def assemble_prompt(spec: dict, p: dict, counters: list[str] | None = None) -> str:
    """Blocks in order, the scene where `scene` sits (else last), then the strip header and every
    counter a defect has earned. Nothing here is free text except the scene and the counters."""
    n = len(spec["panels"])
    idx = [q["id"] for q in spec["panels"]].index(p["id"]) + 1
    blocks = spec.get("promptBlocks") or {}
    order = list(p.get("blocks") or [])
    if "scene" not in order:
        order.append("scene")
    header = (f"PANEL {idx} OF A {n}-PANEL STRIP: {p['beat'].strip()}. "
              + (p.get("frame") or spec.get("panelFrame") or
                 "A TALL NARROW PORTRAIT FRAME. The frame edges ARE the panel edges: nothing "
                 "important touches them. No drawn border and no text of any kind."))
    parts = []
    for b in order:
        if b == "scene":
            parts.append(header)
            parts.append("SCENE: " + p["scene"].strip())
        else:
            parts.append(blocks[b].strip())
    if counters:
        parts.append("CORRECTIONS FROM REJECTED ROLLS OF THIS PANEL (each one is binding): "
                     + " ".join(c.strip() for c in counters))
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------------------------
# Render and judge
# ---------------------------------------------------------------------------------------------

def _rel(spec: dict, p: Path) -> str:
    return str(Path(p).resolve().relative_to(spec["_dir"]))


def next_roll(spec: dict, st: dict, pid: str) -> int:
    ps = st["panels"][pid]
    if ps["kept"]:
        raise StripError(f"panel {pid} is already kept ({ps['kept']}). To redo it, "
                         f"`reopen --panel {pid} --reason ...` first, so the record says why.")
    pending = [r for r in ps["rolls"] if r.get("verdict") is None]
    if pending:
        raise StripError(f"panel {pid} roll {pending[-1]['roll']} has not been judged. Look at "
                         f"it (render-readback, crop_zoom before calling a detail), then "
                         f"`judge --panel {pid} --roll {pending[-1]['roll']} --verdict ...`.")
    n = len(ps["rolls"]) + 1
    if n - ps.get("capBase", 0) > max_rolls(spec):
        raise StripError(f"panel {pid} has used all {max_rolls(spec)} rolls (the first and "
                         f"{max_rolls(spec) - 1} re-rolls). Stop and report the surviving "
                         f"defects; every reject and its reason is in panels/rejected/. A silent "
                         f"fifth attempt is how a cap stops meaning anything.")
    return n


def generate_cmd(spec: dict, p: dict, out: Path, prompt_file: Path) -> list[str]:
    r = spec.get("render") or {}
    cmd = [sys.executable, str(GENERATE), "--out", str(out), "--no-open",
           "--size", p.get("size") or r.get("size") or "1024x1536",
           "--quality", r.get("quality", "high"),
           "--prompt-file", str(prompt_file)]
    if r.get("noWardrobe", True):
        cmd.append("--no-wardrobe")
    if r.get("timeout"):
        cmd += ["--timeout", str(r["timeout"])]
    if r.get("model"):
        cmd += ["--model", r["model"]]
    for e in entity_args(spec, p):
        cmd += ["--entity", e]
    for ref in p.get("refs") or []:
        cmd += ["--ref", str(spec["_universe"] / ref)]
    return cmd


def verify(spec: dict, p: dict, png: Path, guards: list[str] | None = None) -> tuple[bool, list[str]]:
    """The binding check. Returns (bindingOk, problems). A guard that fired and is still unjudged
    is PENDING, not a binding failure: it is exactly what `judge` exists to settle."""
    cmd = [sys.executable, str(VERIFY), str(png)]
    for e in p["entities"]:
        cmd += ["--expect", e]
    for g in guards or []:
        cmd += ["--guard", g]
    r = subprocess.run(cmd, capture_output=True, text=True)
    lines = [l.strip()[2:] for l in r.stderr.splitlines() if l.strip().startswith("- ")]
    if r.returncode == 2:
        raise StripError(f"verify_render refused: {r.stderr.strip()}")
    hard = [l for l in lines if PENDING_GUARD not in l]
    return (not hard, lines)


def cmd_render(spec: dict, pid: str, dry_run: bool = False, runner=subprocess.run) -> dict:
    p = panel(spec, pid)
    pdir = panels_dir(spec)
    with locked(spec):
        st = load_state(spec)
        n = next_roll(spec, st, pid)
        out = pdir / f"{pid}.r{n}.png"
        pf = pdir / f"{pid}.r{n}.prompt.txt"
        prompt = assemble_prompt(spec, p, st["panels"][pid]["counters"])
        cmd = generate_cmd(spec, p, out, pf)
        if dry_run:
            return {"panel": pid, "roll": n, "cmd": cmd, "promptChars": len(prompt)}
        pdir.mkdir(parents=True, exist_ok=True)
        pf.write_text(prompt + "\n")
        # Reserve the roll before the minutes-long call, so a second render of the SAME panel
        # started meanwhile is refused as "not judged" rather than taking the same number.
        roll = {"roll": n, "path": _rel(spec, out), "prompt": _rel(spec, pf),
                "binding": "rendering", "problems": [], "verdict": None}
        st["panels"][pid]["rolls"].append(roll)
        save_state(spec, st)
    rc = runner(cmd).returncode
    ok_files = rc == 0 and out.exists() and Path(str(out) + ".recipe.json").exists()
    ok, problems = verify(spec, p, out) if ok_files else (False, [])
    with locked(spec):
        st = load_state(spec)
        rolls = st["panels"][pid]["rolls"]
        rec = next(r for r in rolls if r["roll"] == n and r["binding"] == "rendering")
        if not ok_files:
            rolls.remove(rec)
            save_state(spec, st)
            raise StripError(f"generate.py exited {rc} for {pid} roll {n}; no image and recipe "
                             f"pair. Nothing was recorded, so the same roll number is free again.")
        rec.update(renderedOn=_now(), binding="ok" if ok else "broken", problems=problems)
        save_state(spec, st)
    return rec


def _move_reject(spec: dict, rel: str, reason: str, counter: str | None) -> str:
    src = spec["_dir"] / rel
    rdir = panels_dir(spec) / "rejected"
    rdir.mkdir(parents=True, exist_ok=True)
    dest = rdir / src.name
    for suffix in ("", ".recipe.json", ".readback.json", ".prompt.txt"):
        s = Path(str(src) + suffix) if suffix != ".prompt.txt" else src.with_suffix(".prompt.txt")
        if s.exists():
            d = Path(str(dest) + suffix) if suffix != ".prompt.txt" else dest.with_suffix(".prompt.txt")
            shutil.move(str(s), str(d))
    Path(str(dest) + ".reject.json").write_text(json.dumps(
        {"reason": reason, "counter": counter, "rejectedOn": _now()}, indent=1) + "\n")
    return _rel(spec, dest)


def cmd_judge(spec: dict, pid: str, roll: int, verdict: str, reason: str = "",
              counter: str | None = None, guards: list[str] | None = None) -> dict:
    with locked(spec):
        return _judge(spec, pid, roll, verdict, reason, counter, guards)


def _judge(spec: dict, pid: str, roll: int, verdict: str, reason: str = "",
           counter: str | None = None, guards: list[str] | None = None) -> dict:
    p = panel(spec, pid)
    st = load_state(spec)
    ps = st["panels"][pid]
    rec = next((r for r in ps["rolls"] if r["roll"] == roll), None)
    if rec is None:
        raise StripError(f"panel {pid} has no roll {roll}")
    if rec.get("verdict") is not None:
        raise StripError(f"panel {pid} roll {roll} was already judged {rec['verdict']}")
    if rec.get("binding") == "rendering":
        raise StripError(f"panel {pid} roll {roll} is still rendering")
    if verdict == "defect" and not reason.strip():
        raise StripError("a DEFECT needs --reason: a reject with no reason teaches the next roll "
                         "nothing, and the reason is the only record the attempt existed for.")
    png = spec["_dir"] / rec["path"]
    if verdict == "pass":
        ok, problems = verify(spec, p, png, guards)
        if problems:
            raise StripError(f"panel {pid} roll {roll} cannot PASS while verify_render reports:\n  "
                             + "\n  ".join(problems)
                             + "\nJudge each fired guard with --guard NAME=pass (or defect:why / "
                               "waived:why). A broken binding is a DEFECT, never a pass.")
        rec.update(verdict="pass", reason=reason or None, judgedOn=_now())
        ps["kept"] = rec["path"]
    else:
        if guards:
            verify(spec, p, png, guards)
        rec.update(verdict="defect", reason=reason, counter=counter, judgedOn=_now())
        rec["path"] = _move_reject(spec, rec["path"], reason, counter)
        rec["prompt"] = str(Path(rec["path"]).with_suffix(".prompt.txt"))
        if counter:
            ps["counters"].append(counter)
    save_state(spec, st)
    left = max_rolls(spec) - (len(ps["rolls"]) - ps.get("capBase", 0))
    return {**rec, "panel": pid, "rollsLeft": left if not ps["kept"] else None}


def cmd_reopen(spec: dict, pid: str, reason: str, counter: str | None = None) -> dict:
    with locked(spec):
        return _reopen(spec, pid, reason, counter)


def _reopen(spec: dict, pid: str, reason: str, counter: str | None = None) -> dict:
    """A kept panel goes back to rolling (a re-roll tap on the board names it). The kept roll is
    moved to rejected/ with the reason, and the roll count restarts its cap from here, because a
    reopen is a new judgement by a person, not a continuation of the agent's own attempts."""
    if not reason.strip():
        raise StripError("reopen needs --reason: say what the operator objected to")
    panel(spec, pid)
    st = load_state(spec)
    ps = st["panels"][pid]
    if not ps["kept"]:
        raise StripError(f"panel {pid} is not kept; just render it")
    rec = next(r for r in ps["rolls"] if r["path"] == ps["kept"])
    rec["path"] = _move_reject(spec, rec["path"], reason, counter)
    rec.update(verdict="defect", reason=reason, counter=counter, reopenedOn=_now())
    ps.setdefault("reopened", []).append({"roll": rec["roll"], "reason": reason, "on": _now()})
    ps["kept"] = None
    if counter:
        ps["counters"].append(counter)
    ps["capBase"] = len(ps["rolls"])
    save_state(spec, st)
    return {"panel": pid, "reopened": rec["roll"], "rejectedTo": rec["path"]}


# ---------------------------------------------------------------------------------------------
# The recipe, and the wiki gate's rules in Python
# ---------------------------------------------------------------------------------------------

def validate_recipe(recipe: dict, rel_asset: str) -> list[str]:
    """The supersuit wiki preset's `validateRecipe` (check-image-provenance.mjs), ported rule for
    rule so a composite is refused HERE, before it is written, rather than in a wiki's prebuild.
    Kept deliberately literal: if the gate changes, the test that runs the real gate says so."""
    problems: list[str] = []

    def has(k):
        v = recipe.get(k)
        return v is not None and v != ""

    def first(*ks):
        return next((k for k in ks if has(k)), None)

    inputs_key = next((k for k in ("refs", "inputs") if k in recipe), None)
    if has("asset"):
        claimed = str(recipe["asset"]).removeprefix("./").split("/")[-1]
        actual = rel_asset.removeprefix("./").split("/")[-1]
        if claimed != actual:
            problems.append(f'claims asset "{recipe["asset"]}" but sits beside "{rel_asset}"')
    mode = recipe.get("mode") or ("derive" if recipe.get("derivedFrom") else None)
    parts = recipe.get("panelRecipes", recipe.get("parts"))
    if isinstance(parts, dict) and parts:
        if not first("compositor", "generator"):
            problems.append("a composite with no `compositor` (or `generator`) naming what "
                            "assembled the parts")
        for name, part in parts.items():
            if not isinstance(part, dict):
                problems.append(f"part {name} is not a recipe")
                continue
            problems += [f"part {name}: {pr}" for pr in validate_recipe(part, rel_asset)]
        return problems
    if mode == "derive":
        if not has("derivedFrom"):
            problems.append('mode "derive" with no `derivedFrom` naming the source')
        if not has("generator"):
            problems.append('mode "derive" with no `generator` naming what transformed it')
    elif not first("model", "provider") and (has("params") or has("seed") or has("generator")):
        if not has("generator"):
            problems.append("a generated asset with no `generator`")
        if not has("seed") and not has("params"):
            problems.append("a generator recipe with neither `seed` nor `params`")
    else:
        if not first("model", "provider"):
            problems.append("no `model` or `provider`")
        if not has("prompt"):
            problems.append("no `prompt` (the EXACT prompt, not a summary)")
        if inputs_key is None:
            problems.append("no `refs`/`inputs` list (use [] when nothing was passed in)")
        elif not isinstance(recipe[inputs_key], list):
            problems.append(f"`{inputs_key}` is not a list")
    if not first("timestamp", "generatedAt", "created"):
        problems.append("no timestamp (`timestamp`, `generatedAt` or `created`)")
    return problems


def completeness(recipe: dict) -> list[str]:
    """Stricter than the wiki gate, on purpose. The gate's composite branch returns after checking
    the parts, so a composite with no top-level prompt, refs or timestamp still passes it, and a
    reader of the ONE file a wiki keeps would then have to chase every panel recipe to learn what
    made the picture. The brief for this verb names the fields; this refuses a recipe missing any."""
    problems = []
    for k in ("asset", "prompt", "model", "provider", "timestamp", "compositor", "sha256"):
        if not recipe.get(k):
            problems.append(f"composite recipe has no `{k}`")
    if not isinstance(recipe.get("refs"), list) or not recipe.get("refs"):
        problems.append("composite recipe has no `refs` list naming every input")
    parts = recipe.get("panelRecipes")
    panels = recipe.get("panels") or []
    if not isinstance(parts, dict) or not parts:
        problems.append("composite recipe has no `panelRecipes`")
    else:
        for pr in panels:
            part = parts.get(pr.get("id"))
            if part is None:
                problems.append(f"panel {pr.get('id')} has no entry in `panelRecipes`")
                continue
            if part.get("prompt") and part["prompt"] not in recipe.get("prompt", ""):
                problems.append(f"panel {pr.get('id')}'s exact prompt is not in the top-level `prompt`")
            refs = {r.get("path") if isinstance(r, dict) else r for r in recipe.get("refs") or []}
            for r in part.get("refs") or []:
                rp = r.get("path") if isinstance(r, dict) else r
                if rp not in refs:
                    problems.append(f"panel {pr.get('id')} ref {rp} is missing from the top-level `refs`")
    return problems


def build_recipe(spec: dict, st: dict, out: Path, asset: str, widths: list[int],
                 c: dict) -> dict:
    panels, parts, prompts, refs, models, providers = [], {}, [], [], [], []
    for p in spec["panels"]:
        ps = st["panels"][p["id"]]
        kept = spec["_dir"] / ps["kept"]
        part = json.loads(Path(str(kept) + ".recipe.json").read_text())
        parts[p["id"]] = part
        prompts.append(f"PANEL {p['id']} ({kept.name}):\n{part.get('prompt', '')}")
        refs.append({"path": str(kept), "role": f"panel {p['id']}"})
        for r in part.get("refs") or []:
            rp = r.get("path") if isinstance(r, dict) else r
            if rp not in [x["path"] for x in refs]:
                refs.append({"path": rp})
        for lst, key in ((models, "model"), (providers, "provider")):
            if part.get(key) and part[key] not in lst:
                lst.append(part[key])
        panels.append({
            "id": p["id"], "beat": p["beat"], "world": p.get("world"),
            "entities": p["entities"], "path": str(kept), "recipe": str(kept) + ".recipe.json",
            "sha256": _sha(kept), "shift": p.get("shift", 0),
            "rolls": len(ps["rolls"]),
            "rejected": [{"path": str(spec["_dir"] / r["path"]), "reason": r.get("reason")}
                         for r in ps["rolls"] if r.get("verdict") == "defect"],
        })
    return {
        "asset": asset,
        "kind": f"composite strip of {len(panels)} panels, composed in code",
        "mode": "composite",
        "compositor": f"abu:compose-strip (skills/compose-strip/scripts/strip.py, abu {abu_version()})",
        "generator": "skills/compose-strip/scripts/strip.py",
        "provider": " + ".join(providers), "model": " + ".join(models),
        "prompt": "\n\n".join(prompts),
        "refs": refs,
        "panelRecipes": parts,
        "panels": panels,
        "compose": {"size": f"{c['w']}x{c['h']}", "margin": c["margin"], "gutter": c["gutter"],
                    "gutterColour": c["colour"], "panelWidths": widths,
                    "panelHeight": c["h"] - 2 * c["margin"],
                    "fit": "scale-to-cover, crop window shifted per panel (-1 left .. +1 right)",
                    "borders": None, "text": None},
        "stripSpec": str(spec["_path"]),
        "canon": spec.get("canon") or [],
        "universe": str(spec["_universe"]),
        "specVersion": _spec_version(),
        "timestamp": _now(),
        "sha256": _sha(out),
    }


def _spec_version() -> str:
    try:
        sys.path.insert(0, str(ABU / "engine"))
        from agenticstory import SPEC_VERSION  # type: ignore
        return SPEC_VERSION
    except Exception:
        return "unknown"
    finally:
        if sys.path and sys.path[0] == str(ABU / "engine"):
            sys.path.pop(0)


def _hex(s: str) -> tuple[int, int, int]:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))  # type: ignore


def compose_image(spec: dict, st: dict, out: Path) -> tuple[list[int], dict]:
    from PIL import Image
    c, widths = canvas(spec), panel_widths(spec)
    ph = c["h"] - 2 * c["margin"]
    img = Image.new("RGB", (c["w"], c["h"]), _hex(c["colour"]))
    x = c["margin"]
    for p, pw in zip(spec["panels"], widths):
        im = Image.open(spec["_dir"] / st["panels"][p["id"]]["kept"]).convert("RGB")
        s = max(pw / im.width, ph / im.height)
        im = im.resize((max(pw, round(im.width * s)), max(ph, round(im.height * s))), Image.LANCZOS)
        shift = float(p.get("shift", 0))
        x0 = round((im.width - pw) / 2 * (1 + shift))
        y0 = (im.height - ph) // 2
        img.paste(im.crop((x0, y0, x0 + pw, y0 + ph)), (x, c["margin"]))
        x += pw + c["gutter"]
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return widths, c


def cmd_compose(spec: dict, export: str | None = None, export_asset: str | None = None) -> dict:
    st = load_state(spec)
    missing = [p["id"] for p in spec["panels"] if not st["panels"][p["id"]]["kept"]]
    if missing:
        raise StripError(f"cannot compose: no kept roll for panel(s) {', '.join(missing)}. Every "
                         f"panel is judged PASS before the strip exists.")
    out = (spec["_dir"] / spec["out"]).resolve()
    widths, c = compose_image(spec, st, out)
    try:
        asset = str(out.relative_to(spec["_universe"]))
    except ValueError:
        asset = out.name
    recipe = build_recipe(spec, st, out, asset, widths, c)
    problems = validate_recipe(recipe, asset) + completeness(recipe)
    if problems:
        raise StripError("the composite recipe would not pass provenance:\n  " + "\n  ".join(problems))
    Path(str(out) + ".recipe.json").write_text(json.dumps(recipe, indent=1) + "\n")
    result = {"out": str(out), "recipe": str(out) + ".recipe.json", "sha256": recipe["sha256"]}
    if export:
        result["export"] = export_webp(spec, out, recipe, Path(export), export_asset)
    return result


def export_webp(spec: dict, src: Path, recipe: dict, dest: Path, asset: str | None) -> dict:
    """The copy a wiki keeps: EXIF-transposed, capped on its long edge, WebP. Its recipe is the
    composite's own, restated for where it will sit, plus a `derived` block naming the transform,
    so the one file the wiki holds answers every provenance question without a trip back here."""
    from PIL import Image, ImageOps
    ex = {**DEFAULT_EXPORT, **(spec.get("export") or {})}
    im = ImageOps.exif_transpose(Image.open(src)).convert("RGB")
    im.thumbnail((ex["maxEdge"], ex["maxEdge"]), Image.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    im.save(dest, "WEBP", quality=ex["quality"])
    asset = asset or spec.get("asset") or dest.name
    r = {**recipe, "asset": asset, "sha256": _sha(dest),
         "derived": {"from": str(src), "fromSha256": recipe["sha256"],
                     "op": f"exif_transpose, {ex['maxEdge']} max edge, webp q{ex['quality']}",
                     "on": _now()}}
    problems = validate_recipe(r, asset) + completeness(r)
    if problems:
        raise StripError("the exported recipe would not pass provenance:\n  " + "\n  ".join(problems))
    Path(str(dest) + ".recipe.json").write_text(json.dumps(r, indent=1) + "\n")
    return {"out": str(dest), "recipe": str(dest) + ".recipe.json", "asset": asset}


# ---------------------------------------------------------------------------------------------
# Plan and stage
# ---------------------------------------------------------------------------------------------

def cmd_plan(spec: dict) -> dict:
    st = load_state(spec)
    rows = []
    for p in spec["panels"]:
        ps = st["panels"][p["id"]]
        if ps["kept"]:
            nxt = "kept"
        elif any(r.get("verdict") is None for r in ps["rolls"]):
            nxt = "judge the pending roll"
        elif len(ps["rolls"]) - ps.get("capBase", 0) >= max_rolls(spec):
            nxt = "EXHAUSTED: report the surviving defects"
        else:
            nxt = f"render roll {len(ps['rolls']) + 1}"
        rows.append({"panel": p["id"], "beat": p["beat"], "world": p.get("world"),
                     "entities": p["entities"], "refs": p.get("refs") or [],
                     "promptChars": len(assemble_prompt(spec, p, ps["counters"])),
                     "rolls": len(ps["rolls"]), "kept": ps["kept"], "next": nxt})
    return {"id": spec["id"], "universe": str(spec["_universe"]),
            "widths": panel_widths(spec), "panels": rows,
            "ready": all(r["kept"] for r in rows)}


def cmd_stage(spec: dict, manifest: Path, board_id: str | None, title: str | None,
              context: str | None, mount: bool = True, runner=subprocess.run) -> dict:
    out = (spec["_dir"] / spec["out"]).resolve()
    if not Path(str(out) + ".recipe.json").exists():
        raise StripError("nothing to stage: compose the strip first")
    manifest = Path(manifest).resolve()
    doc = json.loads(manifest.read_text()) if manifest.exists() else {"items": []}
    items = doc if isinstance(doc, list) else doc.setdefault("items", [])
    entry = {"id": spec["id"], "title": title or spec.get("title") or spec["id"],
             "image": str(out), "recipe": str(out) + ".recipe.json",
             "context": context or spec.get("argues") or "", "page": spec.get("page"),
             "kind": "strip", "stripSpec": str(spec["_path"])}
    for i, it in enumerate(items):
        if isinstance(it, dict) and it.get("id") == spec["id"]:
            items[i] = {**it, **entry}
            break
    else:
        items.append(entry)
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(doc, indent=1) + "\n")
    cmd = [sys.executable, str(WORKS_BOARD), "open", str(manifest), "--json"]
    if board_id:
        cmd += ["--id", board_id]
    if title:
        cmd += ["--title", title]
    if not mount:
        cmd.append("--no-mount")
    r = runner(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise StripError(f"works_board open failed: {(r.stderr or r.stdout).strip()}")
    try:
        board = json.loads(r.stdout)
    except ValueError:
        board = {"raw": r.stdout.strip()}
    return {"manifest": str(manifest), "board": board}


# ---------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="verb", required=True)
    s = sub.add_parser("plan"); s.add_argument("spec"); s.add_argument("--json", action="store_true")
    s = sub.add_parser("prompt"); s.add_argument("spec"); s.add_argument("--panel", required=True)
    s = sub.add_parser("render"); s.add_argument("spec"); s.add_argument("--panel", required=True)
    s.add_argument("--dry-run", action="store_true")
    s = sub.add_parser("judge"); s.add_argument("spec"); s.add_argument("--panel", required=True)
    s.add_argument("--roll", type=int, required=True)
    s.add_argument("--verdict", required=True, choices=["pass", "defect"])
    s.add_argument("--reason", default=""); s.add_argument("--counter", default=None)
    s.add_argument("--guard", action="append", default=[], metavar="NAME=VERDICT[:why]")
    s = sub.add_parser("reopen"); s.add_argument("spec"); s.add_argument("--panel", required=True)
    s.add_argument("--reason", required=True); s.add_argument("--counter", default=None)
    s = sub.add_parser("compose"); s.add_argument("spec")
    s.add_argument("--export", default=None); s.add_argument("--export-asset", default=None)
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("stage"); s.add_argument("spec"); s.add_argument("--manifest", required=True)
    s.add_argument("--board-id", default=None); s.add_argument("--title", default=None)
    s.add_argument("--context", default=None); s.add_argument("--no-mount", action="store_true")
    s = sub.add_parser("check-recipe"); s.add_argument("recipe"); s.add_argument("--asset", default=None)
    a = ap.parse_args(argv)
    try:
        if a.verb == "check-recipe":
            r = json.loads(Path(a.recipe).read_text())
            asset = a.asset or Path(a.recipe).name.removesuffix(".recipe.json")
            problems = validate_recipe(r, asset) + (completeness(r) if r.get("panelRecipes") else [])
            for pr in problems:
                print(f"  INVALID {pr}", file=sys.stderr)
            print("recipe OK" if not problems else f"{len(problems)} problem(s)")
            return 1 if problems else 0
        spec = load_spec(Path(a.spec))
        if a.verb == "plan":
            res = cmd_plan(spec)
            if a.json:
                print(json.dumps(res, indent=1))
            else:
                print(f"strip {res['id']}  widths {res['widths']}")
                for r in res["panels"]:
                    print(f"  {r['panel']:<4} {r['rolls']} roll(s)  next: {r['next']:<26} {r['beat']}")
            return 0
        if a.verb == "prompt":
            p = panel(spec, a.panel)
            print(assemble_prompt(spec, p, load_state(spec)["panels"][a.panel]["counters"]))
            return 0
        if a.verb == "render":
            res = cmd_render(spec, a.panel, dry_run=a.dry_run)
        elif a.verb == "judge":
            res = cmd_judge(spec, a.panel, a.roll, a.verdict, a.reason, a.counter, a.guard)
        elif a.verb == "reopen":
            res = cmd_reopen(spec, a.panel, a.reason, a.counter)
        elif a.verb == "compose":
            res = cmd_compose(spec, a.export, a.export_asset)
        else:
            res = cmd_stage(spec, Path(a.manifest), a.board_id, a.title, a.context, not a.no_mount)
        print(json.dumps(res, indent=1))
        return 0
    except StripError as e:
        print(f"strip: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
