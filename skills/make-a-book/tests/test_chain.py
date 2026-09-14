#!/usr/bin/env python3
"""The chain in `make-a-book` is a CONTRACT, so it is tested like one.

WHY THIS FILE EXISTS. `make-a-book` is a prose orchestrator: there is no compiler to
refuse a dropped step, so a step that is not NUMBERED is a step that runs when someone
remembers it, which `pave-the-path` says about itself and which cost `book-doctor` two
whole periods of failing every book unnoticed. Numbering is the enforcement mechanism
this skill actually has, and prose numbering rots silently: the frontmatter summary and
the body headings are two copies of one list, so one of them is stale within a month and
both still read correctly on their own.

So this asserts the three things a reader of that file relies on:

  SUMMARY AGREES WITH BODY   the arrow chain in the frontmatter description, the arrow
                             chain in the "order is load-bearing" line, and the numbered
                             headings are all the same list in the same order.
  NUMBERS ARE CONTIGUOUS     1..N, each once. A gap is a step someone deleted; a repeat
                             is a step someone inserted without renumbering.
  THE GRADER IS IN THE CHAIN the deliverable's own doctor is a numbered step, after the
                             art exists and before the book is delivered, landed or paved.

It reads the shipped SKILL.md rather than a fixture on purpose: a fixture would pass
forever while the real file drifted, which is the failure being prevented.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1] / "SKILL.md"

# A numbered step heading: "### 4. Words + render -> ...", and the three-in-one
# "### 7. Narrate -> 8. Deliver -> 9. Publish". The lookbehind keeps version numbers
# ("SPEC v0.9") and sub-steps ("### 4b.") from reading as steps.
STEP_RE = re.compile(r"(?<![\w.])(\d+)\.\s+([^\n]+?)(?=\s*->|\s*$)")
CHAIN_RE = re.compile(r"\(([a-z]+(?:\s*->\s*[a-z]+)+)\)")
ORDER_RE = re.compile(r"order is load-bearing:\s*([a-z]+(?:\s*->\s*[a-z]+)+)")


def _split_chain(s: str) -> list[str]:
    return [t.strip() for t in s.split("->")]


class ChainContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = SKILL.read_text(encoding="utf-8")
        _, _, body = cls.text.partition("---\n")
        cls.frontmatter, _, cls.body = body.partition("\n---\n")
        cls.steps = []
        for line in cls.body.splitlines():
            if not line.startswith("#"):
                continue
            for m in STEP_RE.finditer(line):
                cls.steps.append((int(m.group(1)), m.group(2).strip()))

    def test_frontmatter_declares_the_chain(self):
        m = CHAIN_RE.search(self.frontmatter)
        self.assertIsNotNone(m, "the frontmatter description no longer names the chain "
                                "in parentheses; the summary a reader sees first is gone")

    def test_summary_and_body_declare_the_same_chain(self):
        front = _split_chain(CHAIN_RE.search(self.frontmatter).group(1))
        body = _split_chain(ORDER_RE.search(self.body).group(1))
        self.assertEqual(front, body,
                         "the frontmatter chain and the 'order is load-bearing' line "
                         "disagree. Two copies of one list; fix both in the same edit.")

    def test_step_numbers_are_contiguous_and_unique(self):
        nums = [n for n, _ in self.steps]
        self.assertEqual(nums, sorted(nums), f"step headings are out of order: {nums}")
        self.assertEqual(nums, list(range(1, len(nums) + 1)),
                         f"step numbers are not 1..N with no gaps: {nums}. A gap is a "
                         f"deleted step; a repeat is an inserted step nobody renumbered.")

    def test_every_chain_token_has_a_numbered_heading_in_order(self):
        chain = _split_chain(ORDER_RE.search(self.body).group(1))
        self.assertEqual(len(chain), len(self.steps),
                         f"{len(chain)} chain tokens but {len(self.steps)} numbered "
                         f"headings: {[t for _, t in self.steps]}")
        for token, (num, heading) in zip(chain, self.steps):
            self.assertIn(token, heading.lower(),
                          f"chain step {num} is '{heading}', which does not name the "
                          f"chain token {token!r}. The summary and the body have drifted.")

    def test_book_doctor_is_a_numbered_step(self):
        """The grader of the DELIVERABLE, wired in rather than remembered."""
        chain = _split_chain(ORDER_RE.search(self.body).group(1))
        self.assertIn("doctor", chain,
                      "book-doctor is not in the chain. It grades the finished book, and "
                      "a check nobody invokes rots unnoticed: book-doctor's own file "
                      "records two periods in which it failed every book.")
        self.assertIn("abu:book-doctor", self.body,
                      "the chain names a doctor step but never delegates to the skill")

    def test_the_doctor_runs_after_the_art_and_before_delivery(self):
        chain = _split_chain(ORDER_RE.search(self.body).group(1))
        i = chain.index("doctor")
        self.assertGreater(i, chain.index("cover"),
                           "the doctor grades a finished book, so it cannot run before "
                           "the cover exists")
        for later in ("deliver", "publish", "land", "pave"):
            self.assertLess(i, chain.index(later),
                            f"the doctor must run before {later}: it grades the book on "
                            f"local disk BEFORE it is delivered anywhere")

    def test_the_doctor_step_auto_advances_like_its_neighbours(self):
        """Its neighbours run on every book without being asked; so must it."""
        step = self.body.split("### 6.")[1].split("\n### ")[0]
        self.assertIn("ALWAYS", step,
                      "the doctor step does not say it runs on every book. pave-the-path "
                      "and universe-doctor both do, and a step that reads as optional is "
                      "the state book-doctor was already in.")


if __name__ == "__main__":
    unittest.main(verbosity=1)
