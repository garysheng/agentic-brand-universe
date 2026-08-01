"""The framework's OWN docs as a DERIVED artifact.

`canonfile` made a universe's CANON.md a projection of its record store, because a
hand-maintained shared file drifts and git cannot catch it. The framework's own
documentation had exactly the same disease and no cure: on 2026-07-30 the public
README claimed spec v0.6 while SPEC.md was v0.16, claimed "165 tests across seven
skill suites" against a real 541 across 16, and taught two layer names ("Projection",
"Composition") that v0.14 had renamed to Form and Work. Every one of those numbers
was true when it was typed. That is the whole problem: prose asserts a fact once and
then rots silently while the thing it describes keeps moving.

So the same fix applies one level up. Anything whose truth already lives in a file is
GENERATED between fences; only judgement is hand-written. The generated blocks:

  status         (README.md)        versions + counts, the facts that rot fastest
  skills         (docs/REFERENCE.md) every skills/*/SKILL.md, by frontmatter
  cli            (docs/REFERENCE.md) every verb, by introspecting the real parser
  agents         (docs/REFERENCE.md) every agents/*.md, by frontmatter
  commands       (docs/REFERENCE.md) every commands/*.md, by frontmatter
  providers      (docs/REFERENCE.md) registry/providers.json
  forms          (docs/REFERENCE.md) forms/*/form.json
  spec-changelog (docs/REFERENCE.md) the v0.N changelog headlines in SPEC.md

and one derived file that carries no fences, `.claude-plugin/marketplace.json`, whose
entry description is projected wholesale from `.claude-plugin/plugin.json`.

Agents and commands were added on 2026-08-01 for a reason worth recording, because it
is this module's own thesis turned on itself. The plugin had shipped an `abu-steward`
subagent since 0.5x that no generated doc mentioned, because this file enumerated
`skills/` and nothing else. Undocumented is close to unreachable: it was invoked zero
times across a full book session in which the main agent hand-rolled five shoot
scripts the framework already owned. The fix was NOT to write a paragraph about the
steward. A surface the generator cannot see will be forgotten again the moment someone
adds the next one, so the generator learned to see whole directories instead.

`check()` is the half that matters. Regenerating docs is a convenience; FAILING when
they are stale is the mechanism, which is why `build-docs --check` runs inside
`run-tests.sh`. Documentation you have to remember to refresh is not documentation,
for the same reason provenance you have to remember to save is not provenance.

It also enforces one cross-file invariant prose cannot: SPEC.md's version and the
engine's SPEC_VERSION must agree. They are bumped by hand in two files and the
comment in `__init__.py` asking for lockstep is not a mechanism.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from . import SPEC_VERSION, __version__

MARK = "<!-- {} GENERATED: {} -->"

# The one derived artifact that is not a markdown fence. `.claude-plugin/plugin.json`
# is the catalog of record; the marketplace entry for the same plugin is a COPY of its
# description, and on 2026-08-01 the copy was already behind by a whole paragraph (the
# `make-a-work` entry, shipped in plugin.json, absent from the marketplace). Two hand-kept
# copies of a four-thousand-character string is the disease this module treats, so the
# marketplace entry is projected from the plugin manifest instead of pasted into it.
MANIFEST = ".claude-plugin/marketplace.json"
PLUGIN = ".claude-plugin/plugin.json"


def begin(name: str) -> str:
    return MARK.format("BEGIN", name)


def end(name: str) -> str:
    return MARK.format("END", name)


def repo_root() -> Path:
    """The framework repo root, inferred from this module (engine/agenticstory/)."""
    return Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------- sources


def spec_version(root: Path) -> tuple[str, str]:
    """(version, date) from SPEC.md's header line, the authoritative declaration."""
    text = (root / "SPEC.md").read_text()
    m = re.search(r"\*\*v(\d+\.\d+)\s*[—-]\s*(\d{4}-\d{2}-\d{2})", text)
    return (m.group(1), m.group(2)) if m else ("unknown", "unknown")


def spec_changelog(root: Path) -> list[dict]:
    """Every `> **v0.N changelog — headline**` block, newest first as written."""
    text = (root / "SPEC.md").read_text()
    out = []
    for m in re.finditer(r"\*\*v(\d+\.\d+) changelog\s*[—-]\s*(.+?)\*\*", text, re.S):
        out.append({"version": m.group(1), "headline": " ".join(m.group(2).split())})
    return out


def frontmatter(path: Path) -> dict:
    """The YAML-ish frontmatter of a SKILL.md. Only `name` and `description` are read,
    and `description` is a single (very long) line by convention, so a real YAML
    parser is not worth a dependency here."""
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    block = text.split("---", 2)[1]
    out, key = {}, None
    for line in block.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            out[key] = m.group(2).strip()
        elif key and line.strip():
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def first_sentence(text: str, floor: int = 40) -> str:
    """The lead sentence of a skill description. Fragments shorter than `floor` are
    rejoined, because these descriptions are dense with "(SPEC §4.7)." and "v0.13."
    and a naive split on the first period truncates mid-clause."""
    parts = re.split(r"(?<=\.)\s+", " ".join(text.split()))
    out = ""
    for p in parts:
        out = (out + " " + p).strip()
        if len(out) >= floor:
            break
    return out


def skills(root: Path) -> list[dict]:
    out = []
    for d in sorted((root / "skills").iterdir()):
        f = d / "SKILL.md"
        if not f.is_file():
            continue
        fm = frontmatter(f)
        out.append({
            "id": fm.get("name") or d.name,
            "summary": first_sentence(fm.get("description", "")),
            "tests": len(list((d / "tests").glob("test*.py"))) if (d / "tests").is_dir() else 0,
        })
    return out


def _md_dir(root: Path, name: str) -> list[Path]:
    """Every documented `*.md` in a plugin surface directory. Leading-underscore files
    are shared includes rather than surfaces (the convention plugins already use for
    `_conventions.md`), so they are not rows."""
    d = root / name
    if not d.is_dir():
        return []
    return [p for p in sorted(d.glob("*.md")) if not p.name.startswith("_")]


def agents(root: Path) -> list[dict]:
    out = []
    for p in _md_dir(root, "agents"):
        fm = frontmatter(p)
        out.append({
            "id": fm.get("name") or p.stem,
            "summary": first_sentence(fm.get("description", "")),
            "tools": " ".join(fm.get("tools", "").split()),
        })
    return out


def commands(root: Path) -> list[dict]:
    """Slash commands. `id` is the invocation as typed, which is the plugin name and
    the file stem, so the table answers "what do I type" rather than "what file is it"."""
    plugin = plugin_name(root)
    out = []
    for p in _md_dir(root, "commands"):
        fm = frontmatter(p)
        out.append({
            "id": f"/{plugin}:{p.stem}" if plugin else f"/{p.stem}",
            "summary": first_sentence(fm.get("description", "")),
            "args": fm.get("argument-hint", ""),
        })
    return out


def plugin_name(root: Path) -> str:
    p = root / ".claude-plugin" / "plugin.json"
    return json.loads(p.read_text()).get("name", "") if p.is_file() else ""


def cli_verbs() -> list[dict]:
    """The real parser, introspected. Not a hand-kept list, which is how `archived`
    and `land` shipped undocumented."""
    from .cli import build_parser
    out = []
    for action in build_parser()._subparsers._group_actions:
        for name, sub in action.choices.items():
            out.append({"verb": name, "help": " ".join((sub.description or _help_of(action, name) or "").split())})
    return sorted(out, key=lambda r: r["verb"])


def _help_of(action, name: str) -> str:
    for ch in action._choices_actions:
        if ch.dest == name:
            return ch.help or ""
    return ""


def providers(root: Path) -> list[dict]:
    p = root / "registry" / "providers.json"
    if not p.is_file():
        return []
    data = json.loads(p.read_text()).get("providers", {})
    return [{"id": k, "quirks": len(v.get("quirks", []))} for k, v in sorted(data.items())]


def forms(root: Path) -> list[dict]:
    d = root / "forms"
    if not d.is_dir():
        return []
    out = []
    for f in sorted(d.iterdir()):
        j = f / "form.json"
        if not j.is_file():
            continue
        data = json.loads(j.read_text())
        surface = data.get("surface", {})
        out.append({
            "id": data.get("id", f.name),
            "medium": surface.get("medium", ""),
            "summary": first_sentence(data.get("description", "")),
        })
    return out


def test_counts(root: Path) -> dict:
    """Counted statically. Executing the suite to document it would make the doc
    build slow, network-shy and recursive; `def test_` is the same number."""
    files = sorted(root.glob("engine/tests/test*.py")) + sorted(root.glob("skills/*/tests/test*.py"))
    n = 0
    for f in files:
        n += len(re.findall(r"^\s*def test_[A-Za-z0-9_]+", f.read_text(), re.M))
    return {"tests": n, "files": len(files)}


# ---------------------------------------------------------------- rendering


def _table(header: list[str], rows: list[list[str]]) -> list[str]:
    sep = "|" + "|".join("---" for _ in header) + "|"
    out = ["| " + " | ".join(header) + " |", sep]
    out += ["| " + " | ".join(c.replace("|", "\\|") for c in r) + " |" for r in rows]
    return out


def render_status(root: Path) -> list[str]:
    sv, sd = spec_version(root)
    tc = test_counts(root)
    rows = [
        ["Spec", f"v{sv}", f"`SPEC.md`, dated {sd}"],
        ["Engine conforms to", f"v{SPEC_VERSION}", "`engine/agenticstory/__init__.py`"],
        ["Engine version", f"v{__version__}", "`engine/agenticstory/__init__.py`"],
        ["Skills", str(len(skills(root))), "`skills/*/SKILL.md`"],
        ["CLI verbs", str(len(cli_verbs())), "`abu --help`"],
        ["Agents", str(len(agents(root))), "`agents/*.md`"],
        ["Commands", str(len(commands(root))), "`commands/*.md`"],
        ["Tests", str(tc["tests"]), f"across {tc['files']} files; `./run-tests.sh`"],
    ]
    return _table(["", "Value", "Source"], rows)


def render_skills(root: Path) -> list[str]:
    rows = [[f"`{s['id']}`", s["summary"], "yes" if s["tests"] else ""] for s in skills(root)]
    return _table(["Skill", "What it does", "Tested"], rows)


def render_cli(root: Path) -> list[str]:
    return _table(["Verb", "What it does"], [[f"`{v['verb']}`", v["help"]] for v in cli_verbs()])


def render_agents(root: Path) -> list[str]:
    rows = [[f"`{a['id']}`", a["summary"], f"`{a['tools']}`" if a["tools"] else "all"]
            for a in agents(root)]
    return _table(["Agent", "What it is for", "Tools"], rows)


def render_commands(root: Path) -> list[str]:
    rows = [[f"`{c['id']}`", f"`{c['args']}`" if c["args"] else "", c["summary"]]
            for c in commands(root)]
    return _table(["Command", "Takes", "What it does"], rows)


def render_providers(root: Path) -> list[str]:
    rows = [[f"`{p['id']}`", str(p["quirks"])] for p in providers(root)]
    return _table(["Provider", "Recorded quirks"], rows)


def render_forms(root: Path) -> list[str]:
    rows = [[f"`{f['id']}`", f"`{f['medium']}`", f["summary"]] for f in forms(root)]
    return _table(["Form", "Medium", "What it is"], rows)


def render_spec_changelog(root: Path) -> list[str]:
    rows = [[f"v{c['version']}", c["headline"]] for c in spec_changelog(root)]
    return _table(["Version", "What changed"], rows)



def render_guards(root: Path) -> list[str]:
    """Every auto-injected prompt guard, read off the compiler itself.

    SPEC 4.6 listed these by hand and drifted twice: MOTION_GUARD shipped
    2026-07-28 and the section still read "four rules" months later, and two more
    guards landed 2026-08-01 undocumented. A test was added to assert the names
    were present, which is the weaker fix. Gary, 2026-08-01: "isn't the spec
    partially generated anyway?" It is, and this belongs in that machinery: the
    guard list already lives in `assemble_prompt.py`, so the spec should PROJECT
    it rather than restate it. Presence is now generated and `build-docs --check`
    fails when it is stale, exactly like every other derived block.

    What stays hand-written is the JUDGEMENT beneath each entry: what the guard
    means, the defect that earned it, when to reach past it. That is the split
    this module exists to draw.
    """
    src = (root / "skills/compose-spread/scripts/assemble_prompt.py").read_text()
    # Each guard is a module-level constant; a CONDITIONAL one has a predicate
    # applied at the call site, which is what distinguishes the two kinds.
    names = sorted(set(re.findall(r"^([A-Z_]+_GUARD)\s*=", src, re.M)))
    emitted = dict(re.findall(r"^\s+([A-Z_]+_GUARD)(?:\s+if\s+(\w+)\()?", src, re.M))
    rows = [["Guard", "Fires", "Predicate"]]
    for n in names:
        pred = emitted.get(n) or ""
        rows.append([
            f"`{n}`",
            "conditional" if pred else "every render",
            f"`{pred}()`" if pred else "unconditional",
        ])
    w = [max(len(r[i]) for r in rows) for i in range(3)]
    out = ["| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(rows[0])) + " |",
           "|" + "|".join("-" * (w[i] + 2) for i in range(3)) + "|"]
    for r in rows[1:]:
        out.append("| " + " | ".join(c.ljust(w[i]) for i, c in enumerate(r)) + " |")
    return out


def render_scale_plate_contract(root: Path) -> list[str]:
    """The scale-plate geometry, read off the matrix module itself.

    Same split as `render_guards`: the LIST is enumerable and lives in one place
    (`matrix.SCALE_PLATE_CONTRACT`), so the spec projects it instead of restating it
    and cannot drift. The judgement beneath it stays hand-written: why the measured
    reference defaults to something architectural rather than clinical, why the shot
    is `optional` rather than in `shots`, and the v0.9 setting lineage it inherits.
    """
    src = (root / "engine/agenticstory/matrix.py").read_text()
    m = re.search(r"SCALE_PLATE_CONTRACT:\s*list\[str\]\s*=\s*\[(.*?)\]", src, re.S)
    items = re.findall(r'"([^"]+)"', m.group(1)) if m else []
    d = re.search(r"SCALE_REFERENCE_DEFAULT\s*=\s*\((.*?)\)\n", src, re.S)
    # The constant is a parenthesised multi-line string literal, so naive joining leaves
    # double spaces at every line break. Collapse to single spaces before emitting.
    default = re.sub(r"\s+", " ",
                     "".join(re.findall(r'"([^"]*)"', d.group(1)))).strip() if d else ""
    out = [f"- {i}" for i in items]
    if default:
        out += ["", f"Default measured reference, when a universe declares no "
                    f"`identity.scaleReference`: {default}"]
    return out


BLOCKS = {
    "README.md": {"status": render_status},
    "SPEC.md": {"guards": render_guards,
                "scale-plate-contract": render_scale_plate_contract},
    "docs/REFERENCE.md": {
        "skills": render_skills,
        "cli": render_cli,
        "agents": render_agents,
        "commands": render_commands,
        "forms": render_forms,
        "providers": render_providers,
        "spec-changelog": render_spec_changelog,
    },
}


def _replace_block(text: str, name: str, body: list[str]) -> str:
    b, e = begin(name), end(name)
    if b not in text or e not in text:
        raise ValueError(f"markers not found for block '{name}'")
    pre, rest = text.split(b, 1)
    _, post = rest.split(e, 1)
    return pre + "\n".join([b, *body, e]) + post


def build_file(root: Path, rel: str) -> str:
    """The regenerated text of one documented file. Does not write."""
    text = (root / rel).read_text()
    for name, render in BLOCKS[rel].items():
        text = _replace_block(text, name, render(root))
    return text


def project_manifest(root: Path) -> str | None:
    """The regenerated text of `MANIFEST`, or None when there is nothing to project.

    Only the description of the entry whose `name` matches the plugin manifest is
    projected. The marketplace's OWN top-level description is a different thing (one
    short sentence aimed at someone browsing, not the skill catalog) and is hand-written
    on purpose, so it is left alone.
    """
    pj, mj = root / PLUGIN, root / MANIFEST
    if not pj.is_file() or not mj.is_file():
        return None
    plugin = json.loads(pj.read_text())
    market = json.loads(mj.read_text())
    for entry in market.get("plugins", []):
        if entry.get("name") == plugin.get("name"):
            entry["description"] = plugin.get("description", "")
    return json.dumps(market, indent=2) + "\n"


def build(root: Path | None = None, write: bool = True) -> list[str]:
    """Regenerate every generated block. Returns the files that changed."""
    root = root or repo_root()
    changed = []
    for rel in BLOCKS:
        path = root / rel
        if not path.is_file():
            continue
        new = build_file(root, rel)
        if new != path.read_text():
            changed.append(rel)
            if write:
                path.write_text(new)

    projected = project_manifest(root)
    if projected is not None and projected != (root / MANIFEST).read_text():
        changed.append(MANIFEST)
        if write:
            (root / MANIFEST).write_text(projected)
    return changed


def check(root: Path | None = None) -> list[str]:
    """Problems that make the docs untrustworthy."""
    root = root or repo_root()
    problems = []

    sv, _ = spec_version(root)
    if sv != SPEC_VERSION:
        problems.append(
            f"spec version mismatch: SPEC.md declares v{sv}, engine SPEC_VERSION is "
            f"v{SPEC_VERSION}. Bump them in lockstep.")

    # The PUBLIC site is the credibility surface, and it is hand-designed HTML rather
    # than a generated block, so it is CHECKED instead. It claimed spec v0.5 against
    # v0.16 for weeks, in three places, sitting beside a "five layers" claim against
    # six. Collect EVERY version token rather than a few phrasings: the first attempt
    # matched "spec v0.5" and "standard · v0.5" and missed "The spec is v0.5" three
    # inches away, which is how the drift survived a sweep that was looking for it.
    site = root / "site" / "index.html"
    if site.is_file():
        allowed = {sv}
        wrong = sorted(set(re.findall(r"\bv(\d+\.\d+)\b", site.read_text())) - allowed)
        if wrong:
            problems.append(
                f"site/index.html claims v{', v'.join(wrong)}; the repo declares "
                f"v{' and v'.join(sorted(allowed))}")

    for rel in BLOCKS:
        path = root / rel
        if not path.is_file():
            problems.append(f"{rel} is missing: run `abu build-docs`")
            continue
        try:
            if build_file(root, rel) != path.read_text():
                problems.append(f"{rel} is stale: run `abu build-docs`")
        except ValueError as exc:
            problems.append(f"{rel}: {exc}")

    projected = project_manifest(root)
    if projected is not None and projected != (root / MANIFEST).read_text():
        problems.append(
            f"{MANIFEST} has drifted from {PLUGIN}: run `abu build-docs`. The plugin "
            f"manifest is the catalog of record; the marketplace entry is projected "
            f"from it.")
    return problems
