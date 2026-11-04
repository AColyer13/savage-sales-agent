---
description: Audit job titles the matcher didn't recognize, fix the rules so it can't repeat, and re-run the tests
argument-hint: <optional: a contacts CSV to re-run afterwards>
---
Read automation/PERSONAS.md and automation/personas.json. Run: python automation/audit_titles.py list
If the queue is empty, say so and stop. For each queued title, reason about what it most likely is in this market (use profile.md and the personas; do not guess when the evidence is thin) and choose ONE decision:
- exclude: clearly not a buyer persona (vendor, student, former, foreign-language non-buyer, etc.). Safe, you may apply it yourself.
- ambiguous: could be a buyer or not (bare credential, unclear seniority, unknown role). Safe, you may apply it yourself. It forces a human to look at every contact with that title.
- include: clearly a buyer persona I missed. This makes MORE contacts eligible, so you may NOT apply it without asking me. Show the title, the persona, and your reasoning, wait for my yes, then apply with --confirmed-by-user.
When unsure between ambiguous and include, choose ambiguous.
Apply with: python automation/audit_titles.py apply --title "<title>" --decision <exclude|ambiguous|include> [--persona <id>] [--reason "<why>"]
Then run: python -m unittest discover -s tests   and report any failure. Never edit "approved" flags in personas.json, and never send or contact anyone.
If $ARGUMENTS is a contacts CSV, re-run: python automation/match_persona.py <csv> --personas automation/personas.json --out outputs/matched.csv --no-queue   and summarize eligible vs needs-review counts.
End with a short table: title, decision, reason, applied or waiting for my approval.
