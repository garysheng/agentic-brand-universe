#!/usr/bin/env node
// mount.mjs — put the works board in the operator's Freedom frapp store, at one stable URL.
//
//   node mount.mjs --slug abu-works --file <works-board.mjs>
//
// Prints ONE JSON line: { ok, slug, file, changed, restarted, local, phone } or { ok:false, why }.
//
// WHY MOUNTED AND NOT ONE-SHOT. The shot board is one-shot on purpose: a shoot's approval round
// is today's work and never comes back. A works board is the opposite. Fifty-seven heroes are
// judged over a day, from a phone, in sittings, and the link has to keep working across every
// one of them and across a reboot. A mounted frapp is a FILE the store imports at boot and
// serves at `https://<tailnet>/<slug>/`, which is the stable URL; its state is read from disk
// per request, so nothing is lost when the store restarts.
//
// NOTHING OF THE STORE LIVES HERE. The registry, the token and the link shape are Freedom's
// (`freedom-frapp-host.mjs`), resolved from the newest installed Freedom at every start, never a
// pinned version (freedom#106). This file only decides whether the row already points here.
import { existsSync, readdirSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import { pathToFileURL } from "node:url";
import { execFileSync } from "node:child_process";

const argv = process.argv.slice(2);
const argOf = (f, d = null) => { const i = argv.indexOf(f); return i > -1 && argv[i + 1] ? argv[i + 1] : d; };
const SLUG = argOf("--slug", "abu-works");
const FILE = resolve(argOf("--file", ""));
const say = (o) => { console.log(JSON.stringify(o)); process.exit(o.ok ? 0 : 1); };

const CACHE = process.env.FREEDOM_CACHE_DIR
  || join(homedir(), ".claude", "plugins", "cache", "freedom-workspace", "freedom");
function freedom(rel) {
  const dev = process.env.FREEDOM_LIB_DIR;
  if (dev && rel.startsWith(".agents/lib/") && existsSync(join(dev, rel.slice(12)))) return join(dev, rel.slice(12));
  let vs = [];
  try { vs = readdirSync(CACHE).filter((v) => existsSync(join(CACHE, v, rel))); } catch { /* none */ }
  vs.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  return vs.length ? join(CACHE, vs.at(-1), rel) : null;
}

if (!existsSync(FILE)) say({ ok: false, why: `no board page at ${FILE}` });
const hostLib = freedom(".agents/lib/freedom-frapp-host.mjs");
const hostCli = freedom(".agents/skills/create-or-manage-frapp/scripts/host.mjs");
if (!hostLib || !hostCli) say({ ok: false, why: `no Freedom install under ${CACHE}, so there is no frapp store to mount in` });
const H = await import(pathToFileURL(hostLib).href);

const row = H.readRegistry().find((f) => f.slug === SLUG);
const current = row && row.file ? H.resolveMountFile(row.file) : null;
// Re-point only when the row is missing, dead, or a different copy. A row that already names
// this file is left alone, so opening a second board costs no restart.
const changed = !row || !current || !existsSync(current) || resolve(current) !== FILE;
let restarted = false;
if (changed) {
  try {
    execFileSync(process.execPath, [hostCli, "add", FILE, "--slug", SLUG], { encoding: "utf8", timeout: 60000 });
  } catch (e) { say({ ok: false, why: `the store refused the mount: ${String(e.stderr || e.stdout || e.message).trim().slice(-500)}` }); }
  if (H.agentProbe().loaded) {
    try {
      execFileSync("launchctl", ["kickstart", "-k", `gui/${process.getuid()}/${H.LABEL}`], { timeout: 20000 });
      restarted = true;
    } catch (e) { say({ ok: false, why: `mounted, but the store did not restart: ${e.message}` }); }
  }
}

// The link is the store's own shape (portalLink), once the store is answering again.
let link = null;
for (let i = 0; i < 40 && !link; i++) {
  link = H.portalLink(SLUG);
  if (!link) await new Promise((r) => setTimeout(r, 500));
}
if (!link) say({ ok: false, why: H.agentProbe().loaded
  ? `mounted as ${SLUG}, but the store is not answering on its port`
  : `mounted as ${SLUG}, but no frapp store is installed: run /freedom:create-or-manage-frapp (install) once` });
say({ ok: true, slug: SLUG, file: FILE, changed, restarted, local: link.local, phone: link.phone });
