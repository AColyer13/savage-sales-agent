import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(__file__)
sys.path.insert(0, os.path.join(HERE, "..", "automation"))
import audit_titles as a  # noqa: E402
import match_persona as m  # noqa: E402

EXAMPLE = os.path.join(HERE, "..", "examples", "personas.example.json")
NO_RULES = {"global_exclude": [], "ambiguous": [], "include": {}, "decisions": []}


def personas(approved=False):
    ps = m.load_personas(EXAMPLE)
    for p in ps:
        p["approved"] = approved
    return ps


def run(approved=True, rules=None, **c):
    c.setdefault("email", "x@y.com")
    return m.match(c, personas(approved), rules if rules is not None else NO_RULES)


D = dict(industry="Dental", numberofemployees="12")

# (title, kwargs overrides, expected persona, expected eligible). Each row is a written-down edge case.
CASES = [
    # --- clear matches
    ("Owner / Dentist", {}, "owner-dentist", True),
    ("Practice Owner", {}, "owner-dentist", True),
    ("Office Manager", {}, "office-manager", True),
    ("OFFICE MANAGER", {}, "office-manager", True),                       # caps
    ("Dentist & Owner", {}, "owner-dentist", True),                       # ampersand
    ("Owner, Dr. Kim DDS", {}, "owner-dentist", True),
    ("Office Mgr", {}, "office-manager", True),                           # abbreviation
    ("Practice Mgr.", {}, "office-manager", True),
    # --- bare credential: owner or associate? must never be auto-eligible
    ("Dentist", {}, "owner-dentist", False),
    ("DDS", {}, "owner-dentist", False),
    ("D.D.S.", {}, "owner-dentist", False),
    ("DMD", {}, "owner-dentist", False),
    ("Dr. Kim, DDS", {}, "owner-dentist", False),
    ("General Dentist", {}, "owner-dentist", False),
    ("Doctor", {}, "", False),
    # --- not a buyer role at all
    ("Associate Dentist", {}, "", False),
    ("Dental Assistant", {}, "", False),
    ("Dental Hygienist", {}, "", False),
    ("Dental Sales Representative", {}, "", False),                       # vendor at a dental company
    ("Dental Supply Rep", {}, "", False),
    ("Dental Practice Consultant", {}, "", False),
    ("Dental Student", {}, "", False),
    ("Intern", {}, "", False),
    ("Former Owner", {}, "", False),                                       # stale
    ("Ex-Owner", {}, "", False),
    ("Retired Dentist", {}, "", False),
    ("Executive Assistant to the Owner", {}, "", False),
    ("Assistant Office Manager", {}, "", False),
    ("Dentistry Recruiter", {}, "", False),                                # substring trap: dentist in dentistry
    # --- missing or junk
    ("", {}, "", False),
    ("N/A", {}, "", False),
    ("-", {}, "", False),
    # --- wrong company
    ("Owner", dict(industry="Software", numberofemployees="12"), "", False),   # owner of the wrong industry
    ("VP Engineering", dict(industry="Software", numberofemployees="200"), "", False),
    ("Owner", dict(industry=""), "owner-dentist", False),                  # industry unknown: human
    ("Owner", dict(industry="", company="Bright Dental Care"), "owner-dentist", True),  # company name rescues
    # --- size
    ("Practice Manager", dict(numberofemployees="300"), "office-manager", False),
    ("Owner", dict(numberofemployees="1"), "owner-dentist", False),       # solo, below range
    # --- unicode / typos / bad data
    ("Ofice Manager", {}, "office-manager", False),                        # typo: fuzzy, human
    ("Office Manager ", {}, "office-manager", True),                       # whitespace
    ("Officé Manager", {}, "office-manager", True),                        # accent
    ("Zahnarzt", {}, "", False),                                           # foreign-language title
]


class Edge(unittest.TestCase):
    def test_table(self):
        for title, over, persona, eligible in CASES:
            c = {**D, **over, "jobtitle": title}
            r = run(**c)
            with self.subTest(title=title, **over):
                self.assertEqual(r["persona"], persona, r)
                self.assertEqual(r["eligible"], eligible, r)

    def test_unapproved_persona_never_eligible(self):
        r = run(approved=False, jobtitle="Owner / Dentist", **D)
        self.assertEqual(r["confidence"], "high")
        self.assertFalse(r["eligible"])

    def test_invalid_email_never_eligible(self):
        for bad in ["", "not-an-email", "a@b"]:
            r = run(jobtitle="Owner", email=bad, **D)
            self.assertFalse(r["eligible"], bad)

    def test_deterministic(self):
        c = dict(jobtitle="Owner", **D)
        self.assertEqual(run(**c), run(**c))

    def test_credential_only_triggers_audit(self):
        self.assertTrue(run(jobtitle="Dentist", **D)["audit_needed"])
        self.assertTrue(run(jobtitle="Ofice Manager", **D)["audit_needed"])

    def test_clear_cases_and_known_exclusions_do_not_audit(self):
        self.assertFalse(run(jobtitle="Owner / Dentist", **D)["audit_needed"])
        self.assertFalse(run(jobtitle="Dental Sales Representative", **D)["audit_needed"])
        self.assertFalse(run(jobtitle="", **D)["audit_needed"])

    def test_unknown_title_triggers_audit(self):
        self.assertTrue(run(jobtitle="Zahnarzt", **D)["audit_needed"])


class SelfCorrection(unittest.TestCase):
    def setUp(self):
        d = tempfile.mkdtemp()
        self.queue = os.path.join(d, "q.jsonl")
        self.rules = os.path.join(d, "rules.json")
        a.REGRESSIONS = os.path.join(d, "reg.json")
        self.contact = dict(jobtitle="Zahnarzt", email="z@y.com", **D)

    def test_queue_dedupes(self):
        r = run(**self.contact)
        self.assertTrue(m.queue_for_audit(self.contact, r, self.queue))
        self.assertFalse(m.queue_for_audit(self.contact, r, self.queue))

    def test_exclude_decision_is_permanent_and_regression_recorded(self):
        m.queue_for_audit(self.contact, run(**self.contact), self.queue)
        code = a.main(["--queue", self.queue, "--rules", self.rules, "apply", "--title", "Zahnarzt",
                       "--decision", "exclude", "--reason", "non-US title"])
        self.assertEqual(code, 0)
        rules = m.load_rules(self.rules)
        self.assertIn("zahnarzt", rules["global_exclude"])
        self.assertEqual(a.read_queue(self.queue), [])
        self.assertEqual(a.load_json(a.REGRESSIONS, [])[0]["expect"], "no_persona")
        self.assertEqual(run(rules=rules, **self.contact)["persona"], "")
        self.assertFalse(run(rules=rules, **self.contact)["audit_needed"])

    def test_ambiguous_decision_caps_and_stops_requeue(self):
        c = dict(jobtitle="Principal Doctor", email="p@y.com", **D)
        a.main(["--queue", self.queue, "--rules", self.rules, "apply", "--title", "Principal Doctor",
                "--decision", "ambiguous"])
        r = run(rules=m.load_rules(self.rules), **c)
        self.assertFalse(r["eligible"])

    def test_include_requires_user_confirmation(self):
        args = ["--queue", self.queue, "--rules", self.rules, "apply", "--title", "Practice Principal",
                "--decision", "include", "--persona", "owner-dentist"]
        self.assertEqual(a.main(args), 2)                    # refused without confirmation
        self.assertFalse(os.path.exists(self.rules))
        self.assertEqual(a.main(args + ["--confirmed-by-user"]), 0)
        r = run(rules=m.load_rules(self.rules), jobtitle="Practice Principal", **D)
        self.assertEqual(r["persona"], "owner-dentist")

    def test_include_requires_persona(self):
        code = a.main(["--queue", self.queue, "--rules", self.rules, "apply", "--title", "X",
                       "--decision", "include", "--confirmed-by-user"])
        self.assertEqual(code, 2)


class Regressions(unittest.TestCase):
    """Replays every past audit decision so a fixed mistake can never come back."""

    def test_replay(self):
        path = os.path.join(HERE, "..", "automation", "title_regressions.json")
        rules_path = os.path.join(HERE, "..", "automation", "title_rules.json")
        if not (os.path.exists(path) and os.path.exists(rules_path)):
            self.skipTest("no audit decisions yet")
        rules = m.load_rules(rules_path)
        for case in a.load_json(path, []):
            c = {"jobtitle": case["title"], "industry": case["industry"], "company": case["company"],
                 "numberofemployees": case["employees"], "email": "x@y.com"}
            r = m.match(c, personas(True), rules)
            with self.subTest(title=case["title"]):
                if case["expect"] == "no_persona":
                    self.assertEqual(r["persona"], "")
                elif case["expect"] == "not_eligible":
                    self.assertFalse(r["eligible"])
                else:
                    self.assertEqual(r["persona"], case["expect"].split(":", 1)[1])


if __name__ == "__main__":
    unittest.main()
