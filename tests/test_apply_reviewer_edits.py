"""Guard for /apply Step 4: every reviewer edit is applied, skipped or reported.

Live run (private copy, Uber, 2026-10-31): one of the reviewer's Part A edits
to the CV came back "Error editing file", the drafter moved on, and the final
report never mentioned it. The user would have submitted a CV missing a fix
the reviewer asked for, with a checklist that said everything passed. Step 4
said only "re-read a file if an edit fails"; nothing said to retry, or to
tell the user what was left undone. These tests pin both halves: Step 4 keeps
a per-edit outcome and retries a failed edit against the current text, and
Step 6 reports the tally, naming every edit that did not land.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APPLY = REPO / ".claude" / "commands" / "apply.md"


def section(heading):
    """The body of one markdown section, up to the next heading of the same or higher level."""
    text = APPLY.read_text(encoding="utf-8")
    level = len(heading) - len(heading.lstrip("#"))
    start = text.index(heading) + len(heading)
    rest = text[start:]
    end = re.search(r"^#{1,%d} " % level, rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


class Step4TracksEveryEdit(unittest.TestCase):
    def setUp(self):
        self.step4 = section("## Step 4: DRAFTER - Revise Based on Feedback")

    def test_each_part_a_edit_gets_an_outcome(self):
        for outcome in ("applied", "skipped", "failed"):
            self.assertIn(f"`{outcome}`", self.step4, outcome)

    def test_a_failed_edit_is_retried_against_the_current_text(self):
        self.assertRegex(self.step4, r"(?i)edit fails.*re-read")
        self.assertRegex(self.step4, r"(?i)already (says|carries|has)")

    def test_a_failed_edit_is_never_dropped_silently(self):
        self.assertRegex(self.step4, r"(?i)never drop .*silently")


class Step6ReportsTheTally(unittest.TestCase):
    def setUp(self):
        self.step6 = section("## Step 6: Present Final Output")

    def test_report_has_a_reviewer_edits_section(self):
        self.assertIn("### Reviewer Edits", self.step6)

    def test_report_names_every_edit_that_did_not_land(self):
        block = section("### Reviewer Edits")
        self.assertRegex(block, r"(?i)applied.*skipped.*failed")
        self.assertRegex(block, r"(?i)quote")
        self.assertRegex(block, r"(?i)never .*pass")


if __name__ == "__main__":
    unittest.main()
