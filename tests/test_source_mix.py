"""Equal source shares, missing-detail ranking and closing for /scrape.

/scrape used to pool every portal's hits, so the biggest one filled the report
(live: 20 of 27 postings were LinkedIn). tools/source_mix.py now gives each of
four sources (linkedin, freehire, indeed, careers) a share, flags postings that
lack a detail the reader needs, and reports postings tagged with any other
source. scrape_state.py records `missing_details` on store and closes postings
the user removed with `drop`. These tests pin that behaviour and the wiring in
the skill and search-queries.md.
"""
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "tools"))
import scrape_state  # noqa: E402
import source_mix  # noqa: E402

SKILL = REPO / ".claude" / "skills" / "job-scraper" / "SKILL.md"
QUERIES = REPO / ".claude" / "skills" / "job-scraper" / "search-queries.md"
EQUAL = {"linkedin": 2, "freehire": 2, "indeed": 2, "careers": 2}


def job(portal, title, **over):
    base = {
        "portal": portal, "source": "cli", "title": title, "company": f"Co {title}",
        "location": "Dubai", "url": f"https://example.com/{portal}/{title}",
        "posted_date": "2026-11-04", "description_words": 120,
    }
    base.update(over)
    return base


class SlotParsing(unittest.TestCase):
    def test_default_table_is_equal_for_the_four_sources(self):
        self.assertEqual(source_mix.table_slots(QUERIES), {s: 5 for s in source_mix.SOURCES})

    def test_override_pairs(self):
        self.assertEqual(source_mix.parse_pairs("indeed=8, careers=2"), {"indeed": 8, "careers": 2})

    def test_bad_pairs_are_rejected(self):
        for bad in ("bing=3", "indeed", "indeed=x", "indeed=-1"):
            with self.assertRaises(ValueError, msg=bad):
                source_mix.parse_pairs(bad)

    def test_table_missing_a_source_is_an_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "q.md"
            path.write_text("## Source slots\n\n| Source | Slots |\n|---|---|\n| linkedin | 5 |\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                source_mix.table_slots(path)


class MissingDetails(unittest.TestCase):
    def test_complete_posting_has_none(self):
        self.assertEqual(source_mix.missing_details(job("linkedin-search", "a")), [])
        self.assertEqual(source_mix.completeness(job("linkedin-search", "a")), 4)

    def test_each_gap_is_named(self):
        self.assertEqual(source_mix.missing_details(job("x", "a", company="")), ["company"])
        self.assertEqual(source_mix.missing_details(job("x", "a", location=None)), ["location"])
        self.assertEqual(source_mix.missing_details(job("x", "a", description_words=29)), ["description"])
        self.assertEqual(source_mix.missing_details(job("x", "a", url="not a link")), ["apply_link"])

    def test_description_text_counts_when_no_word_count(self):
        j = job("indeed", "a", description="word " * 40)
        j.pop("description_words")
        self.assertEqual(source_mix.missing_details(j), [])

    def test_description_is_not_judged_when_not_provided(self):
        j = job("x", "a")
        j.pop("description_words")
        self.assertEqual(source_mix.missing_details(j), ["description"])
        self.assertEqual(source_mix.missing_details(j, judge_description=False), [])

    def test_placeholder_values_count_as_missing(self):
        self.assertEqual(source_mix.missing_details(job("x", "a", company="null")), ["company"])


class Assess(unittest.TestCase):
    def test_even_split_holds_back_the_overflow(self):
        pool = [job("linkedin-search", f"l{i}") for i in range(5)] + [job("freehire-search", "f0")]
        out = source_mix.assess(pool, EQUAL)
        self.assertEqual(out["sources"]["linkedin"]["shown"], 2)
        self.assertEqual(out["sources"]["linkedin"]["held_back"], 3)
        self.assertEqual(out["sources"]["freehire"]["short_by"], 1)
        self.assertEqual(out["sources"]["indeed"]["short_by"], 2)
        self.assertEqual(len(out["shown_keys"]), 3)

    def test_nothing_is_redistributed_unless_asked(self):
        pool = [job("linkedin-search", f"l{i}") for i in range(6)]
        out = source_mix.assess(pool, EQUAL)
        self.assertEqual(out["sources"]["linkedin"]["shown"], 2)
        self.assertFalse(out["redistributed"])

    def test_redistribution_gives_spare_slots_to_the_busy_source(self):
        pool = [job("linkedin-search", f"l{i}") for i in range(6)]
        out = source_mix.assess(pool, EQUAL, redistribute=True)
        self.assertEqual(out["sources"]["linkedin"]["shown"], 6)  # 2 own + 6 spare slots, 6 found
        self.assertEqual(out["sources"]["linkedin"]["slots"], 2)
        self.assertTrue(out["redistributed"])

    def test_complete_postings_fill_the_slots_first(self):
        pool = [job("linkedin-search", "bad", company=""), job("linkedin-search", "ok1"), job("linkedin-search", "ok2")]
        out = source_mix.assess(pool, EQUAL)
        self.assertEqual(out["incomplete"], [])
        self.assertEqual(len(out["held_back_keys"]), 1)

    def test_incomplete_list_is_least_complete_first(self):
        pool = [
            job("freehire-search", "two", company="", location=""),
            job("linkedin-search", "one", location=""),
            job("indeed", "three", company="", location="", description_words=0),
        ]
        out = source_mix.assess(pool, {s: 5 for s in source_mix.SOURCES})
        self.assertEqual([r["title"] for r in out["incomplete"]], ["three", "two", "one"])
        self.assertEqual([r["completeness"] for r in out["incomplete"]], [1, 2, 3])
        self.assertEqual(out["incomplete"][0]["missing"], ["company", "location", "description"])

    def test_closed_keys_leave_the_counts(self):
        pool = [job("linkedin-search", "a"), job("linkedin-search", "b", company="")]
        first = source_mix.assess(pool, {s: 5 for s in source_mix.SOURCES})
        key = first["incomplete"][0]["key"]
        again = source_mix.assess(pool, {s: 5 for s in source_mix.SOURCES}, closed={key})
        self.assertEqual(again["sources"]["linkedin"]["found"], 1)
        self.assertEqual(again["incomplete"], [])

    def test_unknown_source_tag_is_reported_not_capped(self):
        pool = [job("whatjobs.com", f"w{i}", source="cli") for i in range(3)]
        out = source_mix.assess(pool, EQUAL)
        self.assertEqual(len(out["shown_keys"]), 3)
        self.assertEqual({r["tag"] for r in out["other_source_tags"]}, {"whatjobs.com"})
        self.assertEqual({r["fetched_via"] for r in out["other_source_tags"]}, {"cli"})
        self.assertIn("different source tag", out["other_source_notice"])
        self.assertIn("whatjobs.com", out["other_source_notice"])

    def test_no_notice_when_every_tag_is_known(self):
        out = source_mix.assess([job("linkedin-search", "a")], EQUAL)
        self.assertIsNone(out["other_source_notice"])
        self.assertEqual(out["other_source_tags"], [])

    def test_invalid_jobs_are_listed_and_skipped(self):
        out = source_mix.assess([{"portal": "indeed", "title": "t"}], EQUAL)
        self.assertEqual(len(out["invalid"]), 1)
        self.assertEqual(out["shown_keys"], [])

    def test_newer_posting_wins_among_equals(self):
        pool = [job("linkedin-search", "old", posted_date="2026-10-30"),
                job("linkedin-search", "new", posted_date="2026-11-05"),
                job("linkedin-search", "mid", posted_date="2026-11-02")]
        out = source_mix.assess(pool, {**EQUAL, "linkedin": 2})
        shown = [k for k in out["shown_keys"]]
        self.assertEqual(len(shown), 2)
        self.assertTrue(any("new" in k for k in shown))
        self.assertTrue(any("mid" in k for k in shown))


class StoreAndDrop(unittest.TestCase):
    def _entry(self, **over):
        base = {
            "title": "Backend Engineer", "company": "Acme", "location": "Dubai",
            "url": "https://example.com/j/1", "first_seen": "2026-11-05", "posted_date": "2026-11-04",
            "deadline": None, "fit": "medium", "status": "new", "portal": "linkedin-search",
            "source": "cli",
        }
        base.update(over)
        return base

    def test_drop_marks_new_entries_skipped_with_a_reason(self):
        seen = {"k1": self._entry(missing_details=["description"]), "k2": self._entry(status="ranked")}
        out = scrape_state.drop_entries(seen, ["k1", "k2", "nope"])
        self.assertEqual(out["dropped"], ["k1"])
        self.assertEqual(out["unknown"], ["nope"])
        self.assertEqual(out["not_dropped"], [{"key": "k2", "status": "ranked"}])
        self.assertEqual(seen["k1"]["status"], "skipped")
        self.assertTrue(seen["k1"]["dropped"])
        self.assertEqual(seen["k1"]["dropped_reason"], "missing details: description")
        self.assertEqual(seen["k2"]["status"], "ranked")

    def test_drop_is_idempotent(self):
        seen = {"k1": self._entry(status="skipped")}
        self.assertEqual(scrape_state.drop_entries(seen, ["k1"])["dropped"], ["k1"])

    def test_store_records_missing_details_and_drops_the_word_count(self):
        job_in = self._entry(description_words=5)
        self.assertEqual(source_mix.missing_details(job_in), ["description"])
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "seen.json"
            results = Path(tmp) / "r.json"
            results.write_text(json.dumps([job_in]), encoding="utf-8")

            class Args:
                command = "store"
                results = None
                tracker = Path(tmp) / "none.csv"
            args = Args()
            args.results, args.state = results, state
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scrape_state.run(args), 0)
            seen = json.loads(state.read_text(encoding="utf-8"))["seen"]
            entry = next(iter(seen.values()))
            self.assertEqual(entry["missing_details"], ["description"])
            self.assertNotIn("description_words", entry)

            class DropArgs:
                command = "drop"
                keys = next(iter(seen))
            drop = DropArgs()
            drop.state = state
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(scrape_state.run(drop), 0)
            entry = next(iter(json.loads(state.read_text(encoding="utf-8"))["seen"].values()))
            self.assertEqual(entry["status"], "skipped")


class Wiring(unittest.TestCase):
    def test_skill_describes_the_mix_the_drop_and_careers(self):
        text = SKILL.read_text(encoding="utf-8")
        for needle in (
            "tools/source_mix.py assess", "Store only `shown_keys`", "other source tag:",
            "scrape_state.py drop --keys", "#### 1e. Employer careers pages",
            "tools/robots_check.py", "skipped (robots)", "keep filling that source",
            "--slots linkedin=5,freehire=5,indeed=5,careers=5",
        ):
            self.assertIn(needle, text, needle)

    def test_queries_file_has_the_table_and_the_employer_placeholder(self):
        text = QUERIES.read_text(encoding="utf-8")
        self.assertIn("## Source slots", text)
        self.assertIn("## Careers-page employers", text)
        self.assertIn("[YOUR_TARGET_EMPLOYER_1]", text)


if __name__ == "__main__":
    unittest.main()
