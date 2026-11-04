import csv
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "automation"))
import export_drafts as ed  # noqa: E402

GOOD = "Hi Ann,\nNoticed the new location.\nOpen to hearing how others handled it?\nNot relevant? Just reply and I will not email again."


class ExportDrafts(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.csv = os.path.join(self.dir, "matched.csv")
        with open(self.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["email", "persona", "eligible"])
            w.writerow(["ok@x.com", "owner", "True"])
            w.writerow(["no@x.com", "owner", "False"])

    def tearDown(self):
        self.tmp.cleanup()

    def run_export(self, drafts):
        p = os.path.join(self.dir, "d.json")
        with open(p, "w", encoding="utf-8") as f:
            json.dump(drafts, f)
        return ed.export(self.csv, p, os.path.join(self.dir, "out"))

    def test_good_draft_written_unsent(self):
        log, refused = self.run_export([{"email": "ok@x.com", "subject": "second location", "body": GOOD}])
        self.assertEqual((len(log), len(refused)), (1, 0))
        with open(os.path.join(self.dir, "out", log[0]["file"]), encoding="utf-8") as fh:
            eml = fh.read()
        self.assertIn("X-Unsent: 1", eml)
        self.assertEqual(log[0]["status"], "drafted_not_sent")

    def test_ineligible_refused(self):
        _, refused = self.run_export([{"email": "no@x.com", "subject": "s", "body": GOOD},
                                      {"email": "ghost@x.com", "subject": "s", "body": GOOD}])
        self.assertEqual(len(refused), 2)

    def test_placeholder_refused(self):
        _, refused = self.run_export([{"email": "ok@x.com", "subject": "s", "body": GOOD + " [ADD METRIC: x]"}])
        self.assertTrue(any("placeholder" in p for p in refused[0][1]))

    def test_missing_opt_out_refused(self):
        _, refused = self.run_export([{"email": "ok@x.com", "subject": "s", "body": "Hi, quick question?"}])
        self.assertTrue(any("opt-out" in p for p in refused[0][1]))

    def test_newline_subject_and_empty_refused(self):
        _, refused = self.run_export([{"email": "ok@x.com", "subject": "a\nBcc: z@z.com", "body": GOOD},
                                      {"email": "ok@x.com", "subject": "", "body": ""}])
        self.assertEqual(len(refused), 2)

    def test_module_cannot_send(self):
        with open(os.path.join(ROOT, "automation", "export_drafts.py"), encoding="utf-8") as fh:
            src = fh.read()
        for word in ("smtplib", "requests", "urllib", "socket"):
            self.assertNotIn("import " + word, src)


if __name__ == "__main__":
    unittest.main()
