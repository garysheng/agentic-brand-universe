# Wiki Hero Local Engine (Unit A) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make a freshly forked wiki able to render a multipanel article hero on a machine that has no ABU, no `~/.agents`, and no prior image experience.

**Architecture:** One door (`illustrations/scripts/render-hero.sh`) reads `hero_register.mode` from `wiki.config.json` and routes to a vendored, self-contained generator in `local` mode. The generator owns the register, the panel law, and the five-artifact output contract, so no page author has to remember them. A `--dry-run` flag prints the assembled prompt without calling the API, which is what makes every test in this plan free.

**Tech Stack:** bash, python3 via `uv` (PEP 723 inline deps), OpenAI `gpt-image-2`, Pillow, `cwebp`, Docusaurus 3.

**Source spec:** `docs/superpowers/specs/2026-08-03-wiki-article-hero-design.md`

**Repo under change:** `~/Documents/github-repos/supersuit-repos/wiki-template`
(plus two hosted generators in `~/Documents/github-repos/supersuit-repos/truth-management-wiki/static/generators/`, and one global skill file)

## Global Constraints

- **No em dashes** in any prose, code comment, doc, or commit message you WRITE. Two em dashes appear in this plan inside quotations of text that already exists in the repo (the `init-wiki.sh` prompt at line 708, the SPEC heading at line 817). Those are exact-match strings you have to find before replacing. Do not "fix" them or the match fails.
- **No `~/.agents/...` path may appear** anywhere under `illustrations/` or `scripts/`. This is the bug the whole unit exists to kill. Verify with `grep -rn "\.agents/skills" illustrations/ scripts/` returning nothing.
- **Multipanel is the default**, 3 panels, `--single` is the documented exception.
- **The five-artifact output contract**, for slug `<s>`, emitted on every successful render:
  1. `static/img/illustrations/<s>.webp` (deploy asset, what MDX embeds)
  2. `illustrations/<s>.png` (source archive, never deleted)
  3. `static/img/illustrations/<s>.webp.recipe.json` (provenance, beside the SHIPPED asset)
  4. alt text in the MDX = the verbatim prompt
  5. frontmatter `image: "/img/illustrations/<s>.webp"`
- **MDX embeds `.webp`, never `.png`.**
- **Model default:** `gpt-image-2`. **Size:** `1536x1024`. **Quality:** `high`.
- **`openai>=2.48` is a load-bearing floor**, not tidiness. Older SDKs hang on multi-image edit calls. Copy the floor verbatim into vendored PEP 723 headers.
- **Commits use Gary's real git identity.** Never pass `-c user.email=`. Never add `Co-Authored-By: Claude` or "Generated with Claude Code" to any commit or PR body.
- **Do not push.** Every task commits locally. Pushing waits for an explicit go.

## File Structure

| File | Responsibility |
|---|---|
| `illustrations/scripts/generate.py` | CREATE. Vendored OpenAI adapter. Prompt in, PNG plus recipe out. Knows nothing about wikis. |
| `illustrations/scripts/prompt_guards.py` | CREATE. Vendored standing guards. Imported by `generate.py`. |
| `illustrations/scripts/check_panels.py` | CREATE. Pure image geometry. Counts panels in a rendered strip. No API, no network. |
| `illustrations/scripts/render-hero.sh` | CREATE. The one door. Config reading, register assembly, panel law, preflights, contract emission. |
| `illustrations/scripts/tests/test_check_panels.py` | CREATE. Synthetic-image tests for the panel counter. |
| `illustrations/scripts/tests/test_render_hero.sh` | CREATE. Dry-run tests for the door. No API calls. |
| `illustrations/scripts/render-page.sh` | DELETE. Replaced by `render-hero.sh`. |
| `scripts/render-graphic.sh` | DELETE. Depends on the retired hosted brand OS and exits 1 on the shipped config. |
| `illustrations/SPEC.md` | MODIFY. Multipanel law replaces the single-focal-scene rule. Character becomes opt-in. |
| `wiki.config.json` | MODIFY. Drop `brand_os_url`, add `hero_register`. |
| `wiki.config.schema.json` | MODIFY. Same shape change. |
| `scripts/init-wiki.sh` | MODIFY. Repurpose prompt 7. Count stays 11. |
| `truth-management-wiki/static/generators/starting-your-own-wiki/GENERATE.md` | MODIFY. New key-and-register phase, rename every `render-page.sh` reference. |
| `truth-management-wiki/static/generators/gamify-your-learning-wiki/GENERATE.md` | MODIFY. Q4 sets a register, seeded posts get heroes. |
| `~/.agents/skills/start-new-wiki/SKILL.md` | MODIFY. The documented `printf` slot 7 changed meaning. |

---

### Task 1: Vendor the generator

**Files:**
- Create: `illustrations/scripts/generate.py`
- Create: `illustrations/scripts/prompt_guards.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces: a CLI other tasks shell out to.
  `uv run illustrations/scripts/generate.py --prompt STR --filename PATH [--input-image PATH]... [--size WxH] [--quality high|medium|low] [--model NAME] [--no-guards]`
  Writes `<filename>` and `<filename>.recipe.json`. Exits 1 with a named fix when `OPENAI_API_KEY` is unset.

- [ ] **Step 1: Copy the two source files**

```bash
cd ~/Documents/github-repos/supersuit-repos/wiki-template
mkdir -p illustrations/scripts/tests
cp ~/.agents/skills/chatgpt-images/scripts/prompt_guards.py illustrations/scripts/prompt_guards.py
cp ~/.agents/skills/chatgpt-images/scripts/generate_image.py illustrations/scripts/generate.py
```

- [ ] **Step 2: Add the vendoring header to `generate.py`**

Insert immediately after the PEP 723 block (which must keep `openai>=2.48` verbatim), replacing nothing else:

```python
"""
Vendored image generator for this wiki.

ORIGIN: chatgpt-images/scripts/generate_image.py. This is a deliberate COPY, not a
symlink and not an import. A wiki must render on a laptop that has never heard of
that skill, so portability beats staying in sync. If you are fixing a bug that also
exists upstream, fix it in both places.

Deps install themselves: `uv run` reads the PEP 723 block above. The openai floor is
load-bearing. Older SDKs hang on multi-image edit calls with the socket open and the
process at 0 percent CPU, which reads as a slow API rather than a broken client.
"""
```

- [ ] **Step 3: Point the recipe at the vendored path**

In the `write_recipe` function, change the `generator` field so provenance names the file that actually ran:

```python
        "generator": "illustrations/scripts/generate.py",
```

- [ ] **Step 4: Verify the key error names the fix**

Confirm `get_api_key` prints an actionable message. Replace its body with:

```python
def get_api_key(provided: str | None) -> str:
    key = provided or os.environ.get("OPENAI_API_KEY")
    if not key:
        print(
            "Error: OPENAI_API_KEY is not set.\n"
            "\n"
            "  1. Get a key at https://platform.openai.com/api-keys\n"
            "  2. export OPENAI_API_KEY='sk-...'\n"
            "  3. Add that same line to ~/.zshrc so it survives a new terminal.\n"
            "\n"
            "Images are billed to your own OpenAI account, so the key is yours.",
            file=sys.stderr,
        )
        sys.exit(1)
    return key
```

- [ ] **Step 5: Prove it runs and refuses correctly**

```bash
cd ~/Documents/github-repos/supersuit-repos/wiki-template
env -u OPENAI_API_KEY uv run illustrations/scripts/generate.py \
  --prompt "x" --filename /tmp/x.png; echo "exit=$?"
```

Expected: the three-step message above, `exit=1`. No traceback.

- [ ] **Step 6: Prove no private path survived**

```bash
grep -rln "\.agents/skills" illustrations/
```

Expected at THIS point: exactly one file, `illustrations/scripts/render-page.sh`, which
Task 5 deletes. The clean check only becomes possible after that deletion, so do not
expect zero hits here.

Do NOT satisfy this by explaining the old path in a comment. The vendoring note in
`generate.py` deliberately describes it in words rather than spelling it, because a
blunt grep that its own documentation trips is a check people learn to ignore. Keep the
check blunt and keep the literal path out of the tree.

- [ ] **Step 7: Commit**

```bash
git add illustrations/scripts/generate.py illustrations/scripts/prompt_guards.py
git commit -m "Vendor the image generator into the template

A forked wiki called ~/.agents/skills/chatgpt-images/..., which exists only on
the author's machine, so the one documented image interface died with
No such file or directory on first use."
```

---

### Task 2: The panel checker

**Files:**
- Create: `illustrations/scripts/check_panels.py`
- Test: `illustrations/scripts/tests/test_check_panels.py`

**Interfaces:**
- Consumes: nothing.
- Produces: `count_panels(path: str, *, min_gutter_px: int = 8) -> int`, importable, and a CLI
  `uv run illustrations/scripts/check_panels.py <image.png> --expect N` exiting 0 on match, 1 on mismatch.

A multipanel law that nothing checks is exactly how the single-plate default survived for weeks. This is the check.

- [ ] **Step 1: Write the failing test**

Create `illustrations/scripts/tests/test_check_panels.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Panel counting is pure geometry, so it is testable with synthetic images and
costs nothing. The failure that matters is a single plate passing as a strip."""
import importlib.util, pathlib, tempfile, unittest
from PIL import Image, ImageDraw

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("cp", HERE.parent / "check_panels.py")
cp = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(cp)

CREAM = (255, 250, 236)


def strip(path, panels, w=1536, h=1024, gutter=40):
    """A synthetic strip: N dark blocks on cream, separated by cream gutters."""
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    total_gutter = gutter * (panels - 1)
    pw = (w - total_gutter) // panels
    for i in range(panels):
        x0 = i * (pw + gutter)
        d.rectangle([x0, 0, x0 + pw, h], fill=(40, 40, 60))
    img.save(path)
    return path


def plate(path, w=1536, h=1024):
    """A single plate: one continuous image, no gutters."""
    img = Image.new("RGB", (w, h), CREAM)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, w, h], fill=(40, 40, 60))
    img.save(path)
    return path


class TestCountPanels(unittest.TestCase):
    def test_three_panel_strip_counts_three(self):
        with tempfile.TemporaryDirectory() as t:
            p = strip(pathlib.Path(t) / "a.png", 3)
            self.assertEqual(cp.count_panels(p), 3)

    def test_four_panel_strip_counts_four(self):
        with tempfile.TemporaryDirectory() as t:
            p = strip(pathlib.Path(t) / "b.png", 4)
            self.assertEqual(cp.count_panels(p), 4)

    def test_single_plate_counts_one(self):
        with tempfile.TemporaryDirectory() as t:
            p = plate(pathlib.Path(t) / "c.png")
            self.assertEqual(cp.count_panels(p), 1)

    def test_a_plate_does_not_pass_as_a_strip(self):
        """The regression this file exists for."""
        with tempfile.TemporaryDirectory() as t:
            p = plate(pathlib.Path(t) / "d.png")
            self.assertNotEqual(cp.count_panels(p), 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
```

- [ ] **Step 2: Run it to make sure it fails**

```bash
cd ~/Documents/github-repos/supersuit-repos/wiki-template
uv run illustrations/scripts/tests/test_check_panels.py
```

Expected: FAIL. `FileNotFoundError` or `ModuleNotFoundError` for `check_panels.py`.

- [ ] **Step 3: Write the implementation**

Create `illustrations/scripts/check_panels.py`:

```python
#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow"]
# ///
"""Count the panels in a rendered hero.

A gutter is a full-height run of columns that is uniformly light. So: reduce the
image to one number per column (how much variation that column contains), mark the
flat-and-light columns, and count the interior runs of them. Panels = interior runs
plus one.

Outer margins are ignored, because a strip is normally drawn with breathing room at
both edges and counting those as gutters would report N+2 panels forever.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageStat


def _flat_light_columns(img, flat_max, light_min):
    """One bool per column: is this column near-uniform AND bright."""
    w, h = img.size
    out = []
    for x in range(w):
        col = img.crop((x, 0, x + 1, h))
        st = ImageStat.Stat(col)
        out.append(st.stddev[0] <= flat_max and st.mean[0] >= light_min)
    return out


def count_panels(path, *, min_gutter_px: int = 8, flat_max: float = 6.0,
                 light_min: float = 200.0) -> int:
    img = Image.open(path).convert("L")
    flags = _flat_light_columns(img, flat_max, light_min)
    w = len(flags)

    # Walk in from both edges: leading and trailing gutter-ish columns are margins.
    start = 0
    while start < w and flags[start]:
        start += 1
    end = w - 1
    while end > start and flags[end]:
        end -= 1

    runs, run = 0, 0
    for x in range(start, end + 1):
        if flags[x]:
            run += 1
        else:
            if run >= min_gutter_px:
                runs += 1
            run = 0
    if run >= min_gutter_px:
        runs += 1

    return runs + 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Count panels in a rendered hero.")
    ap.add_argument("image")
    ap.add_argument("--expect", type=int, help="Exit 1 unless the count matches.")
    a = ap.parse_args()

    if not Path(a.image).exists():
        print(f"check_panels: no such file: {a.image}", file=sys.stderr)
        return 1

    n = count_panels(a.image)
    print(f"panels: {n}")
    if a.expect is not None and n != a.expect:
        print(
            f"check_panels: expected {a.expect} panels, found {n}.\n"
            f"  A hero is a STRIP OF BEATS. If this rendered as one plate, the layout\n"
            f"  law did not reach the model. Re-render; do not edit the image.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
uv run illustrations/scripts/tests/test_check_panels.py
```

Expected: `Ran 4 tests` / `OK`.

- [ ] **Step 5: Prove the test bites**

Temporarily make `count_panels` always `return 3`, re-run, and confirm `test_single_plate_counts_one` and `test_a_plate_does_not_pass_as_a_strip` FAIL. Then revert. A test written against code that already passes proves only that it compiles.

- [ ] **Step 6: Commit**

```bash
git add illustrations/scripts/check_panels.py illustrations/scripts/tests/test_check_panels.py
git commit -m "Add the panel checker

The multipanel law had nothing enforcing it, which is how the template kept
shipping a single-focal-scene rule after that rule was reversed."
```

---

### Task 3: The one door

**Files:**
- Create: `illustrations/scripts/render-hero.sh`
- Test: `illustrations/scripts/tests/test_render_hero.sh`

**Interfaces:**
- Consumes: `generate.py` and `check_panels.py` from Tasks 1 and 2.
- Produces: `./illustrations/scripts/render-hero.sh [--panels N|--single] [--dry-run] <slug> "<scene>"`.
  On success emits contract artifacts 1 to 3 and prints the MDX and frontmatter lines for 4 and 5.
  `--dry-run` prints the assembled prompt and resolved refs, calls no API, exits 0.

- [ ] **Step 1: Write the failing test**

Create `illustrations/scripts/tests/test_render_hero.sh`:

```bash
#!/usr/bin/env bash
# Dry-run tests for the hero door. No API calls, no cost.
set -uo pipefail
cd "$(dirname "$0")/../../.." || exit 1
DOOR=./illustrations/scripts/render-hero.sh
pass=0; fail=0
check() { # check <label> <expected-substring> <actual>
  if printf '%s' "$3" | grep -qF "$2"; then
    echo "ok   - $1"; pass=$((pass+1))
  else
    echo "FAIL - $1"; echo "       wanted: $2"; fail=$((fail+1))
  fi
}

out=$($DOOR --dry-run hero-test "a scene" 2>&1)
check "multipanel is the default"      "3 CLEAR PANELS"           "$out"
check "panel law names beats"          "one BEAT of the same"     "$out"
check "no-text law present"            "NO TEXT ANYWHERE"         "$out"
check "scene reaches the prompt"       "a scene"                  "$out"

out=$($DOOR --dry-run --panels 4 hero-test "a scene" 2>&1)
check "--panels 4 honored"             "4 CLEAR PANELS"           "$out"

out=$($DOOR --dry-run --single hero-test "a scene" 2>&1)
check "--single drops the panel law"   "single elegant editorial" "$out"

out=$($DOOR --dry-run hero-test "a glossy 3D photorealistic scene" 2>&1)
check "banned vocabulary refused"      "banned vocabulary"        "$out"

out=$($DOOR 2>&1)
check "usage on no args"               "Usage:"                   "$out"

echo
echo "passed: $pass  failed: $fail"
[ "$fail" -eq 0 ]
```

```bash
chmod +x illustrations/scripts/tests/test_render_hero.sh
```

- [ ] **Step 2: Run it to make sure it fails**

```bash
./illustrations/scripts/tests/test_render_hero.sh
```

Expected: every check FAILs, because `render-hero.sh` does not exist.

- [ ] **Step 3: Write the implementation**

Create `illustrations/scripts/render-hero.sh`:

```bash
#!/usr/bin/env bash
# The ONE door for this wiki's article heroes.
#
#   ./illustrations/scripts/render-hero.sh <slug> "<scene, beat by beat>"
#   ./illustrations/scripts/render-hero.sh --panels 4 <slug> "<scene>"
#   ./illustrations/scripts/render-hero.sh --single <slug> "<scene>"
#   ./illustrations/scripts/render-hero.sh --dry-run <slug> "<scene>"
#
# The register, the panel law and the no-text law live HERE, not in the caller, so
# every page gets them without the author remembering. That is the whole point of a
# generator owning them.
#
# Emits the five-artifact contract:
#   static/img/illustrations/<slug>.webp            the deploy asset
#   illustrations/<slug>.png                        the source archive
#   static/img/illustrations/<slug>.webp.recipe.json  provenance
#   plus the MDX alt-text line and the frontmatter line, printed for you to paste.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

MODE="multipanel"
PANELS=3
DRY_RUN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --single)  MODE="single"; shift ;;
    --panels)  PANELS="$2"; shift 2 ;;
    --dry-run) DRY_RUN=true; shift ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) break ;;
  esac
done

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 [--panels N|--single] [--dry-run] <slug> \"<scene>\""
  echo "  slug:  page slug, no extension (e.g. the-context-floor)"
  echo "  scene: the argument, beat by beat"
  echo "  Multipanel at 3 beats is the default. --single is the exception."
  exit 1
fi

SLUG="${1%.png}"
SCENE="$2"

# --- Config -----------------------------------------------------------------
CONFIG="$REPO_ROOT/wiki.config.json"
[[ -f "$CONFIG" ]] || { echo "ERROR: no wiki.config.json at $CONFIG" >&2; exit 1; }

read_cfg() { # read_cfg <python-expression-on-`h`> <fallback>
  python3 -c "
import json,sys
c=json.load(open('$CONFIG'))
h=c.get('hero_register') or {}
try:
    v=$1
except Exception:
    v=None
print(v if v not in (None,'') else '''$2''')
" 2>/dev/null || printf '%s' "$2"
}

HERO_MODE=$(read_cfg "h.get('mode')" "abu")
OUTDIR=$(read_cfg "h.get('outputDir')" "static/img/illustrations")
CFG_PANELS=$(read_cfg "h.get('defaultPanels')" "3")
CFG_LAYOUT=$(read_cfg "h.get('layout')" "multipanel")
REGISTER=$(read_cfg "h.get('register')" "")

# Config supplies the defaults; explicit flags already overrode them above.
if [[ "$MODE" == "multipanel" && "$PANELS" == "3" ]]; then PANELS="$CFG_PANELS"; fi
if [[ "$CFG_LAYOUT" == "single" && "$MODE" == "multipanel" ]]; then MODE="single"; fi

if [[ "$HERO_MODE" != "local" ]]; then
  echo "ERROR: hero_register.mode is '$HERO_MODE', not 'local'." >&2
  echo "  This door only drives the local engine. For mode 'abu', run:" >&2
  echo "    abu:make-a-work <universe> wiki-article-hero" >&2
  exit 1
fi

# --- Banned vocabulary pre-flight -------------------------------------------
# These either trip OpenAI moderation (named living or recent artists) or violate
# the locked register in illustrations/SPEC.md.
BANNED='\b(Sendak|Quentin[[:space:]]+Blake|Tomi[[:space:]]+Ungerer|Pixar|Disney|anime|manga|chibi|3D|render|photorealistic|hyper-?detailed|HDR|cyberpunk|neon|futuristic|glossy|plastic|smartphone|brand[[:space:]]+logo|watermark)\b'
if echo "$SCENE" | grep -iE "$BANNED" >/dev/null; then
  echo "ERROR: scene contains banned vocabulary." >&2
  echo "Matched: $(echo "$SCENE" | grep -iEo "$BANNED" | head -1)" >&2
  echo "" >&2
  echo "This wiki has a locked visual register in illustrations/SPEC.md. Describe" >&2
  echo "the register generically. To change the register, edit SPEC.md first." >&2
  exit 1
fi

# --- The laws ---------------------------------------------------------------
[[ -n "$REGISTER" ]] || REGISTER="An editorial illustration on a warm cream ground: soft painterly line, gentle shading, a muted natural palette, grounded and human."

if [[ "$MODE" == "multipanel" ]]; then
  LAYOUT="ONE single image divided into ${PANELS} CLEAR PANELS of equal size, arranged left to right in a horizontal row, separated by generous clean cream gutters with NO drawn borders and NO frame lines. Each panel is one BEAT of the same argument and they read in order as a sequence. Beat two shows the CONSEQUENCE of beat one rather than restating it. Keep ONE consistent world and ONE consistent cast across every panel, so the strip reads as a progression rather than ${PANELS} unrelated pictures."
else
  LAYOUT="ONE single elegant editorial plate: no panels, no grid, no dividing lines."
fi

NOTEXT="ABSOLUTELY NO TEXT ANYWHERE: no words, no letters, no numbers, no captions, no speech bubbles, no labels, no UI chrome, no menus, no icons. Every beat must be legible from image alone."

PROMPT="${REGISTER}

${LAYOUT}

The scene, beat by beat: ${SCENE}

${NOTEXT}"

# --- References: style-only by default --------------------------------------
REF_ARGS=()
for f in illustrations/refs/*.png illustrations/refs/*.webp; do
  [[ -f "$f" ]] || continue
  REF_ARGS+=(--input-image "$f")
done

# --- Dry run ----------------------------------------------------------------
if [[ "$DRY_RUN" == true ]]; then
  echo "=== DRY RUN: no API call, no cost ==="
  echo "mode:   $MODE  panels: $PANELS"
  echo "out:    $OUTDIR/$SLUG.webp"
  echo "refs:   ${REF_ARGS[*]:-（none）}"
  echo "--- prompt ---"
  echo "$PROMPT"
  exit 0
fi

# --- Preflight --------------------------------------------------------------
command -v uv >/dev/null 2>&1 || {
  echo "ERROR: uv is not installed. Install it with:" >&2
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh" >&2
  exit 1; }
command -v cwebp >/dev/null 2>&1 || {
  echo "ERROR: cwebp is not installed. Install it with:" >&2
  echo "  brew install webp" >&2
  exit 1; }

mkdir -p illustrations "$OUTDIR"

echo "==> rendering $OUTDIR/$SLUG.webp  [$MODE, $PANELS beats]"

uv run illustrations/scripts/generate.py \
  --prompt "$PROMPT" \
  --filename "illustrations/$SLUG.png" \
  "${REF_ARGS[@]}" \
  --size 1536x1024 \
  --quality high

[[ -f "illustrations/$SLUG.png" ]] || { echo "ERROR: generator produced no file." >&2; exit 1; }

# --- Contract artifact 1: the deploy WebP -----------------------------------
cwebp -quiet -q 85 "illustrations/$SLUG.png" -o "$OUTDIR/$SLUG.webp"

# --- Contract artifact 3: provenance beside the SHIPPED asset ---------------
# The generator writes the recipe next to the PNG it made. The shipped asset is the
# WebP, so an auditor looking at what got deployed must find it there too.
if [[ -f "illustrations/$SLUG.png.recipe.json" ]]; then
  cp "illustrations/$SLUG.png.recipe.json" "$OUTDIR/$SLUG.webp.recipe.json"
fi

# --- Enforce the panel law --------------------------------------------------
if [[ "$MODE" == "multipanel" ]]; then
  uv run illustrations/scripts/check_panels.py "illustrations/$SLUG.png" --expect "$PANELS" || {
    echo "" >&2
    echo "The render did not come back as a ${PANELS}-panel strip. Re-render." >&2
    echo "Do not edit the image; fix the scene so each beat is distinct." >&2
    exit 1; }
fi

# --- Contract artifacts 4 and 5, printed to paste ---------------------------
cat <<EOF

Done. Two lines to paste into docs/<...>/${SLUG}.mdx:

Frontmatter:
  image: "/img/illustrations/${SLUG}.webp"

Body, immediately after the italic definition line (alt text IS the prompt, verbatim):
  ![${SCENE}](/img/illustrations/${SLUG}.webp)
EOF
```

```bash
chmod +x illustrations/scripts/render-hero.sh
```

- [ ] **Step 4: Add `hero_register` so the door can resolve**

This task's test needs `mode: "local"` present. Apply the `wiki.config.json` change now (Task 4 covers the schema and the rest):

```bash
python3 - <<'PY'
import json, pathlib
p = pathlib.Path("wiki.config.json")
c = json.loads(p.read_text())
c.pop("brand_os_url", None)
c["hero_register"] = {
    "mode": "local",
    "layout": "multipanel",
    "defaultPanels": 3,
    "register": "",
    "spec": "illustrations/SPEC.md",
    "refs": [],
    "outputDir": "static/img/illustrations",
}
p.write_text(json.dumps(c, indent=2) + "\n")
PY
```

- [ ] **Step 5: Run the tests to verify they pass**

```bash
./illustrations/scripts/tests/test_render_hero.sh
```

Expected: `passed: 8  failed: 0`.

- [ ] **Step 6: Prove no private path and no dead generator reference**

```bash
grep -rn "\.agents/skills" illustrations/ scripts/ || echo "CLEAN"
```

Expected: `CLEAN`.

- [ ] **Step 7: Commit**

```bash
git add illustrations/scripts/render-hero.sh illustrations/scripts/tests/test_render_hero.sh wiki.config.json
git commit -m "Add render-hero.sh, the one door

Routes on hero_register.mode, owns the register and the panel law, and emits the
five-artifact contract including provenance beside the shipped WebP rather than
beside the archived PNG."
```

---

### Task 4: Config schema and the init prompt

**Files:**
- Modify: `wiki.config.schema.json`
- Modify: `scripts/init-wiki.sh:21`
- Modify: `~/.agents/skills/start-new-wiki/SKILL.md`
- Delete: `scripts/render-graphic.sh`

**Interfaces:**
- Consumes: the `hero_register` shape written in Task 3 Step 4.
- Produces: an `init-wiki.sh` that still takes exactly 11 piped answers, with slot 7 now meaning the visual register.

**This is the trap task.** `brand_os_url` has four consumers, and slot 7 of the 11 `init-wiki.sh` prompts is one of them. `start-new-wiki/SKILL.md` documents an 11-value `printf` pipe whose empty string in position 7 IS that slot. Deleting the prompt shifts every later answer by one and writes a silently wrong config. So the prompt is REPURPOSED, never removed.

- [ ] **Step 1: Confirm the prompt count before touching anything**

```bash
cd ~/Documents/github-repos/supersuit-repos/wiki-template
grep -c 'read -r -p' scripts/init-wiki.sh
```

Expected: `11`. If it is not 11, stop and re-read `scripts/init-wiki.sh` before continuing, because the documented pipe no longer matches the script.

- [ ] **Step 2: Repurpose prompt 7**

In `scripts/init-wiki.sh`, replace the line at 21:

```bash
read -r -p "Brand OS base URL (e.g. https://my-brand-os.vercel.app — leave blank if none): " BRAND_OS_URL
```

with:

```bash
read -r -p "Visual register in one sentence (leave blank for the default cream editorial look): " HERO_REGISTER
```

Then find where the script writes `brand_os_url` into `wiki.config.json` and write the `hero_register` block instead, carrying `HERO_REGISTER` into its `register` field and defaulting `mode` to `local`, `layout` to `multipanel`, `defaultPanels` to `3`, `outputDir` to `static/img/illustrations`.

- [ ] **Step 3: Verify the count did not move**

```bash
grep -c 'read -r -p' scripts/init-wiki.sh
```

Expected: `11`. If this is not 11, the pipe in `start-new-wiki/SKILL.md` is now wrong and every downstream answer is misaligned.

- [ ] **Step 4: Prove the pipe still lands correctly**

```bash
cd /tmp && rm -rf initcheck && cp -R ~/Documents/github-repos/supersuit-repos/wiki-template initcheck && cd initcheck
printf '%s\n' "T" "tag" "https://t.wiki" "org" "repo" "desc" "woodcut prints on cream" "y" "source-grounded" "n" "n" \
  | bash scripts/init-wiki.sh >/dev/null 2>&1
python3 -c "
import json; c=json.load(open('wiki.config.json'))
assert c['title']=='T', c['title']
assert c['intake_mode']=='source-grounded', c['intake_mode']
assert c['noindex'] is True, c['noindex']
assert c['hero_register']['register']=='woodcut prints on cream', c['hero_register']
assert c['hero_register']['mode']=='local'
assert 'brand_os_url' not in c
print('init pipe OK, slots aligned')"
```

Expected: `init pipe OK, slots aligned`. This is the assertion that catches the off-by-one.

- [ ] **Step 5: Update the schema**

In `wiki.config.schema.json`, remove the `brand_os_url` property and add `hero_register` as an object with properties `mode` (enum `local`, `abu`), `layout` (enum `multipanel`, `single`), `defaultPanels` (integer), `register` (string), `spec` (string), `refs` (array of string), `outputDir` (string).

- [ ] **Step 6: Delete the dead generator**

```bash
cd ~/Documents/github-repos/supersuit-repos/wiki-template
git rm scripts/render-graphic.sh
grep -rn "render-graphic" . --exclude-dir=node_modules --exclude-dir=.git || echo "NO DANGLING REFERENCES"
```

Expected: `NO DANGLING REFERENCES`.

- [ ] **Step 7: Fix the documented pipe**

In `~/.agents/skills/start-new-wiki/SKILL.md`, update the `printf` shape so slot 7 is described as the visual register rather than an empty Brand OS URL, and add one line noting the slot changed meaning on 2026-08-03 while the count stayed at 11.

- [ ] **Step 8: Commit**

```bash
cd ~/Documents/github-repos/supersuit-repos/wiki-template
git add -A
git commit -m "Repurpose init prompt 7 from brand OS URL to visual register

brand_os_url had four consumers, not one. Slot 7 of 11 in init-wiki.sh is the
slot the documented printf pipe fills with an empty string, so removing the
prompt would have shifted every later answer by one and written a silently
wrong wiki.config.json. Repurposed instead; count stays 11.

Also deletes scripts/render-graphic.sh, which resolved the retired hosted brand
OS, exited 1 on the shipped empty config, and was referenced nowhere."
```

---

### Task 5: Fix the reversed visual law in SPEC.md

**Files:**
- Modify: `illustrations/SPEC.md:61-67` (composition rules), `:35-43` (character sections), `:105-127` (workflow)

**Interfaces:**
- Consumes: the door's flag surface from Task 3.
- Produces: the prose contract a page author and a future agent read.

- [ ] **Step 1: Replace the composition rules**

Replace the `## Composition rules (CUSTOMIZE)` block, which currently opens with "Single focal scene per illustration. One thing is happening.", with:

```markdown
## Composition rules

- **A hero is a STRIP OF BEATS, not a plate.** The default is 3 panels of equal
  size in a horizontal row, separated by clean cream gutters with no drawn
  borders. One consistent world and cast across every panel.
- **Beat two shows the CONSEQUENCE of beat one.** A middle panel that only
  restates the first is a plate with extra steps.
- **One elegant plate is the EXCEPTION**, used only when the idea genuinely is a
  single image. Reach for it with `--single`, deliberately.
- **Generous white space.** At least 30 percent of the canvas untouched paper.
- **No text in the image.** Page titles and captions live in the surrounding MDX.

> Reversed 2026-07-26, family-wide. This file said "Single focal scene per
> illustration" until 2026-08-03, long after the reversal, so every wiki forked
> from this template was born with the law that had already been overturned.
> These pages argue a before and an after, and one frame flattens that into
> decoration.
```

- [ ] **Step 2: Make the recurring character explicitly opt-in**

Retitle `## Recurring character (OPTIONAL — customize or remove)` to `## Recurring character (OPT-IN, off by default)` and open it with:

```markdown
**The default visual identity is style-only: 2 to 4 blessed reference images in
`refs/`, all passed on every render, and no recurring person.** That is enough to
lock a look, and it skips the master-first character workflow, which is the most
failure-prone part of this system and the step most likely to burn a first hour.

Add a recurring character only if you want one. If you do, the master-first
workflow above is not optional; it is what keeps the character from drifting.
```

- [ ] **Step 3: Rename the interface throughout, in THREE files not one**

`SPEC.md` is not the only doc naming the old script. Two READMEs do too, and the
original plan missed both:

| File | What it says |
|---|---|
| `illustrations/SPEC.md` | the workflow, plus stale `PREFIX`/`SUFFIX` sync instructions |
| `illustrations/scripts/README.md` | "One canonical script: `render-page.sh`" |
| `README.md` | the AI-native illustration system section and fork-time setup |

The `PREFIX`/`SUFFIX` references are stale in a deeper way than a rename fixes: the
register now lives in `hero_register.register` in `wiki.config.json`, not in strings
inside the script. Keeping two copies of one fact in sync is what let them drift. Say
so where you remove them.

```bash
grep -rn "render-page\|render-graphic\|brand_os_url" . \
  --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=build --exclude-dir=.docusaurus
```

Expected after the edit: no output.

- [ ] **Step 3b: The private-path check, correctly scoped**

```bash
grep -rln "\.agents/skills" illustrations/
```

Expected: no output, and this is the first task where that is achievable, since
`render-page.sh` is only deleted in the next step.

Scope this to `illustrations/` and NOT to `scripts/`. `scripts/register-skills.sh`
legitimately documents `~/.agents/skills` as the global registry it writes into, which
has nothing to do with the image generator. A check that flags a correct line teaches
people to ignore it.

- [ ] **Step 4: Delete the superseded script**

```bash
git rm illustrations/scripts/render-page.sh
grep -rn "render-page" . --exclude-dir=node_modules --exclude-dir=.git || echo "NO DANGLING REFERENCES"
```

Expected: `NO DANGLING REFERENCES` (the GENERATE.md references live in another repo and are handled in Task 6).

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "SPEC: multipanel law replaces the reversed single-plate rule

The 2026-07-26 family-wide reversal never reached the template, so every new
wiki was born with the overturned law. Also makes the recurring character
opt-in, since style-only refs are enough to lock a look and skip the most
drift-prone step."
```

---

### Task 6: The interview teaches the key

**Files:**
- Modify: `truth-management-wiki/static/generators/starting-your-own-wiki/GENERATE.md`

**Interfaces:**
- Consumes: `render-hero.sh` and its `--dry-run` flag.
- Produces: a Phase the gamify generator (Task 7) invokes by name.

- [ ] **Step 1: Rename every reference to the old script**

```bash
cd ~/Documents/github-repos/supersuit-repos/truth-management-wiki
grep -n "render-page.sh" static/generators/starting-your-own-wiki/GENERATE.md
```

Replace each with `render-hero.sh`, and update the Phase 3 step 6 body so it describes style-only refs plus the multipanel default instead of the character-sheet-first flow. Update the pitfall that says "Calling `chatgpt-images` directly bypasses the AI-native illustration system" so it names the vendored `generate.py` instead.

- [ ] **Step 2: Add the new phase**

Insert a phase, before the first-concept-page step, titled `Phase 3b: Your image key and your visual register`:

```markdown
### Phase 3b: Your image key and your visual register

Do this WITH the operator, not for them. The point is that they leave knowing
what a key is and having seen an image appear.

**1. Explain, in two sentences.** Images are drawn by a paid model, billed to
their own OpenAI account. The key is theirs, it lives in their shell, and it
never goes in the repo.

**2. Get the key.** Walk them to https://platform.openai.com/api-keys. Have them
create one and copy it.

**3. Set it, and make it survive.**

```bash
export OPENAI_API_KEY='sk-...'
echo "export OPENAI_API_KEY='sk-...'" >> ~/.zshrc
```

Then verify in a FRESH shell: `zsh -lc 'echo ${OPENAI_API_KEY:0:7}'`. An export
that dies with the terminal is the failure mode that reads as "it worked."

**4. Check the toolchain.**

```bash
command -v uv    || curl -LsSf https://astral.sh/uv/install.sh | sh
command -v cwebp || brew install webp
```

**5. Pick the register.** Offer these, or take a custom one:

| Register | One-line description |
|---|---|
| Cream editorial ink-and-wash | soft painterly line, muted natural palette, grounded and human |
| Woodcut print | high-contrast carved line, two inks, visible grain |
| Mid-century textbook diagram | flat shapes, limited palette, confident labels-free geometry |
| Vintage illustrated children's book | warm line, gentle wash, generous paper |

Write the chosen sentence into `hero_register.register` in `wiki.config.json`.
Never name a living or recent illustrator; OpenAI moderation hard-blocks those.

**6. Dry-run first, so the first real spend is not the first test.**

```bash
./illustrations/scripts/render-hero.sh --dry-run first-page "a scene, beat by beat"
```

Read the assembled prompt aloud with them. This costs nothing.

**7. Render the style references.** Two to four non-character scenes that lock
the look. Each is a real render. They approve each one, and the approved files
stay in `illustrations/refs/`. This is the moment they SEE an image appear and
the key becomes real.

**8. Render the first article hero.** Multipanel, 3 beats, through the door.
Paste the two printed lines into the page.

If any render fails, read the error out loud rather than fixing it silently.
Every one of them names its own fix.
```

- [ ] **Step 3: Add the image checks to the verification block**

Append to Phase 4's verification list:

```markdown
- `hero_register.mode` is `local` and `register` is a real sentence, not empty.
- `illustrations/refs/` holds 2 to 4 approved reference images.
- The first page embeds a `.webp` hero, and its frontmatter `image:` matches.
- `ls static/img/illustrations/` shows `.webp` files and a `.recipe.json` beside each.
- `grep -rn "\.agents/skills" illustrations/ scripts/` returns nothing.
- `./illustrations/scripts/tests/test_render_hero.sh` passes.
```

- [ ] **Step 4: Verify no stale references remain**

```bash
grep -c "render-page.sh\|render-graphic.sh\|brand_os_url" static/generators/starting-your-own-wiki/GENERATE.md
```

Expected: `0`.

- [ ] **Step 5: Commit**

```bash
git add static/generators/starting-your-own-wiki/GENERATE.md
git commit -m "Teach the image key in the wiki scaffold interview

OPENAI_API_KEY, uv and image prerequisites appeared zero times in 390 lines, so
a new operator's only guidance was an error string inside a script they did not
have. Ends in a live render so the key becomes real."
```

---

### Task 7: The gamify path gets images

**Files:**
- Modify: `truth-management-wiki/static/generators/gamify-your-learning-wiki/GENERATE.md`

**Interfaces:**
- Consumes: `Phase 3b` from Task 6.
- Produces: the recipe a personal-wiki operator actually runs.

This is the path the friend runs, and today it mentions images zero times.

- [ ] **Step 1: Rewrite Q4**

Replace the Q4 body, which currently says "visual polish is not the optimization", with:

```markdown
**Q4. Brand register.**
The personal-truth-wiki brand is austere in TYPOGRAPHY and restrained in colour.
That restraint is about chrome, not about illustration: each post still gets a
hero, because a strip of beats is how a claim gets remembered.

Capture one primary accent colour, one font choice, and one sentence naming the
visual register for heroes. Defaults: cream, Cormorant Garamond, and "an
editorial ink-and-wash illustration on a warm cream ground, soft painterly line,
muted natural palette."
```

- [ ] **Step 2: Hand the key phase off explicitly**

In Phase 3, after the sentence handing control to the mechanics skill, add:

```markdown
That skill's `Phase 3b: Your image key and your visual register` is REQUIRED
here, not optional. Do not skip it because this wiki is private. A wiki whose
posts have no heroes is the failure this recipe shipped with until 2026-08-03.
```

- [ ] **Step 3: Give the seeded posts heroes**

In Phase 4, after the paragraph about committing the five drafts, add:

```markdown
Then give each of the five a hero. For each post, write the argument as beats,
dry-run it, then render:

```bash
./illustrations/scripts/render-hero.sh --dry-run <slug> "<beat one>. <beat two>. <beat three>."
./illustrations/scripts/render-hero.sh <slug> "<beat one>. <beat two>. <beat three>."
```

Paste the two printed lines into the post: the frontmatter `image:` and the
body `![...](...)` whose alt text is the verbatim prompt.

Five posts is five renders. Show the operator the first one before rendering the
rest, so a register they dislike costs one image and not five.
```

- [ ] **Step 4: Extend the verification block**

Add to the Verification list:

```markdown
- All five seeded posts have a `.webp` hero and a matching frontmatter `image:`.
- Every hero rendered as a strip of beats, not a single plate.
- The operator can state, unprompted, where their API key lives and who is billed.
```

- [ ] **Step 5: Verify**

```bash
grep -c "render-hero.sh" static/generators/gamify-your-learning-wiki/GENERATE.md
```

Expected: at least `2`.

- [ ] **Step 6: Commit**

```bash
git add static/generators/gamify-your-learning-wiki/GENERATE.md
git commit -m "Give the personal-wiki recipe heroes

This recipe mentioned images zero times and told the operator visual polish was
not the optimization, so the path most likely to be run by a first-timer was the
one guaranteed to produce no images at all."
```

---

### Task 8: End-to-end proof on a clean clone

**Files:**
- Test: no new files. This task proves the unit.

**Interfaces:**
- Consumes: everything above.
- Produces: the evidence that Unit A is done.

The rule this task enforces: a tool is not shipped until you have RUN it the way its own docs say to, from OUTSIDE its repo.

- [ ] **Step 1: Clone to a clean path**

```bash
rm -rf /tmp/wikiproof && git clone ~/Documents/github-repos/supersuit-repos/wiki-template /tmp/wikiproof
cd /tmp/wikiproof
```

- [ ] **Step 2: Prove no private path survived the clone**

```bash
grep -rn "\.agents/skills" illustrations/ scripts/ || echo "CLEAN"
grep -rn "render-page\|render-graphic\|brand_os_url" . --exclude-dir=.git --exclude-dir=node_modules || echo "NO DANGLING REFERENCES"
```

Expected: `CLEAN` and `NO DANGLING REFERENCES`.

- [ ] **Step 3: Prove the free tests pass from the clone**

```bash
uv run illustrations/scripts/tests/test_check_panels.py
./illustrations/scripts/tests/test_render_hero.sh
```

Expected: `Ran 4 tests` / `OK`, and `passed: 8  failed: 0`.

- [ ] **Step 4: Prove the missing-key error names its fix**

```bash
env -u OPENAI_API_KEY ./illustrations/scripts/render-hero.sh proof "a scene"; echo "exit=$?"
```

Expected: the three-step key message, `exit=1`, no traceback.

- [ ] **Step 5: Render for real, once**

```bash
./illustrations/scripts/render-hero.sh proof "A person writes one honest claim into a file. The claim hardens into a page others can read. The page corrects an earlier, vaguer version of itself."
```

Expected: a 3-panel strip. `check_panels` passes at 3. This is the only step in the plan that spends money.

- [ ] **Step 6: Prove the five-artifact contract**

```bash
ls -la illustrations/proof.png \
      static/img/illustrations/proof.webp \
      static/img/illustrations/proof.webp.recipe.json
python3 -c "
import json; r=json.load(open('static/img/illustrations/proof.webp.recipe.json'))
assert r['model']=='gpt-image-2', r['model']
assert r['generator']=='illustrations/scripts/generate.py', r['generator']
assert 'CLEAR PANELS' in r['prompt']
print('provenance OK')"
```

Expected: all three files exist, `provenance OK`.

- [ ] **Step 7: Prove the build still passes**

```bash
pnpm install && pnpm run build
```

Expected: green. `onBrokenLinks: throw` is the gate.

- [ ] **Step 8: Report, do not push**

Report the render inline for a look. Do NOT push any of the three repos; pushing waits for an explicit go.

---

## Self-Review

**Spec coverage:**

| Spec item | Task |
|---|---|
| A1 vendor the generator | 1 |
| A2 the one door | 3 |
| A3 delete dead generator, brand_os_url trap | 4 |
| A4 fix the reversed law | 5 |
| A5 style-only default | 5 |
| A6 the interview | 6, 7 |
| Five-artifact contract | 3 (emit), 8 (prove) |
| `hero_register` schema | 3 (data), 4 (schema) |
| Verification list | 8 |
| Panel law enforced by a check | 2, 3 |

**Type consistency:** `count_panels(path, *, min_gutter_px, flat_max, light_min)` is defined in Task 2 and called by name in Task 3 only via the CLI (`--expect`), so no signature drift. `hero_register` keys (`mode`, `layout`, `defaultPanels`, `register`, `spec`, `refs`, `outputDir`) are identical in Task 3 Step 4, Task 4 Step 2, and Task 4 Step 5.

**Known gap, deliberate:** Task 4 Step 2 says "find where the script writes `brand_os_url`" rather than quoting the exact line, because `init-wiki.sh` writes its config in a heredoc whose surrounding lines were not read during planning. Step 4's assertion is what catches a wrong edit, which is why that assertion checks all four fields and not just the new one.
