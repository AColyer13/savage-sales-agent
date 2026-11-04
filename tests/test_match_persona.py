import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "automation"))
import match_persona as m  # noqa: E402

P = m.load_personas(os.path.join(os.path.dirname(__file__), "..", "examples", "personas.example.json"))


def run(**c):
    return m.match(c, P)


class T(unittest.TestCase):
    def test_owner_high_but_not_eligible_until_approved(self):
        r = run(jobtitle="Owner / Dentist", industry="Dental", numberofemployees="12")
        self.assertEqual(r["persona"], "owner-dentist")
        self.assertEqual(r["confidence"], "high")
        self.assertFalse(r["eligible"])

    def test_eligible_once_approved(self):
        for p in P:
            p["approved"] = True
        try:
            r = run(jobtitle="Office Manager", industry="Dentistry", numberofemployees="9")
            self.assertTrue(r["eligible"])
        finally:
            for p in P:
                p["approved"] = False

    def test_excluded_title(self):
        r = run(jobtitle="Associate Dentist", industry="Dental", numberofemployees="8")
        self.assertEqual(r["persona"], "")
        self.assertFalse(r["eligible"])

    def test_wrong_industry_needs_human(self):
        r = run(jobtitle="VP Engineering", industry="Software", numberofemployees="200")
        self.assertFalse(r["eligible"])
        self.assertEqual(r["persona"], "")

    def test_missing_title(self):
        self.assertFalse(run(jobtitle="", industry="Dental")["eligible"])

    def test_too_large_company_not_high(self):
        r = run(jobtitle="Practice Manager", industry="Dental", numberofemployees="300")
        self.assertNotEqual(r["confidence"], "high")

    def test_deterministic(self):
        c = dict(jobtitle="Owner", industry="Dental", numberofemployees="10")
        self.assertEqual(run(**c), run(**c))


if __name__ == "__main__":
    unittest.main()
