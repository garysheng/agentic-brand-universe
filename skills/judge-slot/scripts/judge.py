#!/usr/bin/env python3
"""
ONE implementation of the judge-slot role (SPEC 4.10), for judging OUT OF BAND.

Prefer the role over this script. Inside a composer the judge is simply another
turn with a scoped context, which costs nothing extra and needs no key. This file
exists for the case where you are verifying outside any agent runtime.

Evaluates ONE slot against an entity's itemized invariants, in a FRESH context that
is given the golden, the slot, and the checklist, and NEVER the plan that produced
the slot. That separation is the whole point: a maker shown its own reasoning
defends it instead of inspecting the pixels.

Returns PASS or DEFECT per invariant, with evidence, as JSON.

    ANTHROPIC_API_KEY=... python3 judge.py --golden master.png --slot spread-1.png \
        --invariants a.json --entity chief-of-agents
"""
import argparse, base64, json, os, sys

MODEL = "claude-opus-4-8"

def b64(path):
    with open(path, "rb") as f: return base64.standard_b64encode(f.read()).decode()

def media(path):
    return "image/png" if path.lower().endswith(".png") else "image/jpeg"

PROMPT = """You are a verification gate. You are given TWO images and a checklist.

IMAGE 1 is the LOCKED GOLDEN: the identity of record.
IMAGE 2 is a GENERATED SLOT that claims to depict the same subject.

You have deliberately NOT been told how image 2 was produced, what it was intended to
show, or what anyone hoped it would look like. Do not speculate about intent. Judge the
pixels only.

For EACH invariant below, answer strictly against image 1 as the standard:

{checklist}

Return JSON only, no prose outside it:
{{"verdicts":[{{"invariant":"<verbatim>","verdict":"PASS"|"DEFECT","evidence":"<what you SEE in image 2 vs image 1, one sentence>"}}]}}

A verdict of PASS asserts the invariant is satisfied in image 2. If you cannot tell, return
DEFECT with evidence saying what is ambiguous. Do not pass an invariant you cannot verify."""

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--golden", required=True); ap.add_argument("--slot", required=True)
    ap.add_argument("--invariants", required=True, help="JSON file: entity, or a bare list")
    ap.add_argument("--entity", default=None)
    a = ap.parse_args()

    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        sys.exit("ANTHROPIC_API_KEY required. The judge must run as a real independent call; "
                 "there is no offline mode, because a gate you cannot run is not a gate.")
    try:
        import anthropic
    except ImportError:
        sys.exit("pip install anthropic (or: uv run --with anthropic python3 judge.py ...)")

    raw = json.load(open(a.invariants))
    inv = raw if isinstance(raw, list) else raw.get("structured", {}).get("invariants", [])
    if not inv: sys.exit("no invariants found to check")

    checklist = "\n".join(f"{i+1}. {v}" for i, v in enumerate(inv))
    c = anthropic.Anthropic(api_key=key)
    msg = c.messages.create(model=MODEL, max_tokens=2000, messages=[{"role":"user","content":[
        {"type":"image","source":{"type":"base64","media_type":media(a.golden),"data":b64(a.golden)}},
        {"type":"image","source":{"type":"base64","media_type":media(a.slot),"data":b64(a.slot)}},
        {"type":"text","text":PROMPT.format(checklist=checklist)}]}])

    text = "".join(b.text for b in msg.content if b.type == "text").strip()
    text = text[text.find("{"): text.rfind("}") + 1]
    try:
        out = json.loads(text)
    except json.JSONDecodeError:
        sys.exit(f"judge returned unparseable output, failing CLOSED:\n{text[:400]}")

    defects = [v for v in out["verdicts"] if v["verdict"] != "PASS"]
    for v in out["verdicts"]:
        mark = "PASS " if v["verdict"] == "PASS" else "DEFECT"
        print(f"  {mark}  {v['invariant']}\n          {v['evidence']}")
    print(f"\n{len(out['verdicts']) - len(defects)}/{len(out['verdicts'])} passed on {a.slot}")
    return 1 if defects else 0

if __name__ == "__main__":
    sys.exit(main())
