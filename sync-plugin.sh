#!/usr/bin/env bash
# Mirror skills into the packaged plugin, then PROVE they match.
#
# The plugin keeps identical copies rather than symlinks, so a skill added here
# does not reach the plugin until it is copied. A `cp -r` that silently fails
# leaves the two out of sync with nothing to notice it: `explanatory-plate` lived
# in this repo for hours while the plugin had never heard of it. Assume nothing;
# diff at the end and fail loudly.
set -uo pipefail
SRC="$(cd "$(dirname "$0")" && pwd)/skills"
DST="$HOME/Documents/github-repos/garysheng-claude-plugins/plugins/agenticstory/skills"

[ -d "$DST" ] || { echo "plugin skills dir not found: $DST"; exit 2; }
rsync -a --delete-excluded --exclude '__pycache__' --exclude '*.pyc' "$SRC"/ "$DST"/

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
