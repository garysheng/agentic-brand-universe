// candidates.mjs — the page-side copy of `engine/agenticstory/candidates.py`.
//
// What never goes in front of an operator on an approval board: anything under `rejected/`,
// `superseded*/`, `candidates/`, `photos/` or `pre-reroll-*/`, and any earlier roll kept beside
// its slot as `<slug>.rN.png`. The Python module is the rule; this file exists only because a
// frapp is JavaScript and must not shell out once per file to ask. `engine/tests/test_candidates.py` runs
// both over the same paths, so the two cannot quietly disagree.
//
// Node built-ins only, on purpose: both boards load it before Freedom's library is resolved,
// and a test imports it with nothing installed.
import { readdirSync } from "node:fs";
import { basename, join, relative, resolve, sep } from "node:path";

export const NOT_CANDIDATE_DIR = /^(rejected|superseded.*|candidates|photos|pre-reroll-.*)$/i;
export const ROLL = /\.r\d+\.(png|jpe?g|webp)$/i;
export const IMAGE = /\.(png|jpe?g|webp)$/i;

/** Why `path` is not a current candidate, or null when it is. `root` bounds the folder check. */
export function whyNotCandidate(path, root = null) {
  const name = basename(path);
  if (!IMAGE.test(name)) return `${name} is not an image`;
  if (ROLL.test(name)) return `${name} is an earlier ROLL of its slot`;
  let rel = resolve(path);
  if (root) {
    const r = relative(resolve(root), resolve(path));
    if (!r.startsWith("..")) rel = r;
  }
  const parts = rel.split(sep).filter(Boolean);
  for (const part of parts.slice(0, -1)) {
    if (NOT_CANDIDATE_DIR.test(part)) return `${name} sits in ${part}/, which is never a candidate`;
  }
  return null;
}

export const isCandidate = (path, root = null) => whyNotCandidate(path, root) === null;

/**
 * Every current candidate in an entity's reference folder: its own plates, and one level down
 * for each look folder (`reference/<id>/<look>/*.png`). A retired folder is not a look, however
 * it is named, which is the whole reason this exists: `superseded-unlit-2026-09-24/` was read
 * as a look and its plates were boarded (2026-09-24).
 */
export function entityCandidates(dir) {
  const out = [];
  let top = [];
  try { top = readdirSync(dir, { withFileTypes: true }); } catch { return out; }
  for (const f of top) {
    if (f.isFile()) out.push(join(dir, f.name));
    else if (f.isDirectory()) {
      try { for (const g of readdirSync(join(dir, f.name))) out.push(join(dir, f.name, g)); }
      catch { /* unreadable look folder */ }
    }
  }
  return out.filter((p) => isCandidate(p, dir)).sort();
}
