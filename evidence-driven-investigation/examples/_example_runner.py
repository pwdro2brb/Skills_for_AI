"""Helper shared by the example builders. Not part of the skill's runtime.

Each example's build_example.py drives the public scripts exactly as an agent
would, runs real probes with the current Python, captures their output to
files and records the results. With EDI_FIXED_TIME set, the outputs are
byte-identical across runs and platforms (tests/test_examples.py checks this).
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).resolve().parent.parent
SCRIPTS = SKILL / "scripts"
FIXED_TIME = "2026-11-25T12:00:00Z"
GENERATED = ["investigation.json", "completion.json", "report.md", "report-rigorous.md", "outputs", "work"]


def write_lf(path: Path, text: str) -> None:
    """Write UTF-8 with LF line endings on every platform (Path.write_text lacks newline= before 3.10)."""
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


class Example:
    def __init__(self, folder: Path, workdir: Path = None):
        self.src = Path(folder).resolve()
        self.dir = Path(workdir).resolve() if workdir else self.src
        if self.dir != self.src:
            if self.dir.exists():
                shutil.rmtree(self.dir)
            shutil.copytree(self.src, self.dir, ignore=shutil.ignore_patterns(*GENERATED, "__pycache__"))
        for name in GENERATED:
            target = self.dir / name
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        (self.dir / "outputs").mkdir()
        self.env = dict(os.environ, EDI_FIXED_TIME=FIXED_TIME, PYTHONHASHSEED="0", PYTHONIOENCODING="utf-8")
        self.ledger = "investigation.json"

    def edi(self, script: str, *args: str) -> str:
        """Run a skill script; fail loudly if it refuses."""
        cmd = [sys.executable, str(SCRIPTS / f"{script}.py"), "--ledger", self.ledger, *map(str, args)]
        proc = subprocess.run(cmd, cwd=self.dir, env=self.env, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0:
            raise SystemExit(f"{script} {' '.join(map(str, args))}\n{proc.stdout}{proc.stderr}")
        return proc.stdout.strip()

    def edi_expect_refusal(self, script: str, *args: str) -> str:
        """Run a skill script that SHOULD refuse; return its message (the examples show these)."""
        cmd = [sys.executable, str(SCRIPTS / f"{script}.py"), "--ledger", self.ledger, *map(str, args)]
        proc = subprocess.run(cmd, cwd=self.dir, env=self.env, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode == 0:
            raise SystemExit(f"expected a refusal from {script} {args}")
        return proc.stderr.strip()

    def probe(self, name: str, *args: str) -> str:
        """Run a probe program with the current Python; save stdout+stderr to outputs/<name>.txt."""
        out = self.dir / "outputs" / f"{name}.txt"
        proc = subprocess.run([sys.executable, *args], cwd=self.dir, env=self.env,
                              capture_output=True, text=True, encoding="utf-8")
        text = proc.stdout + proc.stderr
        write_lf(out, text)
        return f"outputs/{name}.txt"

    def read(self, rel: str) -> str:
        return (self.dir / rel).read_text(encoding="utf-8")

    def finish(self, rigorous: bool = False) -> str:
        state = self.edi("evaluate_completion", "--out", "completion.json")
        self.edi("generate_report", "--out", "report.md")
        if rigorous:
            self.edi("generate_report", "--format", "rigorous", "--out", "report-rigorous.md")
        self.edi("validate_ledger")
        return state.splitlines()[0]
