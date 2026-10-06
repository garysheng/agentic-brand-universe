"""The kit (SPEC §13.1, v0.60): pieces and no-gos, validated by `validate` and enforced by
`check-kit`. Earned 2026-10-06 on continental-works, where Gary rejected the six stripes run
down one edge of a selected card and asked that ABU catalog "all these different Lego pieces of
the brand and no-goes".
"""
import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from agenticstory.cli import main
from agenticstory.kit import scan
from agenticstory.store import CanonStore

ASCENT = {
    "id": "the-ascent", "kind": "register-rule", "name": "A", "summary": "s",
    "rules": ["ONE CONTINUOUS RIBBON, NEVER DISCONNECTED PIECES. Gary: 'I don't love the rainbow disconnected'."],
    "tokens": {"teal": {"hex": "#105971"}, "mustard": {"hex": "#E9A23B"}, "tomato": {"hex": "#DB371F"}},
    "icon": {"rules": ["six stripes at 64px and up; three (teal, mustard, tomato) at 36 to 48px"]},
    "surfaces": {"frapp": {"roles": {"chosenOption": "the selection ring (brand-kit selection-ring)"}}},
}

# The two shapes the no-go was written against, as they shipped.
READER_CSS = """.pick button[aria-checked="true"]{background-color:var(--card);border-color:var(--teal);color:var(--ink);background-image:var(--ribbon-across);background-repeat:no-repeat;background-size:12px 100%;padding-left:18px}
"""
FRAPP_STYLE = """const css = `
.opts label:has(input:checked)::before{content:"";position:absolute;inset:0 auto 0 0;width:.55rem;background:var(--ribbon-edge)}
`;
"""
RING_CSS = """.pick button[aria-checked="true"]{background-color:var(--card);border-color:var(--teal);box-shadow:var(--ring)}
.ribbon i:nth-child(1){background:var(--stripe-1)}
"""
DETECT = [
    {"pattern": r"""(?:checked|selected|chosen)[^{}]*\{(?=[^}]*(?:ribbon|stripe))(?=[^}]*background-size:\s*[\d.]+(?:px|rem|em)\s+100%)""",
     "note": "a striped background sized to a narrow strip inside the chosen element"},
    {"pattern": r"""(?:checked|selected|chosen)[^{}]*::?(?:before|after)\s*\{(?=[^}]*(?:ribbon|stripe))(?=[^}]*(?:inset:\s*0\s+auto\s+0\s+0|left:\s*0))""",
     "note": "a striped pseudo-element bar pinned to the chosen element's edge"},
]


def kit(**over):
    k = {
        "id": "brand-kit", "kind": "kit", "name": "Kit", "summary": "pieces and no-gos",
        "tokensFrom": "canon/craft/the-ascent.json#tokens",
        "pieces": [{
            "id": "selection-ring", "name": "The selection ring", "for": "marking the chosen option",
            "recipe": {"tokens": ["teal", "mustard", "tomato"],
                       "css": "border:2px solid teal; box-shadow: inset 0 0 0 2px mustard, inset 0 0 0 4px tomato"},
            "definedAt": "canon/craft/the-ascent.json#icon.rules.0",
            "decided": {"by": "Gary Sheng", "on": "2026-10-06", "verbatim": "make it like a full multi-border"},
        }],
        "noGos": [{
            "id": "edge-stripe-on-selection", "refuses": "stripes down one edge of a selected element",
            "why": "it reads as a tab, not a choice", "instead": "selection-ring",
            "decided": {"by": "Gary Sheng", "on": "2026-10-06", "verbatim": "I really don't like it"},
            "supersedes": [{"at": "canon/craft/the-ascent.json#surfaces.frapp.roles.chosenOption",
                            "said": "the six-stripe ribbon down its leading edge"}],
            "detect": DETECT,
        }, {
            "id": "disconnected-ribbon-pieces", "refuses": "a stripe flourish not connected to the ribbon",
            "why": "there is one ribbon", "instead": None, "insteadNote": "extend the one ribbon",
            "decided": {"by": "Gary Sheng", "on": "2026-09-28"},
            "source": [{"at": "canon/craft/the-ascent.json#rules.0", "quote": "ONE CONTINUOUS RIBBON, NEVER DISCONNECTED PIECES"}],
        }],
    }
    k.update(over)
    return k


class KitTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="abu-kit-"))
        (self.dir / "canon" / "entities").mkdir(parents=True)
        (self.dir / "canon" / "craft").mkdir(parents=True)
        (self.dir / "universe.json").write_text(json.dumps({"id": "t", "name": "T", "assetRoot": ".", "identity": {}}))
        self.write_ascent(ASCENT)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def write_ascent(self, rec):
        (self.dir / "canon" / "craft" / "the-ascent.json").write_text(json.dumps(rec))

    def problems(self, k):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(k))
        return [p for p in CanonStore(self.dir).validate_canon() if "kit" in p]

    def test_a_sound_kit_validates(self):
        self.assertEqual(self.problems(kit()), [])

    def test_no_kit_is_fine(self):
        self.assertEqual([p for p in CanonStore(self.dir).validate_canon() if "kit" in p], [])

    def test_instead_must_name_a_piece(self):
        k = kit(); k["noGos"][0]["instead"] = "selection-halo"
        self.assertTrue(any("not a piece in any kit" in p for p in self.problems(k)))

    def test_null_instead_needs_a_note(self):
        k = kit(); k["noGos"][1].pop("insteadNote")
        self.assertTrue(any("insteadNote" in p for p in self.problems(k)))

    def test_a_ruling_with_no_provenance_is_refused(self):
        k = kit(); k["pieces"][0].pop("decided")
        self.assertTrue(any("'decided' is missing" in p for p in self.problems(k)))
        k = kit(); k["noGos"][0]["decided"] = {"by": "Gary Sheng", "on": "Oct 6"}
        got = "\n".join(self.problems(k))
        self.assertIn("YYYY-MM-DD", got)
        self.assertIn("verbatim is missing", got)

    def test_a_harvested_quote_must_still_be_in_canon(self):
        rec = json.loads(json.dumps(ASCENT)); rec["rules"] = ["One ribbon."]
        self.write_ascent(rec)
        self.assertTrue(any("no longer says" in p for p in self.problems(kit())))

    def test_a_superseded_line_that_still_says_the_old_thing_is_refused(self):
        rec = json.loads(json.dumps(ASCENT))
        rec["surfaces"]["frapp"]["roles"]["chosenOption"] = "teal border plus the six-stripe ribbon down its leading edge"
        self.write_ascent(rec)
        self.assertTrue(any("STILL says" in p for p in self.problems(kit())))

    def test_a_piece_needs_a_recipe_or_a_pointer_that_resolves(self):
        k = kit(); k["pieces"][0].pop("recipe"); k["pieces"][0]["definedAt"] = "canon/craft/the-ascent.json#icon.rules.9"
        got = "\n".join(self.problems(k))
        self.assertIn("does not resolve", got)
        k = kit(); k["pieces"][0].pop("recipe"); k["pieces"][0].pop("definedAt")
        self.assertTrue(any("'recipe' or a 'definedAt'" in p for p in self.problems(k)))

    def test_recipe_tokens_are_checked(self):
        k = kit(); k["pieces"][0]["recipe"]["tokens"].append("gold")
        self.assertTrue(any("recipe token 'gold'" in p for p in self.problems(k)))

    def test_duplicate_ids_and_bad_patterns_are_refused(self):
        k = kit(); k["noGos"][1]["id"] = "selection-ring"; k["noGos"][0]["detect"] = [{"pattern": "(unclosed"}]
        got = "\n".join(self.problems(k))
        self.assertIn("already used", got)
        self.assertIn("does not compile", got)

    def test_a_sibling_repo_source_is_recorded_not_checked(self):
        k = kit(); k["noGos"][1]["source"].append({"at": "other-repo:STATE.md@abc123", "quote": "no italics"})
        self.assertEqual(self.problems(k), [])

    def _surface(self):
        site = self.dir / "site"
        (site / "node_modules" / "x").mkdir(parents=True)
        (site / "reader.css").write_text(READER_CSS)
        (site / "frapp-style.mjs").write_text(FRAPP_STYLE)
        (site / "ring.css").write_text(RING_CSS)
        (site / "node_modules" / "x" / "skip.css").write_text(READER_CSS)
        return site

    def test_scan_finds_both_shipped_shapes_and_passes_the_ring(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        hits = scan(CanonStore(self.dir).craft, [str(self._surface())])
        files = sorted(Path(h["file"]).name for h in hits)
        self.assertEqual(files, ["frapp-style.mjs", "reader.css"])
        self.assertTrue(all(h["nogo"] == "edge-stripe-on-selection" and h["instead"] == "selection-ring" for h in hits))
        self.assertEqual([h["line"] for h in hits if h["file"].endswith(".mjs")], [2])

    def test_check_kit_exit_codes(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        site = self._surface()
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["check-kit", str(self.dir), str(site)]), 1)
        self.assertIn("NO-GO edge-stripe-on-selection", out.getvalue())
        self.assertIn("The selection ring", out.getvalue())
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-kit", str(self.dir), str(site / "ring.css")]), 0)
        k = kit(); k["noGos"][0].pop("detect")
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(k))
        with redirect_stdout(io.StringIO()):
            self.assertEqual(main(["check-kit", str(self.dir), str(site)]), 2)

    def test_kit_verb_lists(self):
        (self.dir / "canon" / "craft" / "brand-kit.json").write_text(json.dumps(kit()))
        with redirect_stdout(io.StringIO()) as out:
            self.assertEqual(main(["kit", str(self.dir)]), 0)
        self.assertIn("piece  selection-ring", out.getvalue())
        self.assertIn("no-go  edge-stripe-on-selection", out.getvalue())


if __name__ == "__main__":
    unittest.main()
