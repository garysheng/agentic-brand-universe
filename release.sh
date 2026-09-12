#!/usr/bin/env bash
# Cut a release. ONE command, and it refuses rather than half-shipping.
#
# WHY THIS EXISTS. The repo IS the marketplace (`source: "."`), and Claude Code's marketplace
# source format carries no ref, so an install always tracks the DEFAULT BRANCH. Verified
# 2026-09-12 by reading an installed marketplace record. That means every commit on master was
# a release to every user, with no staging and nothing immutable to point at: `git tag`
# returned nothing, so a report of "broken since" had no ref to name and the version string in
# plugin.json pointed at a moving branch head.
#
# So: develop is where work lands, master is what ships, and a release is a deliberate act
# that leaves a tag behind.
#
#   ./release.sh 1.24.0            cut it
#   ./release.sh 1.24.0 --dry-run  say what would happen and touch nothing
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

VERSION="${1:-}"
DRY=""
[ "${2:-}" = "--dry-run" ] && DRY=1
[ "$VERSION" = "--help" ] && { awk 'NR>1 && /^#/{sub(/^# ?/,"");print;next} NR>1{exit}' "$0"; exit 0; }
[ -n "$VERSION" ] || { echo "usage: ./release.sh <version> [--dry-run]" >&2; exit 2; }
echo "$VERSION" | grep -qE '^[0-9]+\.[0-9]+\.[0-9]+$' \
  || { echo "refused: '$VERSION' is not x.y.z" >&2; exit 2; }

say() { printf '\n\033[1m%s\033[0m\n' "$*"; }
die() { printf '\nREFUSED: %s\n' "$*" >&2; exit 1; }

# ---- the refusals, in the order they fire -------------------------------------------------
say "checking the tree"
[ -z "$(git status --porcelain | grep -v __pycache__ || true)" ] \
  || die "the working tree is dirty. A release must be reproducible from a commit."

git rev-parse "v$VERSION" >/dev/null 2>&1 && die "v$VERSION is already tagged."

BR="$(git rev-parse --abbrev-ref HEAD)"
[ "$BR" = "develop" ] || [ "$BR" = "master" ] \
  || die "on branch '$BR'. Release from develop (normal) or master (hotfix)."

DECLARED="$(python3 -c "import json;print(json.load(open('.claude-plugin/plugin.json'))['version'])")"
[ "$DECLARED" = "$VERSION" ] \
  || die "plugin.json declares $DECLARED, you asked for $VERSION. Bump it in the commit that
         earned the release, not here: the version belongs to the change rather than to the
         act of publishing it."

grep -q "v$VERSION" SAVE-LOG.md \
  || die "SAVE-LOG.md has no line for v$VERSION. One line, under 80 words, is the changelog
          every future reader gets."

say "running the suite"
./run-tests.sh >/tmp/release-tests.log 2>&1 || { tail -25 /tmp/release-tests.log; \
  die "the suite is red. See /tmp/release-tests.log"; }
tail -2 /tmp/release-tests.log

say "confirming the generated docs are current"
( cd engine && python3 -m agenticstory.cli build-docs --check >/dev/null 2>&1 ) \
  || die "generated docs are stale. Run (cd engine && python3 -m agenticstory.cli build-docs)
          and commit the result."

# ---- the notes, read from the changelog the repo already keeps -----------------------------
NOTES="$(grep -m1 -A0 "v$VERSION" SAVE-LOG.md | sed -E 's/^- *//')"
say "release notes"
echo "  $NOTES"

if [ -n "$DRY" ]; then
  say "dry run"
  echo "  would merge $BR into master, tag v$VERSION, push both, and cut a GitHub release."
  exit 0
fi

# ---- ship ---------------------------------------------------------------------------------
if [ "$BR" = "develop" ]; then
  say "merging develop into master"
  git checkout master
  git merge --no-ff develop -m "release v$VERSION

$NOTES"
fi

say "tagging"
git tag -a "v$VERSION" -m "v$VERSION

$NOTES"

say "pushing"
git push origin master
git push origin "v$VERSION"

say "cutting the GitHub release"
gh release create "v$VERSION" --title "v$VERSION" --notes "$NOTES" \
  --verify-tag 2>&1 | tail -2 || echo "  (gh release failed; the tag is pushed, so this is recoverable)"

# ---- prove it landed ----------------------------------------------------------------------
say "delivery"
set +e
python3 skills/evolve-abu/scripts/check_delivery.py --expect .claude-plugin/plugin.json
rc=$?
set -e
case $rc in
  0) echo "  delivered." ;;
  2) echo "  published. Everything that is yours to do is done; users run /plugin update." ;;
  *) echo "  NOT published. Read the lines above: something is still on this machine." ;;
esac

if [ "$BR" = "develop" ]; then
  say "back to develop"
  git checkout develop
  git merge --ff-only master 2>/dev/null || git merge master -m "sync master back into develop"
fi
say "v$VERSION is out"
