"""Guard for the UAE posting red-flag table in 04-job-evaluation.md.

Added 2026-11: UAE listings carry patterns other markets rarely show (a fee for
the visa, WhatsApp-only applications, a hidden employer, gender or race written
into the ad). `04` now has a "Reading UAE postings (red flags)" table so /rank
and /apply flag them. The table is plain text read by the model, so these tests
pin it: every row exists with the verdict wording it relies on, every row is
covered by a fictional fixture posting (tests/fixtures/uae_red_flag_postings.json),
each fixture really contains the signal it claims, and the clean control posting
matches no row. A later upstream merge that drops or rewrites a row fails here.
"""
import json
import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUIDE = REPO / ".claude" / "skills" / "job-application-assistant" / "04-job-evaluation.md"
FIXTURES = REPO / "tests" / "fixtures" / "uae_red_flag_postings.json"
HEADING = "**Reading UAE postings (red flags).**"


def table_rows():
    """(signal, verdict) for each row of the red-flag table."""
    text = GUIDE.read_text(encoding="utf-8")
    rest = text[text.index(HEADING) + len(HEADING):]
    end = rest.index("\n## ")
    rows = []
    for line in rest[:end].splitlines():
        if not line.startswith("|") or line.startswith("|---") or "Signal in the posting" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split(" | ", 1)]
        rows.append((cells[0], cells[1]))
    return rows


def fixtures():
    return json.loads(FIXTURES.read_text(encoding="utf-8"))


class TableIsPresent(unittest.TestCase):
    def test_has_the_expected_number_of_rows(self):
        self.assertEqual(len(table_rows()), 9)

    def test_scam_row_is_a_stop_not_a_low_score(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("A posting that asks for money is a stop, not a low score", text)
        self.assertIn("overrides every other verdict in this table", text)

    def test_no_verdict_is_a_bare_flag(self):
        """Every row must say what to do next: stop, ask, proceed, or pass."""
        for signal, verdict in table_rows():
            self.assertRegex(verdict, r"do not draft|then ask|then proceed|PASS", signal)

    def test_candidate_cannot_meet_requirement_rule_exists(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("**Requirements the candidate cannot meet.**", text)

    def test_discrimination_rows_cite_both_laws(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("Federal Decree-Law 33/2021, Article 4", text)
        self.assertIn("Federal Decree-Law 34/2023", text)

    def test_sources_list_links_both_laws(self):
        text = GUIDE.read_text(encoding="utf-8")
        self.assertIn("**Sources for the UAE notes**", text)
        self.assertIn("uaelegislation.gov.ae/en/legislations/2131", text)
        self.assertIn("Federal%20Decree-Law%20No.%2033%20of%202021", text)

    def test_discrimination_rows_never_reject_outright(self):
        for signal, verdict in table_rows():
            if signal.startswith(("Gender,", "Nationality", "Age,")):
                self.assertIn("then proceed", verdict, signal)


class FixturesMatchTheTable(unittest.TestCase):
    def test_each_fixture_contains_its_signal(self):
        for fx in fixtures():
            self.assertIn(fx["quote"], fx["text"], fx["id"])

    def test_each_fixture_maps_to_one_row_with_the_expected_verdict(self):
        rows = table_rows()
        for fx in fixtures():
            if fx["row"] is None:
                continue
            hits = [(s, v) for s, v in rows if fx["row"] in s]
            self.assertEqual(len(hits), 1, fx["id"])
            self.assertIn(fx["verdict"], hits[0][1], fx["id"])

    def test_every_row_is_covered_by_a_fixture(self):
        covered = [fx["row"] for fx in fixtures() if fx["row"]]
        for signal, _ in table_rows():
            self.assertTrue(any(c in signal for c in covered), signal)

    def test_control_posting_has_no_flag_wording(self):
        control = [fx for fx in fixtures() if fx["row"] is None]
        self.assertEqual(len(control), 1)
        text = control[0]["text"].lower()
        for word in ("whatsapp", "gmail", "confidential", "only", "photo", "single", "walk-in"):
            self.assertNotIn(word, text)


class CvAndLetterGuidance(unittest.TestCase):
    SKILL = REPO / ".claude" / "skills" / "job-application-assistant"

    def test_cv_guide_says_religion_marital_status_age_are_not_needed(self):
        text = (self.SKILL / "05-cv-templates.md").read_text(encoding="utf-8")
        self.assertIn("**Religion, marital status, age and children:**", text)
        self.assertIn("red-flag table in `04-job-evaluation.md`", text)

    def test_letter_guide_does_not_apologise_for_a_restrictive_posting(self):
        text = (self.SKILL / "06-cover-letter-templates.md").read_text(encoding="utf-8")
        self.assertIn("**Restrictive postings:**", text)
        self.assertIn("do not apologise for it", text)


class FixturesStayFictional(unittest.TestCase):
    def test_no_real_contact_details(self):
        blob = FIXTURES.read_text(encoding="utf-8")
        self.assertNotRegex(blob, r"\+?\d{3}[\s-]?\d{2,3}[\s-]?\d{4,}")
        for email in re.findall(r"[\w.-]+@[\w-]+(?:\.[\w-]+)+", blob):
            self.assertTrue(email.endswith("@example.com"), email)
        self.assertEqual(blob.count("(fictional)"), len(fixtures()))


if __name__ == "__main__":
    unittest.main()
