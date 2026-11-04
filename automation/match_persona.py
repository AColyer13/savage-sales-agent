"""Map contacts (e.g. a HubSpot CSV export) to personas from personas.json.

Deterministic on purpose: no AI call, so the same input always gives the same answer.
Nothing is ever sent from here. It only labels contacts.

Usage:
  python automation/match_persona.py contacts.csv --personas automation/personas.json [--out matched.csv]

Contact columns (HubSpot export names, case-insensitive): email, firstname, lastname,
jobtitle, company, industry, numberofemployees
"""
import argparse
import csv
import json
import re
import sys

HIGH, MEDIUM = 0.70, 0.50
AMBIGUOUS_GAP = 0.10
SENIORITY = ["owner", "founder", "co-founder", "president", "ceo", "chief", "vp", "vice president",
             "director", "head", "manager", "lead"]


def norm(text):
    return re.sub(r"[^a-z0-9 ]+", " ", (text or "").lower()).strip()


def has_phrase(haystack, phrase):
    return f" {norm(phrase)} " in f" {haystack} "


def to_int(value):
    try:
        return int(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def score(persona, contact):
    """Return (score, reasons), or (None, [reason]) if the contact is excluded."""
    title = norm(contact.get("jobtitle"))
    if not title:
        return 0.0, ["no job title"]
    for bad in persona.get("title_exclude", []):
        if has_phrase(title, bad):
            return None, [f"excluded title '{bad}'"]
    s, why = 0.0, []
    includes = persona.get("title_include", [])
    if any(has_phrase(title, k) for k in includes):
        s += 0.6
        why.append("title matches")
    else:
        words = set(title.split())
        overlap = max((len(words & set(norm(k).split())) / max(len(norm(k).split()), 1)
                       for k in includes), default=0)
        if overlap >= 0.5:
            s += 0.3
            why.append("partial title match")
    wanted = [x.lower() for x in persona.get("seniority", [])]
    if wanted and any(has_phrase(title, k) for k in SENIORITY if k in wanted):
        s += 0.15
        why.append("seniority matches")
    inds = [norm(i) for i in persona.get("industries", [])]
    industry = norm(contact.get("industry"))
    if inds and industry and any(i in industry or industry in i for i in inds):
        s += 0.15
        why.append("industry matches")
    lo, hi = persona.get("employee_min"), persona.get("employee_max")
    n = to_int(contact.get("numberofemployees"))
    if n is not None and lo is not None and hi is not None:
        if lo <= n <= hi:
            s += 0.10
            why.append("company size fits")
        else:
            s = min(s, HIGH - 0.01)  # known size outside the ICP range can never be "high"
            why.append("company size outside range")
    return round(s, 2), why


def match(contact, personas):
    scored = []
    for p in personas:
        sc, why = score(p, contact)
        if sc is not None:
            scored.append((sc, p, why))
    scored.sort(key=lambda t: -t[0])
    if not scored or scored[0][0] < MEDIUM:
        best = scored[0][0] if scored else 0
        return {"persona": "", "score": best, "confidence": "none", "eligible": False,
                "reason": "no persona fits well: needs a human"}
    top = scored[0]
    if len(scored) > 1 and scored[1][0] >= MEDIUM and top[0] - scored[1][0] < AMBIGUOUS_GAP:
        return {"persona": top[1]["id"], "score": top[0], "confidence": "ambiguous", "eligible": False,
                "reason": f"ties with {scored[1][1]['id']}: needs a human"}
    conf = "high" if top[0] >= HIGH else "medium"
    approved = bool(top[1].get("approved"))
    reason = "; ".join(top[2]) + ("" if approved else "; persona not approved yet")
    return {"persona": top[1]["id"], "score": top[0], "confidence": conf,
            "eligible": conf == "high" and approved, "reason": reason}


def load_personas(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data["personas"] if isinstance(data, dict) else data


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("contacts")
    ap.add_argument("--personas", default="automation/personas.json")
    ap.add_argument("--out")
    args = ap.parse_args(argv)
    personas = load_personas(args.personas)
    with open(args.contacts, newline="", encoding="utf-8-sig") as f:
        rows = [{(k or "").strip().lower(): v for k, v in r.items()} for r in csv.DictReader(f)]
    out = [{**r, **match(r, personas)} for r in rows]
    fields = list(out[0].keys()) if out else []
    dest = open(args.out, "w", newline="", encoding="utf-8") if args.out else sys.stdout
    w = csv.DictWriter(dest, fieldnames=fields)
    w.writeheader()
    w.writerows(out)
    if args.out:
        dest.close()
        elig = sum(1 for o in out if o["eligible"])
        print(f"{len(out)} contacts, {elig} eligible, {len(out) - elig} need review -> {args.out}")


if __name__ == "__main__":
    main()
