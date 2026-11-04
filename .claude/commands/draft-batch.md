---
description: Draft one personalized email per matched, approved contact (drafts only, nothing is sent)
argument-hint: <path to matched.csv from the matcher, optional extra instructions>
---
Read profile.md, automation/PERSONAS.md, automation/personas.json, playbook/08-supplement-outreach.md and playbook/12-supplement-cold-email-craft.md (and playbook/13-supplement-marketing-trends.md if it exists). Input: $ARGUMENTS
If there is no matched.csv, tell me to run: python automation/match_persona.py <contacts.csv> --personas automation/personas.json --out matched.csv  (HubSpot or any CRM export). If no persona is approved, stop and say so: I approve personas by editing `"approved"` myself.
1. Take ONLY rows with eligible=True. Cap the batch at 25 per run unless I say otherwise. Skip the rest and say how many were skipped and why (review, ambiguous, unapproved).
2. For each contact write one short first-touch email using their persona's angle and their first name, company and title. Use only facts present in the CSV or profile.md. Proof only from profile.md, else leave the proof line out (do not write placeholders in a draft I will send). No invented numbers, no invented peers.
3. Every body must end with a plain opt-out line (for example "Not relevant? Just reply and I won't email again."). Remind me that a postal address / legal footer is my responsibility.
4. Write the drafts as JSON [{"email","subject","body"}] to outputs/drafts.json, then run: python automation/export_drafts.py <matched.csv> outputs/drafts.json --outdir outputs/drafts --from <my address if I gave it>
5. The exporter refuses anyone on the stop list or who has replied; report those as blocked and remind me to run /log-results after I send and when replies come in.
6. Report how many were written and every refusal with its reason; fix refusals you caused, never edit the eligibility or approval flags.
7. Tell me where the .eml files are: double-click opens each as an editable unsent draft in Outlook, Apple Mail or Thunderbird. If a Gmail connector is available in this session, offer to create the same drafts in Gmail as DRAFTS; create them only after I say yes, and never use any send tool.
You never send, schedule or contact anyone. I review and send.
