#!/usr/bin/env node
// works-board — approve a batch of WORKS from a phone, one batch per page (SPEC v0.52).
//
// WHY THIS FILE EXISTS. Every batch of finished works (fifty-seven wiki heroes, a run of covers,
// a set of share cards) was reviewed through a page somebody built by hand for that run, so the
// verdicts landed in whatever file that page happened to write and nothing in ABU could read them
// back. This is the one page for all of them. It is the shot board's sibling, and it keeps the
// shot board's one mechanism: the thing that serves the picture is the thing that records the
// tap, so "was the art in front of them" is a fact the page knows, not a claim anyone makes.
//
// ONE BATCH PER PAGE, large images, a title and the line saying what each work is for, and per
// work APPROVE or RE-ROLL with an optional note, typed or spoken. A re-roll's note is written
// beside the picture so an agent re-rolls from the recipe with the note applied
// (`works_board.py rerolls <board>` prints the exact `reroll-slot` commands).
//
// MOUNTED, NOT ONE-SHOT. The judging happens over a day, in sittings, from a phone, so the link
// has to survive every sitting and a reboot: the store imports this file at boot and serves it at
// `/<slug>/`. Every read comes from disk per request, so a restart loses nothing.
//
// NOTHING OF THE VOCABULARY LIVES HERE. Every write goes through `works_board.py`, which goes
// through `agenticstory.seen`, the same record and the same refusals the shot board and
// `lock-shot` use. This file renders, sends bytes, and shells out. A refused write keeps the card
// as it was and shows the refusal, because a page that advances on a failed save discards work.
import { existsSync, readdirSync, readFileSync, mkdirSync } from "node:fs";
import { createHash } from "node:crypto";
import { spawnSync, execFile } from "node:child_process";
import { join, resolve, dirname, basename, extname } from "node:path";
import { homedir } from "node:os";
import { pathToFileURL, fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const WORKS_BOARD = resolve(HERE, "..", "scripts", "works_board.py");
const PY = process.env.ABU_PYTHON || "python3";
const NAME = "abu-works";
const SOURCE = "abu-works-board";

// ── WHERE FREEDOM'S LIBRARY IS. Resolved at every start from the newest install (freedom#106). ─
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
  if (!v) throw new Error(`${file}: no installed Freedom under ${FREEDOM_CACHE}; a works board needs its frapp library.`);
  return join(FREEDOM_CACHE, v, ".agents", "lib", file);
}
const lib = async (f) => import(pathToFileURL(freedomLib(f)).href);
const { serveFrapp, journal } = await lib("freedom-frapp.mjs");
const { shell } = await lib("freedom-frapp-style.mjs");
// THE SHARED RECORDER, never a hand-rolled MediaRecorder: stacked takes, upload on stop, the
// server-side join, live words, the pinned control (freedom#170).
const REC = await lib("freedom-frapp-recorder.mjs");
// THE SHARED BUS. Every tap is announced so the session that opened the board hears it
// (kind `judged`), instead of polling `status` by hand (2026-09-15, the shot board's lesson).
const NOTIFY = await lib("freedom-frapp-notify.mjs");
let hear = null;
try { ({ hear } = await lib("freedom-transcribe.mjs")); } catch { /* no transcriber: typed notes only */ }

const STATE = process.env.ABU_WORKS_BOARDS || join(homedir(), ".freedom", "frapps", "abu-works-board");
const TAKES = join(STATE, "takes");   // takes waiting on a Save, per batch page
const NOTES = join(STATE, "notes");   // spoken notes once saved, per board

// ── reading the board: always `works_board.py`, never a second parser here ─────────────────
function py(args, { timeout = 60000 } = {}) {
  const r = spawnSync(PY, [WORKS_BOARD, ...args], { encoding: "utf8", timeout,
    env: { ...process.env, ABU_WORKS_BOARDS: STATE } });
  return { ok: r.status === 0, out: `${r.stdout || ""}`.trim(), err: `${r.stderr || ""}`.trim() };
}
function readBatch(bid, n) {
  const r = py(["batch", bid, String(n), "--json"]);
  try { return JSON.parse(r.out); } catch { return { ok: false, error: r.err || r.out || "no board" }; }
}
function readBoards() {
  const r = py(["boards", "--json"]);
  try { return JSON.parse(r.out); } catch { return []; }
}
// The one work a key names, read fresh so a stale card can never reach a file.
function findItem(bid, key) {
  const r = py(["item", bid, key, "--json"]);
  try { const it = JSON.parse(r.out); return it && it.image ? it : null; } catch { return null; }
}

// ── the page ────────────────────────────────────────────────────────────────────────────────
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
// Every URL the page builds is RELATIVE to the mount (`base` is "/abu-works" mounted, "" alone),
// never absolute: an absolute `/img/...` broke every picture on the phone (2026-09-18).
const at = (base, rel) => (base ? `${base}/${rel}` : `/${rel}`);
const withKey = (url, token) => `${url}${url.includes("?") ? "&" : "?"}k=${encodeURIComponent(token)}`;
export const takeId = (bid, n) => `${bid}--b${String(n).padStart(2, "0")}`;

const VERDICT_WORD = { keep: "Approved", reroll: "Re-roll" };

function cardHtml(it, { bid, base, token }) {
  const src = withKey(at(base, `img/${encodeURIComponent(bid)}/${encodeURIComponent(it.key)}`), token);
  const state = it.verdict
    ? `<p class="verdict ${esc(it.verdict)}"><b>${esc(VERDICT_WORD[it.verdict] || it.verdict)}</b>`
      + `${it.note ? ` · ${esc(it.note)}` : ""}${it.audio && it.audio.length ? " · voice note kept" : ""}</p>`
    : "";
  return `<section class="card${it.verdict ? " judged" : ""}" data-key="${esc(it.key)}" data-verdict="${esc(it.verdict || "")}">
    <a href="${src}" target="_blank" rel="noopener"><img class="work" src="${src}" alt="${esc(it.title)}" loading="eager"></a>
    <h2>${esc(it.title)} <span class="take">take ${Number(it.take) || 1}</span></h2>
    ${it.context ? `<p class="ctx">${esc(it.context)}</p>` : ""}
    <p class="file">${esc(it.file)}</p>
    ${state}
    <div class="row">
      <button type="button" data-a="reroll">Re-roll</button>
      <button type="button" class="primary" data-a="keep">Approve</button>
    </div>
    <button type="button" class="linkish" data-a="note">Add a note</button>
    <div class="note" hidden>
      <div class="recslot"></div>
      <textarea rows="2" maxlength="1000" placeholder="What should change? Optional. Or tap the red dot and say it."></textarea>
      <div class="row">
        <button type="button" data-a="send-reroll">Send re-roll</button>
        <button type="button" class="primary" data-a="send-keep">Approve with note</button>
      </div>
    </div>
    <p class="err" hidden></p>
  </section>`;
}

function batchPage(v, { base, token }) {
  const bid = v.id, n = v.n, total = v.batches.length;
  const id = takeId(bid, n);
  const nav = (m, label) => (m >= 1 && m <= total)
    ? `<a class="navbtn" href="${withKey(at(base, `b/${encodeURIComponent(bid)}/${m}`), token)}">${label}</a>`
    : `<span class="navbtn off">${label}</span>`;
  const chips = v.batches.map((b) => `<a class="chip${b.n === n ? " here" : ""}${b.judged === b.count ? " done" : ""}"
      href="${withKey(at(base, `b/${encodeURIComponent(bid)}/${b.n}`), token)}">${b.n}</a>`).join("");
  const here = v.batches[n - 1] || { judged: 0, count: v.items.length };
  const next = v.batches.find((b) => b.n > n && b.judged < b.count) || v.batches.find((b) => b.judged < b.count && b.n !== n);
  const nextHref = next ? withKey(at(base, `b/${encodeURIComponent(bid)}/${next.n}`), token) : null;
  return shell({
    title: v.title,
    subtitle: `Batch ${n} of ${total} · ${here.judged}/${here.count} judged here · ${v.judged}/${v.total} overall`,
    base,
    body: `<nav class="bnav">${nav(n - 1, "‹ Prev")}<details class="chips"><summary>All batches</summary><div>${chips}</div></details>${nav(n + 1, "Next ›")}</nav>
      <div id="recHome" hidden>${REC.recorderHtml({ root: TAKES, id, idle: "Say what should change", hint: "Tap to start, tap again to stop. Every take is kept." })}</div>
      ${v.items.map((it) => cardHtml(it, { bid, base, token })).join("")}
      <div class="finished" ${here.judged === here.count ? "" : "hidden"}>
        <p>Every work in this batch has a verdict.</p>
        ${nextHref ? `<a class="navbtn primary" href="${nextHref}">Next batch to judge ›</a>` : `<p>That was the last one. You can close this.</p>`}
      </div>
      ${v.refused && v.refused.length ? `<details class="refused"><summary>${v.refused.length} not on the board</summary><ul>${v.refused.map((r) => `<li>${esc(r)}</li>`).join("")}</ul></details>` : ""}`,
    head: `<style>${REC.recorderCss()}
      .work{width:100%;height:auto;border-radius:10px;display:block;background:#0002}
      .card{margin-bottom:28px}
      .card h2{margin:.6rem 0 .2rem}
      .ctx{margin:.2rem 0 .3rem;line-height:1.4}
      .file{opacity:.55;font-size:.8rem;margin:0 0 .6rem;word-break:break-all}
      .take{font-size:.75rem;font-weight:500;opacity:.7;padding:.1em .5em;border:1px solid currentColor;border-radius:999px;vertical-align:middle;margin-left:.3em}
      .row{display:flex;gap:10px;margin-top:10px}.row button{flex:1;margin:0}
      .linkish{background:none;border:none;box-shadow:none;padding:6px 0;margin-top:4px;min-height:44px;text-decoration:underline;opacity:.75;width:auto}
      .note:not([hidden]){display:block;margin-top:8px}
      .note textarea{width:100%;box-sizing:border-box;font:inherit;padding:10px;border-radius:10px}
      .verdict{margin:.3rem 0;padding:.4rem .6rem;border-radius:8px;border:1px solid currentColor}
      .verdict.keep{color:var(--good,#1b7f3b)}.verdict.reroll{color:var(--bad,#b3261e)}
      .judged .work{opacity:.8}
      .err{color:#b3261e;margin-top:8px}
      .bnav{display:flex;gap:8px;align-items:flex-start;margin:0 0 16px}
      .navbtn{display:inline-flex;align-items:center;justify-content:center;min-height:44px;padding:0 14px;border-radius:10px;border:1px solid currentColor;text-decoration:none;white-space:nowrap}
      .navbtn.off{opacity:.3}
      .navbtn.primary{font-weight:600}
      .chips{flex:1;text-align:center}.chips summary{min-height:44px;display:flex;align-items:center;justify-content:center;cursor:pointer}
      .chips div{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;padding-top:6px}
      .chip{min-width:40px;min-height:40px;display:inline-flex;align-items:center;justify-content:center;border-radius:8px;border:1px solid currentColor;text-decoration:none;opacity:.7}
      .chip.done{opacity:.35}.chip.here{opacity:1;font-weight:700}
      .finished:not([hidden]){text-align:center;padding:12px 0 24px}
      .refused{opacity:.7;font-size:.85rem}
    </style>`,
    script: `
    const TOKEN = ${JSON.stringify(token)}, BASE = ${JSON.stringify(base)}, BOARD = ${JSON.stringify(bid)}, N = ${n};
    ${REC.recorderJs({ base, token, id, params: { board: bid, n: String(n) } })}
    const rec = document.querySelector('[data-freedom-recorder]');
    let recCard = null;
    // ONE RECORDER PER PAGE (the library's shape), moved into whichever card's note is open, so a
    // spoken note always belongs to the card it was said under.
    function openNote(card) {
      const note = card.querySelector('.note');
      note.hidden = false;
      if (rec && recCard !== card && !(window.freedomRecorder && window.freedomRecorder.pending())) {
        card.querySelector('.recslot').appendChild(rec); recCard = card;
      }
      card.querySelector('[data-a="note"]').hidden = true;
    }
    function done(card, verdict, note) {
      card.dataset.verdict = verdict; card.classList.add('judged');
      let v = card.querySelector('.verdict');
      if (!v) { v = document.createElement('p'); card.querySelector('.row').before(v); }
      v.className = 'verdict ' + verdict;
      v.innerHTML = '<b>' + (verdict === 'keep' ? 'Approved' : 'Re-roll') + '</b>' + (note ? ' · ' + note.replace(/[&<>]/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) : '');
      card.querySelector('.note').hidden = true;
      card.querySelector('[data-a="note"]').hidden = false;
      card.querySelector('textarea').value = '';
      const left = [...document.querySelectorAll('.card')].filter((c) => !c.dataset.verdict).length;
      if (!left) document.querySelector('.finished').hidden = false;
      else { const nx = [...document.querySelectorAll('.card')].find((c) => !c.dataset.verdict); if (nx) nx.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
    }
    document.addEventListener('click', async (e) => {
      const b = e.target.closest('button[data-a]'); if (!b) return;
      const card = b.closest('.card'); if (!card) return;
      const act = b.dataset.a, err = card.querySelector('.err');
      if (act === 'note' || act === 'reroll') { openNote(card); card.querySelector('textarea').focus({ preventScroll: true }); return; }
      const verdict = (act === 'keep' || act === 'send-keep') ? 'keep' : 'reroll';
      const note = (card.querySelector('textarea').value || '').trim();
      const withTakes = recCard === card && window.freedomRecorder && window.freedomRecorder.pending();
      card.querySelectorAll('button').forEach((x) => x.disabled = true); err.hidden = true;
      const post = () => fetch((BASE ? BASE + '/' : '/') + 'answer?k=' + encodeURIComponent(TOKEN), {
        method: 'POST', headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ board: BOARD, n: N, key: card.dataset.key, verdict, note, takes: !!withTakes }),
      }).then(async (r) => { const j = await r.json().catch(() => null); return (r.ok && j && j.ok) ? Object.assign(j, { ok: true }) : { ok: false, error: (j && j.error) || 'not recorded' }; })
        .catch(() => ({ ok: false, error: 'no connection' }));
      const r = withTakes ? await window.freedomRecorder.save(post, { after: 'stay' }) : await post();
      card.querySelectorAll('button').forEach((x) => x.disabled = false);
      // A FAILED WRITE MUST NOT LOOK LIKE PROGRESS. Stay on the card and say what the engine said.
      if (!r || !r.ok) { err.hidden = false; err.textContent = (r && r.error) || 'not recorded, try again'; return; }
      done(card, verdict, r.note || note);
    });`,
  });
}

function indexPage(boards, { base, token }) {
  return shell({
    title: "Works to approve",
    base,
    body: boards.length
      ? boards.map((b) => `<section class="card"><h2>${esc(b.title)}</h2>
          <p>${b.judged}/${b.total} judged across ${b.batches} batch${b.batches === 1 ? "" : "es"}</p>
          <a class="navbtn" href="${withKey(at(base, `b/${encodeURIComponent(b.id)}/${b.nextBatch || 1}`), token)}">${b.judged === b.total ? "Look again" : "Judge the next batch"} ›</a></section>`).join("")
      : `<div class="empty"><p>No works boards are open.</p></div>`,
    head: `<style>.navbtn{display:inline-flex;align-items:center;min-height:44px;padding:0 14px;border-radius:10px;border:1px solid currentColor;text-decoration:none}</style>`,
  });
}

// ── the handler ────────────────────────────────────────────────────────────────────────────
const MIME = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp" };
const json = (res, code, body) => {
  res.writeHead(code, { "content-type": "application/json", "cache-control": "no-store" });
  res.end(JSON.stringify(body));
};
const TAKE_ID = /^([a-z0-9][a-z0-9-]{0,63})--b(\d{2,})$/;

export function handler(req, res, { token = "", base = "" } = {}) {
  const [path, qs] = String(req.url || "/").split("?");

  // Voice takes and live words, through the shared recorder. Gated on the library's own route
  // list, never a literal path, or `/partial` silently 404s (2026-09-24).
  if (REC.isRecorderRoute(path)) {
    mkdirSync(TAKES, { recursive: true });
    return REC.handleTake(req, res, { root: TAKES, known: (id) => TAKE_ID.test(id), hear });
  }

  if (req.method === "GET" && (path === "/" || path === "")) {
    const boards = readBoards().map((b) => ({ ...b, nextBatch: 1 }));
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
    res.end(indexPage(boards, { base, token }));
    return true;
  }

  let m = /^\/b\/([^/]+)\/(\d+)\/?$/.exec(path);
  if (req.method === "GET" && m) {
    const v = readBatch(decodeURIComponent(m[1]), Number(m[2]));
    if (!v || v.ok === false || !v.items) {
      res.writeHead(404, { "content-type": "text/plain" }); res.end(v && v.error ? v.error : "no such board");
      return true;
    }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store" });
    res.end(batchPage(v, { base, token }));
    return true;
  }

  // THE SERVE, WHICH IS THE WHOLE MECHANISM. The bytes go out, and only after they have left is
  // the serve recorded, hashed, against the board. An agent cannot call this truthfully about a
  // picture no browser asked for.
  m = /^\/img\/([^/]+)\/([^/]+)$/.exec(path);
  // HEAD answers whether the picture would serve WITHOUT recording a serve, so an agent can
  // prove the route works over the tailnet and leave the witness untouched for the operator.
  if ((req.method === "GET" || req.method === "HEAD") && m) {
    const bid = decodeURIComponent(m[1]), key = decodeURIComponent(m[2]);
    const it = findItem(bid, key);
    if (!it || !existsSync(it.image)) { res.writeHead(404); res.end("no such work"); return true; }
    let bytes;
    try { bytes = readFileSync(it.image); } catch (e) { res.writeHead(500); res.end(String(e.message || e)); return true; }
    const digest = createHash("sha256").update(bytes).digest("hex").slice(0, 16);
    const type = MIME[extname(it.image).toLowerCase()] || "application/octet-stream";
    if (req.method === "HEAD") {
      res.writeHead(200, { "content-type": type, "cache-control": "no-store", "content-length": bytes.length });
      res.end();
      return true;
    }
    res.on("finish", () => {
      execFile(PY, [WORKS_BOARD, "served", it.image, "--digest", digest, "--url", `/img/${bid}/${key}`],
        { env: { ...process.env, ABU_WORKS_BOARDS: STATE }, timeout: 30000 }, (err, out, stderr) => {
          if (err) journal(NAME, "error", "serve-not-recorded", { work: basename(it.image), out: String(stderr || err.message) });
        });
    });
    res.writeHead(200, { "content-type": type, "cache-control": "no-store", "content-length": bytes.length });
    res.end(bytes);
    return true;
  }

  if (req.method === "POST" && path === "/answer") {
    let body = "";
    req.on("data", (d) => { body += d; if (body.length > 16384) req.destroy(); });
    req.on("end", async () => {
      try {
        const { board, n, key, verdict, note = "", takes = false } = JSON.parse(body);
        const bid = String(board), k = String(key);
        const it = findItem(bid, k);
        if (!it) return json(res, 404, { ok: false, error: "that work is no longer on the board" });
        let text = String(note || "").trim();
        const audio = [];
        if (takes) {
          const id = takeId(bid, Number(n));
          const stamp = new Date().toISOString().replace(/[:.]/g, "-");
          const stem = join(NOTES, bid, `${k}-${stamp}`);
          mkdirSync(dirname(stem), { recursive: true });
          const got = REC.saveWithTakes({ root: TAKES, id, answer: { note: text || "voice" }, stem, write: (x) => x });
          if (got.audio) {
            audio.push(...got.audio.files);
            let said = got.audio.transcript;
            if (!said && hear && got.audio.files[0]) {
              const h = await hear(got.audio.files[0]);
              said = h && h.ok ? h.text : null;
            }
            if (said) text = text ? `${text}\n\n(spoken) ${said.trim()}` : said.trim();
            else if (!text) text = `voice note, not transcribed: ${got.audio.files.join(", ")}`;
          }
        }
        const r = py(["tap", "--board", bid, "--key", k, "--verdict", String(verdict), "--note", text,
          ...audio.flatMap((a) => ["--audio", a]), "--json"]);
        if (!r.ok) {
          journal(NAME, "warn", "verdict-refused", { work: k, out: r.err || r.out });
          return json(res, 409, { ok: false, error: (r.err || r.out).replace(/^works-board:\s*/, "") });
        }
        NOTIFY.judged({ source: SOURCE, title: `works board: ${bid}`, item: `${k}: ${verdict}${text ? ` (${text.slice(0, 120)})` : ""}`,
          notes: `${it.image}.readback.json` });
        return json(res, 200, { ok: true, verdict, note: text });
      } catch (e) {
        return json(res, 500, { ok: false, error: String((e && e.message) || e) });
      }
    });
    return true;
  }

  return false;
}

export const frapp = {
  title: "Works to approve",
  blurb: "One batch of works per page: approve or re-roll each, with a note if you want one.",
  needsSecureContext: true,   // the note can be spoken, and a microphone needs a secure origin
  handler,
};

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const argv = process.argv.slice(2);
  const i = argv.indexOf("--port");
  serveFrapp({ name: NAME, port: Number(i > -1 ? argv[i + 1] : 7463) || 7463, title: frapp.title,
    blurb: frapp.blurb, needsSecureContext: true, open: !argv.includes("--no-open"), handler });
}
