#!/usr/bin/env node
// shot-board — the board that SHOWS the art (SPEC v0.51).
//
// WHY THIS FILE EXISTS. v0.50 settled what SEEN means: a tap on an AskUserQuestion card. It
// left one gap, which `shoot-references`' own map recorded rather than pretending closed --
// an AskUserQuestion preview is TEXT. It carries the path and the entity's invariants and it
// cannot carry the picture. So the record proved the operator tapped a card NAMING a file,
// and proved nothing about whether the art was ever in front of them. A gate like that is
// worse than no gate: it refuses to lock art nobody tapped, which reads as rigour, while
// training the operator to tap through a list of filenames.
//
// A frapp closes it by REMOVING the unverifiable step rather than patching it. The thing
// that serves the image is the thing that records the tap, so "was the art displayed" stops
// being a claim an agent makes and becomes a fact this page knows: the browser asked for the
// bytes, the bytes went out, the verdict came back over the same connection. And it reaches
// the operator's PHONE over their tailnet, which is the half a viewer on this machine can
// never do -- `shoot-references` earned that on 2026-07-30, when "opened 10 images" reported
// success against a screen the operator was nowhere near.
//
// NOTHING OF THE VOCABULARY LIVES HERE. Every write goes through `shot_board.py`, which goes
// through `agenticstory.seen`, because `lock-shot` reads the same record and two copies of
// those refusals would drift. This file renders, sends bytes, and shells out. If a write is
// refused, the card stays and shows the refusal: a page that advances on a failed save is
// discarding work, and because the next card appears on cue it feels like it is working.
//
// ONE-SHOT ON PURPOSE. A shoot's approval round is today's work and never comes back: the
// shots are different next time, so a standing bookmark would point at an empty page. It
// still reaches the phone, because an installed store proxies a one-shot frapp by port.
import { existsSync, readdirSync, readFileSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync } from "node:child_process";
import { join, resolve, dirname, basename } from "node:path";
import { homedir } from "node:os";
import { pathToFileURL, fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const SHOT_BOARD = resolve(HERE, "..", "scripts", "shot_board.py");
const PY = process.env.ABU_PYTHON || "python3";

// ── WHERE FREEDOM'S LIBRARY IS. Resolved every time this starts, never baked in. ──────────
//
// The same rule a scaffolded frapp uses, and for the same reason: a frapp that imported from
// ~/.claude/plugins/cache/freedom-workspace/freedom/<version>/ died the day the next plugin
// update deleted that directory (freedom#106). ABU ships no copy of the library; it resolves
// the newest installed one, so the token gate, the tailnet route, the journal, the
// secure-origin refusal and the design system are inherited and improve without ABU shipping
// anything.
const FREEDOM_CACHE = process.env.FREEDOM_CACHE_DIR
  || join(homedir(), ".claude", "plugins", "cache", "freedom-workspace", "freedom");
function freedomLib(file) {
  const dev = process.env.FREEDOM_LIB_DIR;
  if (dev && existsSync(join(dev, file))) return join(dev, file);
  let versions = [];
  try {
    versions = readdirSync(FREEDOM_CACHE)
      .filter((v) => existsSync(join(FREEDOM_CACHE, v, ".agents", "lib", file)));
  } catch { /* not installed */ }
  versions.sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
  const v = versions.at(-1);
  if (!v) throw new Error(`${file}: no installed Freedom under ${FREEDOM_CACHE}. ABU falls `
    + `back to a text card when Freedom is absent; this file should not have been started.`);
  return join(FREEDOM_CACHE, v, ".agents", "lib", file);
}
const { serveFrapp, journal } = await import(pathToFileURL(freedomLib("freedom-frapp.mjs")).href);
// THE DESIGN SYSTEM. Declaring a palette here is how two frapps end up copying each other's
// unmeasured amber, which is the thing this import exists to end.
const { shell } = await import(pathToFileURL(freedomLib("freedom-frapp-style.mjs")).href);

const NAME = "abu-shot-board";

// ── arguments ────────────────────────────────────────────────────────────────────────────
const argv = process.argv.slice(2);
const argOf = (f, d = null) => {
  const i = argv.indexOf(f);
  return i > -1 && argv[i + 1] && !argv[i + 1].startsWith("--") ? argv[i + 1] : d;
};
const UNIVERSE = argOf("--universe");
const ENTITY = argOf("--entity");
const URLS_OUT = argOf("--urls-out");
const PORT = Number(argOf("--port", "7462")) || 7462;
const IMAGES = argv.filter((a) => !a.startsWith("--") && /\.(png|jpe?g|webp)$/i.test(a))
  .map((p) => resolve(p));

if (!IMAGES.length) {
  console.error("shot-board: no images. usage: shot-board.mjs --universe <u> --entity <id> <png>...");
  process.exit(2);
}

// ── 1. READ THE RECORD. Do not rebuild it. ───────────────────────────────────────────────
//
// The queue is DERIVED on every request from what has no answer yet -- never a cursor this
// page remembers -- so closing the tab costs nothing, a re-roll recorded from the terminal
// disappears from the page by itself, and the same truth serves the frapp and `lock-shot`.
// The record is the sidecar beside each image, which `shot_board.py board` already stamped.
const sidecar = (img) => `${img}.readback.json`;
const readSeen = (img) => {
  try { return (JSON.parse(readFileSync(sidecar(img), "utf8")) || {}).seen || {}; }
  catch { return {}; }
};
const entity = (() => {
  if (!UNIVERSE || !ENTITY) return {};
  try { return JSON.parse(readFileSync(join(UNIVERSE, "canon", "entities", `${ENTITY}.json`), "utf8")); }
  catch { return {}; }
})();
const INVARIANTS = ((entity.structured || {}).invariants || []).map(String).filter(Boolean);

function queue() {
  return IMAGES.map((img, index) => ({ index, img, seen: readSeen(img) }))
    .filter((r) => r.seen.board && !r.seen.verdict)
    .map((r) => ({
      index: r.index,
      img: r.img,
      name: basename(r.img),
      shot: r.seen.board.shot || basename(r.img).replace(/\.[^.]+$/, ""),
      served: Boolean((r.seen.board.display || {}).served),
    }));
}

// ── 2. WRITE BACK IN THE SAME SHAPE. ─────────────────────────────────────────────────────
//
// Both writes go to `shot_board.py`, never to the sidecar directly. The engine owns the
// refusals -- never boarded, off the board, no reason, bytes changed, never served -- and a
// second copy of them in JavaScript would disagree with `lock-shot` within a month.
function py(args) {
  const r = spawnSync(PY, [SHOT_BOARD, ...args], { encoding: "utf8", timeout: 30000 });
  const out = `${r.stdout || ""}${r.stderr || ""}`.trim();
  return { ok: r.status === 0, out };
}
// The route, not the filename: a record that states a URL nothing serves is a small lie in
// a file whose whole job is being true about what happened.
const recordServe = (img, digest, route) =>
  py(["served", img, "--digest", digest, "--url", route]);
const recordTap = (img, verdict, why) =>
  py(["tap", img, "--verdict", verdict, ...(why ? ["--why", why] : [])]);

// ── the page ─────────────────────────────────────────────────────────────────────────────
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const checklist = INVARIANTS.length
  ? INVARIANTS.map((i) => `<li>${esc(i)}</li>`).join("")
  : `<li>No invariants are declared on this entity, so there is no checklist beyond your own eye.</li>`;

// `base` is "" standalone and "/abu-shot-board" through the store. Every URL goes through it,
// so the same page works at both addresses.
const page = (items, token, base) => shell({
  title: ENTITY ? `${ENTITY} — shot board` : "shot board",
  subtitle: items.length ? `${items.length} to judge` : "",
  body: items.length
    ? items.map((i) => `<section class="card" data-i="${i.index}">
        <img class="shot" src="${base}/shot/${i.index}?k=${encodeURIComponent(token)}"
             alt="${esc(i.shot)}" loading="eager">
        <h2>${esc(i.shot)}</h2>
        <p class="file">${esc(i.name)}</p>
        <p class="look">Look for:</p>
        <ul class="look">${checklist}</ul>
        <div class="row">
          <button data-a="reroll">Re-roll</button>
          <button class="primary" data-a="keep">Keep</button>
        </div>
        <div class="why" hidden>
          <input placeholder="What is wrong with it?" maxlength="200">
          <button class="primary" data-a="reroll-send">Send re-roll</button>
        </div>
        <p class="err" hidden></p>
      </section>`).join("")
    : `<div class="empty"><p>Every shot has a verdict.</p><p>You can close this.</p></div>`,
  head: `<style>
    .shot{width:100%;height:auto;border-radius:10px;display:block}
    .file{opacity:.6;font-size:.85rem;margin:.2rem 0 .8rem}
    p.look{margin:.6rem 0 .2rem;font-weight:600}
    ul.look{margin:0 0 .4rem 1.1rem;padding:0}
    .row{display:flex;gap:10px;margin-top:14px}.row button{flex:1;margin:0}
    .why{display:flex;gap:10px;margin-top:10px}.why input{flex:1}
    .err{color:#b3261e;margin-top:8px}
  </style>`,
  script: `
    const TOKEN = ${JSON.stringify(token)}, BASE = ${JSON.stringify(base)};
    document.addEventListener('click', async (e) => {
      const b = e.target.closest('button[data-a]'); if (!b) return;
      const card = b.closest('.card'), act = b.dataset.a;
      const why = card.querySelector('.why'), err = card.querySelector('.err');
      // A re-roll without a reason is a skip with better manners, and the engine refuses it.
      // Ask here so the refusal is a prompt rather than a red line after the fact.
      if (act === 'reroll') { why.hidden = false; why.querySelector('input').focus(); return; }
      const note = act === 'reroll-send' ? (why.querySelector('input').value || '').trim() : '';
      if (act === 'reroll-send' && !note) { why.querySelector('input').focus(); return; }
      b.disabled = true; err.hidden = true;
      const r = await fetch(BASE + '/answer?k=' + encodeURIComponent(TOKEN), {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ index: Number(card.dataset.i),
                               verdict: act === 'keep' ? 'keep' : 'reroll', why: note }),
      }).catch(() => null);
      const body = r ? await r.json().catch(() => null) : null;
      // A FAILED WRITE MUST NOT LOOK LIKE PROGRESS. The engine refuses a verdict for art this
      // page never served, among four other forgeries; when it does, stay on the card and
      // show what it said, because the operator is the only one who can act on it.
      if (!r || !r.ok || !body || !body.ok) {
        b.disabled = false;
        err.hidden = false;
        err.textContent = (body && body.error) || 'not recorded — try again';
        return;
      }
      card.remove();
      if (!document.querySelector('.card'))
        document.querySelector('.wrap').insertAdjacentHTML('beforeend',
          '<div class="empty"><p>Every shot has a verdict.</p><p>You can close this.</p></div>');
    });`,
});

// ── the handler ──────────────────────────────────────────────────────────────────────────
function handler(req, res, { token, base = "" } = {}) {
  // The store strips its mount prefix before dispatch, so a mounted frapp sees the same
  // path a standalone one does. `base` is only for URLs the page BUILDS.
  const path = (req.url || "").split("?")[0] || "/";

  if (req.method === "GET" && path === "/") {
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
    res.end(page(queue(), token, base));
    return true;
  }

  // THE SERVE, WHICH IS THE WHOLE MECHANISM. The bytes go out and this page records that
  // they did, hashed, at that moment. Nobody attests to anything: an agent cannot call this
  // truthfully about a picture no browser asked for.
  const m = /^\/shot\/(\d+)$/.exec(path);
  if (req.method === "GET" && m) {
    const img = IMAGES[Number(m[1])];
    if (!img || !existsSync(img)) { res.writeHead(404); res.end("no such shot"); return true; }
    let bytes;
    try { bytes = readFileSync(img); }
    catch (e) { res.writeHead(500); res.end(String(e.message || e)); return true; }
    const digest = createHash("sha256").update(bytes).digest("hex").slice(0, 16);
    res.on("finish", () => {
      // AFTER the bytes have left, never before: the record says what happened, and a serve
      // recorded for a response that died in flight is the same lie in a smaller size.
      const r = recordServe(img, digest, `/shot/${Number(m[1])}`);
      if (!r.ok) journal(NAME, "error", "serve-not-recorded", { shot: basename(img), out: r.out });
    });
    res.writeHead(200, { "content-type": "image/png", "cache-control": "no-store" });
    res.end(bytes);
    return true;
  }

  if (req.method === "POST" && path === "/answer") {
    let body = "";
    req.on("data", (d) => { body += d; if (body.length > 8192) req.destroy(); });
    req.on("end", () => {
      try {
        const { index, verdict, why } = JSON.parse(body);
        const img = IMAGES[Number(index)];
        if (!img) throw new Error("no such shot");
        const r = recordTap(img, String(verdict), why ? String(why) : "");
        if (!r.ok) {
          // The engine's own sentence, unedited. It names what is missing and how to record
          // it, which a paraphrase would lose.
          journal(NAME, "warn", "verdict-refused", { shot: basename(img), out: r.out });
          res.writeHead(409, { "content-type": "application/json" });
          res.end(JSON.stringify({ ok: false, error: r.out.replace(/^shot-board:\s*/, "") }));
          return;
        }
        res.writeHead(200, { "content-type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      } catch (e) {
        res.writeHead(500, { "content-type": "application/json" });
        res.end(JSON.stringify({ ok: false, error: String((e && e.message) || e) }));
      }
    });
    return true;
  }

  return false;
}

serveFrapp({
  name: NAME,
  port: PORT,
  title: ENTITY ? `${ENTITY} — shot board` : "shot board",
  blurb: "Judge every reference shot with the shot in front of you.",
  handler,
  // The URLs go back to the Python that started this, so the session can hand the operator a
  // link instead of an instruction. Parsed HERE rather than in ABU, because the wording
  // belongs to the library and one parse site is one thing to fix if it changes.
  log: (line) => {
    console.log(line);
    if (!URLS_OUT) return;
    const url = /(https?:\/\/[^\s]+\?k=[^\s]+)/.exec(String(line));
    if (!url) return;
    let doc = {};
    try { doc = JSON.parse(readFileSync(URLS_OUT, "utf8")); } catch { /* first line */ }
    doc[/phone:/.test(String(line)) ? "phone" : "mac"] = url[1];
    try { writeFileSync(URLS_OUT, JSON.stringify(doc)); } catch { /* best effort */ }
  },
});
