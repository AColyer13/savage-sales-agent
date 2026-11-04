---
description: Research what marketing experts are saying now, track it with sources, and (with your yes) feed it into the playbook
argument-hint: <topic, e.g. "cold email deliverability", or blank to use my market from profile.md; or "review" to go through pending trends>
---
Read profile.md, automation/trends.py (its docstring is the interface) and, if present, playbook/13-supplement-marketing-trends.md. Topic: $ARGUMENTS
If the argument is "review", run `python automation/trends.py list --status new` and `--stale`, walk me through each pending or stale trend, and stop.

Otherwise research:
1. Use WebSearch/WebFetch for recent (ideally last 12 months) material from named practitioners, publications and data sources on the topic as it applies to selling to my market. Prefer original sources over roundups. Open the page where you can; if you could not open it, say so in notes.
2. Pick at most 8 distinct trends. For each, record ONE paraphrased claim (never a long quote), the real URL, the source name, the publish date, the expert's name if there is one, and the kind: `data` (a measured study), `expert-opinion` (a named practitioner or publication with a public track record, not a friend, a colleague or hearsay) or `vendor-claim` (a company selling something). Do not invent a date, URL, name or statistic; if a date is unknown, skip that item. Do not copy wording from paywalled content.
Two audiences: if the topic is about how I sell (outreach, email, positioning), tag --applies with outreach, cold-script, etc. If I ask for material to SHARE with my buyers (their industry, regulations, tools, benchmarks), research THEIR business, not marketing, and tag --applies campaign (plus the persona id).
3. Add each with `python automation/trends.py add ...` (set --applies to the commands it affects, e.g. outreach, cold-script, personas, draft-batch). They are saved as `new` and NO command uses them yet.
4. Show me a table: id, claim, kind, source, date, what it would change in my outreach/prospecting, and your honest confidence. Flag disagreements between experts. Say which look like marketing hype.
5. Ask which to adopt. Adopt ONLY the ids I confirm, with `python automation/trends.py decide <id> --decision adopt --confirmed-by-user`; reject the ones I decline. Adopting regenerates playbook 13, which the other commands then read as a supplement.
Never edit playbook 13 by hand, never adopt without my yes, and never contact anyone. Trends are hypotheses to test; the course wins on conflict.
