"""Map contacts (e.g. a HubSpot CSV export) to personas from personas.json.

Deterministic: no AI call, same input gives the same answer. Nothing is ever sent from here.
It labels contacts, and queues titles it does not understand into automation/title_review.jsonl
so the /title-audit command can review them and write a permanent rule (see audit_titles.py).

Usage:
  python automation/match_persona.py contacts.csv --personas automation/personas.json [--out matched.csv]

Contact columns (HubSpot export names, case-insensitive): email, firstname, lastname,
jobtitle, company, industry, numberofemployees
"""
import argparse
import csv
import datetime
import difflib
import json
import os
import re
import sys
import unicodedata

HIGH, MEDIUM = 0.70, 0.50
CAP_MEDIUM = HIGH - 0.01          # 0.69: can never be "high"
CAP_NONE = MEDIUM - 0.01          # 0.49: no persona
AMBIGUOUS_GAP = 0.10
HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_RULES = os.path.join(HERE, "title_rules.json")
DEFAULT_QUEUE = os.path.join(HERE, "title_review.jsonl")

SENIORITY = ["owner", "founder", "co-founder", "president", "ceo", "chief", "vp", "vice president",
              "director", "head", "manager", "lead", "partner", "principal"]

# Common abbreviations, expanded per token before matching.
ABBREV = {"mgr": "manager", "mngr": "manager", "dir": "director", "asst": "assistant", "admin": "administrator",
          "coord": "coordinator", "pres": "president", "exec": "executive", "sr": "senior", "jr": "junior",
          "dr": "doctor", "vp": "vp", "ofc": "office", "pract": "practice"}

# Roles that are never a buyer persona. A title containing any of these has no persona.
BASE_EXCLUDE = ["former", "formerly", "ex", "retired", "past", "student", "intern", "interns", "trainee",
                "resident", "seeking", "open to work", "unemployed", "assistant", "hygienist", "technician",
                "lab", "sales", "salesperson", "representative", "rep", "recruiter", "recruiting", "broker",
                "vendor", "supplier", "consultant", "marketing", "business development", "account executive"]

# Words that name a credential or specialty but not a role. A title made only of these cannot say
# whether the person is the owner or an employee/associate.
CREDENTIAL_TOKENS = {"dds", "dmd", "md", "ms", "msd", "doctor", "dentist", "dental", "general", "pediatric",
                     "cosmetic", "family", "orthodontist", "periodontist", "endodontist", "prosthodontist",
                     "oral", "surgeon", "and", "of", "the", "at", "practice"}

JUNK_TITLES = {"", "n a", "na", "none", "null", "unknown", "self employed", "freelance"}


def norm(text):
    t = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode().lower()
    t = t.replace("&", " and ")
    t = re.sub(r"(?<=\w)\.(?=\w)", "", t)          # d.d.s. -> dds
    t = re.sub(r"[^a-z0-9 ]+", " ", t)
    tokens = [ABBREV.get(w, w) for w in t.split()]
    return " ".join(tokens)


def has_phrase(haystack, phrase):
    return f" {norm(phrase)} " in f" {haystack} "


def to_int(value):
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def load_rules(path=DEFAULT_RULES):
    base = {"global_exclude": [], "ambiguous": [], "include": {}, "decisions": []}
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            base.update(json.load(f))
    return base


def title_excluded(title, rules):
    for bad in BASE_EXCLUDE + rules.get("global_exclude", []):
        if has_phrase(title, bad):
            return bad
    return None


def score(persona, contact, rules):
    """Return (score, reasons, flags), or (None, [reason], flags) if excluded."""
    raw = contact.get("jobtitle")
    title = norm(raw)
    flags = []
    if title in JUNK_TITLES:
        return 0.0, ["no usable job title"], flags
    bad = title_excluded(title, rules)
    if bad:
        return None, [f"excluded title '{bad}'"], flags
    for bad in persona.get("title_exclude", []):
        if has_phrase(title, bad):
            return None, [f"excluded title '{bad}'"], flags

    s, why, cap = 0.0, [], 1.0
    includes = list(persona.get("title_include", [])) + rules.get("include", {}).get(persona.get("id"), [])
    matched = [k for k in includes if has_phrase(title, k)]
    if matched:
        s += 0.6
        why.append("title matches")
        if all(set(norm(k).split()) <= CREDENTIAL_TOKENS for k in matched):
            flags.append("credential_only")       # e.g. bare "Dentist" or "DDS": owner or associate?
            why.append("title names a credential, not a role")
    else:
        words = set(title.split())
        overlap = max((len(words & set(norm(k).split())) / max(len(norm(k).split()), 1)
                       for k in includes), default=0)
        close = difflib.get_close_matches(title, [norm(k) for k in includes], n=1, cutoff=0.85)
        if close:
            s += 0.3
            cap = min(cap, CAP_MEDIUM)
            flags.append("fuzzy")
            why.append(f"title looks like '{close[0]}' (typo or variant)")
        elif overlap >= 0.5:
            s += 0.3
            why.append("partial title match")

    wanted = [x.lower() for x in persona.get("seniority", [])]
    if wanted and any(has_phrase(title, k) for k in SENIORITY if k in wanted):
        s += 0.15
        why.append("seniority matches")

    inds = [norm(i) for i in persona.get("industries", [])]
    if inds:
        industry = norm(contact.get("industry"))
        company = norm(contact.get("company"))
        text = f"{industry} {company}".strip()
        if industry and any(i in industry or industry in i for i in inds):
            s += 0.15
            why.append("industry matches")
        elif company and any(i in company for i in inds):
            s += 0.10
            why.append("company name suggests industry")
        elif industry:
            cap = min(cap, CAP_NONE)
            flags.append("industry_mismatch")
            why.append("industry does not match")
        else:
            cap = min(cap, CAP_MEDIUM)
            flags.append("industry_unknown")
            why.append("industry unknown")

    lo, hi = persona.get("employee_min"), persona.get("employee_max")
    n = to_int(contact.get("numberofemployees"))
    if n is not None and lo is not None and hi is not None:
        if lo <= n <= hi:
            s += 0.10
            why.append("company size fits")
        else:
            cap = min(cap, CAP_MEDIUM)
            flags.append("size_outside_range")
            why.append("company size outside range")

    if "credential_only" in flags:
        cap = min(cap, CAP_MEDIUM)
    if title in rules.get("ambiguous", []):
        cap = min(cap, CAP_MEDIUM)
        flags.append("known_ambiguous")
        why.append("title previously reviewed as ambiguous")
    return round(min(s, cap), 2), why, flags      # caps apply last so no bonus can lift a capped score


def match(contact, personas, rules=None):
    rules = rules if rules is not None else load_rules()
    title = norm(contact.get("jobtitle"))
    scored = []
    all_flags = []
    for p in personas:
        sc, why, flags = score(p, contact, rules)
        if sc is not None:
            scored.append((sc, p, why, flags))
    scored.sort(key=lambda t: -t[0])
    email = (contact.get("email") or "").strip()
    bad_email = not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)

    if not scored or scored[0][0] < MEDIUM:
        excluded = title_excluded(title, rules) is not None and title not in JUNK_TITLES
        best = scored[0] if scored else None
        flags = best[3] if best else []
        unknown = bool(title) and title not in JUNK_TITLES and not excluded and "industry_mismatch" not in flags
        return {"persona": "", "score": best[0] if best else 0, "confidence": "none", "eligible": False,
                "flags": ",".join(flags), "audit_needed": unknown,
                "reason": "no persona fits well: needs a human"}

    top = scored[0]
    flags = list(top[3])
    if bad_email:
        flags.append("invalid_email")
    if len(scored) > 1 and scored[1][0] >= MEDIUM and top[0] - scored[1][0] < AMBIGUOUS_GAP:
        flags.append("tie")
        return {"persona": top[1]["id"], "score": top[0], "confidence": "ambiguous", "eligible": False,
                "flags": ",".join(flags), "audit_needed": True,
                "reason": f"ties with {scored[1][1]['id']}: needs a human"}
    conf = "high" if top[0] >= HIGH else "medium"
    approved = bool(top[1].get("approved"))
    needs_audit = any(f in flags for f in ("credential_only", "fuzzy", "industry_unknown")) and \
        "known_ambiguous" not in flags
    reason = "; ".join(top[2]) + ("" if approved else "; persona not approved yet")
    return {"persona": top[1]["id"], "score": top[0], "confidence": conf,
            "eligible": conf == "high" and approved and not bad_email,
            "flags": ",".join(flags), "audit_needed": needs_audit, "reason": reason}


def queue_for_audit(contact, result, path=DEFAULT_QUEUE):
    """Append a title the matcher could not settle to the review queue (deduplicated)."""
    title = norm(contact.get("jobtitle"))
    key = f"{title}|{result['flags']}|{result['persona']}"
    seen = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    seen.add(json.loads(line)["key"])
                except (ValueError, KeyError):
                    pass
    if key in seen:
        return False
    entry = {"key": key, "title": contact.get("jobtitle", ""), "norm_title": title,
             "industry": contact.get("industry", ""), "company": contact.get("company", ""),
             "employees": contact.get("numberofemployees", ""), "candidate_persona": result["persona"],
             "flags": result["flags"], "reason": result["reason"],
             "date": datetime.date.today().isoformat()}
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return True


def load_personas(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["personas"] if isinstance(data, dict) else data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("contacts")
    ap.add_argument("--personas", default=os.path.join(HERE, "personas.json"))
    ap.add_argument("--rules", default=DEFAULT_RULES)
    ap.add_argument("--queue", default=DEFAULT_QUEUE)
    ap.add_argument("--no-queue", action="store_true", help="do not write titles to the review queue")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    personas = load_personas(args.personas)
    rules = load_rules(args.rules)
    with open(args.contacts, newline="", encoding="utf-8-sig") as f:
        rows = [{(k or "").strip().lower(): v for k, v in r.items()} for r in csv.DictReader(f)]
    out, queued = [], 0
    for r in rows:
        res = match(r, personas, rules)
        if res["audit_needed"] and not args.no_queue and queue_for_audit(r, res, args.queue):
            queued += 1
        out.append({**r, **res})
    fields = list(out[0].keys()) if out else []
    dest = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    w = csv.DictWriter(dest, fieldnames=fields)
    w.writeheader()
    w.writerows(out)
    if args.out:
        dest.close()
    elig = sum(1 for o in out if o["eligible"])
    msg = f"{len(out)} contacts, {elig} eligible, {len(out) - elig} need review, {queued} new titles queued for audit"
    print(msg, file=sys.stderr if not args.out else sys.stdout)


if __name__ == "__main__":
    main()
