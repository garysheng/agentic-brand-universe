"""Where the framework's own files live, resolved rather than assumed.

Four scripts each hardcoded an absolute path into ONE developer's home directory
(`~/.agents/skills/chatgpt-images/...`, `~/Documents/github-repos/agenticstory/engine`).
Copy-pasted four times, which is the tell that the resolution itself wanted to be a
function. The cost was not style: a fresh clone of this repo could validate canon and
run every test, and then fail to generate a single image, because the one thing the
framework could not find was the thing that draws.

So the provider scripts are VENDORED under `providers/<id>/` and located relative to
this module. That is the same self-containment rule §3a already imposes on a Style
Pack, which copies its refs IN rather than pointing at wherever they happened to sit.
A framework that demands self-containment of its content and does not practice it on
itself is asserting a standard it fails.

Resolution order for a provider script, first hit wins:

  1. `$ABU_PROVIDER_<ID>` — an explicit override (id upper-cased, `-` to `_`), for
     pointing at a fork or a local experiment without editing the repo.
  2. `<repo>/providers/<id>/generate_image.py` — the vendored copy. The normal path.
  3. The legacy home-directory locations, so an existing machine that has always run
     from `~/.agents/skills/` keeps working and nothing silently changes under it.

A miss raises with every path it tried, because "provider not found" with no list is
the error that costs an hour.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

# The historical locations, kept so an existing install does not break. New installs
# never reach these: the vendored copy is found first.
LEGACY = {
    "gpt-image-2": ["~/.agents/skills/chatgpt-images/scripts/generate_image.py"],
    "nano-banana-pro": [
        "~/.claude/skills/nano-banana-pro/scripts/generate_image.py",
        "~/.agents/skills/nano-banana-pro/scripts/generate_image.py",
    ],
}


def repo_root() -> Path:
    """The framework repo root, from this module's own location.

    `.resolve()` matters: skills are installed by symlinking `skills/<name>` into
    `~/.claude/skills/`, so an unresolved `__file__` would report the symlink's
    directory and land outside the repo entirely.
    """
    return Path(__file__).resolve().parents[2]


def engine_dir() -> Path:
    """The directory to put on `sys.path` to import this package."""
    return repo_root() / "engine"


def env_var(provider: str) -> str:
    return "ABU_PROVIDER_" + provider.upper().replace("-", "_")


def candidates(provider: str) -> list[Path]:
    """Every path that would be accepted, in order, whether or not it exists."""
    out = []
    override = os.environ.get(env_var(provider))
    if override:
        out.append(Path(override).expanduser())
    out.append(repo_root() / "providers" / provider / "generate_image.py")
    out += [Path(p).expanduser() for p in LEGACY.get(provider, [])]
    return out


def resolve(provider: str) -> Path:
    """The generation script for `provider`. Raises with the full search path."""
    tried = candidates(provider)
    for p in tried:
        if p.is_file():
            return p
    listing = "\n".join(f"    {p}" for p in tried)
    raise FileNotFoundError(
        f"no generation script found for provider '{provider}'. Tried:\n{listing}\n"
        f"  Set {env_var(provider)} to point at one, or restore "
        f"providers/{provider}/generate_image.py in the repo.")


def resolve_str(provider: str) -> str:
    return str(resolve(provider))


# OpenAI image models the `gpt-image-2` adapter has moved past. A recipe naming one of
# these records what drew an OLD asset, and is kept verbatim for that reason; it is never
# a model any script should REACH for on its own. The adapter id is the same string as the
# oldest entry here, which is why the two keep getting confused (see adapter_default_model).
SUPERSEDED_MODELS = frozenset({
    "gpt-image-2", "gpt-image-1.5", "gpt-image-1", "gpt-image-1-mini", "dall-e-3", "dall-e-2",
})

_MODEL_DEFAULT = re.compile(r'--model["\']\s*,\s*default\s*=\s*["\']([^"\']+)["\']')


def adapter_default_model(provider: str = "gpt-image-2") -> str:
    """The model a provider adapter draws with when nobody passes --model.

    The ONE place any script learns the current model. The adapter owns that choice and
    moves it when a better model ships; every caller that wrote its own model string
    instead drifted silently. On 2026-09-16 three of them still said `gpt-image-2` a week
    after the adapter moved to gpt-image-2.5-sunburst: compose-spread and shoot-references
    stamped the old name into the recipe of every 2.5 render, and reroll-slot then replayed
    that recorded name with `--model`, so a re-roll of a spread went back to the old model.

    Parsed from source rather than imported, so reading one string never pulls in the
    provider's SDK or needs an API key. Raises rather than guessing: a caller that
    substitutes a model name when this fails has rebuilt the defect.
    """
    src = resolve(provider)
    m = _MODEL_DEFAULT.search(src.read_text())
    if not m:
        raise LookupError(f"cannot read the default --model out of {src}; pass --model "
                          f"explicitly and fix the adapter or this resolver")
    return m.group(1)
