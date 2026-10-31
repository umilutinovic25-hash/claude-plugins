---
name: searching-serbia-tech-jobs
description: Use when searching for or applying to junior/medior AI or software engineering jobs in Belgrade/Serbia, or when asked to check for new postings, verify a job listing, or fill out a job application form for this search.
---

# Searching Serbia Tech Jobs

## Overview

Built for a junior/medior AI or software engineer targeting Belgrade or remote-open-to-Serbia roles, up to ~3 years seniority. Infostud/HelloWorld alone dry up fast — most real openings surface on company career pages or LinkedIn first. Every candidate must be verified before it's shown to the user; a promising title hides a lot in the full page.

**Candidate profile.** Read `~/.config/serbia-job-search/profile.md` before searching. If it doesn't exist, ask the user for target roles, core stack, max years of experience, city/remote preference and the CV file path, then save it there. The seniority and location checks below use these values (defaults: ≤3 years, Belgrade).

## Workflow

**1. Source broadly.** Never rely on Infostud/HelloWorld alone:
- Use the bundled `poslovi` MCP server (`search_jobs`, then `get_job` for the full text) for Infostud and HelloWorld.rs.
- Hit company career pages directly. Tracked employers: HTEC, Comtrade, Levi9, Nordeus, Vega IT, Seven Bridges, Infobip, Ubisoft Belgrade, King, Microsoft, Sysdig, ThoughtWorks, Symphony, Smartcat, Mainstream, EPAM, Endava. (EPAM/Endava historically skew senior in Serbia — check anyway, don't skip on memory alone.)
- Run LinkedIn searches with varied keywords, not just one phrase: "junior/medior AI Engineer", "Software Engineer", "Data Scientist", "Python Developer", "praksa", "internship" — combined with location=Serbia and the remote filter.
- Re-sweep every session; postings rotate inside 24-48h windows.

**2. Verify every candidate — reject silently, don't just flag for later:**

| Check | Reject if... |
|---|---|
| Seniority | Tagged Senior/Lead/Management, or body text requires more than ~3 years, or any "X+ years" with X>3 |
| Location | Full job page shows a city outside Belgrade with no remote-for-Serbia option |
| Legitimacy | No named employer; generic template ("hiring for one of our clients... we hire based on skills and expertise") — usually an AI-data-labeling gig mill (micro1/Hire Feed/Hired/Quik Hire Staffing pattern), not a real engineering role |
| Duplicate | Same company+title already in memory files or in Infostud "Moje prijave" history (paginate recent pages, don't trust the first page alone) |

Always open the **full job page**, not the search-result snippet — a snippet can undersell seniority ("AI Compiler" hid "6+ years / 3+ years LLVM / 2+ years leading a team" in the body) or misstate the city (a "Junior SEO Specialist" search hit was actually Niš, not Beograd).

**3. Present the verified list and wait for explicit approval before applying to anything.**

**4. Apply (only after approval):**
- Adapt to whatever ATS the employer uses — Greenhouse, Lever, a custom on-page form, iCIMS, SAP SuccessFactors. Read the form once with `get_page_text` before filling.
- Upload the CV with the `file_upload` tool on the actual file-input ref. Never click a file-picker button expecting a native dialog — you can't see or drive it.
- Write a short, specific cover note per posting (2-4 sentences: one real relevant project, why this role, "CV attached") — no copy-pasted generic text across postings.
- Multi-city forms (e.g. Vega IT) default to nothing selected — explicitly tick the Belgrade checkbox, don't assume a default.
- LinkedIn's detail pane loads async: after clicking a result, `get_page_text` can return stale/list content. Re-click or add a short wait, then re-read, before trusting the description you extract.
- Cookie banners: pick the privacy-preserving option (reject non-essential / manage preferences) rather than "accept all".

## Blockers to flag, never fake

Stop and report to the user — do not attempt to work around these:
- **Anti-AI-content clauses** ("use only your own words, AI-generated content disqualifies you") — essay-style answers on that form must come from the candidate themselves.
- **Required video/photo/personality tests** (DISC test, Berlitz score + screenshot, self-recorded video intro) — a generic BPO/virtual-assistant recruiting pattern, not a signal of a real tech pipeline. Note it and skip rather than trying to fill it in.
- **Broken ATS pages** (e.g. an iCIMS page that stays blank after repeated reloads) — note the failure, move to the next target.
- **reCAPTCHA v3** (the passive "protected by reCAPTCHA" badge, no visible challenge) needs no interaction — submit normally. A **v2 checkbox/image challenge** must never be solved by Claude — stop and ask the user.

## Common mistakes

- Recommending a job from the search snippet alone → always open the full page first.
- Trusting "no experience" wording in a title without reading the body — some "bez iskustva" postings still list a required-skills section that's effectively medior+.
- Re-listing a company+role the user already applied to in a prior session — grep memory *and* Infostud history before calling something new.
- Filling personal essay/video/test requirements on the user's behalf to "get it done" — always flag and stop instead.
