import csv
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "automation"))
import outreach_state as st  # noqa: E402
import export_drafts as ed  # noqa: E402
import match_persona as mp  # noqa: E402

GOOD = "Hi,\nQuick idea.\nSource: https://example.com/x\nNot useful? Reply and I won't email you again."


class State(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.sup = os.path.join(self.d, "sup.csv")
        self.out = os.path.join(self.d, "out.csv")

    def tearDown(self):
        self.tmp.cleanup()

    def test_suppress_email_and_domain_case_insensitive(self):
        self.assertTrue(st.suppress("Ann@X.com", "stop", self.sup).startswith("Suppressed"))
        self.assertIn("already", st.suppress("ann@x.com", "", self.sup))
        st.suppress("@bigcorp.com", "company asked", self.sup)
        rows = st.load_suppression(self.sup)
        self.assertTrue(st.is_suppressed("ANN@x.com", rows))
        self.assertTrue(st.is_suppressed("anyone@BigCorp.com", rows))
        self.assertIsNone(st.is_suppressed("bob@other.com", rows))

    def test_bad_targets_refused(self):
        for bad in ("not-an-email", "@", "a b@x.com", ""):
            self.assertTrue(st.suppress(bad, "", self.sup).startswith("REFUSED"), bad)

    def test_unsuppress_needs_user(self):
        st.suppress("a@x.com", "", self.sup)
        self.assertTrue(st.unsuppress("a@x.com", False, self.sup).startswith("REFUSED"))
        self.assertTrue(st.is_suppressed("a@x.com", st.load_suppression(self.sup)))
        st.unsuppress("a@x.com", True, self.sup)
        self.assertFalse(st.load_suppression(self.sup))

    def test_unsubscribe_bounce_notinterested_auto_suppress(self):
        for i, o in enumerate(("unsubscribed", "bounced-hard", "not-interested")):
            st.mark(f"u{i}@x.com", o, sup_path=self.sup, out_path=self.out)
            self.assertTrue(st.is_suppressed(f"u{i}@x.com", st.load_suppression(self.sup)), o)
        st.mark("soft@x.com", "bounced-soft", sup_path=self.sup, out_path=self.out)
        self.assertFalse(st.is_suppressed("soft@x.com", st.load_suppression(self.sup)))

    def test_reply_blocks_until_user_confirms(self):
        st.mark("r@x.com", "replied", sup_path=self.sup, out_path=self.out)
        sup, out = st.load_suppression(self.sup), st.load_outcomes(self.out)
        self.assertIn("follow up personally", st.blocked_reason("r@x.com", sup, out))
        self.assertTrue(st.mark("r@x.com", "sent", sup_path=self.sup, out_path=self.out).startswith("REFUSED"))
        st.mark("r@x.com", "sent", confirmed=True, sup_path=self.sup, out_path=self.out)
        self.assertIsNone(st.blocked_reason("r@x.com", sup, st.load_outcomes(self.out)))

    def test_invalid_outcome_refused(self):
        self.assertTrue(st.mark("a@x.com", "ghosted", sup_path=self.sup, out_path=self.out).startswith("REFUSED"))

    def test_export_drafts_refuses_blocked_contacts(self):
        matched = os.path.join(self.d, "m.csv")
        with open(matched, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["email", "persona", "eligible"])
            for e in ("ok@x.com", "stop@x.com", "rep@x.com", "any@bigcorp.com"):
                w.writerow([e, "owner", "True"])
        st.suppress("stop@x.com", "asked", self.sup)
        st.suppress("@bigcorp.com", "company", self.sup)
        st.mark("rep@x.com", "replied", sup_path=self.sup, out_path=self.out)
        drafts = os.path.join(self.d, "d.json")
        with open(drafts, "w", encoding="utf-8") as f:
            json.dump([{"email": e, "subject": "s", "body": GOOD} for e in ("ok@x.com", "stop@x.com", "rep@x.com", "any@bigcorp.com")], f)
        log, refused = ed.export(matched, drafts, os.path.join(self.d, "o"), sup_path=self.sup, out_path=self.out)
        self.assertEqual([l["email"] for l in log], ["ok@x.com"])
        self.assertEqual(len(refused), 3)
        self.assertTrue(all(any("blocked" in p for p in r[1]) for r in refused))

    def test_matcher_marks_blocked_not_eligible(self):
        st.suppress("a@x.com", "asked", self.sup)
        old = (st.SUPPRESSION, st.OUTCOMES)
        st.SUPPRESSION, st.OUTCOMES = self.sup, self.out
        try:
            outp = os.path.join(self.d, "m.csv")
            personas = os.path.join(ROOT, "examples", "personas.example.json")
            with open(personas, encoding="utf-8") as f:
                data = json.load(f)
            for p in (data["personas"] if isinstance(data, dict) else data):
                p["approved"] = True
            pj = os.path.join(self.d, "p.json")
            with open(pj, "w", encoding="utf-8") as f:
                json.dump(data, f)
            mp.main([os.path.join(ROOT, "tests", "contacts.sample.csv"), "--personas", pj, "--no-queue", "--out", outp])
            with open(outp, newline="", encoding="utf-8") as f:
                rows = {r["email"]: r for r in csv.DictReader(f)}
            self.assertEqual(rows["a@x.com"]["eligible"], "False")
            self.assertIn("blocked", rows["a@x.com"]["flags"])
            self.assertEqual(rows["b@x.com"]["eligible"], "True")
        finally:
            st.SUPPRESSION, st.OUTCOMES = old

    def test_module_makes_no_network_calls(self):
        with open(os.path.join(ROOT, "automation", "outreach_state.py"), encoding="utf-8") as fh:
            src = fh.read()
        for w in ("requests", "urllib", "socket", "smtplib"):
            self.assertNotIn("import " + w, src)


if __name__ == "__main__":
    unittest.main()
