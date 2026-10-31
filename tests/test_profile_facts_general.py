"""Guard for how /apply and /interview write a new fact into the profile.

The write-back rule is right: a fact that lives only in chat is stripped from
later drafts as a fabrication. But it said nothing about the wording. Live
run (private copy, Uber, 2026-10-31): the user said they could start on
1 Feb 2027, and the profile gained "can manage the Uber internship as posted,
starting 1 Feb 2027, full time for 3-6 months". The next application is not
at Uber, so the fact the user gave (full-time availability from February,
during the final semester) is buried in a sentence about one posting. These
tests pin the rule: write the fact about the candidate, not the posting, and
quote the line back to the user.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APPLY = REPO / ".claude" / "commands" / "apply.md"
INTERVIEW = REPO / ".claude" / "commands" / "interview.md"


def standing_rule():
    text = APPLY.read_text(encoding="utf-8")
    start = text.index("**Standing rule")
    end = text.index("## Step 0")
    return text[start:end]


class ApplyWritesGeneralFacts(unittest.TestCase):
    def setUp(self):
        self.rule = standing_rule()

    def test_fact_is_about_the_candidate_not_the_posting(self):
        self.assertRegex(self.rule, r"(?i)general form")
        self.assertRegex(self.rule, r"(?i)without the company")

    def test_posting_details_stay_out_of_the_profile(self):
        self.assertRegex(self.rule, r"(?i)facts about the posting.*(tracker|archive)")

    def test_the_written_line_is_quoted_to_the_user(self):
        self.assertRegex(self.rule, r"(?i)quote the line")


class InterviewFollowsTheSameRule(unittest.TestCase):
    def test_interview_points_to_the_apply_rule(self):
        text = INTERVIEW.read_text(encoding="utf-8")
        exception = text[text.index("**The exception is `01-candidate-profile.md`.**"):]
        exception = exception[: exception.index("\n\n")] if "\n\n" in exception else exception
        self.assertRegex(exception, r"(?i)general form")
        self.assertIn("apply.md", exception)


if __name__ == "__main__":
    unittest.main()
