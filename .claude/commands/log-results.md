---
description: Tell the agent what happened to your emails (sent, replied, bounced, unsubscribed) so it never re-drafts the wrong people
argument-hint: <paste what happened, e.g. "Ann Kim replied, Bo Lee asked to stop, c@x.com bounced", or a path to a CRM/mail export CSV>
---
Read automation/outreach_state.py (its docstring is the interface). Input: $ARGUMENTS
You only learn what I tell you; I send from my own mail app. For each person in my input:
1. Work out the contact's email address (ask me if I only gave a name and it is ambiguous; never guess an address) and the outcome: sent, replied, meeting, not-interested, unsubscribed, bounced-hard, bounced-soft. A reply that says stop / remove me / not interested / wrong person is `unsubscribed` or `not-interested`, not `replied`. When unsure between replied and not-interested, ask me; wrongly resuming someone who opted out is the worse mistake.
2. Record it: `python automation/outreach_state.py mark <email> --outcome <outcome> [--campaign <name> --issue <n>] [--note "<short reason>"]`. Unsubscribed, not-interested and hard bounces are suppressed automatically.
3. If I give a whole domain or company that opted out, use `python automation/outreach_state.py suppress @domain.com --reason "..."`. For a CSV of opt-outs use `import`.
4. Never run `unsuppress`, and never use `--confirmed-by-user`, unless I explicitly told you in this conversation to bring that exact person back. Say so if I ask and show what you will run first.
5. Finish with a table: email, outcome, effect (suppressed / drafts blocked / logged only), and the count now on the stop list (`python automation/outreach_state.py list`). If a campaign was named, give the reply rate so far (replies / sent) and say how small the sample is.
Never contact anyone and never edit the suppression or outcome files by hand.
