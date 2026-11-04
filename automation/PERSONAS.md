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
