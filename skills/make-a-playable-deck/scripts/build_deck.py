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
COMMON = {"kind", "id", "notes", "ground"}


def spectrum_depth(live_hex: str, n: int = 7) -> list[str]:
    """Edge-to-core, the way the blue mark is actually built.

    MEASURED off the blessed light-ground cut: its depth bands run #066BFA at the stroke's
    edge to #4CC7FB at the core, with saturation falling 0.98 to 0.70 and hue drifting 0.598
    to 0.550 toward cyan. This walks the live token along that same path, so the chrome is
    the mark's cross-section rather than a second blue that can disagree with it.
    """
    import colorsys
    r, g, b = (int(live_hex.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4))
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    out = []
    for k in range(n):
        f = k / (n - 1)
        rr, gg, bb = colorsys.hsv_to_rgb(h - 0.048 * f, s * (1 - 0.30 * f), v)
        out.append("#%02X%02X%02X" % (round(rr * 255), round(gg * 255), round(bb * 255)))
    return out


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
    g = sl.get("ground")
    ground = f" ground-{esc(g)}" if g and g not in NO_CLASS_GROUNDS else ""
    return (f'<section class="s{ground}"{sid}>\n  <div class="in">{inner}</div>\n'
            f'</section>')


# `ink` is accepted and emits NO class, because it is the shell's default. Refusing it was
# the first behaviour and it is wrong: being explicit about a slide's ground is good practice,
# and an author who writes the default out loud should not be punished for it. The refusal
# exists for an UNKNOWN ground, whose failure is silent.
GROUNDS = {"cream", "ink"}
NO_CLASS_GROUNDS = {"ink"}


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
        g = sl.get("ground")
        if g is not None and g not in GROUNDS:
            sys.exit(f"build_deck: slide {n} has ground {g!r}; the shell styles "
                     f"{', '.join(sorted(GROUNDS))} and defaults to ink. An unstyled ground "
                     f"emits a dead class and the slide silently stays dark.")
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
        # THE BAR IS THE BLUE MARK'S CROSS-SECTION. Gary: "something resembling how color
        # permeates the logo when on white background is more what I wanted." The blessed
        # light-ground cut is deep blue at the stroke's edge with a soft luminous core down
        # the middle of its thickness and the faintest spectrum trace where that inner light
        # is strongest. Measured, its depth bands run #066BFA at the edge to #4CC7FB at the
        # core, saturation 0.98 falling to 0.70 with the hue drifting 0.598 to 0.550 toward
        # cyan. Those are the numbers this reproduces, derived from the live token by the
        # same walk rather than pasted, so a token change moves the chrome with it.
        #
        # The drifting POOLS are retired. They were a reasonable reading of "organic" and
        # the wrong structure: colour arriving from outside and passing through is not what
        # the mark does. The mark's colour comes from WITHIN, which is also the canon rule,
        # since the blue is the core and the spectrum is what it becomes on the way out.
        core = spectrum_depth(live)
        trace = spectrum_from(live, sat=0.80)
        css += f"""
/* --- THE FREEDOM GLOW ON THE CHROME: the blue mark's own cross-section. ---
 *
 * Deep blue at both edges, a luminous core down the middle, and the faintest spectrum only
 * where that inner light is strongest. Vertical, because the structure is through the bar's
 * THICKNESS rather than along its length: an ordered spectrum running left to right reads as
 * a flag, and that is what the first two attempts kept rediscovering.
 *
 * It is alive in the two ways the light itself is: the core BREATHES, and the spectrum trace
 * drifts slowly along it so the colour is never in the same place twice. Both animate
 * opacity and transform only, so they composite and cost a phone nothing. */
.glowbar{{position:relative;overflow:hidden;
  background:linear-gradient(to bottom,{core[0]} 0%,{core[2]} 26%,{core[6]} 50%,
    {core[2]} 74%,{core[0]} 100%)}}
/* The core, breathing. A separate layer so its opacity can move without touching the blue. */
.glowbar::before{{content:"";position:absolute;inset:0;
  background:linear-gradient(to bottom,transparent 22%,{core[6]} 50%,transparent 78%);
  animation:corebreathe 4.6s ease-in-out infinite}}
@keyframes corebreathe{{0%,100%{{opacity:.45}}50%{{opacity:1}}}}
/* The trace: a wide soft band of spectrum riding the core, drifting. Low opacity on purpose.
 * Canon: inside the body the separation has only FAINTLY begun. */
.glowbar > i{{position:absolute;left:0;top:38%;height:24%;width:38%;border-radius:50%;
  filter:blur(2px);pointer-events:none}}
.glowbar > i:nth-child(1){{background:radial-gradient(closest-side,{trace[1]},transparent 70%);
  opacity:.34;animation:wander1 19s ease-in-out infinite}}
.glowbar > i:nth-child(2){{background:radial-gradient(closest-side,{trace[3]},transparent 70%);
  opacity:.30;animation:wander2 27s ease-in-out infinite}}
.glowbar > i:nth-child(3){{background:radial-gradient(closest-side,{trace[5]},transparent 70%);
  opacity:.28;animation:wander3 23s ease-in-out infinite}}
.glowbar > i:nth-child(4){{display:none}}
/* Three unrelated periods and three different paths, two of them reversed. A shared keyframe
 * at three speeds is a procession, which the eye reassembles into the ordered sweep this
 * design exists to avoid. */
@keyframes wander1{{0%{{transform:translateX(-30%)}}50%{{transform:translateX(200%)}}
  100%{{transform:translateX(-30%)}}}}
@keyframes wander2{{0%{{transform:translateX(220%)}}50%{{transform:translateX(20%)}}
  100%{{transform:translateX(220%)}}}}
@keyframes wander3{{0%{{transform:translateX(90%)}}40%{{transform:translateX(240%)}}
  75%{{transform:translateX(-20%)}}100%{{transform:translateX(90%)}}}}

#scrub .track{{background:rgba(240,236,229,.14)}}
#scrub .fill{{border-radius:5px}}

/* The thumb is the one element the reader's own thumb sits on, so it is where aliveness is
 * felt rather than watched. White core, blue halo, breathing. */
#scrub .thumb{{background:#fff;animation:breathe 3.2s ease-in-out infinite}}
@keyframes breathe{{
  0%,100%{{box-shadow:0 0 0 3px rgba(255,255,255,.20),0 0 9px 3px rgba(0,122,255,.28)}}
  50%{{box-shadow:0 0 0 4px rgba(255,255,255,.28),0 0 15px 5px rgba(0,122,255,.42)}}}}
#scrub.seeking .thumb{{animation:none;
  box-shadow:0 0 0 4px rgba(255,255,255,.32),0 0 18px 7px rgba(0,122,255,.46)}}

.kicker{{color:{live}}}
.nav button:active{{box-shadow:0 0 12px 2px rgba(0,122,255,.35)}}

/* REDUCED MOTION KEEPS THE COLOUR AND DROPS THE MOTION: the core sits at full and the trace
 * parks along it. Removing the colour would take the brand out of the chrome for a reader who
 * asked only not to be moved at. */
@media(prefers-reduced-motion:reduce){{
  .glowbar::before{{animation:none;opacity:.8}}
  .glowbar > i{{animation:none}}
  .glowbar > i:nth-child(1){{transform:translateX(15%)}}
  .glowbar > i:nth-child(2){{transform:translateX(95%)}}
  .glowbar > i:nth-child(3){{transform:translateX(175%)}}
  #scrub .thumb{{animation:none}}}}
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
