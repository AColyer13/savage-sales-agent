# personas.json schema and matching rules

`automation/personas.json` is created by `/persona-gen` and read by `match_persona.py`. Contacts are labeled; nothing here sends anything.

## Fields (per persona)
| Field | Meaning |
|---|---|
| `id` | short slug, unique |
| `name` | display name |
| `approved` | `false` until YOU review and set `true`. Unapproved personas never make a contact eligible for sending. |
| `title_include` | job-title phrases that identify this persona (include variants and abbreviations) |
| `title_exclude` | phrases that rule a contact out (e.g. "intern", "associate") |
| `seniority` | words such as owner, founder, president, manager, director, vp, head |
| `industries` | words the CRM industry field would contain |
| `employee_min`, `employee_max` | optional company size range. A known size outside the range caps confidence below "high". |
| `goals`, `pains`, `objections` | messaging inputs. Hypotheses until verified with real customers. |
| `angle` | one-sentence message angle |
| `evidence` | where the claims come from; default "hypothesis: verify with 3 real customers" |

## Scoring (deterministic, 0 to 1)
title phrase match 0.60 (partial 0.30) + seniority 0.15 + industry 0.15 + company size 0.10.
Excluded title = out. No title = 0.
- `high` is 0.70 or more, `medium` is 0.50 to 0.69, below 0.50 = no persona ("needs a human").
- If the top two personas are within 0.10 of each other and both 0.50 or more = `ambiguous` ("needs a human").
- `eligible` is true only when confidence is `high` AND the persona is `approved`. Everything else goes to a human.

## Input
HubSpot export CSV with columns (any case): email, firstname, lastname, jobtitle, company, industry, numberofemployees.

## Run
`python automation/match_persona.py contacts.csv --personas automation/personas.json --out matched.csv`
Tests: `python -m unittest discover -s tests`

## Edge cases handled (all covered by tests/test_match_persona.py)
| Case | Behavior |
|---|---|
| Bare credential: "Dentist", "DDS", "D.D.S.", "DMD", "Dr. Kim, DDS", "General Dentist" | Matches the owner persona but is capped below "high" (owner or associate? cannot tell). Always goes to a human and into the audit queue. |
| "Associate Dentist", assistant, hygienist, technician, student, intern, resident | No persona. |
| Vendors and sellers at dental companies: sales rep, representative, supplier, consultant, marketing, recruiter, broker | No persona. |
| Stale: former, ex-, retired, past | No persona. |
| "Dentistry Recruiter" (substring trap) | Whole-word matching, so "dentist" never matches inside "dentistry". |
| Wrong industry ("Owner" at a software company) | No persona. |
| Industry blank | Capped below "high" unless the company name contains the industry word ("Bright Dental Care"). |
| Company size outside your range, including solo practices below the minimum | Capped below "high". |
| Abbreviations: Mgr, Dir, Asst, Admin, Coord, Dr | Expanded before matching. |
| CAPS, accents, "&", periods, extra spaces | Normalized. |
| Typos: "Ofice Manager" | Fuzzy match, capped below "high", queued for audit. |
| Foreign-language or unknown titles: "Zahnarzt" | No persona, queued for audit. |
| Empty, "N/A", "-", "none" | No persona, not queued (nothing to learn). |
| Invalid or missing email | Never eligible. |
| Persona not approved | Never eligible. |
| Two personas tie within 0.10 | "ambiguous": human decides, queued. |

## Self-correction loop
1. The matcher cannot settle a title -> it writes it once (deduplicated) to `automation/title_review.jsonl`.
2. `/title-audit` has the agent review each queued title and choose: exclude, ambiguous, or include.
3. Decisions are saved to `automation/title_rules.json` (permanent), the title leaves the queue, and a regression case is added to `automation/title_regressions.json`. The test suite replays all past decisions, so a fixed mistake cannot come back.
4. Safety asymmetry: `exclude` and `ambiguous` (fewer contacts eligible) the agent may apply by itself. `include` (more contacts eligible) needs your yes, and the tool refuses without `--confirmed-by-user`.
5. The agent never edits `approved` flags and never sends anything.
The matcher itself makes no AI call. The "thinking" happens when `/title-audit` runs (by hand now; it can be scheduled later in the autopilot job).

## Enabling unattended /title-audit (optional, your decision)
Interactive use just prompts you. A scheduled run needs permission to run the three tools above. `automation/settings.suggested.json` lists exactly those commands and nothing else. To turn it on, copy it yourself:
`copy automation\settings.suggested.json .claude\settings.json` (then delete the `_note` line if you like).
