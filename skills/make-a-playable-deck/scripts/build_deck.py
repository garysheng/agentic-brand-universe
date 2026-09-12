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


def spectrum_from(live_hex: str, n: int = 7, sat: float = 0.52) -> list[str]:
    """The spectrum a core colour separates INTO, derived rather than picked.

    THIS IS THE CANON RULE EXPRESSED AS CODE. `canon/craft/palette.json` says the blue is the
    core and the rainbow is what the blue becomes as it leaves, and that the separation is
    faint INSIDE the object and complete OUTSIDE it. UI chrome is light that has left, so it
    takes the saturated end.

    So the stops are the live token's own saturation and value, walked around the hue circle
    in the order the mark's material law names: cyan, green, gold, warm pink, violet. Nothing
    is typed, which matters because a hand-picked rainbow would be a second definition of the
    brand's spectrum sitting next to the measured one and free to disagree with it.
    """
    import colorsys
    r, g, b = (int(live_hex.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    # LIGHT, NOT PAINT, and the first attempt got this wrong in a way worth recording. The
    # live token is fully saturated, so rotating its hue at that saturation produced neon
    # (#FF14C8, #FFF314): rainbow confetti, the exact failure canon warns against in its own
    # words, "accents are enough ... it never has to be loud". Dropping saturation and
    # holding value high is what makes a hue read as something EMITTING rather than painted.
    s = s * sat
    out = []
    for k in range(n):
        # BACKWARD from the blue, which is the order the material law names: cyan, green,
        # gold, warm pink, violet. Forward put violet first and read as a UI theme rather
        # than as a separation.
        hh = (h - k / n) % 1.0
        rr, gg, bb = colorsys.hsv_to_rgb(hh, s, v)
        out.append("#%02X%02X%02X" % (round(rr * 255), round(gg * 255), round(bb * 255)))
    return out


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

    # THE GLOW, opt-in per deck and OFF by default. A universe whose canon has no glow law
    # must not inherit a rainbow chrome from a shared shell, so this is a deck's declaration
    # rather than a shell default.
    glow_note = "chrome: flat accent"
    if deck.get("glow"):
        live = theme.get("live", "#007AFF")
        stops = spectrum_from(live)
        # The core first, then the separation. On the progress and scrub bars the gradient
        # spans the FULL width while the fill reveals it, so the further the bar has
        # travelled the more of what it was carrying is visible. That is the canon rule
        # doing a job rather than decorating one.
        c = stops                       # cyan, green, gold, warm pink, magenta, violet
        # THE POOLS NEED MORE CHROMA THAN THE CALM SET, and this is the second thing the
        # first attempt got wrong. They were drawn at the tempered saturation AND composited
        # with mix-blend-mode:screen, which ADDS light: a pale hue screened over a saturated
        # blue goes white, so the effect read as white blooms and the colour was invisible.
        # Gary, looking at it: "Where are the rainbow colors". Normal blending, real chroma.
        pool = spectrum_from(live, sat=0.88)
        css += f"""
/* --- THE FREEDOM GLOW ON THE CHROME. Derived from the live token, never typed. ---
 *
 * NO ORDERED SPECTRUM, AND THAT IS THE WHOLE DESIGN. The first version was a left-to-right
 * rainbow ramp, which reads as a FLAG however the hues are tuned, because an ordered
 * spectrum band is flag semantics rather than a colour choice. Gary: "I don't want it to
 * just be left right rainbow I want it animated organically like color flowing unexpectedly
 * like energy pulsing."
 *
 * So the bar is BLUE, and colour BLOOMS THROUGH IT. Four soft radial pools, each a single
 * hue, drifting across the bar on four unrelated periods (13s, 17s, 23s, 29s) while their
 * opacity swells on four more. Coprime periods mean the combination does not visibly repeat,
 * which is what makes it read as energy rather than as a loop: no two passes look the same.
 *
 * This is also the canon law rather than a liberty taken with it: the blue is the core and
 * the rainbow is what the blue becomes AS IT LEAVES, so colour appearing out of a blue
 * ground is the argument, and colour arranged in a row beside it is not.
 *
 * Everything animates transform and opacity only, so it composites and costs a phone nothing. */
.glowbar{{position:relative;overflow:hidden;background:{live}}}
.glowbar > i{{position:absolute;top:-300%;height:700%;width:46%;border-radius:50%;
  filter:blur(3px);opacity:0;will-change:transform,opacity}}
.glowbar > i:nth-child(1){{background:radial-gradient(closest-side,{pool[1]},transparent 62%);
  animation:drift1 13s ease-in-out infinite,swell 7s ease-in-out infinite}}
.glowbar > i:nth-child(2){{background:radial-gradient(closest-side,{pool[3]},transparent 62%);
  animation:drift2 17s ease-in-out infinite,swell 11s ease-in-out infinite -3s}}
.glowbar > i:nth-child(3){{background:radial-gradient(closest-side,{pool[5]},transparent 62%);
  animation:drift3 23s ease-in-out infinite,swell 9s ease-in-out infinite -5s}}
.glowbar > i:nth-child(4){{background:radial-gradient(closest-side,{pool[2]},transparent 62%);
  animation:drift4 29s ease-in-out infinite,swell 13s ease-in-out infinite -8s}}
/* Each pool takes a DIFFERENT PATH, and two of them run the other way. A single shared
 * keyframe would put every pool on the same journey at different speeds, which the eye
 * reassembles into a procession. */
@keyframes drift1{{0%{{transform:translateX(-40%) scaleX(1)}}
  50%{{transform:translateX(190%) scaleX(1.5)}}100%{{transform:translateX(-40%) scaleX(1)}}}}
@keyframes drift2{{0%{{transform:translateX(230%) scaleX(1.3)}}
  50%{{transform:translateX(10%) scaleX(.8)}}100%{{transform:translateX(230%) scaleX(1.3)}}}}
@keyframes drift3{{0%{{transform:translateX(60%) scaleX(.7)}}
  35%{{transform:translateX(250%) scaleX(1.2)}}70%{{transform:translateX(-30%) scaleX(1.6)}}
  100%{{transform:translateX(60%) scaleX(.7)}}}}
@keyframes drift4{{0%{{transform:translateX(150%) scaleX(1.1)}}
  40%{{transform:translateX(-20%) scaleX(1.4)}}100%{{transform:translateX(150%) scaleX(1.1)}}}}
/* Never fully on and never fully off: a pool that reaches zero reads as a light switching
 * rather than as energy moving through. */
@keyframes swell{{0%,100%{{opacity:.30}}50%{{opacity:1}}}}

#scrub .fill{{border-radius:3px}}

/* The thumb is the one element the reader's own thumb sits on, so it is where aliveness is
 * felt rather than watched. White core, blue halo, breathing. */
#scrub .thumb{{background:#fff;animation:breathe 3.2s ease-in-out infinite}}
@keyframes breathe{{
  0%,100%{{box-shadow:0 0 0 3px rgba(255,255,255,.20),0 0 9px 3px rgba(0,122,255,.28)}}
  50%{{box-shadow:0 0 0 4px rgba(255,255,255,.28),0 0 15px 5px rgba(0,122,255,.42)}}}}
#scrub.seeking .thumb{{animation:none;
  box-shadow:0 0 0 4px rgba(255,255,255,.32),0 0 18px 7px rgba(0,122,255,.46)}}

/* The active dot: a white core with colour contained at its edge, turning slowly. Same
 * structure as the mark, where the white holds the middle and colour hugs the inside. */
.dot{{position:relative;isolation:isolate}}
.dot.on{{background:#fff}}
.dot.on::after{{content:"";position:absolute;inset:-3.5px;border-radius:50%;z-index:-1;
  background:conic-gradient({", ".join(c + [c[0]])});animation:turn 9s linear infinite;
  opacity:.8}}
@keyframes turn{{to{{transform:rotate(360deg)}}}}

.kicker{{color:{live}}}
.nav button:active{{box-shadow:0 0 12px 2px rgba(0,122,255,.35)}}

/* REDUCED MOTION KEEPS THE COLOUR AND DROPS THE MOTION. Removing the colour too would take
 * the brand out of the chrome for a reader who asked only not to be moved at, so the pools
 * are parked mid-drift at a readable opacity instead of hidden. */
@media(prefers-reduced-motion:reduce){{
  .glowbar > i{{animation:none;opacity:.5}}
  .glowbar > i:nth-child(1){{transform:translateX(0%)}}
  .glowbar > i:nth-child(2){{transform:translateX(70%)}}
  .glowbar > i:nth-child(3){{transform:translateX(140%)}}
  .glowbar > i:nth-child(4){{transform:translateX(210%)}}
  .dot.on::after,#scrub .thumb{{animation:none}}}}
"""
        glow_note = f"chrome: the Freedom Glow, derived from live {live} -> {len(stops)} stops"

    if a.assets:
        src = pathlib.Path(a.assets).expanduser()
        for p in sorted(src.rglob("*")):
            if p.is_file():
                dst = out / p.relative_to(src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(p, dst)

    sections = "\n".join(render(sl, n) for n, sl in enumerate(deck["slides"], 1))
    # The drifting pools are DOM rather than background layers, because four independent
    # transforms cannot be expressed as one element's background.
    glowcls = " glowbar" if deck.get("glow") else ""
    pools = "<i></i><i></i><i></i><i></i>" if deck.get("glow") else ""
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
<!-- Built by abu make-a-playable-deck. {esc(theme_note)}. {esc(glow_note)} -->
<style>
{css}</style>
</head>
<body>
<div id="no"></div>
<div id="stage">
{sections}
</div>
<footer>
  <div id="dots"></div>
  <div id="scrub" role="slider" aria-label="Slide" aria-valuemin="1"
       aria-valuemax="{len(deck['slides'])}"><div class="track"></div>
       <div class="fill{glowcls}">{pools}</div>
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
    print(f"[deck] {glow_note}")
    print("[deck] OPEN IT ON A PHONE BEFORE SENDING IT. The fit is measured at run time "
          "against a real viewport, so a desktop window proves almost nothing about the "
          "device most people will read it on.")


if __name__ == "__main__":
    main()
