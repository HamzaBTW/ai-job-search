"""Guard for how a cover letter handles requirements the candidate lacks.

/apply asks for every stated requirement to be "matched or honestly gapped",
and 03-writing-style.md bans apologetic language, but nothing said how to
write the gap. Live run (private copy, Uber, 2026-10-31): the letter gave a
whole paragraph to "Two gaps, stated plainly. ... I have not yet ... I have
not built ...", and a strength bullet ended with "which I have not yet done on
real demand data". Honest, but it read as a list of reasons to reject. These
tests pin the rule in 06-cover-letter-templates.md (bridge, don't confess) and
the pointers to it from /apply.
"""
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUIDE = REPO / ".claude" / "skills" / "job-application-assistant" / "06-cover-letter-templates.md"
APPLY = REPO / ".claude" / "commands" / "apply.md"
HEADING = "### Gaps: Bridge, Don't Confess"


def section(path, heading):
    text = path.read_text(encoding="utf-8")
    level = len(heading) - len(heading.lstrip("#"))
    rest = text[text.index(heading) + len(heading):]
    end = re.search(r"^#{1,%d} " % level, rest, re.MULTILINE)
    return rest[: end.start()] if end else rest


class GuideSaysHowToWriteAGap(unittest.TestCase):
    def setUp(self):
        self.gaps = section(GUIDE, HEADING)

    def test_one_sentence_inside_a_strength_never_a_paragraph(self):
        self.assertRegex(self.gaps, r"(?i)one sentence")
        self.assertRegex(self.gaps, r"(?i)never a (separate )?paragraph")

    def test_no_i_have_not_openers_and_no_caveated_claims(self):
        self.assertIn('"I have not"', self.gaps)
        self.assertRegex(self.gaps, r"(?i)narrower claim")

    def test_honesty_rule_is_kept(self):
        self.assertRegex(self.gaps, r"(?i)never imply")
        self.assertIn("07-interview-prep.md", self.gaps)

    def test_checklist_has_the_gap_item(self):
        checklist = section(GUIDE, "## Checklist Before Finalizing")
        self.assertRegex(checklist, r"(?i)gap.*bridge")


class ApplyPointsToTheRule(unittest.TestCase):
    def test_requirement_coverage_links_the_guide(self):
        coverage = section(APPLY, "### Requirement coverage (both documents)")
        self.assertIn("06-cover-letter-templates.md", coverage)
        self.assertIn("Bridge, Don't Confess", coverage)

    def test_reviewer_is_told_the_same(self):
        # The reviewer prompt (Step 3) has its own headings; its rules sit under "6. Produce Feedback".
        feedback = section(APPLY, "### 6. Produce Feedback")
        self.assertIn("Bridge, Don't Confess", feedback)
        self.assertRegex(feedback, r"(?i)narrower claim")


if __name__ == "__main__":
    unittest.main()
