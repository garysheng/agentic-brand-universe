#!/usr/bin/env python3
"""The words-before-art gate, as a REFUSAL instead of a paragraph.

`voice-gate` shipped as a SKILL.md and nothing else, which means it was prose, and
prose does not bind. Every rule this framework lost during a real book run was prose;
every rule it kept was a refusal in code. A gate described in a markdown file is a gate
an agent carrying a book's momentum reads, agrees with, and does not run.

So this is the same checks, exiting non-zero.

THE RULES LIVE AT https://garysheng.com/voice.md. That published file is the authority
and this script carries a MECHANIZED SUBSET of it, because "read it aloud and see if it
sounds like a slogan" cannot be a regex. Two consequences:

1. The spec is FETCHED, hashed, and compared against the hash this rule table was
   derived from. When the published spec moves, the gate fails with the diff and a
   one-command fix (`--adopt-spec`). Without that, the real failure mode is silent: a
   rule added to VOICE.md that the sweep never enforces. Totalizing emphasis was added
   2026-07-28 and had still never been checked here on 2026-08-02, by which point "the
   whole ___" had reached 192 shipped books, and "the entire ___" was invisible on top
   of that because the wordlist only ever said "whole".
2. Network failure never fails the gate. A vendored copy sits in `../data/voice.md`, so
   an offline run still checks; the report says which copy it used.

SEVERITY IS THE DESIGN. A gate that fires on every "just" in thirty spreads of dialogue
gets forced, and a forced gate is worse than none because it also lies about having
checked. So there are three tiers and only two of them stop you:

  BLOCK     mechanical certainty, no judgment exists. An em dash is an em dash.
  REVIEW    real judgment, rare enough to adjudicate one at a time. FIX it, or WAIVE it
            with a written reason. This is where totalizing emphasis and filler live.
  ADVISORY  printed, never gated. Genuinely undecidable by grep: Nation of Fire's own
            `capitalizeNote` says the `Spirit` rule INVERTS on the possessive ("his
            spirit" is a man's own spirit-man, and capitalizing it is a doctrinal error
            rather than a style win), and `neverDisparage` needs to know whether the
            narrator holds an attitude or is attributing it to the world.

A waiver is a written decision, not a mute button. It records the rule, the exact match,
the verbatim line and a reason, and it is keyed on the LINE TEXT rather than the line
number: edit the sentence and the waiver retires itself, because the reasoning was about
a sentence that no longer exists.

  python3 voice_gate.py <universe> <text-file> [...] [--waivers P] [--offline]
  python3 voice_gate.py <universe> <text-file> --emit-waivers   # stubs for open REVIEWs
  python3 voice_gate.py --adopt-spec                            # after reading the diff
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

SPEC_URL = "https://garysheng.com/voice.md"
VENDORED_SPEC = Path(__file__).resolve().parent.parent / "data" / "voice.md"

# sha256 of the published spec this rule table was derived from. Bump it with
# `--adopt-spec` AFTER reading the diff and porting any new hard rule into RULES.
RULES_DERIVED_FROM = "4993b2fb7122f60d43380c1ae7f52c498f8e44d6c7e26bd6e4c9250358330a06"

BLOCK, REVIEW, ADVISORY = "BLOCK", "REVIEW", "ADVISORY"


@dataclass(frozen=True)
class Rule:
    id: str
    severity: str
    pattern: re.Pattern
    note: str
    #: Skip inside a markdown blockquote. VOICE.md exempts verbatim Scripture
    #: ("quotations keep their printed casing"), and a book in this framework quotes
    #: Scripture on nearly every closing plate. A blockquote is also where sourced
    #: testimony belongs, which is what makes this narrow exemption safe.
    quotation_exempt: bool = False


# `just` has senses that are not filler, and deleting them changes the meaning:
# comparative ("just as our master did"), temporal ("just then", "you just told me" =
# moments ago), spatial ("just past the gate"), limiting ("just enough", "just a nicer
# building", "just going"). Flagging those trains the author to ignore the gate, and an
# ignored gate is worse than none. Checked on the word AFTER, which is where the sense
# lives. What survives is the filler sense, an adjective or comparative it only
# underlines ("this is just better"), which is the one the removal test deletes.
JUST_OK = re.compile(
    r"\bjust\s+(?:"
    r"as|like|then|now|before|after|past|beyond|inside|outside|over|under|off|above|"
    r"below|short|enough|about|barely|shy"
    r"|a|an|one|two|the"                    # limiting: "just a nicer building"
    r"|\w+ing\b|\w+ed\b"                    # "just going" / "just described"
    # irregular past tenses, where "just" means moments ago
    r"|told|did|found|said|saw|gave|came|went|made|took|put|heard|spoke|left|read"
    r"|brought|got|had|been|felt|sent|kept|held|caught|met|lost|won|paid|sat|stood"
    r"|ran|began|wrote|bought|taught|thought"
    r")\b", re.I)


def one_word_split(term: str) -> str:
    """Regex matching a `oneWord` term that has been SPLIT by a space or hyphen.

    Anchored on the FULL term: every alternative is a real split point, so
    prefix + suffix always reassembles into the term itself. The previous
    implementation matched `term[:6] + r"[ -]\\w"`, a fixed six-character prefix
    with anything after it, which in a Christian universe made `Christofuturist`
    fire on the word "Christ" followed by any word at all. "Christ will not come
    back" was reported as a BLOCKING misspelling of Christofuturist. The check
    never caught a real defect that this one misses, because a genuine split of a
    compound is exactly what this enumerates.
    """
    alts = "|".join(
        rf"{re.escape(term[:i])}[ -]{re.escape(term[i:])}"
        for i in range(1, len(term))
    )
    return rf"\b(?:{alts})\b"


RULES: tuple[Rule, ...] = (
    # --- BLOCK: no judgment call exists. -----------------------------------------
    Rule("em-dash", BLOCK, re.compile(r"[—–]"),
         "use a colon, a period, parentheses, or two sentences"),
    Rule("christofuturist-spelling", BLOCK,
         re.compile(r"Christo-futurist|Christian futurist"),
         "'Christofuturist' is one word, no hyphen"),
    Rule("claude-credit", BLOCK,
         re.compile(r"Co-Authored-By: Claude|Generated with \[?Claude Code"),
         "personal-voice work is never co-authored by Claude"),
    Rule("spirit-compound", BLOCK, re.compile(r"\bspirit[ -](dead|alive|led)\b"),
         "'Spirit-dead' / 'Spirit-alive' / 'Spirit-led': capitalized and hyphenated"),

    # --- REVIEW: judgment, but rare enough to adjudicate one at a time. -----------
    Rule("totalizing-emphasis", REVIEW,
         re.compile(r"\bthe (?:whole|entire)\b(?:\s+\w+)?|\bthat(?: i|')s all\b|"
                    r"\ball of it\b", re.I),
         "delete the word and check whether anything changed. If nothing did, it was "
         "emphasis standing in for a sentence good enough to land alone. Concrete and "
         "temporal uses are ordinary English and stay ('the whole time')",
         quotation_exempt=True),
    Rule("not-x-but-y", REVIEW,
         re.compile(r"\bnot\s+(?:only\s+)?[^.;:!?\n]{2,60}?,?\s+but\s+(?:rather\s+)?"
                    r"[^.;:!?\n]{2,60}", re.I),
         "cut X unless a smart reader would plausibly hold it before this sentence"),
    Rule("tautology-then-negation", REVIEW,
         re.compile(r"\b(?:was|were|is|are) real\.|\b(?:None|Nothing|Nobody|No one)\b"
                    r"[^.!?\n]*\b(?:fake|false|untrue|staged|made up|imagined)\b"),
         "delete the negative sentence. If the reader would think the same thing, it "
         "was carrying nothing"),
    Rule("automate-vs-streamline", REVIEW,
         re.compile(r"\bautomat(?:e|ed|es|ing|ion)\b", re.I),
         "prefer 'streamline' or 'hand off'. Reserve 'automate' for removing the human "
         "entirely, which is almost always a caution"),
    Rule("casual-slang", REVIEW, re.compile(r"\b(?:bussin|no cap|glaz(?:e|ing))\b", re.I),
         "no casual slang on a public surface"),
    Rule("filler", REVIEW, re.compile(r"\b(?:really|just|very|truly)\b(?:\s+\w+)?", re.I),
         "removal test, not a wordlist: cut it if the meaning does not change",
         quotation_exempt=True),
)


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str
    where: str
    line: str
    match: str
    note: str

    def key(self) -> tuple[str, str, str]:
        """Waiver identity: rule + what matched + the verbatim line.

        Deliberately NOT the line NUMBER. A waiver written against line 22 would follow
        an inserted spread down to line 25 and go on muting a sentence nobody ever
        adjudicated.
        """
        return (self.rule, self.match.strip(), self.line.strip())


# ---------------------------------------------------------------------------
# the published spec
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SpecSource:
    sha256: str
    origin: str          # "network" | "vendored"
    text: str = ""
    detail: str = ""

    @property
    def current(self) -> bool:
        return self.sha256 == RULES_DERIVED_FROM


def fetch_spec(timeout: float = 8.0, offline: bool = False) -> SpecSource:
    """The published spec, or the vendored copy when the network is unavailable.

    Never raises. An offline machine still gets a full check; it just gets told which
    copy of the rules it ran against.
    """
    detail = "network disabled by --offline"
    if not offline:
        try:
            req = urllib.request.Request(SPEC_URL, headers={"User-Agent": "abu-voice-gate"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8")
            return SpecSource(hashlib.sha256(text.encode()).hexdigest(), "network", text)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            detail = f"{type(e).__name__}, fell back to the vendored copy"
    text = VENDORED_SPEC.read_text(encoding="utf-8") if VENDORED_SPEC.exists() else ""
    return SpecSource(hashlib.sha256(text.encode()).hexdigest(), "vendored", text, detail)


def spec_diff(spec: SpecSource) -> list[str]:
    if spec.origin != "network" or not VENDORED_SPEC.exists():
        return []
    old = VENDORED_SPEC.read_text(encoding="utf-8").splitlines()
    return [ln for ln in difflib.unified_diff(old, spec.text.splitlines(),
                                              "vendored", "published", n=0, lineterm="")
            if ln.startswith(("+", "-")) and not ln.startswith(("+++", "---"))]


# ---------------------------------------------------------------------------
# checking
# ---------------------------------------------------------------------------

def universe_voice(universe: Path) -> dict:
    try:
        return (json.loads((universe / "universe.json").read_text())
                .get("identity", {}).get("voice") or {})
    except (OSError, ValueError):
        return {}


#: A manuscript's closing Scripture. Every book in this framework ends on one, and it is
#: written under this marker rather than as a blockquote, so the blockquote exemption
#: alone flagged "Bring the whole tithe into the storehouse" as totalizing emphasis. It
#: is Malachi. The exemption covers the marker line and the next non-empty line.
CLOSING_VERSE = re.compile(r"^\s*\*?\*?closing verse", re.I)


def is_quotation(line: str) -> bool:
    """A markdown blockquote: how this framework sets Scripture and sourced testimony.

    **Straight quotation MARKS are deliberately NOT an exemption.** They used to be, and
    that one decision is why Gary's complaint was true: in a picture book almost all the
    prose is authored dialogue inside quotes, so blanking quoted spans exempted the
    manuscript from its own voice rules. Two of the three totalizing hits in the two most
    recent books sat inside dialogue and passed a gate that had already run.

    Genuinely verbatim sourced material belongs in a blockquote (where it is exempt) or
    in a waiver (where the reason is written down). Neither is a wildcard.
    """
    return line.lstrip().startswith(">")


def check_file(path: Path, voice: dict) -> list[Finding]:
    findings: list[Finding] = []
    verse_window = 0
    for n, raw in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        where = f"{path.name}:{n}"
        if CLOSING_VERSE.match(raw):
            verse_window = 2          # this line and the next non-empty one
        quoted = is_quotation(raw) or verse_window > 0
        if verse_window and raw.strip():
            verse_window -= 1
        for rule in RULES:
            if quoted and rule.quotation_exempt:
                continue
            for m in rule.pattern.finditer(raw):
                # A match spans the flagged word PLUS the word after it, so that two
                # hits on one line stay distinguishable to a waiver ("the whole Bible"
                # vs "the whole tenth"). Compare the first token, never the whole span.
                if rule.id == "filler" and m.group(0).split()[0].lower() == "just" and \
                        any(j.start() == m.start() for j in JUST_OK.finditer(raw)):
                    continue
                findings.append(Finding(rule.id, rule.severity, where, raw.strip(),
                                        m.group(0), rule.note))

        # Universe-local term rules. `oneWord` is mechanical; `capitalize` is not.
        for term in voice.get("oneWord") or []:
            for m in re.finditer(one_word_split(term), raw, re.I):
                findings.append(Finding("one-word-term", BLOCK, where, raw.strip(),
                                        m.group(0), f"{term!r} must be one word"))
        for term in voice.get("capitalize") or []:
            for m in re.finditer(rf"\b{re.escape(term.lower())}\b", raw):
                before = raw[max(0, m.start() - 24):m.start()].lower()
                poss = bool(re.search(r"\b(my|your|his|her|their|our|its|a|the man's)\s+$",
                                      before))
                findings.append(Finding(
                    "capitalize-term", ADVISORY, where, raw.strip(), m.group(0),
                    "looks possessive, so lowercase is probably RIGHT" if poss else
                    f"if this means the Holy {term} it must be capitalized"))
        for term in voice.get("neverDisparage") or []:
            if re.search(rf"\b{re.escape(term)}\b", raw, re.I) and re.search(
                    r"\b(ridiculous|silly|absurd|pointless|embarrassing|foolish|stupid|"
                    r"badly|awkwardly|poorly)\b", raw, re.I):
                findings.append(Finding(
                    "never-disparage", ADVISORY, where, raw.strip(), term,
                    "an act of faith sits beside a dismissive word. The narrator never "
                    "joins in; a character or the world may"))
    return findings


# ---------------------------------------------------------------------------
# waivers
# ---------------------------------------------------------------------------

def default_waivers(target: Path) -> Path:
    """Beside the manuscript, named for it. Diffable, reviewable, in the same commit."""
    return target.with_suffix("").with_suffix(".voice-waivers.json")


def load_waivers(path: Path) -> list[dict]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data.get("waived", []) if isinstance(data, dict) else list(data)


def apply_waivers(findings: list[Finding], waivers: list[dict]
                  ) -> tuple[list[Finding], list[Finding], list[dict]]:
    """Split into (open, waived), and surface waivers that now match nothing.

    A stale waiver is reported rather than ignored: it means the sentence changed, so the
    decision recorded against it no longer describes anything in the manuscript. A
    reason still reading TODO is not a decision and does not waive anything.
    """
    index = {(w.get("rule", ""), (w.get("match") or "").strip(),
              (w.get("line") or "").strip()): w
             for w in waivers
             if (w.get("reason") or "").strip()
             and not (w.get("reason") or "").strip().startswith("TODO")}
    used: set = set()
    open_f: list[Finding] = []
    waived_f: list[Finding] = []
    for f in findings:
        if f.severity == REVIEW and f.key() in index:
            used.add(f.key())
            waived_f.append(f)
        else:
            open_f.append(f)
    return open_f, waived_f, [w for k, w in index.items() if k not in used]


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="voice_gate.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("universe", nargs="?", help="dir holding universe.json (its term rules)")
    ap.add_argument("files", nargs="*", help="manuscript / narration script / caption text")
    ap.add_argument("--waivers", help="waiver file (default: <manuscript>.voice-waivers.json)")
    ap.add_argument("--emit-waivers", action="store_true",
                    help="print waiver stubs for every open REVIEW, ready to annotate")
    ap.add_argument("--offline", action="store_true", help="skip the spec fetch")
    ap.add_argument("--adopt-spec", action="store_true",
                    help="re-vendor the published spec and print the new hash, AFTER you "
                         "have read the diff and ported any new rule")
    args = ap.parse_args(argv)

    spec = fetch_spec(offline=args.offline)

    if args.adopt_spec:
        if spec.origin != "network":
            print(f"voice-gate: cannot adopt, no published spec fetched ({spec.detail})")
            return 2
        VENDORED_SPEC.parent.mkdir(parents=True, exist_ok=True)
        VENDORED_SPEC.write_text(spec.text, encoding="utf-8")
        print(f"re-vendored {SPEC_URL} -> {VENDORED_SPEC}")
        print(f'now set RULES_DERIVED_FROM = "{spec.sha256}" in {Path(__file__).name}')
        print("  and port any NEW hard rule in that diff into RULES, or you have only "
              "silenced the alarm.")
        return 0

    if not args.universe or not args.files:
        ap.print_help()
        return 2

    voice = universe_voice(Path(args.universe).expanduser())
    targets = [Path(f).expanduser() for f in args.files]
    findings: list[Finding] = []
    for t in targets:
        findings += check_file(t, voice)

    wpath = Path(args.waivers).expanduser() if args.waivers else default_waivers(targets[0])
    open_f, waived_f, stale = apply_waivers(findings, load_waivers(wpath))

    blocking = [f for f in open_f if f.severity == BLOCK]
    review = [f for f in open_f if f.severity == REVIEW]
    advisory = [f for f in open_f if f.severity == ADVISORY]

    if args.emit_waivers:
        print(json.dumps({"waived": [
            {"rule": f.rule, "match": f.match.strip(), "line": f.line,
             "reason": "TODO: why this one stays"} for f in review]}, indent=2))
        return 0

    print(f"voice-gate: rules from {SPEC_URL} [{spec.origin}]"
          + (f" ({spec.detail})" if spec.detail and spec.origin == "vendored" else ""))
    if spec.origin == "network" and not spec.current:
        print("\nSPEC DRIFT: the published voice spec changed since these rules were "
              "derived.\n  A rule added upstream is a rule this gate is silently not "
              "enforcing, so this fails\n  until someone looks. The diff:")
        for ln in spec_diff(spec)[:40]:
            print(f"    {ln[:160]}")
        print(f"\n  fix: port any new hard rule into RULES, then "
              f"`python3 {Path(__file__).name} --adopt-spec`")
        return 1

    for label, items in (("ADVISORY (never blocks, a human must read the sense)", advisory),
                         ("REVIEW (fix it, or waive it with a reason)", review),
                         ("BLOCKING", blocking)):
        if items:
            print(f"\n{label}: {len(items)}")
            for f in items:
                print(f"  - {f.where} [{f.rule}] {f.match!r}: {f.note}\n      {f.line[:120]}")
    if waived_f:
        print(f"\nwaived: {len(waived_f)} (adjudicated in {wpath.name})")
    if stale:
        print(f"\nSTALE WAIVERS: {len(stale)} in {wpath.name} match nothing in the text. "
              f"The line changed, so the decision no longer applies. Delete them.")
        for w in stale:
            print(f"  - [{w.get('rule')}] {str(w.get('match'))[:60]!r}")

    if blocking or review:
        print(f"\nvoice-gate: BLOCKED on {len(blocking)} violation(s) and {len(review)} "
              f"unadjudicated review item(s).\n  Words do not lock and audio does not "
              f"render until each is fixed or waived.\n  Waiver stubs: "
              f"`python3 {Path(__file__).name} {args.universe} {args.files[0]} "
              f"--emit-waivers` -> {wpath.name}")
        return 1
    print(f"\nvoice-gate: PASS ({len(advisory)} advisory item(s) to read, "
          f"{len(waived_f)} waived).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
