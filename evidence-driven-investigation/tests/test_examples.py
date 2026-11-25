"""Golden test: every example rebuilds byte-for-byte from its build_example.py.

This proves the committed example outputs are real script output, and that the
scripts are deterministic given EDI_FIXED_TIME.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXAMPLES = ["software-debugging", "reverse-engineering", "mathematical-investigation", "data-analysis"]
GENERATED = ["investigation.json", "completion.json", "report.md", "report-rigorous.md"]


def files(folder: Path):
    out = {name: folder / name for name in GENERATED if (folder / name).exists()}
    for p in sorted((folder / "outputs").glob("*")):
        out[f"outputs/{p.name}"] = p
    return out


class TestExamples(unittest.TestCase):
    def test_examples_rebuild_identically(self):
        for name in EXAMPLES:
            with self.subTest(example=name), tempfile.TemporaryDirectory() as tmp:
                src = ROOT / "examples" / name
                dst = Path(tmp) / name
                proc = subprocess.run([sys.executable, str(src / "build_example.py"), str(dst)],
                                      capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                committed, rebuilt = files(src), files(dst)
                self.assertEqual(sorted(committed), sorted(rebuilt))
                for rel in committed:
                    self.assertEqual(committed[rel].read_bytes(), rebuilt[rel].read_bytes(), f"{name}/{rel} differs")

    def test_example_states(self):
        expected = {"software-debugging": "COMPLETE_VERIFIED", "reverse-engineering": "COMPLETE_VERIFIED",
                    "mathematical-investigation": "COMPLETE_WITH_LIMITATIONS",
                    "data-analysis": "COMPLETE_WITH_LIMITATIONS"}
        for name, state in expected.items():
            text = (ROOT / "examples" / name / "completion.json").read_text(encoding="utf-8")
            self.assertIn(f'"state": "{state}"', text, name)


if __name__ == "__main__":
    unittest.main()
