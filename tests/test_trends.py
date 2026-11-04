import datetime
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "automation"))
import trends as t  # noqa: E402

GOOD = dict(claim="Short plain-text emails get more replies than designed ones.", source_name="Example Blog",
            url="https://example.com/post", published="2026-10-01", kind="expert-opinion")


class Trends(unittest.TestCase):
    def test_add_and_dedupe(self):
        es = []
        e, msg = t.add(es, **GOOD)
        self.assertEqual(e["status"], "new")
        e2, msg2 = t.add(es, **GOOD)
        self.assertIsNone(e2)
        self.assertEqual(len(es), 1)

    def test_refuses_bad_input(self):
        for bad in (dict(url="not a url"), dict(published="last week"), dict(published="2999-01-01"),
                    dict(kind="rumor"), dict(claim=""), dict(claim="x" * 301), dict(source_name=" ")):
            e, msg = t.add([], **{**GOOD, **bad})
            self.assertIsNone(e, bad)
            self.assertTrue(msg.startswith("REFUSED"))

    def test_adopt_needs_user_confirmation(self):
        es = []
        e, _ = t.add(es, **GOOD)
        self.assertTrue(t.decide(es, e["id"], "adopt").startswith("REFUSED"))
        self.assertEqual(es[0]["status"], "new")
        t.decide(es, e["id"], "adopt", confirmed=True)
        self.assertEqual(es[0]["status"], "adopted")

    def test_reject_needs_no_confirmation(self):
        es = []
        e, _ = t.add(es, **GOOD)
        t.decide(es, e["id"], "reject")
        self.assertEqual(es[0]["status"], "rejected")

    def test_unknown_id(self):
        self.assertTrue(t.decide([], "nope", "reject").startswith("REFUSED"))

    def test_render_only_adopted_with_sources(self):
        es = []
        a, _ = t.add(es, **GOOD, applies=["outreach"])
        b, _ = t.add(es, **{**GOOD, "claim": "Other claim.", "url": "https://example.com/b"})
        t.decide(es, a["id"], "adopt", confirmed=True)
        out = t.render(es)
        self.assertIn("https://example.com/post", out)
        self.assertIn("## outreach", out)
        self.assertNotIn("Other claim", out)

    def test_render_empty_and_stale(self):
        self.assertIn("No adopted trends yet", t.render([]))
        es = []
        e, _ = t.add(es, **{**GOOD, "published": "2020-01-01"})
        t.decide(es, e["id"], "adopt", confirmed=True)
        self.assertIn("STALE", t.render(es))

    def test_vendor_claim_marked_directional(self):
        es = []
        e, _ = t.add(es, **{**GOOD, "kind": "vendor-claim"})
        t.decide(es, e["id"], "adopt", confirmed=True)
        self.assertIn("directional", es[0]["notes"])

    def test_save_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x", "trends.json")
            es = []
            t.add(es, **GOOD)
            t.save(es, p)
            self.assertEqual(t.load(p), es)
            self.assertEqual(t.load(os.path.join(d, "missing.json")), [])

    def test_stale_boundary(self):
        e = {"published": (datetime.date.today() - datetime.timedelta(days=t.STALE_DAYS)).isoformat()}
        self.assertFalse(t.is_stale(e))
        e = {"published": (datetime.date.today() - datetime.timedelta(days=t.STALE_DAYS + 1)).isoformat()}
        self.assertTrue(t.is_stale(e))

    def test_module_makes_no_network_calls(self):
        with open(os.path.join(ROOT, "automation", "trends.py"), encoding="utf-8") as fh:
            src = fh.read()
        for w in ("requests", "urllib", "socket", "http.client"):
            self.assertNotIn("import " + w, src)


if __name__ == "__main__":
    unittest.main()
