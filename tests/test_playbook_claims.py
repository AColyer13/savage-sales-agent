"""Guard the 'never invent proof' rule: templates in supplement playbooks may not contain
literal numbers, percentages or peer claims. Only [ADD ...] placeholders are allowed."""
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PLAYBOOK = os.path.join(ROOT, "playbook", "12-supplement-cold-email-craft.md")


def template_blocks(text):
    return re.findall(r"```\n(.*?)```", text, flags=re.S)


class TemplateClaims(unittest.TestCase):
    def test_templates_exist(self):
        with open(PLAYBOOK, encoding="utf-8") as f:
            self.assertGreaterEqual(len(template_blocks(f.read())), 3)

    def test_no_literal_numbers_in_templates(self):
        with open(PLAYBOOK, encoding="utf-8") as f:
            blocks = template_blocks(f.read())
        for b in blocks:
            stripped = re.sub(r"\[[^\]]*\]", "", b)  # placeholders may hold anything
            self.assertIsNone(re.search(r"\d", stripped), f"literal number in template:\n{b}")
            self.assertIsNone(re.search(r"\b(\d+x|percent)\b", stripped, re.I))

    def test_every_template_has_placeholders(self):
        with open(PLAYBOOK, encoding="utf-8") as f:
            for b in template_blocks(f.read()):
                self.assertIn("[ADD", b)


if __name__ == "__main__":
    unittest.main()
