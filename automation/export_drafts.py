#!/usr/bin/env python3
"""Turn agent-written outreach drafts into reviewable .eml draft files. NEVER sends anything.

Input 1: matched.csv from match_persona.py (only rows with eligible=True may get a draft).
Input 2: drafts JSON: [{"email": ..., "subject": ..., "body": ...}, ...] written by /draft-batch.

Campaign mode (--campaign NAME --issue N): each body must cite a source URL, the same issue is never drafted twice for a contact,
and a contact gets at most one draft per --min-days (default 7), also outside campaign mode.

Output: <outdir>/NNN-<slug>.eml  (X-Unsent: 1 so Outlook / Apple Mail / Thunderbird open it as an editable draft)
        <outdir>/drafts_log.csv   (email, subject, persona, file, status) for logging or CRM import.
Each draft is refused if the contact is not eligible, an [ADD ...] placeholder is unresolved, the subject or body is empty,
or the body has no opt-out line. Postal-address and law compliance are the sender's responsibility.

  python automation/export_drafts.py matched.csv drafts.json --outdir outputs/drafts [--from you@example.com]
"""
import argparse
import csv
import datetime
import json
import os
import re
import sys
from email.message import EmailMessage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import outreach_state as state  # noqa: E402  (suppression list + outcome log)

OPT_OUT = re.compile(r"unsubscribe|opt[ -]?out|(won't|will not|wont) (email|contact|message)( you)?( again)?|not (email|contact) (you )?again|stop (emailing|these)|remove you", re.I)
PLACEHOLDER = re.compile(r"\[[^\]" + chr(10) + r"]{2,}\]")  # any [bracketed text] left in a draft


def load_eligible(path):
    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return {r["email"].strip().lower(): r for r in rows if str(r.get("eligible", "")).strip().lower() == "true"}


def check(draft, eligible):
    """Return a list of problems; empty means OK."""
    problems = []
    email = str(draft.get("email", "")).strip().lower()
    if email not in eligible:
        problems.append("contact is not eligible (not high-confidence, persona not approved, or not in matched.csv)")
    subject = str(draft.get("subject", "")).strip()
    body = str(draft.get("body", "")).strip()
    if not subject:
        problems.append("empty subject")
    if not body:
        problems.append("empty body")
    if PLACEHOLDER.search(subject + "\n" + body):
        problems.append("unresolved [bracketed] placeholder (fill it in, e.g. your name)")
    if body and not OPT_OUT.search(body):
        problems.append("no opt-out line (add e.g. 'Not relevant? Just reply and I won't email you again.')")
    if re.search(r"[\r\n]", subject):
        problems.append("newline in subject")
    return problems


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "draft"


FIELDS = ["date", "email", "subject", "persona", "campaign", "issue", "file", "status"]
URL = re.compile(r"https?://[^\s/]+\.[^\s]+")


def load_log(path):
    if not os.path.exists(path):
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def campaign_problems(draft, history, campaign, issue, min_days, today):
    """Extra checks for newsletter/nurture drafts: traceable source, no duplicate issue, no over-mailing."""
    probs = []
    email = str(draft.get("email", "")).strip().lower()
    if not URL.search(str(draft.get("body", ""))):
        probs.append("campaign emails must cite a source URL for the insight they share")
    for h in history:
        if h.get("email") != email:
            continue
        if campaign and h.get("campaign") == campaign and str(h.get("issue")) == str(issue):
            probs.append(f"issue {issue} of '{campaign}' was already drafted for this contact")
        try:
            age = (today - datetime.date.fromisoformat(h.get("date", ""))).days
        except ValueError:
            continue
        if age < min_days:
            probs.append(f"this contact already has a draft from {age} day(s) ago (minimum gap {min_days})")
            break
    return probs


def export(matched_csv, drafts_json, outdir, sender=None, campaign=None, issue=None, min_days=7, today=None,
           sup_path=None, out_path=None):
    today = today or datetime.date.today()
    eligible = load_eligible(matched_csv)
    with open(drafts_json, encoding="utf-8") as f:
        drafts = json.load(f)
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "drafts_log.csv")
    history = load_log(path)
    sup_rows, out_rows = state.load_suppression(sup_path), state.load_outcomes(out_path)
    log, refused = [], []
    n = len(history)
    for d in drafts:
        probs = check(d, eligible)
        blocked = state.blocked_reason(str(d.get("email", "")), sup_rows, out_rows)
        if blocked:
            probs.append("blocked: " + blocked)
        if campaign:
            probs += campaign_problems(d, history + log, campaign, issue, min_days, today)
        elif not probs:
            probs += [x for x in campaign_problems(d, history + log, None, None, min_days, today) if "already has a draft" in x]
        if probs:
            refused.append((d.get("email", "?"), probs))
            continue
        n += 1
        email = d["email"].strip().lower()
        msg = EmailMessage()
        msg["To"] = email
        if sender:
            msg["From"] = sender
        msg["Subject"] = d["subject"].strip()
        msg["X-Unsent"] = "1"
        msg.set_content(d["body"].strip() + chr(10))
        fname = f"{n:03d}-{slug(email.split('@')[0])}.eml"
        with open(os.path.join(outdir, fname), "wb") as f:
            f.write(bytes(msg))
        log.append({"date": today.isoformat(), "email": email, "subject": d["subject"].strip(),
                    "persona": eligible[email].get("persona", ""), "campaign": campaign or "",
                    "issue": issue if issue is not None else "", "file": fname, "status": "drafted_not_sent"})
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(history + log)
    return log, refused


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("matched_csv")
    ap.add_argument("drafts_json")
    ap.add_argument("--outdir", default="outputs/drafts")
    ap.add_argument("--from", dest="sender", default=None)
    ap.add_argument("--campaign", help="campaign name; turns on source-URL, duplicate-issue and spacing checks")
    ap.add_argument("--issue", type=int, help="issue number within the campaign")
    ap.add_argument("--min-days", type=int, default=7, help="minimum days between drafts to the same contact")
    a = ap.parse_args(argv)
    if a.campaign and a.issue is None:
        ap.error("--campaign needs --issue")
    log, refused = export(a.matched_csv, a.drafts_json, a.outdir, a.sender, a.campaign, a.issue, a.min_days)
    print(f"{len(log)} drafts written to {a.outdir} (nothing was sent), {len(refused)} refused")
    for email, probs in refused:
        print(f"  REFUSED {email}: " + "; ".join(probs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
