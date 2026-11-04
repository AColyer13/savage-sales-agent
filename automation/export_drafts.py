#!/usr/bin/env python3
"""Turn agent-written outreach drafts into reviewable .eml draft files. NEVER sends anything.

Input 1: matched.csv from match_persona.py (only rows with eligible=True may get a draft).
Input 2: drafts JSON: [{"email": ..., "subject": ..., "body": ...}, ...] written by /draft-batch.

Output: <outdir>/NNN-<slug>.eml  (X-Unsent: 1 so Outlook / Apple Mail / Thunderbird open it as an editable draft)
        <outdir>/drafts_log.csv   (email, subject, persona, file, status) for logging or CRM import.
Each draft is refused if the contact is not eligible, an [ADD ...] placeholder is unresolved, the subject or body is empty,
or the body has no opt-out line. Postal-address and law compliance are the sender's responsibility.

  python automation/export_drafts.py matched.csv drafts.json --outdir outputs/drafts [--from you@example.com]
"""
import argparse
import csv
import json
import os
import re
import sys
from email.message import EmailMessage

OPT_OUT = re.compile(r"unsubscribe|opt[ -]?out|(won't|will not|wont) (email|contact|message) you|not (email|contact) (you )?again|stop (emailing|these)|remove you", re.I)
PLACEHOLDER = re.compile(r"\[(ADD|TODO|PEER|METRIC)[^\]]*\]", re.I)


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
        problems.append("unresolved [ADD ...] placeholder")
    if body and not OPT_OUT.search(body):
        problems.append("no opt-out line (add e.g. 'Not relevant? Just reply and I won't email again.')")
    if re.search(r"[\r\n]", subject):
        problems.append("newline in subject")
    return problems


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "draft"


def export(matched_csv, drafts_json, outdir, sender=None):
    eligible = load_eligible(matched_csv)
    with open(drafts_json, encoding="utf-8") as f:
        drafts = json.load(f)
    os.makedirs(outdir, exist_ok=True)
    log, refused = [], []
    n = 0
    for d in drafts:
        probs = check(d, eligible)
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
        msg.set_content(d["body"].strip() + "\n")
        fname = f"{n:03d}-{slug(email.split('@')[0])}.eml"
        with open(os.path.join(outdir, fname), "wb") as f:
            f.write(bytes(msg))
        log.append({"email": email, "subject": d["subject"].strip(),
                    "persona": eligible[email].get("persona", ""), "file": fname, "status": "drafted_not_sent"})
    path = os.path.join(outdir, "drafts_log.csv")
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["email", "subject", "persona", "file", "status"])
        w.writeheader()
        w.writerows(log)
    return log, refused


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("matched_csv")
    ap.add_argument("drafts_json")
    ap.add_argument("--outdir", default="outputs/drafts")
    ap.add_argument("--from", dest="sender", default=None)
    a = ap.parse_args(argv)
    log, refused = export(a.matched_csv, a.drafts_json, a.outdir, a.sender)
    print(f"{len(log)} drafts written to {a.outdir} (nothing was sent), {len(refused)} refused")
    for email, probs in refused:
        print(f"  REFUSED {email}: " + "; ".join(probs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
