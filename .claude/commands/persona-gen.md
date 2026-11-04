---
description: Generate buyer personas for my market as a reviewable file (automation/personas.json) for later outreach automation
argument-hint: <my market, e.g. "independent dental practices, 3-40 staff, US", or blank to use profile.md>
---
Read profile.md, automation/PERSONAS.md (the schema), examples/personas.example.json, and playbook/07-territory-and-skills.md (personas) and 08-supplement-outreach.md. Market: $ARGUMENTS
If profile.md is blank or the market is vague, ask me up to 5 short questions first (who buys, who uses it, who could block it, company size, industry names as they appear in HubSpot). In practice mode, say so at the top.

Generate 3-5 personas for this market. Rules:
- Every pain, goal, objection and day-in-the-life line is a HYPOTHESIS unless I told you it. Mark each `(hypothesis)` and list the 3-customer interview questions that would verify them. Never invent statistics, customer names or results.
- Include a blocker/skeptic persona (the one who feels threatened), not only buyers.
- `title_include` and `title_exclude` must be real job-title strings as they appear in CRMs (include common variants and abbreviations); `industries` must use the words HubSpot's industry field would contain; give `employee_min` and `employee_max` only if I gave a size, else leave them out.
- Set `"approved": false` on every persona. I approve each one by editing the file after I review it. Say this clearly at the end.
- Per persona also give: goals, pains, objections, one-sentence `angle`, and an `evidence` field saying "hypothesis: verify with 3 real customers".

Write valid JSON to automation/personas.json (same shape as examples/personas.example.json). Write the human-readable version (day in the life, direct/indirect value, who feels threatened, phone opener, cold email under 125 words, proof placeholders like [ADD CASE STUDY]) to outputs/personas.md.
Then run: python automation/match_persona.py <contacts csv> --personas automation/personas.json  ONLY if I give you a contacts CSV, and summarize how many contacts matched, were ambiguous, or need a human. Never send or contact anyone.
