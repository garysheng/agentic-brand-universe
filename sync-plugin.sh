#!/usr/bin/env bash
# RETIRED 2026-07-30. Kept as a signpost, not a tool.
#
# This script copied skills into a SECOND repo (a private marketplace) and then
# nagged about versions and caches, because ABU used to ship from there. It does
# not any more: this repo IS the marketplace. `.claude-plugin/marketplace.json`
# points at `source: "."`, so the plugin payload is simply the repo, and there is
# nothing to sync anywhere.
#
# Two marketplaces advertising one plugin meant two sources of truth, and the
# copy was always the staler one. Installing is now:
#
#   /plugin marketplace add garysheng/agentic-brand-universe
#   /plugin install abu@agentic-brand-universe
#
# Shipping a change is: commit, push, bump `version` in
# `.claude-plugin/plugin.json`, then `/plugin update` in Claude Code.
echo "sync-plugin.sh is retired: this repo IS the marketplace (source: \".\")."
echo "  ship a change: commit + push, bump .claude-plugin/plugin.json version, /plugin update"
exit 0
