"""Review titles the matcher could not settle, and turn each decision into a permanent rule.

  python automation/audit_titles.py list
  python automation/audit_titles.py apply --title "Zahnarzt" --decision exclude --reason "not a US title"
  python automation/audit_titles.py apply --title "Dentist" --decision ambiguous
  python automation/audit_titles.py apply --title "Practice Principal" --decision include --persona owner-dentist --confirmed-by-user

Safety rule (asymmetric autonomy):
  exclude / ambiguous  -> make FEWER contacts eligible. The agent may apply these on its own.
  include              -> makes MORE contacts eligible. Requires --confirmed-by-user (you said yes).
Every applied decision removes the title from the queue, is written to title_rules.json, and is added as a
regression case in automation/title_regressions.json so tests fail if the mistake ever comes back.
"""
import argparse
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import match_persona as m  # noqa: E402

REGRESSIONS = os.path.join(m.HERE, "title_regressions.json")


def read_queue(path):
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def write_queue(path, items):
    with open(path, "w", encoding="utf-8") as f:
        for it in items:
            f.write(json.dumps(it) + "\n")


def load_json(path, default):
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def cmd_list(args):
    items = read_queue(args.queue)
    if not items:
        print("Review queue is empty.")
        return 0
    for i, it in enumerate(items, 1):
        print(f"{i}. '{it['title']}' | industry={it['industry']!r} size={it['employees']!r} | "
              f"flags={it['flags']} | candidate={it['candidate_persona'] or '-'} | {it['reason']}")
    return 0


def cmd_apply(args):
    decision = args.decision
    if decision == "include" and not args.confirmed_by_user:
        print("REFUSED: 'include' makes more contacts eligible. Ask the user, then re-run with --confirmed-by-user.")
        return 2
    if decision == "include" and not args.persona:
        print("REFUSED: --persona is required for include.")
        return 2
    nt = m.norm(args.title)
    if not nt:
        print("REFUSED: empty title.")
        return 2
    rules = m.load_rules(args.rules)
    if decision == "exclude":
        if nt not in rules["global_exclude"]:
            rules["global_exclude"].append(nt)
    elif decision == "ambiguous":
        if nt not in rules["ambiguous"]:
            rules["ambiguous"].append(nt)
    else:
        rules["include"].setdefault(args.persona, [])
        if nt not in rules["include"][args.persona]:
            rules["include"][args.persona].append(nt)
    rules["decisions"].append({"title": args.title, "decision": decision, "persona": args.persona or "",
                               "reason": args.reason or "", "date": datetime.date.today().isoformat(),
                               "confirmed_by_user": bool(args.confirmed_by_user)})
    save_json(args.rules, rules)

    queue = read_queue(args.queue)
    ctx = next((q for q in queue if q["norm_title"] == nt), {})
    write_queue(args.queue, [q for q in queue if q["norm_title"] != nt])

    expect = {"exclude": "no_persona", "ambiguous": "not_eligible", "include": f"persona:{args.persona}"}[decision]
    reg = load_json(REGRESSIONS, [])
    reg.append({"title": args.title, "industry": ctx.get("industry", args.industry or ""),
                "company": ctx.get("company", ""), "employees": ctx.get("employees", args.employees or ""),
                "expect": expect})
    save_json(REGRESSIONS, reg)
    print(f"Applied '{decision}' for '{args.title}'. Rule saved, queue updated, regression case added.")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue", default=m.DEFAULT_QUEUE)
    ap.add_argument("--rules", default=m.DEFAULT_RULES)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    a = sub.add_parser("apply")
    a.add_argument("--title", required=True)
    a.add_argument("--decision", required=True, choices=["exclude", "ambiguous", "include"])
    a.add_argument("--persona")
    a.add_argument("--reason")
    a.add_argument("--industry")
    a.add_argument("--employees")
    a.add_argument("--confirmed-by-user", action="store_true")
    args = ap.parse_args(argv)
    return cmd_list(args) if args.cmd == "list" else cmd_apply(args)


if __name__ == "__main__":
    sys.exit(main())
