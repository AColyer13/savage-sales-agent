#!/usr/bin/env python3
"""Suppression list + outcome log. Local files, standard library only, no network.

Why: the tool only drafts; you send from your own mail app, so it cannot see what happened. This file is how it learns.
  - Suppression list (automation/suppression.csv): addresses (or whole @domains) that must NEVER be drafted again.
  - Outcome log (automation/outcomes.csv): what happened per contact/campaign/issue.

Commands
  python automation/outreach_state.py suppress EMAIL_OR_@DOMAIN --reason "asked to stop"
  python automation/outreach_state.py unsuppress EMAIL_OR_@DOMAIN --confirmed-by-user     (agent may not do this alone)
  python automation/outreach_state.py import file.csv [--reason "..."]        CSV with an email column -> suppress all
  python automation/outreach_state.py mark EMAIL --outcome OUTCOME [--campaign NAME] [--issue N] [--note "..."]
  python automation/outreach_state.py status EMAIL          history + whether blocked
  python automation/outreach_state.py list                   everything suppressed

Outcomes: sent, replied, meeting, not-interested, unsubscribed, bounced-hard, bounced-soft
  unsubscribed, not-interested and bounced-hard suppress the address automatically.
  replied and meeting block automated drafts (a person should follow up); they are lifted by `mark EMAIL --outcome sent`
  only after you confirm with --confirmed-by-user.
"""
import argparse
import csv
import datetime
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SUPPRESSION = os.path.join(HERE, "suppression.csv")
OUTCOMES = os.path.join(HERE, "outcomes.csv")
OUTCOME_VALUES = ("sent", "replied", "meeting", "not-interested", "unsubscribed", "bounced-hard", "bounced-soft")
AUTO_SUPPRESS = ("unsubscribed", "not-interested", "bounced-hard")
HOLD = ("replied", "meeting")
S_FIELDS = ["email", "reason", "date"]
O_FIELDS = ["date", "email", "campaign", "issue", "outcome", "note"]
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def clean(value):
    return (value or "").strip().lower()


def valid_target(t):
    return bool(EMAIL_RE.match(t)) or bool(re.match(r"^@[^@\s]+\.[^@\s]+$", t))


def _read(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write(path, fields, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def load_suppression(path=None):
    return _read(path or SUPPRESSION)


def load_outcomes(path=None):
    return _read(path or OUTCOMES)


def suppress(target, reason="", path=None, today=None):
    target = clean(target)
    if not valid_target(target):
        return f"REFUSED: '{target}' is not an email address or @domain."
    rows = load_suppression(path)
    if any(r["email"] == target for r in rows):
        return f"{target} is already suppressed."
    rows.append({"email": target, "reason": reason.strip(), "date": (today or datetime.date.today()).isoformat()})
    _write(path or SUPPRESSION, S_FIELDS, rows)
    return f"Suppressed {target}."


def unsuppress(target, confirmed=False, path=None):
    target = clean(target)
    if not confirmed:
        return "REFUSED: removing someone from the stop list can cause an email to a person who opted out. Ask the user, then re-run with --confirmed-by-user."
    rows = load_suppression(path)
    keep = [r for r in rows if r["email"] != target]
    if len(keep) == len(rows):
        return f"{target} was not suppressed."
    _write(path or SUPPRESSION, S_FIELDS, keep)
    return f"Removed {target} from the stop list."


def is_suppressed(email, suppression_rows):
    e = clean(email)
    domain = "@" + e.split("@")[-1] if "@" in e else ""
    for r in suppression_rows:
        if r["email"] == e or (r["email"].startswith("@") and r["email"] == domain):
            return r
    return None


def latest_outcome(email, outcome_rows):
    e = clean(email)
    mine = [r for r in outcome_rows if r["email"] == e]
    return mine[-1] if mine else None


def blocked_reason(email, suppression_rows, outcome_rows):
    """Return a human reason the contact must not get an automated draft, or None."""
    s = is_suppressed(email, suppression_rows)
    if s:
        return f"suppressed ({s['reason'] or 'no reason recorded'}, {s['date']})"
    last = latest_outcome(email, outcome_rows)
    if last and last["outcome"] in HOLD:
        return f"{last['outcome']} on {last['date']}: follow up personally, no automated drafts"
    return None


def mark(email, outcome, campaign="", issue="", note="", confirmed=False, sup_path=None, out_path=None, today=None):
    email = clean(email)
    if not EMAIL_RE.match(email):
        return f"REFUSED: '{email}' is not an email address."
    if outcome not in OUTCOME_VALUES:
        return "REFUSED: outcome must be one of " + ", ".join(OUTCOME_VALUES)
    rows = load_outcomes(out_path)
    last = latest_outcome(email, rows)
    if outcome == "sent" and last and last["outcome"] in HOLD and not confirmed:
        return "REFUSED: this contact replied or booked a meeting. Marking 'sent' again would resume automated drafts. Ask the user, then add --confirmed-by-user."
    day = (today or datetime.date.today()).isoformat()
    rows.append({"date": day, "email": email, "campaign": campaign, "issue": issue, "outcome": outcome, "note": note})
    _write(out_path or OUTCOMES, O_FIELDS, rows)
    msg = f"Logged {outcome} for {email}."
    if outcome in AUTO_SUPPRESS:
        msg += " " + suppress(email, f"{outcome}" + (f": {note}" if note else ""), sup_path, today)
    elif outcome in HOLD:
        msg += " Automated drafts to this contact are now blocked."
    return msg


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("suppress"); s.add_argument("target"); s.add_argument("--reason", default="")
    u = sub.add_parser("unsuppress"); u.add_argument("target"); u.add_argument("--confirmed-by-user", action="store_true")
    i = sub.add_parser("import"); i.add_argument("csv"); i.add_argument("--reason", default="imported")
    m = sub.add_parser("mark"); m.add_argument("email"); m.add_argument("--outcome", required=True)
    m.add_argument("--campaign", default=""); m.add_argument("--issue", default=""); m.add_argument("--note", default="")
    m.add_argument("--confirmed-by-user", action="store_true")
    st = sub.add_parser("status"); st.add_argument("email")
    sub.add_parser("list")
    a = ap.parse_args(argv)

    if a.cmd == "suppress":
        msg = suppress(a.target, a.reason)
    elif a.cmd == "unsuppress":
        msg = unsuppress(a.target, a.confirmed_by_user)
    elif a.cmd == "import":
        n = 0
        with open(a.csv, newline="", encoding="utf-8-sig") as f:
            for r in csv.DictReader(f):
                r = {(k or "").strip().lower(): v for k, v in r.items()}
                if r.get("email") and suppress(r["email"], a.reason).startswith("Suppressed"):
                    n += 1
        msg = f"Suppressed {n} new addresses."
    elif a.cmd == "mark":
        msg = mark(a.email, a.outcome, a.campaign, a.issue, a.note, a.confirmed_by_user)
    elif a.cmd == "status":
        sup, out = load_suppression(), load_outcomes()
        lines = [f"{r['date']} {r['outcome']} {r['campaign']} {r['issue']} {r['note']}".strip() for r in out if r["email"] == clean(a.email)]
        msg = "\n".join(lines + [f"BLOCKED: {blocked_reason(a.email, sup, out)}" if blocked_reason(a.email, sup, out) else "not blocked"])
    else:
        rows = load_suppression()
        msg = "\n".join(f"{r['email']}  {r['reason']}  {r['date']}" for r in rows) + f"\n{len(rows)} suppressed"
    print(msg)
    return 1 if msg.startswith("REFUSED") else 0


if __name__ == "__main__":
    sys.exit(main())
