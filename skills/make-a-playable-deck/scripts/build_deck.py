#!/usr/bin/env python3
# /// script
# dependencies = []
# ///
"""Build a mobile-friendly playable deck from slides declared as DATA.

    build_deck.py deck.json --out <dir> [--palette <palette.json>] [--assets <dir>]

WHY A GENERATOR. A deck is deterministic output: given the same slides it must produce the
same bytes, and everything that makes it good on a phone (fit-to-viewport, swipe, deep-linked
slides, a scrub bar you can drag across the whole argument) is mechanism rather than content.
Hand-writing that per deck means hand-writing 300 lines of JavaScript per deck, and the second
deck is where it silently diverges from the first.

WHERE IT CAME FROM. Extracted 2026-09-12 from one deck that was built by hand and used in
front of a real audience on real phones. That deck is the entire evidence base, so treat the
slide vocabulary below as a hypothesis: it covers what that deck needed and what the first
deck through this generator needed, and nothing else has tested it.

THE PALETTE IS READ, NEVER TYPED. Pass --palette and the deck's ink, cream and live come from
the universe's own tokens, so a canon colour change reaches the deck on the next build. Absent
a palette the shell's neutral defaults apply and the deck says so in its provenance.

SLIDE KINDS. Every slide is {"kind": ..., ...} and unknown keys are REFUSED by name rather
than ignored, because a typo in a slide is invisible in the output: the content simply is not
there, on one slide, and nobody notices until someone reads it.
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import shutil
import sys

HERE = pathlib.Path(__file__).resolve().parent
SHELL = HERE / "shell"

KINDS = {
    "cover":     {"kicker", "heading", "lede", "image", "caption"},
    "statement": {"kicker", "heading", "body"},
    "image":     {"kicker", "heading", "image", "caption", "plain", "body"},
    "pair":      {"kicker", "heading", "images", "body"},
    "split":     {"kicker", "heading", "body", "image", "caption"},
    "quote":     {"kicker", "quote", "who", "body"},
    "chat":      {"kicker", "heading", "turns", "body"},
    "table":     {"kicker", "heading", "columns", "rows", "pick", "body"},
    "list":      {"kicker", "heading", "items", "body", "ordered"},
}
COMMON = {"kind", "id", "notes"}


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def rich(s) -> str:
    """The one formatting affordance: **bold** and *italic*, so a slide can stress a word.

    Deliberately not a markdown library. A deck slide is a sentence or two, and pulling in a
    parser would let a slide carry headings, lists and tables that the slide KINDS are there
    to decide. The escape happens first, so no input can inject markup.
    """
    out = esc(s)
    for mark, tag in (("**", "strong"), ("*", "em")):
        parts = out.split(mark)
        if len(parts) % 2 == 1:                      # balanced pairs only
            out = "".join(p if n % 2 == 0 else f"<{tag}>{p}</{tag}>"
                          for n, p in enumerate(parts))
    return out


def paras(body) -> str:
    if not body:
        return ""
    items = body if isinstance(body, list) else [body]
    return "\n".join(f"<p>{rich(p)}</p>" for p in items)


def kicker(s) -> str:
    return f'<p class="kicker">{esc(s)}</p>' if s else ""


def figure(src, caption=None, plain=False) -> str:
    cls = ' class="plain"' if plain else ""
    cap = f"<figcaption>{rich(caption)}</figcaption>" if caption else ""
    return f'<figure{cls}><img src="{esc(src)}" alt="{esc(caption or "")}" loading="lazy">{cap}</figure>'


def render(sl: dict, n: int) -> str:
    k = sl["kind"]
    K = kicker(sl.get("kicker"))
    h = sl.get("heading")
    head = f"<h1>{rich(h)}</h1>" if (k == "cover" and h) else (f"<h2>{rich(h)}</h2>" if h else "")

    if k == "cover":
        inner = (K + head
                 + (f'<p class="lede">{rich(sl["lede"])}</p>' if sl.get("lede") else "")
                 + (figure(sl["image"], sl.get("caption"), plain=True) if sl.get("image") else ""))
    elif k == "statement":
        inner = K + head + paras(sl.get("body"))
    elif k == "image":
        inner = K + head + figure(sl["image"], sl.get("caption"), sl.get("plain", False)) \
                + paras(sl.get("body"))
    elif k == "pair":
        cells = "".join(figure(im["image"], im.get("caption"), im.get("plain", False))
                        for im in sl["images"])
        inner = K + head + f'<div class="pair">{cells}</div>' + paras(sl.get("body"))
    elif k == "split":
        inner = (K + head + '<div class="split"><div>' + paras(sl.get("body")) + "</div><div>"
                 + (figure(sl["image"], sl.get("caption")) if sl.get("image") else "")
                 + "</div></div>")
    elif k == "quote":
        who = f"<cite>{esc(sl['who'])}</cite>" if sl.get("who") else ""
        inner = (K + f"<blockquote><p>{rich(sl['quote'])}</p>{who}</blockquote>"
                 + paras(sl.get("body")))
    elif k == "chat":
        bubbles = "".join(
            f'<div class="b {"me" if t.get("from") == "me" else "them"}">{rich(t["text"])}</div>'
            for t in sl["turns"])
        inner = K + head + f'<div class="chat">{bubbles}</div>' + paras(sl.get("body"))
    elif k == "table":
        cols = sl["columns"]
        thead = "".join(f"<th>{esc(c)}</th>" for c in cols)
        pick = sl.get("pick")
        body = ""
        for r in sl["rows"]:
            cls = ' class="pick"' if pick is not None and r[0] == pick else ""
            cells = "".join(
                f'<td class="n">{rich(c)}</td>' if j else f"<td>{rich(c)}</td>"
                for j, c in enumerate(r))
            body += f"<tr{cls}>{cells}</tr>"
        inner = (K + head + f"<table><thead><tr>{thead}</tr></thead><tbody>{body}</tbody></table>"
                 + paras(sl.get("body")))
    elif k == "list":
        tag = "ol" if sl.get("ordered") else "ul"
        items = "".join(f"<li>{rich(x)}</li>" for x in sl["items"])
        inner = K + head + f"<{tag}>{items}</{tag}>" + paras(sl.get("body"))
    else:                                            # unreachable; validate() refuses first
        raise SystemExit(f"slide {n}: unhandled kind {k!r}")

    sid = f' id="{esc(sl["id"])}"' if sl.get("id") else ""
    return f'<section class="s"{sid}>\n  <div class="in">{inner}</div>\n</section>'


def validate(deck: dict) -> None:
    if not deck.get("slides"):
        sys.exit("build_deck: the deck declares no slides")
    for n, sl in enumerate(deck["slides"], 1):
        k = sl.get("kind")
        if k not in KINDS:
            sys.exit(f"build_deck: slide {n} has kind {k!r}; known kinds are "
                     f"{', '.join(sorted(KINDS))}")
        # REFUSE AN UNKNOWN KEY BY NAME. A mistyped key is the one defect a deck cannot show
        # you: the content is simply absent, on one slide, and the deck still looks finished.
        unknown = set(sl) - KINDS[k] - COMMON
        if unknown:
            sys.exit(f"build_deck: slide {n} ({k}) has unknown key(s) "
                     f"{', '.join(sorted(unknown))}. Allowed here: "
                     f"{', '.join(sorted(KINDS[k] | COMMON))}")
        for req, need in (("image", {"image", "cover", "split"}),
                          ("images", {"pair"}), ("quote", {"quote"}),
                          ("turns", {"chat"}), ("items", {"list"}), ("rows", {"table"})):
            if k in need and k != "cover" and k != "split" and req not in sl:
                sys.exit(f"build_deck: slide {n} ({k}) needs {req!r}")
        if k == "table" and "columns" not in sl:
            sys.exit(f"build_deck: slide {n} (table) needs 'columns'")


def theme_from(palette: pathlib.Path | None) -> tuple[dict, str]:
    if not palette:
        return {}, ("no palette passed; the shell's neutral defaults are in force, so this "
                    "deck is NOT carrying a universe's tokens")
    rec = json.loads(palette.read_text())
    tok = rec.get("tokens") or {}
    out = {}
    for name in ("ink", "cream", "live"):
        hexv = (tok.get(name) or {}).get("hex")
        if hexv:
            out[name] = hexv
    missing = [n for n in ("ink", "cream", "live") if n not in out]
    note = f"palette {palette.name}: " + ", ".join(f"{k} {v}" for k, v in out.items())
    if missing:
        note += f"; MISSING {', '.join(missing)}, shell default used"
    return out, note


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("deck")
    ap.add_argument("--out", required=True)
    ap.add_argument("--palette")
    ap.add_argument("--assets", help="directory of images referenced by the slides; copied "
                                     "beside the html so the folder is self-contained")
    a = ap.parse_args()

    deck = json.loads(pathlib.Path(a.deck).expanduser().read_text())
    validate(deck)
    out = pathlib.Path(a.out).expanduser()
    out.mkdir(parents=True, exist_ok=True)

    theme, theme_note = theme_from(pathlib.Path(a.palette).expanduser() if a.palette else None)
    css = SHELL.joinpath("deck.css").read_text()
    js = SHELL.joinpath("deck.js").read_text()
    if theme:
        css += "\n:root{" + "".join(f"--{k}:{v};" for k, v in theme.items()) + "}\n"

    if a.assets:
        src = pathlib.Path(a.assets).expanduser()
        for p in sorted(src.rglob("*")):
            if p.is_file():
                dst = out / p.relative_to(src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)

    sections = "\n".join(render(sl, n) for n, sl in enumerate(deck["slides"], 1))
    title = esc(deck.get("title", "Deck"))
    summary = esc(deck.get("summary", ""))
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="robots" content="noindex,nofollow">
<title>{title}</title>
<meta name="description" content="{summary}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{summary}">
<meta name="theme-color" content="{theme.get('ink', '#1E1B19')}">
<!-- Built by abu make-a-playable-deck. {esc(theme_note)} -->
<style>
{css}</style>
</head>
<body>
<div id="bar"></div><div id="no"></div>
<div id="stage">
{sections}
</div>
<footer>
  <div id="dots"></div>
  <div id="scrub" role="slider" aria-label="Slide" aria-valuemin="1"
       aria-valuemax="{len(deck['slides'])}"><div class="track"></div><div class="fill"></div>
       <div class="thumb"></div><div class="pill"></div></div>
  <div class="nav"><button id="prev" aria-label="Previous">&#8249;</button>
       <button id="next" aria-label="Next">&#8250;</button></div>
</footer>
<script>
{js}</script>
</body>
</html>
"""
    (out / "index.html").write_text(doc)
    print(f"[deck] {len(deck['slides'])} slides -> {out / 'index.html'}")
    print(f"[deck] theme: {theme_note}")
    print("[deck] OPEN IT ON A PHONE BEFORE SENDING IT. The fit is measured at run time "
          "against a real viewport, so a desktop window proves almost nothing about the "
          "device most people will read it on.")


if __name__ == "__main__":
    main()
