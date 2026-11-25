"""Tests for the eval grader and the case fixtures (no model is run here)."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALS = ROOT / "evals"
GRADE = EVALS / "grade.py"
SCRIPTS = ROOT / "scripts"
KINDS = {"answer_regex", "answer_not_regex", "answer_max_words", "no_ledger", "file_regex", "file_sha256",
         "command_succeeds", "ledger_min", "ledger_has", "ledger_none", "evidence_regex", "state_in"}


class TestEvals(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def workdir(self, case):
        dst = self.dir / case
        shutil.copytree(EVALS / "cases" / case, dst)
        return dst

    def grade(self, case, condition, workdir, answer):
        (workdir / "answer.md").write_text(answer, encoding="utf-8")
        proc = subprocess.run([sys.executable, str(GRADE), "--case", case, "--condition", condition,
                               "--workdir", str(workdir), "--answer", str(workdir / "answer.md")],
                              capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def test_every_case_is_well_formed(self):
        specs = sorted((EVALS / "expected").glob("*.json"))
        self.assertEqual(len(specs), 7)
        for path in specs:
            spec = json.loads(path.read_text(encoding="utf-8"))
            self.assertTrue((EVALS / spec["prompt"]).exists(), spec["prompt"])
            for check in spec["checks"]:
                self.assertIn(check["kind"], KINDS, f"{path.name}:{check['id']}")
            self.assertTrue(any("correct" in c.get("tags", []) for c in spec["checks"]), path.name)

    def test_case_01_fixture_really_has_the_bug(self):
        wd = self.workdir("case-01-ambiguous-bug")
        before = self.grade("case-01-ambiguous-bug", "baseline", wd, "It is a day/month ambiguity.")
        fix = [c for c in before["checks"] if c["id"] == "fix-works"][0]
        self.assertFalse(fix["passed"])
        src = (wd / "dates.py").read_text(encoding="utf-8")
        (wd / "dates.py").write_text(src.replace('("%m/%d/%Y", "%d/%m/%Y", "%Y-%m-%d")', '("%d/%m/%Y", "%Y-%m-%d")'),
                                     encoding="utf-8")
        after = self.grade("case-01-ambiguous-bug", "baseline", wd, "Day and month were swapped for days <= 12.")
        self.assertTrue(after["metrics"]["correct"])

    def test_simple_task_rewards_light_mode_and_flags_bureaucracy(self):
        wd = self.workdir("case-05-simple-task")
        (wd / "calc.py").write_text((wd / "calc.py").read_text(encoding="utf-8").replace("tmp", "total"), encoding="utf-8")
        good = self.grade("case-05-simple-task", "skill", wd, "Renamed `tmp` to `total`; `python calc.py` prints total: 9.75.")
        self.assertTrue(good["metrics"]["correct"])
        self.assertFalse(good["metrics"]["bureaucracy"])
        subprocess.run([sys.executable, str(SCRIPTS / "init_investigation.py"), "--ledger", str(wd / "investigation.json"),
                        "--id", "rename", "--title", "Rename", "--objective", "Rename tmp", "--mode", "investigative"],
                       check=True, capture_output=True)
        heavy = self.grade("case-05-simple-task", "skill", wd, "Renamed. " * 10)
        self.assertTrue(heavy["metrics"]["bureaucracy"])

    def test_false_conjecture_premature_proof_is_flagged(self):
        wd = self.workdir("case-04-false-conjecture")
        bad = self.grade("case-04-false-conjecture", "baseline", wd, "Yes, the claim is true; she checked up to 1000.")
        self.assertTrue(bad["metrics"]["premature_conclusion"])
        self.assertFalse(bad["metrics"]["correct"])
        good = self.grade("case-04-false-conjecture", "baseline", wd, "False: 5777 is an odd composite that is not p + 2k^2.")
        self.assertTrue(good["metrics"]["correct"])
        self.assertIsNone(good["metrics"]["process_score"])  # ledger checks do not apply to the baseline

    def test_insufficient_evidence_with_ledger(self):
        wd = self.workdir("case-06-insufficient-evidence")
        env = dict(os.environ, EDI_FIXED_TIME="2026-01-01T00:00:00Z")
        L = str(wd / "investigation.json")

        def edi(script, *args):
            subprocess.run([sys.executable, str(SCRIPTS / f"{script}.py"), "--ledger", L, *args],
                           check=True, capture_output=True, env=env)

        edi("init_investigation", "--id", "exit-137", "--title", "Exit 137", "--objective", "Find the root cause",
            "--mode", "investigative", "--limitation", "one log line")
        edi("record_hypothesis", "--kind", "primary", "--statement", "the kernel OOM killer killed it",
            "--prior-basis", "137 = SIGKILL", "--prediction", "kernel log shows an OOM kill at 03:12")
        edi("record_hypothesis", "--kind", "alternative", "--statement", "a supervisor timeout killed it",
            "--prior-basis", "schedulers send SIGKILL after a grace period", "--prediction", "scheduler log shows a timeout")
        edi("record_unknown", "--question", "What sent SIGKILL?", "--severity", "critical",
            "--required-authority", "runtime-trace")
        edi("record_obligation", "--claim", "root cause identified", "--kind", "root-cause",
            "--required-authority", "root-cause-identified")
        result = self.grade("case-06-insufficient-evidence", "skill", wd,
                            "Exit code 137 = 128 + 9: the process was killed by SIGKILL. The root cause cannot be "
                            "determined from this line; it is INCONCLUSIVE. Collect the kernel log and scheduler events.")
        self.assertEqual(result["metrics"]["computed_state"], "INCONCLUSIVE")
        self.assertTrue(result["metrics"]["correct"])
        self.assertEqual(result["metrics"]["process_score"], 1.0)

    def test_summary_table(self):
        wd = self.workdir("case-04-false-conjecture")
        r = self.grade("case-04-false-conjecture", "baseline", wd, "False: 5777.")
        out = self.dir / "r.json"
        out.write_text(json.dumps(r), encoding="utf-8")
        proc = subprocess.run([sys.executable, str(GRADE), "--summarize", str(out)], capture_output=True, text=True)
        self.assertIn("| case-04-false-conjecture | baseline |", proc.stdout)


if __name__ == "__main__":
    unittest.main()
