#!/usr/bin/env python3
"""
Explanatory-plate emitter.

Deterministic SVG for the EXPLANATORY layer. Never an image model: labels must be
exact, type must stay crisp at print, a diagram is edited more than drawn, and only
vector follows the reader's theme.

One source emits TWO files: the theme-aware wiki plate and the light-locked copy for
an always-cream surface (a deck). That duplication used to be a manual @media strip,
which is what let a dark plate ship onto a cream slide.
"""
import json, re, sys

# --- tokens: the ONLY colours a plate may use (mirrors the explanatory-plate doctrine)
T = {
    "ink": "#1a1a17", "clay": "#cc785c", "clayLight": "#e08b6d", "cream": "#f7f4ed",
    "paper": "#ece7dc", "line": "#e6dfd1", "mute": "#6b6862", "hair": "#d9d2c4",
    "darkGround": "#141312", "darkCard": "#1e1c1a", "darkLine": "#2f2c28",
    "darkInk": "#f0ede8", "darkMute": "#9a948c", "darkClay": "#e08a5f", "darkYou": "#5d5a55",
}
SANS = "system-ui,-apple-system,sans-serif"

def esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))

# --- the Anthropic mark, as geometry rather than a font glyph -------------------
# THE AUTHENTIC MARK, lifted verbatim from anthropic.com's nav (viewBox 0 0 35 24).
# Do not redraw it by hand: an eyeballed A and a typographic backslash get the
# cap height, the stroke weight, and above all the A-to-bar gap wrong.
# Drawn in a 176x100 box and scaled. Rendering it as the text "A\" gives a serif A
# and a typographic backslash that overshoots the cap height, which reads as wrong.
MARK_W, MARK_H = 35.0, 24.0
_MARK_A = "M9.49897 0L0 24H5.31125L7.25395 18.96H17.1914L19.1341 24H24.4454L14.9464 0H9.49897ZM8.97193 14.5029L12.2227 6.06857L15.4735 14.5029H8.97193Z"
_MARK_BAR = "M24.5475 0H19.3384L28.8374 24H34.0465L24.5475 0Z"

def anthropic_mark(cx, cy, h, cls):
    """Mark centred on (cx, cy) at cap-height h."""
    s = h / MARK_H
    x = cx - (MARK_W * s) / 2.0
    y = cy - h / 2.0
    return (f'<g class="{cls}" transform="translate({x:.2f},{y:.2f}) scale({s:.4f})">'
            f'<path d="{_MARK_A}"/><path d="{_MARK_BAR}"/></g>')

# --- primitives ----------------------------------------------------------------
def rows(spec, out, y):
    """Labelled rows, each with chips saying WHO does it. (the altitudes shape)"""
    cols = spec["columns"]; n = len(cols)
    CW, CH, GAP = spec.get("colWidth", 150), 28, 22
    right = spec.get("width", 900) - 28
    xs = [right - (n - i) * CW - (n - 1 - i) * GAP for i in range(n)]
    # Each column carries its OWN plain-language header. A shared header with
    # cryptic sub-labels floating under row one makes the reader hunt for what
    # the columns mean, which is the job the header was supposed to do.
    out.append(f'<text class="h mute" x="34" y="{y}">{esc(spec["reachFor"])}</text>')
    for i, c in enumerate(cols):
        for j, ln in enumerate(str(c).split("|")):
            out.append(f'<text class="h mute" x="{xs[i]+CW/2}" y="{y+j*16}" text-anchor="middle">{esc(ln)}</text>')
    y += 16 * max(len(str(c).split("|")) for c in cols) + 16
    for r in spec["rows"]:
        out.append(f'<rect class="row" x="28" y="{y}" width="844" height="56" rx="8"/>')
        out.append(f'<text class="n ink" x="48" y="{y+24}">{esc(r["name"])}</text>')
        out.append(f'<text class="s mute" x="48" y="{y+43}">{esc(r["sub"])}</text>')
        for i, who in enumerate(r["who"]):
            cy = y + (56 - CH) / 2
            mine = str(who).upper() == "YOU"
            out.append(f'<rect class="{"you" if mine else "ant"}" x="{xs[i]}" y="{cy}" width="{CW}" height="{CH}" rx="6"/>')
            if mine:
                out.append(f'<text class="chip" x="{xs[i]+CW/2}" y="{cy+19}" text-anchor="middle">YOU</text>')
            else:
                out.append(anthropic_mark(xs[i] + CW / 2, cy + CH / 2, 13, "markfill"))
        y += 64
    if spec.get("base"):
        y += 6
        out.append(f'<rect class="ant" x="28" y="{y}" width="844" height="32" rx="8"/>')
        out.append(f'<text class="b onclay" x="450" y="{y+21}" text-anchor="middle">{esc(spec["base"])}</text>')
        y += 32
    return y

def dotgrid(spec, out, y):
    """N dots, the first k filled. (the corpus shape)"""
    total, on = spec["total"], spec["on"]
    cols = spec.get("cols", 32); R, SP = 8.5, 26
    out.append(f'<text class="h mute" x="34" y="{y}">{esc(spec["eyebrow"])}</text>')
    out.append(f'<text class="n ink" x="34" y="{y+28}">{esc(spec["headline"])}</text>')
    y += 50
    for i in range(total):
        cx = 34 + (i % cols) * SP + R; cy = y + (i // cols) * SP + R
        out.append(f'<circle class="{"on" if i < on else "off"}" cx="{cx}" cy="{cy}" r="{R}"/>')
    y += ((total + cols - 1) // cols) * SP + 30
    for lab in spec.get("legend", []):
        out.append(f'<circle class="{"on" if lab["on"] else "off"}" cx="{34+R}" cy="{y-5}" r="{R}"/>')
        out.append(f'<text class="n ink" x="60" y="{y}">{esc(lab["n"])}</text>')
        out.append(f'<text class="s mute" x="104" y="{y}">{esc(lab["text"])}</text>')
        y += 31
    return y

def split(spec, out, y):
    """Two panels arguing against each other. (the two-layers shape)"""
    PW = 380
    for i, panel in enumerate(spec["panels"]):
        x = 34 + i * (PW + 72)
        accent = "clay" if panel.get("accent") else "mute"
        out.append(f'<rect class="card" x="{x}" y="{y}" width="{PW}" height="{spec.get("h",320)}" rx="12"/>')
        out.append(f'<text class="h {accent}" x="{x+24}" y="{y+36}">{esc(panel["eyebrow"])}</text>')
        out.append(f'<text class="k ink" x="{x+24}" y="{y+74}">{esc(panel["headline"])}</text>')
        out.append(f'<line class="rule" x1="{x+24}" y1="{y+94}" x2="{x+PW-24}" y2="{y+94}"/>')
        yy = y + 128
        for item in panel["items"]:
            out.append(f'<text class="t {"ink" if panel.get("accent") else "mute"}" x="{x+24}" y="{yy}">{esc(item)}</text>')
            yy += 34
        if panel.get("foot"):
            out.append(f'<text class="s mute" x="{x+24}" y="{y+spec.get("h",320)-22}">{esc(panel["foot"])}</text>')
    return y + spec.get("h", 320)

PRIMITIVES = {"rows": rows, "dotgrid": dotgrid, "split": split}

# --- emit ----------------------------------------------------------------------
def style(dark):
    css = f"""
  .bg{{fill:{T['cream']}}} .ink{{fill:{T['ink']}}} .mute{{fill:{T['mute']}}} .clay{{fill:{T['clay']}}}
  .row,.card{{fill:{T['paper']};stroke:{T['line']};stroke-width:2}}
  .you{{fill:{T['mute']}}} .ant{{fill:{T['clay']}}} .markfill{{fill:{T['cream']}}}
  .on{{fill:{T['clay']}}} .off{{fill:none;stroke:{T['hair']};stroke-width:2}}
  .rule{{stroke:{T['line']};stroke-width:2;stroke-linecap:round}}
  .onclay{{fill:{T['cream']}}}
  .chip{{font:600 12.5px {SANS};letter-spacing:.06em;fill:{T['cream']}}}
  .h{{font:600 11.5px {SANS};letter-spacing:.13em}}
  .n{{font:600 15px {SANS}}} .s{{font:12.5px {SANS}}} .t{{font:15px {SANS}}}
  .k{{font:600 26px Georgia,serif}} .b{{font:600 13px {SANS};letter-spacing:.06em}}"""
    if dark:
        css += f"""
  @media (prefers-color-scheme: dark){{
    .bg{{fill:{T['darkGround']}}} .ink{{fill:{T['darkInk']}}} .mute{{fill:{T['darkMute']}}}
    .row,.card{{fill:{T['darkCard']};stroke:{T['darkLine']}}}
    .you{{fill:{T['darkYou']}}} .ant,.on{{fill:{T['darkClay']}}} .off{{stroke:{T['darkLine']}}}
    .rule{{stroke:{T['darkLine']}}} .markfill,.chip,.onclay{{fill:{T['darkGround']}}}
    .clay{{fill:{T['darkClay']}}}
  }}"""
    return css

def build(spec, dark):
    W = spec.get("width", 900)
    out = []
    y = spec.get("padTop", 32)
    body = []
    y = PRIMITIVES[spec["primitive"]](spec, body, y)
    if spec.get("foot"):
        y += 26
        body.append(f'<text class="s mute" x="28" y="{y}">{esc(spec["foot"])}</text>')
    H = int(y + spec.get("padBottom", 22))
    out.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" width="{W}" height="{H}">')
    out.append(f'<title>{esc(spec["title"])}</title>')
    out.append(f'<style>{style(dark)}\n</style>')
    out.append(f'<rect class="bg" width="{W}" height="{H}" rx="10"/>')
    out += body
    out.append('</svg>')
    return "\n".join(out) + "\n", H

# --- gate ----------------------------------------------------------------------
def gate(svg, H, path):
    errs = []
    stray = {h.lower() for h in re.findall(r'#[0-9a-fA-F]{6}', svg)} - {v.lower() for v in T.values()}
    if stray: errs.append(f"off-palette colour(s): {sorted(stray)}")
    if "<title>" not in svg: errs.append("missing <title>")
    if 'role="img"' not in svg: errs.append('missing role="img"')
    # content must fit the viewBox: nothing may be drawn below the declared height
    for m in re.finditer(r'\by="(-?[\d.]+)"', svg):
        if float(m.group(1)) > H: errs.append(f"content at y={m.group(1)} exceeds height {H} (clipped)"); break
    if errs:
        print(f"  GATE FAIL {path}:"); [print(f"    - {e}") for e in errs]
        return False
    return True

def gate_headers(spec):
    """Catch a column header wider than its column. Two headers that overlap read
    as one garbled word, which is the failure that looks fine in code and is
    obvious the second it renders."""
    if spec.get("primitive") != "rows": return True
    cw = spec.get("colWidth", 150); bad = []
    for c in spec.get("columns", []):
        for ln in str(c).split("|"):
            w = len(ln) * 11.5 * 0.60 + len(ln) * 1.5   # 11.5px semibold + .13em tracking
            if w > cw - 8: bad.append((ln, round(w), cw))
    if bad:
        print("  GATE FAIL headers do not fit their column:")
        for ln, w, cw in bad: print(f"    - {ln!r} needs ~{w}px, column is {cw}px")
        return False
    return True

def main(spec_path):
    spec = json.load(open(spec_path))
    ok = True
    if not gate_headers(spec): return 1
    for dark, out_path in ((True, spec["out"]), (False, spec.get("outLightLocked"))):
        if not out_path: continue
        svg, H = build(spec, dark)
        if not gate(svg, H, out_path): ok = False; continue
        open(out_path, "w").write(svg)
        print(f"  wrote {out_path}  ({spec['width']}x{H}, {'theme-aware' if dark else 'light-locked'})")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
