"""Consistency between the instructions, the references, the schemas and the scripts."""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = [ROOT / "SKILL.md", ROOT / "README.md"] + sorted((ROOT / "references").glob("*.md"))
CALL = re.compile(r"(\w+)\.py((?:[ \t]+(?:--?[\w-]+|\"[^\"]*\"|'[^']*'|`[^`]*`|[^\s|`]+))*)")


class TestDocs(unittest.TestCase):
    def test_skill_frontmatter(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        front = text.split("---")[1]
        name = re.search(r"^name:\s*(.+)$", front, re.M).group(1).strip()
        desc = re.search(r"^description:\s*(.+)$", front, re.M).group(1).strip()
        self.assertEqual(name, ROOT.name)
        self.assertRegex(name, r"^[a-z0-9-]{1,64}$")
        self.assertLessEqual(len(desc), 1024)
        self.assertNotRegex(desc, r"[<>]")
        self.assertLess(len(text.splitlines()), 500)

    def test_every_documented_flag_exists(self):
        helps = {}
        for s in (ROOT / "scripts").glob("*.py"):
            if s.name != "ledger_core.py":
                helps[s.stem] = subprocess.run([sys.executable, str(s), "--help"], capture_output=True, text=True).stdout
        checked = 0
        for doc in DOCS:
            text = re.sub(r"\\\n\s*", " ", doc.read_text(encoding="utf-8"))
            for m in (m for line in text.splitlines() for m in CALL.finditer(line)):
                if m.group(1) in helps:
                    for flag in re.findall(r"(?<![\w-])(--[a-z][\w-]*)", m.group(2)):
                        checked += 1
                        self.assertIn(flag, helps[m.group(1)], f"{doc.name}: {m.group(1)}.py {flag}")
        self.assertGreater(checked, 50)

    def test_every_validation_code_is_documented(self):
        code = (ROOT / "scripts" / "ledger_core.py").read_text(encoding="utf-8")
        gates = (ROOT / "references" / "completion-gates.md").read_text(encoding="utf-8")
        for c in sorted(set(re.findall(r'(?:err|warn)\("([A-Z]\d+)"', code))):
            prefix, num = re.match(r"([A-Z]+)(\d+)", c).groups()
            ranges = re.findall(rf"\b{prefix}(\d+)-{prefix}?(\d+)\b", gates)
            in_range = any(int(a) <= int(num) <= int(b) for a, b in ranges)
            self.assertTrue(re.search(rf"\b{c}\b", gates) or in_range, f"{c} not documented")

    def test_backticked_claim_types_and_authorities_exist(self):
        m = json.loads((ROOT / "references" / "authority-matrix.json").read_text(encoding="utf-8"))
        table = (ROOT / "references" / "verification-authority.md").read_text(encoding="utf-8").split("## Core matrix")[1]
        table = table.split("## Three")[0]
        for name in re.findall(r"`([a-z][a-z0-9-]+)`", table):
            self.assertTrue(name in m["claim_types"] or name in m["authorities"], name)

    def test_skill_lists_every_script_and_reference(self):
        text = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for s in (ROOT / "scripts").glob("*.py"):
            if s.name != "ledger_core.py":
                self.assertIn(s.name, text)
        for r in (ROOT / "references").glob("*.md"):
            self.assertIn(f"references/{r.name}", text)


if __name__ == "__main__":
    unittest.main()
