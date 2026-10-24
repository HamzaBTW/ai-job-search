# Search Queries for Job Scraper

<!-- SETUP: Customize these queries based on your skills and target roles. Location terms are pre-set for the UAE (see "UAE Locations"). -->

## Installed portal CLIs (primary for `/scrape`)

`/scrape` discovers every portal skill under `.agents/skills/*/SKILL.md` and runs its CLI first. Shipped country-agnostic CLIs include `linkedin-search` and `freehire-search`; Danish demos and any skill you add with `/add-portal` are included the same way. You do **not** need a matching `site:` line below for those CLIs to run.

The `site:` query templates in this file are the **WebSearch fallback** — for portals without a CLI, company career pages, or when a CLI fails.

**Language scope:** write every query category in every language listed in your CLAUDE.md Languages table (typically 1-2, sometimes more). A posting requiring a language you have *not* declared, as a job condition, is excluded before scoring; a posting requiring a *higher level* than you declared in a language you *do* work in is flagged for your own judgment, not excluded — see `04-job-evaluation.md`'s Language Gate, the single source of truth for this rule. Translate each category's keywords rather than machine-translating word-for-word (e.g. "Frontend Developer" -> "Desarrollador Frontend", not a literal word-for-word translation) if you work in more than one language.

## Search Sites

Primary (UAE-usable sources - scaffold more with `/add-portal`):
- **linkedin.com/jobs** - LinkedIn job listings, filtered to the United Arab Emirates; also covered by the `linkedin-search` CLI (personal use only, keep volume low)
- **freehire** - tech roles via the `freehire-search` CLI (`--country AE`, or `--region mena`)
- **Indeed** - through the claude.ai Indeed connector only, never scraped (its terms prohibit scraping)
- **[YOUR_JOB_BOARD]** - any UAE board you add with `/add-portal`; the `site:[YOUR_JOB_BOARD]` lines below apply only once you have one, otherwise use the `linkedin.com/jobs` lines
- **[YOUR_INDUSTRY_JOB_BOARD]** - a niche/industry board for your field (optional)

Secondary (company career pages via Google):
- Direct Google searches with `site:` filters for known target companies (employer careers pages)

### Sources deliberately not used

Bayt, GulfTalent, NaukriGulf and Glassdoor are **not** in the lists above, and not as `site:` fallbacks either: each was checked and either blocks automated access (Cloudflare challenge), requires a login, or could not have its robots.txt confirmed. A `site:` query would only route around that decision.

This is a status, not a ban on the portals. If you can build a compliant integration (robots.txt honored, no cookie reuse, no paid unblocking, no Cloudflare bypass), add it with `/add-portal` and send a PR.

## UAE CLI usage

```
# LinkedIn - personal use only, keep volume low
bun run .agents/skills/linkedin-search/cli/src/cli.ts search -q "<title>" -l "Dubai, United Arab Emirates" --jobage 14 --format table

# freehire - tech roles; --country takes ISO codes, --region mena widens to the Middle East and North Africa
bun run .agents/skills/freehire-search/cli/src/cli.ts search -q "<keyword>" --country AE --jobage 14 --format table
bun run .agents/skills/freehire-search/cli/src/cli.ts search -q "<keyword>" --region mena --jobage 14 --format table
```

## Query Categories

Queries are grouped by priority. Write **each category in every language from your Languages table** (see Language scope above). Combine each query with your location terms (e.g. your city, region, or metro area) where the site supports it.

**Organize by function, not job title.** The same underlying work carries different titles across companies and markets (a "Data Scientist" role at one employer may be posted as "Insights Analyst" or "Data Consultant" at another). Name each priority category after the function it covers, and list several plausible job titles as query variants within that category rather than betting an entire priority tier on one exact title string.

### Priority 1: [YOUR_PRIMARY_ROLE_TYPE]

These match your strongest and most desired career direction.

```
site:[YOUR_JOB_BOARD] "[YOUR_PRIMARY_JOB_TITLE_1]" [YOUR_CITY]
site:[YOUR_JOB_BOARD] "[YOUR_PRIMARY_JOB_TITLE_2]" [YOUR_CITY]
site:[YOUR_JOB_BOARD] "[YOUR_KEY_SKILL]" [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_PRIMARY_JOB_TITLE_1]" [YOUR_COUNTRY]
```

### Priority 2: [YOUR_DOMAIN_EXPERTISE]

These match your domain expertise.

```
site:[YOUR_JOB_BOARD] [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY] OR [YOUR_REGION]
site:[YOUR_JOB_BOARD] [YOUR_DOMAIN_KEYWORD_2] [YOUR_COUNTRY]
site:linkedin.com/jobs [YOUR_DOMAIN_KEYWORD_1] [YOUR_CITY] [YOUR_COUNTRY]
```

### Priority 3: [YOUR_ADJACENT_ROLE_TYPE]

Adjacent roles you could pivot into.

```
site:[YOUR_JOB_BOARD] "[YOUR_ADJACENT_TITLE_1]" [YOUR_KEY_SKILL] [YOUR_CITY]
site:[YOUR_JOB_BOARD] "[YOUR_ADJACENT_TITLE_2]" [YOUR_KEY_SKILL] [YOUR_CITY]
```

### Priority 4: Broader Technical / Consulting

Wider net for general technical roles.

```
site:[YOUR_JOB_BOARD] [YOUR_KEY_SKILL] developer [YOUR_CITY]
site:linkedin.com/jobs "[YOUR_KEY_SKILL] developer" [YOUR_CITY]
site:[YOUR_JOB_BOARD] "technical consultant" [YOUR_DOMAIN] [YOUR_CITY]
```

## UAE Locations

Combine the location terms below with each query where the site supports it. Dubai and Abu Dhabi come first because most postings sit there.

| Priority | Term (use in queries) | LinkedIn `-l` value |
|---|---|---|
| 1 | Dubai | `"Dubai, United Arab Emirates"` |
| 1 | Abu Dhabi | `"Abu Dhabi, United Arab Emirates"` |
| 2 | Sharjah | `"Sharjah, United Arab Emirates"` |
| 2 | Ajman | `"Ajman, United Arab Emirates"` |
| 3 | Ras Al Khaimah | `"Ras Al Khaimah, United Arab Emirates"` |
| 3 | Fujairah | `"Fujairah, United Arab Emirates"` |
| 3 | Umm Al Quwain | `"Umm Al Quwain, United Arab Emirates"` |
| any | UAE-wide / remote UAE-based | `"United Arab Emirates"` |

Free-zone names (DIFC, ADGM, DMCC, Dubai Internet City, Masdar City) are optional hints that narrow a query to an employer cluster; do not rely on them as filters.

Replace `[YOUR_CITY]` in the templates above with one of these terms, or run one query per priority-1 emirate. `[YOUR_COUNTRY]` is `United Arab Emirates` (or `UAE`).

When evaluating results, verify the job location is an emirate you can live and work in (commute between emirates is long: Dubai to Abu Dhabi is roughly 90 minutes by road). Define your acceptable emirates in CLAUDE.md.

## Language Filter

Your working languages and levels are in CLAUDE.md's Languages table. When filtering scraped results, apply `04-job-evaluation.md`'s Language Gate: a posting requiring a language you haven't declared at all is excluded; a posting requiring a higher level than you declared in a language you do work in is not excluded, flag it clearly instead (see `job-scraper/SKILL.md`'s Step 3 "Quick Fit Assessment" for how the flag surfaces in `/scrape` output). Postings simply *written* in a language you don't work in, that don't require it on the job, are fine.

## Date Filter

Only include jobs posted within the last 14 days, or with an application deadline that has not yet passed. If a posting date cannot be determined, include it but flag as "date unknown".

## Adapting Queries

If the user specifies a focus area, select queries from the matching category and also generate 2-3 custom queries for that focus. For example:
- "/scrape [focus_area]" -> relevant category queries + custom focus-specific queries
