#!/usr/bin/env python3
"""Split a /scrape run evenly across its sources and flag postings with gaps.

/scrape pools hits from LinkedIn, freehire, Indeed and employer careers pages.
Left alone the biggest portal fills the report, so this tool gives each source
a share ("slots"), reports how many postings each source found, and lists the
postings that lack a detail the reader needs to decide. A posting tagged with
any other source (for example a portal added with /add-portal) is not capped,
but is listed with its tag and the route it came through.

    python tools/source_mix.py assess --results pool.json [--slots a=5,b=5]
                                      [--closed key1,key2] [--redistribute]

`pool.json` is the deduplicated candidate list (the `selected` output of
`scrape_state.py candidates`, enriched by the detail fetch). Per job the tool
reads `portal`, `title`, `company`, `location`, `url`, `posted_date` and either
`description` (text) or `description_words` (an integer, for entries whose text
is not kept in the history).

The default shares come from the "Source slots" table in
`.claude/skills/job-scraper/search-queries.md`; `--slots` overrides them for
one run. Nothing is redistributed unless `--redistribute` is given: a source
that falls short is reported, and the choice (give its spare slots to the other
sources, or keep filling it) belongs to the user.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from job_key import make_key

SOURCES = ("linkedin", "freehire", "indeed", "careers")
DETAILS = ("company", "location", "description", "apply_link")
MIN_DESCRIPTION_WORDS = 30
QUERIES = Path(__file__).resolve().parent.parent / ".claude" / "skills" / "job-scraper" / "search-queries.md"
HEADING = "## Source slots"


def source_of(job: dict) -> str | None:
    """Map a job's `portal` tag to one of the four sources; None when unlisted."""
    portal = str(job.get("portal") or "").lower()
    for name in SOURCES:
        if name in portal:
            return name
    return None


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def description_words(job: dict) -> int:
    words = job.get("description_words")
    if isinstance(words, int) and not isinstance(words, bool):
        return max(words, 0)
    return len(_text(job.get("description")).split())


def missing_details(job: dict, judge_description: bool = True) -> list[str]:
    """The details the reader needs that this posting lacks, in DETAILS order.

    `judge_description=False` skips the description check, for an entry that
    carries no description information at all (so its absence means "not
    provided", not "the posting has none").
    """
    gaps = []
    if _text(job.get("company")).lower() in ("", "null", "none", "unknown", "n/a"):
        gaps.append("company")
    if _text(job.get("location")).lower() in ("", "null", "none", "unknown", "n/a"):
        gaps.append("location")
    if judge_description and description_words(job) < MIN_DESCRIPTION_WORDS:
        gaps.append("description")
    url = _text(job.get("url"))
    if not re.match(r"https?://\S+$", url):
        gaps.append("apply_link")
    return gaps


def completeness(job: dict) -> int:
    """How many of the four details are present, 0 to 4."""
    return len(DETAILS) - len(missing_details(job))


def parse_pairs(text: str) -> dict[str, int]:
    """'linkedin=5,indeed=3' -> {'linkedin': 5, 'indeed': 3}."""
    slots = {}
    for part in text.split(","):
        if not part.strip():
            continue
        name, sep, number = part.partition("=")
        name = name.strip().lower()
        if not sep or name not in SOURCES:
            raise ValueError(f"unknown source or bad pair: {part.strip()!r} (sources: {', '.join(SOURCES)})")
        if not number.strip().isdigit():
            raise ValueError(f"slots for {name} must be a whole number, got {number.strip()!r}")
        slots[name] = int(number)
    return slots


def table_slots(path: Path = QUERIES) -> dict[str, int]:
    """Read the default shares from the 'Source slots' table."""
    text = path.read_text(encoding="utf-8")
    if HEADING not in text:
        raise ValueError(f"{path.name} has no '{HEADING}' table")
    rest = text[text.index(HEADING) + len(HEADING):]
    nxt = re.search(r"^## ", rest, re.MULTILINE)
    slots = {}
    for line in (rest[: nxt.start()] if nxt else rest).splitlines():
        cells = [c.strip().strip("`").lower() for c in line.strip().strip("|").split("|")]
        if len(cells) >= 2 and cells[0] in SOURCES and cells[1].isdigit():
            slots[cells[0]] = int(cells[1])
    missing = [s for s in SOURCES if s not in slots]
    if missing:
        raise ValueError(f"'{HEADING}' table lacks: {', '.join(missing)}")
    return slots


def assess(jobs: list, slots: dict[str, int], closed: set[str] = frozenset(), redistribute: bool = False) -> dict:
    keyed = []
    invalid = []
    for index, job in enumerate(jobs):
        try:
            key = make_key(job["company"], job["title"], job["url"])
        except (KeyError, TypeError, ValueError) as exc:
            invalid.append({"index": index, "error": str(exc) or "missing company, title or url"})
            continue
        if key in closed:
            continue
        keyed.append((index, key, job))

    by_source: dict[str, list] = {name: [] for name in SOURCES}
    unlisted = []
    for item in keyed:
        name = source_of(item[2])
        (by_source[name] if name else unlisted).append(item)

    # Newest first among equals, then most complete first, then run order.
    def rank(item):
        index, _, job = item
        date = _text(job.get("posted_date"))
        return (-completeness(job), _neg_date(date), index)

    for name in SOURCES:
        by_source[name].sort(key=rank)

    quota = dict(slots)
    spare = {n: max(quota[n] - len(by_source[n]), 0) for n in SOURCES}
    if redistribute:
        pool = sum(spare.values())
        hungry = [n for n in SOURCES if len(by_source[n]) > quota[n]]
        while pool > 0 and hungry:
            for name in list(hungry):
                if pool == 0:
                    break
                quota[name] += 1
                pool -= 1
                if len(by_source[name]) <= quota[name]:
                    hungry.remove(name)

    summary = {}
    shown = []
    held_back = []
    for name in SOURCES:
        items = by_source[name]
        keep, extra = items[: quota[name]], items[quota[name]:]
        shown.extend(keep)
        held_back.extend(extra)
        summary[name] = {
            "slots": slots[name],
            "slots_after_redistribution": quota[name],
            "found": len(items),
            "shown": len(keep),
            "held_back": len(extra),
            "short_by": max(slots[name] - len(items), 0),
        }
    shown.extend(unlisted)

    # A posting whose source tag is not one of the four known sources still
    # reaches the report (it is never capped), but the reader is told which
    # tag it carries and how it was fetched, so a mismatch is visible.
    other_tags = [
        {
            "key": key,
            "title": job.get("title"),
            "company": job.get("company"),
            "tag": _text(job.get("portal")) or "(none)",
            "fetched_via": _text(job.get("source")) or "unknown",
        }
        for _, key, job in unlisted
    ]
    notice = None
    if other_tags:
        tags = sorted({row["tag"] for row in other_tags})
        notice = (
            f"{len(other_tags)} posting(s) came in through a known search route but carry a different "
            f"source tag ({', '.join(tags)}) than the four tracked sources "
            f"({', '.join(SOURCES)}). They are shown without a share."
        )

    incomplete = [
        {
            "key": key,
            "title": job.get("title"),
            "company": job.get("company"),
            "source": source_of(job) or "other",
            "missing": missing_details(job),
            "completeness": completeness(job),
        }
        for _, key, job in shown if missing_details(job)
    ]
    incomplete.sort(key=lambda row: (row["completeness"], row["source"], str(row["title"])))
    return {
        "sources": summary,
        "shown_keys": [key for _, key, _ in shown],
        "held_back_keys": [key for _, key, _ in held_back],
        "incomplete": incomplete,
        "other_source_tags": other_tags,
        "other_source_notice": notice,
        "invalid": invalid,
        "redistributed": bool(redistribute),
    }


def _neg_date(date: str) -> str:
    """Sort key that puts later ISO dates first and empty dates last."""
    if not date:
        return "~"
    return "".join(chr(0x7E - (ord(c) - 0x20)) if 0x20 <= ord(c) <= 0x7E else c for c in date)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("assess",))
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--slots", default="", help="override, e.g. linkedin=5,freehire=5,indeed=5,careers=5")
    parser.add_argument("--closed", default="", help="comma-separated keys the user closed; left out of the counts")
    parser.add_argument("--redistribute", action="store_true",
                        help="give spare slots of short sources to sources with more postings than slots")
    args = parser.parse_args()
    try:
        slots = table_slots()
        slots.update(parse_pairs(args.slots))
        data = json.loads(args.results.read_text(encoding="utf-8"))
        jobs = data.get("selected") if isinstance(data, dict) else data
        if not isinstance(jobs, list):
            raise ValueError("results must be a JSON array of jobs (or an object with a 'selected' array)")
        closed = {k.strip() for k in args.closed.split(",") if k.strip()}
        print(json.dumps(assess(jobs, slots, closed, args.redistribute), ensure_ascii=False))
        return 0
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"source_mix: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
