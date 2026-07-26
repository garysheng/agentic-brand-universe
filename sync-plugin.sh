#!/usr/bin/env bash
# Mirror skills into the packaged plugin, then PROVE they match.
#
# The plugin keeps identical copies rather than symlinks, so a skill added here
# does not reach the plugin until it is copied. A `cp -r` that silently fails
# leaves the two out of sync with nothing to notice it: `explanatory-plate` lived
# in this repo for hours while the plugin had never heard of it. Assume nothing;
# diff at the end and fail loudly.
#
# COPYING IS NOT DELIVERING. This script once printed "in sync: 23 skills, scripts
# verified" for an entire day while every `agenticstory:*` invocation ran the previous
# morning's code, because the files had been copied into the marketplace repo and never
# committed or pushed, and the INSTALLED plugin is a separate clone of that remote. The
# check was true and useless. So the copy check now runs to the end of the chain:
#   source repo  ->  marketplace repo  ->  git remote  ->  installed plugin cache
# and anything short of the remote is reported as STALE.
set -uo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
SRC="$ROOT/skills"
DST="$HOME/Documents/github-repos/garysheng-claude-plugins/plugins/agenticstory/skills"

[ -d "$DST" ] || { echo "plugin skills dir not found: $DST"; exit 2; }
rsync -a --delete-excluded --exclude '__pycache__' --exclude '*.pyc' "$SRC"/ "$DST"/

# agents/ ride the same chain as skills/: source -> marketplace -> remote -> cache.
# A plugin ships agents from its agents/ dir; a copied-but-undelivered agent is as
# useless as a copied-but-undelivered skill, so mirror + verify it the same way.
AGENT_SRC="$ROOT/agents"
AGENT_DST="$HOME/Documents/github-repos/garysheng-claude-plugins/plugins/agenticstory/agents"
if [ -d "$AGENT_SRC" ]; then
  mkdir -p "$AGENT_DST"
  rsync -a --delete-excluded --exclude '__pycache__' --exclude '*.pyc' "$AGENT_SRC"/ "$AGENT_DST"/
  amissing=$(comm -23 <(ls "$AGENT_SRC" | sort) <(ls "$AGENT_DST" | sort))
  [ -n "$amissing" ] && { echo "MISSING agents from plugin: $amissing"; exit 1; }
  echo "agents synced: $(ls "$AGENT_SRC" | wc -l | tr -d ' ')"
fi

missing=$(comm -23 <(ls "$SRC" | sort) <(ls "$DST" | sort))
extra=$(comm -13 <(ls "$SRC" | sort) <(ls "$DST" | sort))
if [ -n "$missing" ] || [ -n "$extra" ]; then
  [ -n "$missing" ] && echo "MISSING from plugin: $missing"
  [ -n "$extra" ]   && echo "EXTRA in plugin:    $extra"
  exit 1
fi

# a SKILL.md that copied but whose scripts did not is the sneakier failure
for d in "$SRC"/*/; do
  s=$(basename "$d")
  a=$(find "$SRC/$s" -name '*.py' | wc -l | tr -d ' ')
  b=$(find "$DST/$s" -name '*.py' | wc -l | tr -d ' ')
  [ "$a" != "$b" ] && { echo "SCRIPT MISMATCH in $s: src=$a plugin=$b"; exit 1; }
done

echo "in sync: $(ls "$SRC" | wc -l | tr -d ' ') skills, scripts verified"

# --- delivery, not just copying -------------------------------------------------
PLUGIN_REPO="$(dirname "$(dirname "$DST")")"          # .../plugins/agenticstory -> repo root
cd "$PLUGIN_REPO" || exit 1
dirty=$(git status --porcelain | wc -l | tr -d ' ')
ahead=$(git log --oneline @{u}..HEAD 2>/dev/null | wc -l | tr -d ' ')

if [ "$dirty" != "0" ] || [ "$ahead" != "0" ]; then
  echo
  echo "STALE: the files match, but they have NOT been delivered."
  [ "$dirty" != "0" ] && echo "  $dirty uncommitted file(s) in $PLUGIN_REPO"
  [ "$ahead" != "0" ] && echo "  $ahead commit(s) not pushed to the remote"
  echo "  Commit them, then bump the version in the plugin manifest and run /plugin update."
  exit 1
fi

# The installed cache is the thing users actually invoke. Compare it directly.
# The cache lives under a VERSIONED hash directory, not directly under the plugin name.
# The first version of this check hardcoded the wrong path, found nothing, and cheerfully
# reported "nothing to compare" about a cache that was in fact stale. A check that cannot
# find its target must say so loudly, never pass.
# PICK THE CACHE DIR FOR THE VERSION THE MANIFEST DECLARES, not whatever sorts first.
# `ls | head -1` sorted these ALPHABETICALLY, so 0.11.0 beat 0.17.1 and the check
# compared against a long-dead cache directory. It reported STALE forever, no matter
# how many times the plugin was actually updated, and sent a session chasing a
# non-existent update three times before the operator caught it (2026-07-26).
MANIFEST_VERSION=$(sed -n 's/.*"version"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' \
  "$(dirname "$DST")/.claude-plugin/plugin.json" 2>/dev/null | head -1)
CACHE=""
if [ -n "$MANIFEST_VERSION" ] && \
   [ -d "$HOME/.claude/plugins/cache/garysheng/agenticstory/$MANIFEST_VERSION/skills" ]; then
  CACHE="$HOME/.claude/plugins/cache/garysheng/agenticstory/$MANIFEST_VERSION/skills"
else
  # No dir for the declared version means it genuinely has not been installed yet.
  # Fall back to the most RECENTLY MODIFIED cache so the message names something real.
  CACHE=$(ls -dt "$HOME"/.claude/plugins/cache/garysheng/agenticstory/*/skills 2>/dev/null | head -1)
  [ -n "$CACHE" ] && echo "note: no cache dir for manifest version ${MANIFEST_VERSION:-unknown}; comparing newest ($CACHE)"
fi
if [ -n "$CACHE" ] && [ -d "$CACHE" ]; then
  if diff -rq --exclude='__pycache__' --exclude='*.pyc' "$SRC" "$CACHE" >/dev/null 2>&1; then
    echo "installed plugin matches source"
  else
    echo
    echo "INSTALLED PLUGIN IS STALE: $CACHE differs from source."
    echo "  This marketplace is a DIRECTORY source, not a git remote, so pushing does"
    echo "  nothing for it. The cache refreshes on a VERSION CHANGE, so a manifest with"
    echo "  no version (or an unchanged one) makes /plugin update a silent no-op."
    echo "  Fix: bump \"version\" in"
    echo "    <marketplace>/plugins/agenticstory/.claude-plugin/plugin.json"
    echo "  then run /plugin update in Claude Code."
    exit 1
  fi
else
  echo
  echo "CANNOT VERIFY: no installed plugin cache found under"
  echo "  ~/.claude/plugins/cache/garysheng/agenticstory/*/skills"
  echo "  Either the plugin is not installed, or the layout moved. Do not assume it is"
  echo "  current: an unverifiable check is not a passing one."
  exit 1
fi
