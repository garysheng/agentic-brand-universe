#!/usr/bin/env python3
"""works_board.py and its page: a batch of works judged one batch per page (v0.52).

What is load-bearing:

  * the manifest is read loosely (every batch that already exists wrote its own shape), and
    batches follow the recorded `batch` when there is one, else chunks of five in order;
  * nothing that is not a current candidate reaches the board: no `.rN` roll, nothing under
    `rejected/` or `superseded*/`, and the refusal names the item;
  * a verdict is the SHOT BOARD's verdict, in the same sidecar, under the same refusals: no
    approval for a picture the page never served, and a re-roll keeps its note so an agent can
    apply it with `reroll-slot`;
  * re-opening a board never erases a tap, and `--restamp` forgets only an unjudged serve;
  * the page shows only the current candidates, HEAD proves an image serves WITHOUT recording a
    serve, a GET records one, and a tap is announced on the Freedom bus as `judged`.

NOTHING HERE MOUNTS OR SERVES ON A PORT. The page's handler is driven with fake request and
response objects, because a test that takes the operator's tailnet mapping changes the machine
it runs on (the shot board's first test run, 2026-09-14).
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "works_board.py"
PAGE = HERE.parent / "frapps" / "works-board.mjs"
spec = importlib.util.spec_from_file_location("works_board", SCRIPT)
wb = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wb)

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "engine"))
from agenticstory import display, seen  # noqa: E402

FRAPP = (display.FRAPP, "")


def _png(p: Path, tag: str) -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    # A REAL png, distinct per tag, so the page's preview resize has something to decode.
    import struct, zlib
    w = h = 64; shade = (sum(tag.encode()) % 200) + 30
    raw = b"".join(b"\x00" + bytes([shade, 255 - shade, 128]) * w for _ in range(h))
    chunk = lambda t, d: struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d) & 0xffffffff)
    p.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
                  + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"") + tag.encode())
    return p


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.state = self.tmp / "state"
        self.env = mock.patch.dict(os.environ, {"ABU_WORKS_BOARDS": str(self.state),
                                               "FREEDOM_REVIEW_INBOX": str(self.tmp / "inbox.jsonl")})
        self.env.start()
        self.addCleanup(self.env.stop)
        self.chan = mock.patch.object(wb.display, "resolve_channel", return_value=FRAPP)
        self.chan.start()
        self.addCleanup(self.chan.stop)
        self.u = self.tmp / "u"
        self.works = self.u / "works" / "heroes"
        heroes = []
        for i in range(7):
            slug = f"hero-{i}"
            _png(self.works / f"{slug}.png", slug)
            (self.works / f"{slug}.png.recipe.json").write_text(json.dumps({"prompt": "p"}))
            heroes.append({"id": slug, "title": f"Hero {i}", "argues": f"argues {i}",
                           "out": f"works/heroes/{slug}.png"})
        _png(self.works / "hero-0.r1.png", "old roll")
        _png(self.works / "rejected" / "hero-9.png", "turned down")
        _png(self.works / "superseded-unlit" / "hero-8.png", "retired")
        heroes += [{"id": "roll", "title": "Old roll", "out": "works/heroes/hero-0.r1.png"},
                   {"id": "rej", "title": "Rejected", "out": "works/heroes/rejected/hero-9.png"},
                   {"id": "sup", "title": "Retired", "out": "works/heroes/superseded-unlit/hero-8.png"},
                   {"id": "gone", "title": "Missing", "out": "works/heroes/nope.png"}]
        self.manifest = self.works / "heroes.json"
        self.manifest.write_text(json.dumps({"note": "n", "heroes": heroes}))

    def open(self, *extra):
        with mock.patch("sys.stdout"):
            return wb.main(["open", str(self.manifest), "--id", "heroes", "--no-mount", *extra])


class ManifestTest(Base):
    def test_reads_the_list_under_its_key_and_resolves_paths_upward(self):
        items, refused = wb.items_of(self.manifest)
        self.assertEqual([i["key"] for i in items], [f"hero-{i}" for i in range(7)])
        self.assertEqual(items[0]["context"], "argues 0")
        self.assertTrue(items[0]["recipe"].endswith("hero-0.png.recipe.json"))

    def test_chunks_of_five_when_no_batch_is_recorded(self):
        items, _ = wb.items_of(self.manifest)
        self.assertEqual([i["batch"] for i in items], [1, 1, 1, 1, 1, 2, 2])

    def test_recorded_batches_win(self):
        doc = json.loads(self.manifest.read_text())
        for n, h in enumerate(doc["heroes"][:7]):
            h["batch"] = "b" if n % 2 else "a"
        self.manifest.write_text(json.dumps(doc))
        items, _ = wb.items_of(self.manifest)
        self.assertEqual([i["batch"] for i in items], [1, 2, 1, 2, 1, 2, 1])

    def test_a_bare_list_is_a_manifest(self):
        m = self.works / "list.json"
        m.write_text(json.dumps([{"title": "x", "image": "hero-1.png"}]))
        items, _ = wb.items_of(m)
        self.assertEqual(len(items), 1)

    def test_never_boards_what_is_not_a_current_candidate(self):
        items, refused = wb.items_of(self.manifest)
        imgs = " ".join(i["image"] for i in items)
        self.assertNotIn(".r1.", imgs)
        self.assertNotIn("rejected", imgs)
        self.assertNotIn("superseded", imgs)
        joined = "\n".join(refused)
        for title in ("Old roll", "Rejected", "Retired", "Missing"):
            self.assertIn(title, joined)


class VerdictTest(Base):
    def img(self, n=0):
        return self.works / f"hero-{n}.png"

    def test_open_stamps_every_candidate_on_its_batch_board(self):
        self.assertEqual(self.open(), 0)
        b = seen.read_seen(self.img(6))["board"]
        self.assertEqual(b["works"], "heroes")
        self.assertEqual(b["id"], "heroes-b02")
        self.assertEqual(b["options"], ["keep", "reroll"])
        self.assertFalse(seen.sidecar_path(self.works / "hero-0.r1.png").exists())

    def test_no_approval_for_a_picture_the_page_never_served(self):
        self.open()
        with self.assertRaises(ValueError):
            wb.tap(self.img(), "keep")
        seen.record_serve(self.img(), sent_digest=seen.digest(self.img()))
        self.assertEqual(wb.tap(self.img(), "keep")["verdict"], "keep")

    def test_a_reroll_keeps_its_note_and_the_command_applies_it(self):
        self.open()
        wb.tap(self.img(2), "reroll", note="warmer light", audio=["/tmp/n.m4a"])
        s = seen.read_seen(self.img(2))
        self.assertEqual(s["why"], "warmer light")
        self.assertEqual(s["note"], {"text": "warmer light", "audio": ["/tmp/n.m4a"], "at": s["on"]})
        with mock.patch("sys.stdout") as out:
            wb.main(["rerolls", "heroes", "--json"])
        rows = json.loads("".join(c.args[0] for c in out.write.call_args_list))
        self.assertEqual(len(rows), 1)
        self.assertIn("reroll_from_recipe.py", rows[0]["command"])
        self.assertIn("--note 'warmer light'", rows[0]["command"])

    def test_a_reroll_with_no_note_says_so_rather_than_inventing_one(self):
        self.open()
        s = wb.tap(self.img(3), "reroll")
        self.assertEqual(s["why"], wb.NOTELESS)
        self.assertNotIn("note", s)

    def test_reopening_never_erases_a_tap(self):
        self.open()
        wb.tap(self.img(1), "reroll", note="n")
        self.open()
        self.open("--restamp")
        self.assertEqual(seen.read_seen(self.img(1))["verdict"], "reroll")

    def test_restamp_forgets_an_unjudged_serve(self):
        self.open()
        seen.record_serve(self.img(4), sent_digest=seen.digest(self.img(4)))
        self.open()
        self.assertTrue(seen.read_seen(self.img(4))["board"]["display"]["served"])
        self.open("--restamp")
        self.assertFalse(seen.read_seen(self.img(4))["board"]["display"].get("served"))

    def test_a_reroll_written_to_the_same_path_is_shown_again(self):
        self.open()
        seen.record_serve(self.img(5), sent_digest=seen.digest(self.img(5)))
        wb.tap(self.img(5), "keep")
        _png(self.img(5), "the new roll")
        self.open()
        self.assertNotIn("verdict", seen.read_seen(self.img(5)))

    def test_the_view_batches_and_counts(self):
        self.open()
        wb.tap(self.img(0), "reroll", note="x")
        v = wb.board_view("heroes")
        self.assertEqual((v["judged"], v["total"], len(v["batches"])), (1, 7, 2))
        self.assertEqual(v["batches"][0]["rerolls"], 1)
        self.assertEqual(wb.find_item("heroes", "hero-6")["batch"], 2)


NODE = shutil.which("node")


def _freedom_installed() -> bool:
    return display.freedom_lib() is not None


@unittest.skipUnless(NODE and _freedom_installed(), "needs node and an installed Freedom")
class PageTest(Base):
    """The page's handler, driven in-process with fake req/res. No port, no mount."""

    DRIVER = textwrap.dedent("""
        import { EventEmitter } from "node:events";
        const { handler, takeId } = await import(process.env.PAGE_URL);
        function call(method, url, body) {
          return new Promise((done) => {
            const req = new EventEmitter(); req.method = method; req.url = url;
            const res = new EventEmitter(); let code = 0, headers = {}, chunks = [];
            res.writeHead = (c, h) => { code = c; headers = h || {}; return res; };
            res.end = (b) => { if (b) chunks.push(Buffer.from(b)); res.emit("finish");
              setTimeout(() => done({ code, headers, size: Buffer.concat(chunks).length,
                text: Buffer.concat(chunks).toString("utf8") }), 1500); };
            const handled = handler(req, res, { token: "T", base: "/abu-works" });
            if (!handled) done({ code: "unhandled" });
            setImmediate(() => { if (body !== undefined) req.emit("data", JSON.stringify(body)); req.emit("end"); });
          });
        }
        const out = {};
        out.page = await call("GET", "/b/heroes/1");
        out.head = await call("HEAD", "/img/heroes/hero-0");
        out.get = await call("GET", "/img/heroes/hero-1");
        out.full = await call("GET", "/img/heroes/hero-1?full=1");
        out.tap = await call("POST", "/answer", { board: "heroes", n: 1, key: "hero-1", verdict: "keep", note: "" });
        out.refused = await call("POST", "/answer", { board: "heroes", n: 1, key: "hero-2", verdict: "keep", note: "" });
        out.index = await call("GET", "/");
        out.take = takeId("heroes", 3);
        console.log(JSON.stringify(out));
    """)

    def drive(self):
        f = self.tmp / "drive.mjs"
        f.write_text(self.DRIVER)
        r = subprocess.run([NODE, str(f)], capture_output=True, text=True, timeout=120,
                           env={**os.environ, "PAGE_URL": PAGE.as_uri()})
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout.strip().splitlines()[-1])

    def test_the_page_serves_records_and_announces(self):
        self.open()
        out = self.drive()
        page = out["page"]["text"]
        self.assertEqual(out["page"]["code"], 200)
        self.assertIn("Batch 1 of 2", page)
        for i in range(5):
            self.assertIn(f"/abu-works/img/heroes/hero-{i}?k=T", page)
        self.assertNotIn("hero-5", page)
        # The refused ones are named in the "not on the board" list, never drawn as a card.
        for key in ("roll", "rej", "sup"):
            self.assertNotIn(f"img/heroes/{key}", page)
        self.assertIn("4 not on the board", page)
        self.assertIn("data-freedom-recorder", page)
        # HEAD proves the route without recording a serve; GET records one.
        self.assertEqual(out["head"]["code"], 200)
        self.assertEqual(out["head"]["size"], 0)
        self.assertFalse(seen.read_seen(self.works / "hero-0.png")["board"]["display"].get("served"))
        self.assertEqual(out["get"]["code"], 200)
        self.assertTrue(seen.read_seen(self.works / "hero-1.png")["board"]["display"]["served"])
        # The phone gets a compressed preview; ?full=1 gets the original. The witness is the
        # original either way, which the approval below proves by being accepted.
        if shutil.which("sips"):
            self.assertEqual(out["get"]["headers"]["content-type"], "image/jpeg")
        self.assertEqual(out["full"]["headers"]["content-type"], "image/png")
        self.assertIn("full=1", page)
        # The served picture takes an approval; the unserved one is refused, in the engine's words.
        self.assertEqual(out["tap"]["code"], 200)
        self.assertEqual(seen.read_seen(self.works / "hero-1.png")["verdict"], "keep")
        self.assertEqual(out["refused"]["code"], 409)
        self.assertIn("never served", out["refused"]["text"])
        lines = [json.loads(x) for x in (self.tmp / "inbox.jsonl").read_text().splitlines()]
        judged = [x for x in lines if x["kind"] == "judged"]
        self.assertEqual(len(judged), 1)
        self.assertEqual(judged[0]["source"], "abu-works-board")
        self.assertIn("hero-1: keep", judged[0]["item"])
        self.assertIn("1/7 judged", out["index"]["text"])
        self.assertEqual(out["take"], "heroes--b03")


if __name__ == "__main__":
    unittest.main()
