#!/usr/bin/env python3
"""Generate an entity's reference matrix as a GOLDEN CHAIN. Kind-agnostic.

ONE meta-process for every entity kind (character, setting, visual-metaphor,
prop, motif), because the problem is identical in all of them: a reference matrix
is a set whose entire purpose is AGREEING WITH ITSELF, so its shots are not
independent jobs and must never be fanned out concurrently. Text alone cannot
hold a room or a face still; N shots generated in parallel from the same prose
come back as N different subjects that merely share a description.

An image model has no persistent geometry, so AN ACCEPTED IMAGE HAS TO SERVE AS
THE GEOMETRY:

    seed (hero shot, human-blessed)
      -> shot 2   conditioned on [seed]
      -> shot 3   conditioned on [seed, 2]
      -> shot 4   conditioned on [seed, 2, 3]
    the accumulated, mutually-consistent set IS the matrix.

Only ACCEPTED shots enter the conditioning set; a defect regenerates and does not
propagate, or drift compounds down the chain.

GOLDEN IS A HUMAN GATE. This script refuses to chain off a seed nobody blessed.
Bless it explicitly (after looking at it) with --bless-seed.

Usage:
  chain_matrix.py <universe> <entity-id> --print-plan
  chain_matrix.py <universe> <entity-id> --bless-seed <shot>
  chain_matrix.py <universe> <entity-id> [--seed <shot>] [--shots a,b,c]
                  [--size WxH] [--max-conditioning N] [--skip-existing] [--dry-run]
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

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
    """The engine importable, resolved from the ABU root rather than assumed."""
    eng = str(_abu_root() / "engine")
    if eng not in sys.path:
        sys.path.insert(0, eng)
    return eng


def _provider_script(provider="gpt-image-2"):
    """The generation script, resolved rather than assumed. This script lives at
    <repo>/skills/<name>/scripts/, so the repo root is 3 up; `.resolve()` first
    because skills are installed by symlinking into ~/.claude/skills."""
    from pathlib import Path as _P
    _engine_on_path()
    from agenticstory.providers import resolve_str
    return resolve_str(provider)

# Which shot seeds the chain, per kind: the view exposing the MOST geometry, so
# the least is left for the model to invent downstream. First match wins.
HERO_BY_KIND = {
    "character":       ["turnaround", "forward-fullbody", "man", "front", "gabr", "face-3q", "face-neutral"],
    "setting":         ["c1-wide", "wide", "establishing", "turnaround", "master", "gabr"],
    "visual-metaphor": ["master", "wide", "turnaround", "hero"],
    "prop":            ["hero", "master", "sheet", "turnaround"],
    "motif":           ["hero", "master", "sheet", "gabr"],
}

def style_line(register_name: str | None, poles) -> str:
    """The register, restated IN EVERY SHOT'S PROMPT.

    The scaffolded prompts.md writes the register into the file HEADER, but the
    parser only ever sent each shot's BODY, so the style never actually reached
    the model. The file implied a guarantee it did not provide, which is exactly
    the bug already fixed for the `Negatives (every shot)` header; the register
    was the remaining instance.

    Passing the anchor IMAGE and the rejected poles as bare negatives is NOT
    enough on its own. "Character reference sheet" carries very strong
    photographic priors, and four character seeds in a row came back photoreal
    in a universe whose register explicitly rejects `photoreal` and whose anchor
    is a painting (earned 2026-07-30, The Lord Saw). Naming the medium
    positively, in the body, is what actually moves it.

    Sourced from `universe.json` (or the Style Pack) rather than from the
    markdown, so a prompts.md that forgets to mention the register still gets it.
    """
    if not register_name:
        return ""
    out = f"STYLE, AND IT OVERRIDES ANY OTHER READING OF THE REFERENCE IMAGES: render this in {register_name}."
    if poles:
        out += " It is NEVER " + ", never ".join(poles) + "."
    return out


SAME_SUBJECT = (
    "CRITICAL: every reference image after the first shows THE SAME SINGLE SUBJECT, already locked. "
    "Reproduce it EXACTLY as those images show it: the same shapes, proportions, materials, colors, "
    "markings, and the same relative placement of every element. Do NOT redesign, restyle, recolor, "
    "resize, add, or remove anything. Change ONLY the camera position and framing."
)

# For a real-person entity the PHOTOGRAPHS are the ground truth, and the accepted
# goldens are only paintings OF that truth. Without this the chain builds every
# downstream shot from a painting of a painting and the likeness drifts off the
# real face while every plate still looks internally consistent, which is the
# worst kind of failure because nothing looks wrong until someone who knows the
# person sees it.
REAL_PERSON = (
    "IDENTITY GROUND TRUTH: the PHOTOGRAPHS among the reference images are the REAL PERSON this "
    "subject depicts. Build the likeness faithfully and exactly from those photographs: bone "
    "structure, hairline, hair colour and texture, eye shape, nose, mouth, and the way the face "
    "creases when it smiles. Where a painted reference and a photograph disagree about the face, "
    "THE PHOTOGRAPH WINS. Keep the painterly rendering of the painted references and the likeness "
    "of the photographs."
)


class Refuse(Exception):
    pass


def load(p: Path):
    with open(p) as f:
        return json.load(f)


def sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()[:16]


def _header_block(text: str, name: str) -> list[str]:
    """Every item under a `**<name> (...):**` header, however many LINES it spans.

    The bug this replaces: both the Negatives and the Refs headers were read with
    `^\\*\\*Name[^:]*:\\*\\*\\s*(.+)$` under `re.M`, where `.` does not cross a newline and
    `$` stops at the first line ending. A header authored across four lines therefore
    contributed ONLY its first line and the rest was dropped in silence.

    That is not cosmetic. On gary's first seed, 5 of 18 negatives reached the model and
    `a crucifix` was among the thirteen discarded, so the pendant rendered as a plain
    Latin crucifix, which the entity's own invariant forbids by name. A render was spent
    proving a parser bug. It is the same class as the header-implies-a-guarantee defects
    already fixed twice in this file: the file states a constraint, the author believes
    it is in force, and nothing carries it to the model.

    THE SECOND BUG, introduced by the first fix and caught one render later. Ending the
    block only at the next header or EOF means a BLANK LINE does not end it, so ordinary
    prose written underneath the list was parsed as negatives: one run sent 15 junk items
    to the model, including raw markdown fragments like the sentence describing this very
    parser. Making multi-line headers safe made trailing prose unsafe, and the fix for a
    silent-drop must not become a silent-absorb.

    So the block now ends at whichever comes first: the next `**bold header:**`, ANY `#`
    heading, a `>` blockquote, or a blank line that is not followed by another list item.
    That last clause is what lets an author write the list, leave a gap, and then explain
    themselves in prose without the explanation becoming canon.

    Items separate on commas OR newlines, and a leading list marker is stripped, so every
    shape an author might reasonably write is read identically. Anything that still looks
    like markdown rather than a constraint is dropped with a warning rather than sent: a
    negative the author never wrote is as wrong as one they wrote and never got.
    """
    m = re.search(rf"^\*\*{re.escape(name)}[^:]*:\*\*[ \t]*(.*?)(?=^\s*\*\*[^*]+:\*\*|^\s*#|^\s*>|\Z)",
                  text, flags=re.M | re.S)
    if not m:
        return []

    # Stop at the first blank line whose next non-empty line is not another list item.
    lines, kept = m.group(1).split("\n"), []
    for i, line in enumerate(lines):
        if line.strip():
            kept.append(line)
            continue
        nxt = next((l for l in lines[i + 1:] if l.strip()), "")
        if not re.match(r"^\s*[-*•]\s+", nxt):
            break
        kept.append(line)

    items = []
    for chunk in re.split(r"[,\n]", "\n".join(kept)):
        chunk = re.sub(r"^\s*[-*•]\s*", "", chunk).strip()
        if not chunk:
            continue
        # A constraint is short and prose-free. Anything carrying markdown syntax or
        # running long is a paragraph that leaked in, not something an author meant the
        # model to obey. Warn rather than swallow, so the author can see and fix it.
        if len(chunk) > 120 or re.search(r"(\*\*|`|^>|\]\(|^#)", chunk):
            print(f"  WARNING: ignoring a suspicious '{name}' item, which reads like prose "
                  f"rather than a constraint: {chunk[:70]!r}", file=sys.stderr)
            continue
        items.append(chunk)
    return items


def _split_ids(s: str) -> list[str]:
    return [x.strip().strip("`") for x in re.split(r"[,\s]+", s) if x.strip().strip("`")]


def parse_prompts(md: Path) -> dict:
    """reference/<id>/prompts.md -> {shot: prompt}. A shot is an '## <name>' or
    '## <label> -> `reference/<id>/<name>.png`' heading; its body is the prompt."""
    return parse_prompts_full(md)["prompts"]


def parse_prompts_full(md: Path) -> dict:
    """Parse prompts.md into {prompts, negatives, refs}.

    Beyond the shot bodies, the file may declare two things the chain must honour:

      **Negatives (every shot):** a, b, c
          Entity-specific negatives, MERGED with the universe's rejectedPoles.
          Before this was read, a prompts.md could state a negative that never
          reached the model, so the file implied a guarantee it did not provide.

      **Refs (every shot):** other-entity-id, ...     (header, applies to all shots)
      REFS: other-entity-id, ...                      (inside a shot body, that shot only)
          CROSS-ENTITY references. A spread or plate that shows another canon
          entity must be conditioned on THAT entity's locked art, never redrawn
          from prose. REFS lines are stripped out of the prompt text.
    """
    if not md.exists():
        raise Refuse(f"no prompts.md at {md}")
    text = md.read_text()

    # An UNFILLED prompts.md is refused here, at the one place every shoot passes
    # through. `add-entity` scaffolds each body as "TODO(author): replace each body
    # below"; nothing used to check it, so an agent that met the stub wrote its prompts
    # inline in a throwaway bash script and called the model directly. That happened
    # FIVE times in one session (2026-07-30). The tool existed; the authoring step had
    # been skipped; routing around it was easier than noticing.
    # Scoped to the SHOT BODIES, deliberately. The scaffold's own header instruction is
    # the string "TODO(author): replace each body below", so a whole-file scan can only
    # be satisfied by DELETING the guidance that tells an author what a prompt must
    # contain. A refusal whose only remedy is destroying documentation is a refusal
    # people learn to route around, which is the exact behaviour this one exists to stop.
    bodies = text[text.index("\n## "):] if "\n## " in text else ""
    if TODO_MARKER in bodies:
        raise Refuse(
            f"{md} still contains {TODO_MARKER!r}. Fill the shot bodies there before "
            "shooting. Do NOT put the prompts in a one-off script instead: that is the "
            "failure this refusal exists to catch, and it loses the prompt the moment "
            "the session ends."
        )

    negatives = [n.rstrip(".") for n in _header_block(text, "Negatives")]
    header_refs = _split_ids(", ".join(_header_block(text, "Refs")))

    out, refs, sizes, cur, buf, cur_refs = {}, {}, {}, None, [], []
    for line in text.splitlines():
        m = re.match(r"^##\s+(.*)$", line)
        if m:
            if cur:
                out[cur] = " ".join(buf).strip()
                refs[cur] = list(dict.fromkeys(header_refs + cur_refs))
            head = m.group(1)
            path = re.search(r"reference/[^/]+/([A-Za-z0-9._-]+)\.png", head)
            cur = path.group(1) if path else head.split("—")[0].split("->")[0].strip()
            # PER-SHOT SIZE, declared in the heading as "(WxH)". A reference matrix
            # legitimately MIXES aspects: full-body and profiles want portrait, while
            # multi-panel sheets (expressions, era/turnaround rows) want landscape.
            # One --size for the whole matrix letterboxes the sheets into the wrong
            # canvas with dead bands, wasting most of the frame. The sizes were
            # already written here; the chain just was not reading them.
            sz = re.search(r"\((\d{3,5})\s*[xX×]\s*(\d{3,5})\)", head)
            if sz:
                sizes[cur] = f"{sz.group(1)}x{sz.group(2)}"
            buf, cur_refs = [], []
        elif cur:
            r = re.match(r"^\s*REFS:\s*(.+)$", line, flags=re.I)
            if r:
                cur_refs += _split_ids(r.group(1))
            else:
                buf.append(line.strip())
    if cur:
        out[cur] = " ".join(buf).strip()
        refs[cur] = list(dict.fromkeys(header_refs + cur_refs))

    prompts = {k: v for k, v in out.items() if v}
    return {"prompts": prompts,
            "negatives": negatives,
            "sizes": {k: sizes[k] for k in prompts if k in sizes},
            "refs": {k: refs.get(k, []) for k in prompts}}


def entity_ref_images(uroot: Path, eid: str) -> list[str]:
    """Absolute paths of another entity's LOCKED reference art, for cross-entity conditioning.

    Refuses on an unlocked/missing entity: passing prose instead of real art is the
    exact failure this exists to prevent (a mark rendered without its mark).
    """
    ent_path = uroot / "canon" / "entities" / f"{eid}.json"
    if not ent_path.exists():
        raise Refuse(f"REFS names '{eid}', which is not a canon entity")
    ent = load(ent_path)
    st = ent.get("structured") or {}
    sheets = st.get("sheets") or {}
    wanted = [s for s in (st.get("requiredForRender") or []) if sheets.get(s)]
    if not wanted:
        for k in ("master", "hero", "forward-fullbody", "sheet", "turnaround"):
            if sheets.get(k):
                wanted = [k]
                break
    if not wanted:
        raise Refuse(f"REFS names '{eid}', which has no locked reference art to pass")
    paths = []
    for s in wanted:
        p = (uroot / sheets[s]).resolve()
        if not p.exists():
            raise Refuse(f"REFS '{eid}.{s}' -> {p} (NOT ON DISK)")
        paths.append(str(p))
    return paths


def pick_seed(kind: str, shots: list[str], override: str | None) -> str:
    if override:
        if override not in shots:
            raise Refuse(f"--seed '{override}' is not one of: {', '.join(shots)}")
        return override
    for pref in HERO_BY_KIND.get(kind, []):
        for s in shots:
            if s == pref or s.startswith(pref):
                return s
    return shots[0]


def marker(refdir: Path, shot: str) -> Path:
    return refdir / f"{shot}.golden.json"


def resolve_register(uroot: Path, uni: dict, override=None):
    """Which Style Pack this matrix is shot in.

    Defaults to `identity.register`, which is correct for a universe that has
    ONE look. It is not correct for a universe where `identity.register` names
    only the DEFAULT and each look is its own Style Pack under
    `reference/style/<id>/`: there, an entity whose story declares a different
    register would have its matrix shot in a medium it is never rendered in,
    and a sheet in the wrong medium is a weaker identity reference than one in
    the right medium. Hence the override.

    Returns (universe-relative anchor path, rejected poles, register id).
    """
    if not override:
        reg = (uni.get("identity") or {}).get("register") or {}
        anchor = reg.get("anchor")
        if not anchor:
            raise Refuse(
                "identity.register.anchor is null: the universe style is not locked; "
                "do not generate")
        return anchor, list(reg.get("rejectedPoles", [])), reg.get("name")

    pack_rel = Path("reference") / "style" / override
    pack_file = uroot / pack_rel / "pack.json"
    if not pack_file.exists():
        raise Refuse(f"--register {override}: no Style Pack at {pack_file}")
    pack = load(pack_file)
    a = pack.get("anchor")
    if not a:
        raise Refuse(f"--register {override}: {pack_file} declares no anchor")
    # A pack's `anchor` is relative to the pack dir; every other path here is
    # universe-relative, so normalise it once rather than at each use site.
    anchor = str(pack_rel / a)
    if not (uroot / anchor).exists():
        raise Refuse(f"--register {override}: anchor not on disk: {uroot / anchor}")
    return anchor, list(pack.get("rejectedPoles", [])), override


def build_plan(uroot: Path, eid: str, seed_override=None, shots_override=None,
               register_override=None, look=None):
    """`look` shoots a DECLARED ALT-LOOK (an era body, a wardrobe state) instead of the
    default matrix.

    This path did not exist. `lock-shot --look` could file an era plate into
    `structured.altLooks[key].sheets`, and `make-a-book` documented at length how such a
    plate must be generated, but nothing generated one, so every era look in this
    framework was shot by a hand-written provider call or not shot at all. The second
    outcome is the dangerous one and it is silent: the look's prose says "gaunt and grey"
    while the references passed are the entity's HEALTHY plates, and a reference image
    outranks a word every time. The pose reads as prose that had no effect, and a book
    about a man being broken and remade renders him hale throughout.

    Two rules, both from `make-a-book` and both load-bearing here:

      * The look's plates live in `reference/<id>/<look>/` with their OWN prompts.md, so
        an era body never lands in the default matrix.
      * The chain seeds off the entity's FACE sheets and photo stack, NEVER off
        `forward-fullbody`. That plate is the present-day silhouette the era supersedes,
        and passing it drags the old body into the new one.
    """
    uni = load(uroot / "universe.json")
    anchor, poles, register_id = resolve_register(uroot, uni, register_override)

    ent = load(uroot / "canon" / "entities" / f"{eid}.json")
    kind = ent.get("kind", "character")
    refdir = uroot / "reference" / eid
    base_sheets = dict((ent.get("structured") or {}).get("sheets") or {})
    if look:
        declared_looks = (ent.get("structured") or {}).get("altLooks") or {}
        if look not in declared_looks:
            raise Refuse(
                f"{eid} declares no altLook {look!r}. Known: "
                f"{', '.join(sorted(declared_looks)) or '(none)'}. Declare it on the entity "
                f"first; a look invented at the command line has no invariants to read back "
                f"against.")
        refdir = refdir / look
        if not (refdir / "prompts.md").is_file():
            raise Refuse(
                f"no prompts.md at {refdir}. An alt-look needs its OWN prompt bodies: the "
                f"default matrix describes the body this look supersedes.")
    parsed = parse_prompts_full(refdir / "prompts.md")
    prompts = parsed["prompts"]

    shots = shots_override or list(prompts.keys())
    missing = [s for s in shots if s not in prompts]
    if missing:
        raise Refuse(f"no prompt block for: {', '.join(missing)}")

    if not shots:
        raise Refuse(
            f"no shot blocks found in {refdir / 'prompts.md'}.\n"
            "Every shot MUST be a level-2 heading of the form:\n"
            "  ## <shot-name> -> `reference/<entity>/<shot-name>.png`"
        )

    # The shot headings in prompts.md MUST be the entity's declared sheet names.
    # Without this check a prompts.md authored with '###' shot blocks parses its
    # PROSE headings as the shot list, and the chain silently generates garbage
    # conditioned on nothing instead of failing. Refuse loudly instead.
    declared = set(((ent.get("structured") or {}).get("altLooks", {}).get(look, {}) or {})
                   .get("sheets") or {}) if look else set(base_sheets)
    if look and not declared:
        declared = set()          # a look shot for the first time has no sheets yet
    if declared:
        bogus = [s for s in shots if s not in declared]
        if bogus:
            raise Refuse(
                f"prompts.md shot headings do not match {eid}'s declared sheets.\n"
                f"  parsed:   {', '.join(shots)}\n"
                f"  declared: {', '.join(sorted(declared))}\n"
                f"  unknown:  {', '.join(bogus)}\n"
                "Every shot MUST be a level-2 heading of the form:\n"
                "  ## <shot-name> -> `reference/<entity>/<shot-name>.png`\n"
                "Prose sections must be level-3 or deeper, or they are read as shots."
            )

    # A real person's photo stack is ground truth for the likeness and must ride
    # along on EVERY shot, not just the seed. Refuse on a declared-but-missing
    # photo, the same discipline as a missing cross-entity ref: a path that does
    # not resolve is a silent downgrade to "invent the face from prose".
    # The FACE sheets of the DEFAULT matrix, passed on every shot of an alt-look.
    # `make-a-book`: generate an era look from the FACE, never from the body, because
    # forward-fullbody is the present-day silhouette this look supersedes and a
    # reference image outranks any number of words.
    look_refs = []
    if look:
        al = ((ent.get("structured") or {}).get("altLooks") or {}).get(look) or {}
        # A look's OWN anchorPhoto and photoStack outrank the base face sheets, because a
        # look that carries them exists precisely to REPLACE the face, and `compose-spread`
        # already treats anchorPhoto that way at render time. Shooting the look from base
        # sheets while rendering it from anchorPhoto would build the matrix off one face
        # and then hand the spreads another.
        for rel in ([al.get("anchorPhoto")] if al.get("anchorPhoto") else []) + list(
                al.get("photoStack") or []):
            q = (uroot / rel).resolve()
            if not q.exists():
                raise Refuse(f"{eid}.altLooks.{look} names {rel} (NOT ON DISK)")
            if str(q) not in look_refs:
                look_refs.append(str(q))
        if not look_refs:
            for k in ("face-neutral", "face-3q", "expressions"):
                rel = base_sheets.get(k)
                if rel:
                    q = (uroot / rel).resolve()
                    if q.exists():
                        look_refs.append(str(q))
        # No face reference at all is NOT an error. Some looks exist to introduce a face
        # the default matrix never had: `the-lord`'s default look holds his face inside
        # his light and resolves nothing, so a "revealed" look has no prior face to
        # inherit and must be seeded from the register anchor alone.
        if not look_refs:
            print(f"note: {eid} has no locked FACE sheet and {look!r} declares no anchorPhoto; "
                  f"seeding from the register anchor alone. The look DEFINES this face.")

    # ONE implementation of the photo-stack rule, shared with the render-time assembler
    # (v0.21). A DIRECTORY entry expands to the images inside it, which is the form SPEC
    # §12 calls idiomatic, and `realPerson.photoLimit` caps the result AFTER expansion.
    # This used to refuse a directory outright and never read the cap, so the idiomatic
    # stack could be RENDERED from and not SHOT from, and a declared ceiling was honored
    # at render time and ignored here. Earned 2026-08-01 on christofuturism `gary`.
    _engine_on_path()
    from agenticstory.refs import photo_stack as _photo_stack
    try:
        photos = _photo_stack(ent, uroot)
    except FileNotFoundError as e:
        raise Refuse(f"{eid}.realPerson.photoStack: {e}")

    seed = pick_seed(kind, shots, seed_override)
    rest = [s for s in shots if s != seed]
    return {
        "entity": eid, "kind": kind, "anchor": anchor, "refdir": refdir,
        "register": register_id, "look": look, "lookRefs": look_refs,
        "photos": photos,
        "seed": seed, "order": [seed] + rest, "prompts": prompts,
        # register rejectedPoles FIRST, then the entity's CANON negatives, then the
        # ones authored in prompts.md. All three reach the model; none is dropped.
        #
        # `structured.negatives` (SPEC v0.23) is the entity's person-scoped negative set,
        # and `compose-spread` has honoured it since the day it shipped. This shooter did
        # not, so the same rules had to be written TWICE: once in canon for every scene
        # that casts the entity, once in prompts.md for the shoot that defines it, with
        # nothing keeping the two in sync. That is exactly the duplication v0.23 existed
        # to remove, and it had a real consequence: the plates that DEFINE a character
        # were shot under a different negative set than every render that later casts
        # them. Reading it here makes canon the single source and prompts.md the
        # shoot-specific addition.
        "negatives": list(dict.fromkeys(
            poles
            + list((ent.get("structured") or {}).get("negatives") or [])
            + parsed["negatives"])),
        # The register's OWN rejected poles, kept separate from the merged
        # negative list so the style line names the medium's opposites and not
        # every prop the entity happens to forbid.
        "poles": list(poles),
        "refs": parsed["refs"],
        "sizes": parsed.get("sizes", {}),
        "uroot": uroot,
    }


TODO_MARKER = "TODO(author)"


def _unused_refuse_unfilled_prompts(prompts_path, shots):
    """Refuse to shoot from a prompts.md nobody filled in.

    `add-entity` scaffolds every shot body as `TODO(author): replace each body below`.
    Nothing used to check it, so an agent that found the stub simply wrote its prompts
    inline in a throwaway bash script and called the model directly. That happened FIVE
    times in one session (2026-07-30): the tool existed, the authoring step had been
    skipped, and routing around it was easier than noticing.

    Failing loudly here is the whole point. The fix is to write the prompts into
    `prompts.md`, where they are versioned, reviewable, and reused on every re-run,
    rather than into a script that is deleted at the end of the session.
    """
    try:
        body = Path(prompts_path).read_text()
    except OSError:
        return
    if TODO_MARKER not in body:
        return
    stale = [s for s in shots if TODO_MARKER in _section_for(body, s)] if shots else []
    raise SystemExit(
        f"chain_matrix: {prompts_path} still contains {TODO_MARKER!r}"
        + (f" for: {', '.join(stale)}" if stale else "")
        + ".\n  Fill the shot bodies in prompts.md before shooting. Do NOT write the"
        "\n  prompts into a one-off script instead: that is the failure this refusal"
        "\n  exists to catch, and it loses the prompt the moment the session ends."
    )


def _section_for(body, shot):
    """The prompt body under `## <shot>`, tolerant of the `## <shot> -> path` form."""
    import re as _re
    m = _re.search(rf"^##\s+{_re.escape(shot)}\b.*?$(.*?)(?=^##\s|\Z)", body, _re.M | _re.S)
    return m.group(1) if m else ""


def _shoot(plan, shot, goldens, args, anchor_abs, neg, refdir, uroot) -> int:
    """Generate ONE shot and write its recipe. Returns 0 on success.

    Extracted from the chain loop so `--shoot-seed` can use the SAME code path.
    Before this, the refusal on an unblessed seed told the operator to "generate it
    alone", which is the framework instructing you to leave the framework: the seed
    got shot by a hand-written provider call, so it carried no recipe, no register
    line and no size from prompts.md, and it was the one plate every other shot in
    the matrix would inherit from. The human gate is still a human gate. Only the
    hand-rolling is gone.
    """
    out = refdir / f"{shot}.png"
    # STYLE FIRST. The register leads every shot body, because the medium is
    # the thing a reference sheet drifts off first and the anchor image alone
    # does not hold it. See style_line().
    prompt = " ".join(x for x in [style_line(plan["register"], plan["poles"]),
                                  plan["prompts"][shot], SAME_SUBJECT,
                                  REAL_PERSON if plan["photos"] else "", neg] if x)
    # Per-shot size when prompts.md declared one; --size is only the fallback.
    shot_size = plan["sizes"].get(shot, args.size)
    # CONDITIONING WINDOW. Identity is carried by the blessed seed plus the few
    # most recent accepted shots, NOT by every golden ever made: the back view
    # adds payload, not likeness. Passing all of them grows the request at every
    # step until the tail of a big matrix dies on an API timeout, which is the
    # worst place to fail because those shots are the most expensive to redo.
    cond = goldens
    if args.max_conditioning and len(goldens) > args.max_conditioning:
        cond = [goldens[0]] + goldens[-(args.max_conditioning - 1):]
    cmd = ["uv", "run", _provider_script(), "--prompt", prompt, "--filename", str(out),
           "--size", shot_size, "--quality", "high", "--no-open",
           "--input-image", anchor_abs]
    # photographs BEFORE the painted goldens: the likeness is the thing the
    # chain must not drift on, and later references carry more weight.
    for ph in plan["photos"]:
        cmd += ["--input-image", ph]
    # LOOK REFS ARE FOR THE SEED ONLY. They are the DEFAULT matrix's face sheets,
    # passed so the first plate of an alt-look has an identity to be built from. Once
    # the look has its own blessed plate, those defaults become a liability: they carry
    # the very body the look supersedes, and a reference image outranks a word. Passing
    # them to the second shot of the `wasted` era returned a hale man in a blazer,
    # against a prompt that asked for a thinner man in loose plain clothes.
    if not goldens:
        for lr in plan.get("lookRefs") or []:
            cmd += ["--input-image", lr]
    for g in cond:
        cmd += ["--input-image", g]
    # Cross-entity refs: another entity in frame is conditioned on ITS locked
    # art, never redrawn from prose. Collected rather than only appended, because the
    # recipe below has to be able to name them (see crossEntityRefs).
    cross = []
    for other in plan["refs"].get(shot, []):
        for p in entity_ref_images(plan["uroot"], other):
            cmd += ["--input-image", p]
            cross.append({"entity": other, "path": p, "sha256_16": sha(Path(p))})
    rc = subprocess.run(cmd).returncode
    if rc != 0 or not out.exists():
        print(f"{shot}: FAILED rc={rc}; chain STOPS (a defect must not propagate)", file=sys.stderr)
        return 1
    # provenance travels with the asset (nothing is a mystery)
    (refdir / f"{shot}.recipe.json").write_text(json.dumps({
        "shot": shot, "entity": plan["entity"], "kind": plan["kind"],
        "model": "gpt-image-2", "size": shot_size, "prompt": prompt,
        "anchor": {"path": plan["anchor"], "sha256_16": sha(Path(anchor_abs))},
        "photoStack": [{"path": p, "sha256_16": sha(Path(p))} for p in plan["photos"]],
        "conditionedOn": [{"path": g, "sha256_16": sha(Path(g))} for g in cond],
        # CROSS-ENTITY REFS BELONG IN THE RECIPE, not only on the command line.
        #
        # This sidecar recorded anchor + photoStack + conditionedOn and silently omitted
        # every image resolved from a shot's `REFS:` line. On gary's seed that was 3 of
        # 13 inputs, all three of them the north-star-cross mark plates. It matters
        # because `lock-shot --recipe` freezes provenance from EXACTLY this file: a
        # golden locked from it would record an approval against inputs it was never
        # approved against, and no future divergence check could notice the mark plates
        # changing underneath it. Under-reporting provenance is the one thing a
        # provenance writer may not do.
        "crossEntityRefs": cross,
        "method": ("golden-chain (sequential; each shot conditions on the blessed seed "
                   f"plus the most recent accepted shots, window={args.max_conditioning or 'unbounded'})"),
    }, indent=1))
    print(f"{shot}: OK (conditioned on {len(cond)} golden(s), size {shot_size})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("universe")
    ap.add_argument("entity")
    ap.add_argument("--seed")
    ap.add_argument("--shots")
    ap.add_argument("--size", default="1536x1024",
                    help="FALLBACK size only. A shot whose prompts.md heading declares "
                         "'(WxH)' uses that instead, so one matrix can mix portrait "
                         "full-bodies with landscape multi-panel sheets.")
    ap.add_argument("--max-conditioning", type=int, default=4, metavar="N",
                    help="Cap on accepted goldens passed as conditioning (default 4). "
                         "The blessed SEED is always kept and the most recent N-1 "
                         "accepted shots ride along. Unbounded accumulation makes every "
                         "step a larger upload than the last until the final shots of a "
                         "big matrix time out. 0 disables the cap.")
    ap.add_argument("--register", metavar="ID",
                    help="Shoot the matrix in the Style Pack at "
                         "reference/style/<ID>/ instead of the universe's "
                         "identity.register. For a MULTI-REGISTER universe, where "
                         "identity.register names only the default and each look is "
                         "its own pack: an entity whose story declares a different "
                         "register needs its sheets shot in the medium it is actually "
                         "rendered in. Defaults to the universe register.")
    ap.add_argument("--skip-existing", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--print-plan", action="store_true")
    ap.add_argument("--bless-seed", metavar="SHOT",
                    help="record HUMAN approval of the seed so the chain may proceed")
    ap.add_argument("--look", default=None,
                    help="shoot a declared altLook (an era body, a wardrobe state) into "
                         "reference/<id>/<look>/ instead of the default matrix. The chain seeds "
                         "off the FACE and the photo stack, never off forward-fullbody, which is "
                         "the silhouette the look supersedes")
    ap.add_argument("--shoot-seed", action="store_true",
                    help="generate the seed shot ALONE (anchor + photo stack only, no goldens) "
                         "and stop, so a human can look at it and then --bless-seed it")
    args = ap.parse_args()

    uroot = Path(args.universe)
    try:
        plan = build_plan(uroot, args.entity, args.seed,
                          args.shots.split(",") if args.shots else None,
                          register_override=args.register, look=args.look)
    except Refuse as e:
        print(f"REFUSE: {e}", file=sys.stderr)
        return 2

    refdir, seed = plan["refdir"], plan["seed"]

    if args.bless_seed:
        shot = args.bless_seed
        img = refdir / f"{shot}.png"
        if not img.exists():
            print(f"REFUSE: cannot bless '{shot}': {img} does not exist", file=sys.stderr)
            return 2
        marker(refdir, shot).write_text(json.dumps(
            {"shot": shot, "sha256_16": sha(img), "blessedBy": "human",
             "note": "Golden is a human gate. This marker records that a person looked at this "
                     "seed and approved it; the chain conditions every later shot on it."}, indent=1))
        print(f"blessed seed: {shot}")
        return 0

    if args.print_plan or args.dry_run:
        print(f"entity={plan['entity']} kind={plan['kind']} "
              f"register={plan['register'] or '(universe default)'}")
        print(f"seed (hero) = {seed}")
        for i, s in enumerate(plan["order"]):
            # Show the ACTUAL conditioning window, not every prior shot: a plan that
            # advertises conditioning the run will not perform is worse than no plan.
            prior = plan["order"][:i]
            if args.max_conditioning and len(prior) > args.max_conditioning:
                prior = [prior[0], "..."] + prior[-(args.max_conditioning - 1):]
            cond = "HUMAN-BLESSED SEED" if i == 0 else \
                   "anchor + " + ", ".join(prior)
            xrefs = plan["refs"].get(s) or []
            if xrefs and i > 0:
                cond += " + refs(" + ", ".join(xrefs) + ")"
            sz = plan["sizes"].get(s, args.size)
            print(f"  {i+1}. {s:<18} [{sz}] conditioned on: {cond}")
        if plan["negatives"]:
            print("negatives: " + ", ".join(plan["negatives"]))
        # The photographs ride on EVERY shot and they are the identity ground truth, so
        # the plan states which ones resolved. A stack declared as a directory used to be
        # invisible here, which meant the one thing worth checking before spending money
        # (are these the right faces, and how many are they) could not be checked.
        if plan["photos"]:
            print(f"photo stack ({len(plan['photos'])}, passed on every shot):")
            for ph in plan["photos"]:
                print(f"  - {Path(ph).name}")
        blessed = marker(refdir, seed).exists()
        print(f"seed blessed: {blessed}" + ("" if blessed else "  <-- chain will REFUSE"))
        return 0

    neg = ("NEGATIVES: " + ", ".join(plan["negatives"]) + ".") if plan["negatives"] else ""
    anchor_abs = str((uroot / plan["anchor"]).resolve())

    if args.shoot_seed:
        # No goldens. The seed is the first painted thing this entity has, so it is
        # conditioned on the register anchor and (for a real person) the photographs,
        # and on nothing else. It is deliberately NOT blessed here: a run that shot
        # its own seed and then approved it would have no human in the loop at all,
        # which is the one thing this whole chain exists to prevent.
        rc = _shoot(plan, seed, [], args, anchor_abs, neg, refdir, uroot)
        if rc != 0:
            return rc
        print(f"\nSEED SHOT, NOT BLESSED: {refdir / (seed + '.png')}")
        print("Look at it with a human. If it is right:")
        print(f"  chain_matrix.py <universe> {plan['entity']} --bless-seed {seed}")
        print("If it is wrong, re-run --shoot-seed. Nothing downstream exists yet, so a "
              "bad seed costs one image and not a matrix.")
        return 0

    # The human gate. Golden is not something the agent may award itself.
    if not marker(refdir, seed).exists():
        img = refdir / f"{seed}.png"
        how = ("--shoot-seed to generate it" if not img.exists()
               else f"--bless-seed {seed} once a human has looked at it")
        print(f"REFUSE: seed '{seed}' is not blessed. Run: chain_matrix.py <universe> "
              f"{plan['entity']} {how}", file=sys.stderr)
        return 2

    goldens = [str((refdir / f"{seed}.png").resolve())]
    if not Path(goldens[0]).exists():
        print(f"REFUSE: blessed seed image missing: {goldens[0]}", file=sys.stderr)
        return 2

    for shot in plan["order"][1:]:
        out = refdir / f"{shot}.png"
        if args.skip_existing and out.exists():
            print(f"{shot}: exists, skip")
            goldens.append(str(out.resolve()))
            continue
        if _shoot(plan, shot, goldens, args, anchor_abs, neg, refdir, uroot) != 0:
            return 1
        goldens.append(str(out.resolve()))

    print(f"CHAIN COMPLETE: {len(goldens)} mutually-consistent shot(s). "
          f"Read back each, then lock-shot the passers.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
