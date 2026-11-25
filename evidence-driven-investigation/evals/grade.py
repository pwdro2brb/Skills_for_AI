#!/usr/bin/env python3
"""Deterministic grader for the evidence-driven-investigation evals.

Grades one finished run (an agent's working folder plus its final answer)
against evals/expected/<case>.json, and summarizes many graded runs.

  python evals/grade.py --case case-04-false-conjecture --condition skill \
      --workdir runs/case-04/skill-1 --answer runs/case-04/skill-1/answer.md \
      --run-stats runs/case-04/skill-1/stats.json --out results/case-04-skill-1.json

  python evals/grade.py --summarize results/*.json > results/summary.md

Conditions: "skill" (agent had the skill) or "baseline" (no skill). Ledger checks
apply only to the skill condition; answer and file checks apply to both.
--run-stats is an optional JSON {"tokens": int, "tool_calls": int, "seconds": float}
recorded by your harness; the grader only passes it through.
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
sys.path.insert(0, str(EVALS.parent / "scripts"))
import ledger_core as core  # noqa: E402

LEDGER_KINDS = {"ledger_min", "ledger_has", "ledger_none", "evidence_regex", "state_in"}
AUTHORITY_CODES = {"E02", "E03", "H03", "U01", "O02", "O07", "F07"}


def find_ledgers(workdir: Path):
    return sorted((p for p in workdir.rglob("investigation.json")), key=lambda p: (len(p.parts), str(p)))


def matches(rec, where):
    return all(rec.get(k) == v for k, v in where.items())


def run_check(check, ctx):
    kind = check["kind"]
    answer, ledger, workdir = ctx["answer"], ctx["ledger"], ctx["workdir"]
    if kind in LEDGER_KINDS and ctx["condition"] != "skill":
        return None, "not applicable without the skill"
    if kind in LEDGER_KINDS and ledger is None:
        return False, "no ledger found"
    if kind == "answer_regex":
        ok = re.search(check["pattern"], answer) is not None
        return ok, "" if ok else f"answer lacks /{check['pattern']}/"
    if kind == "answer_not_regex":
        m = re.search(check["pattern"], answer)
        return m is None, "" if m is None else f"answer contains {m.group(0)!r}"
    if kind == "answer_max_words":
        n = len(answer.split())
        return n <= check["max"], f"{n} words"
    if kind == "no_ledger":
        found = find_ledgers(workdir)
        return not found, "" if not found else f"ledger created: {found[0]}"
    if kind == "file_regex":
        text = (workdir / check["path"]).read_text(encoding="utf-8") if (workdir / check["path"]).exists() else ""
        ok = re.search(check["pattern"], text) is not None and not (check.get("absent") and re.search(check["absent"], text))
        return ok, "" if ok else "file content does not match"
    if kind == "file_sha256":
        want = check["sha256"]
        if want == "@fixture":
            want = hashlib.sha256((ctx["case_dir"] / check["path"]).read_bytes()).hexdigest()
        p = workdir / check["path"]
        got = hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "missing"
        return got == want, "" if got == want else "original file was modified or removed"
    if kind == "command_succeeds":
        cmd = [sys.executable if c == "python" else c for c in check["command"]]
        try:
            proc = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired:
            return False, "timeout"
        ok = proc.returncode == 0 and (not check.get("stdout_regex") or re.search(check["stdout_regex"], proc.stdout))
        return bool(ok), "" if ok else f"exit {proc.returncode}: {(proc.stdout + proc.stderr)[-200:]}"
    if kind == "ledger_min":
        n = sum(1 for r in ledger.get(check["collection"], []) if matches(r, check.get("where", {})))
        return n >= check["min"], f"{n} found"
    if kind == "ledger_has":
        ok = any(matches(r, check.get("where", {})) for r in ledger.get(check["collection"], []))
        return ok, "" if ok else "no matching record"
    if kind == "ledger_none":
        hits = [r["id"] for r in ledger.get(check["collection"], []) if matches(r, check.get("where", {}))]
        return not hits, "" if not hits else f"forbidden records {hits}"
    if kind == "evidence_regex":
        ok = any(re.search(check["pattern"], e.get("claim", "")) for e in ledger.get("evidence", []))
        return ok, "" if ok else "no evidence mentions it"
    if kind == "state_in":
        if ctx["state"] is None:
            return False, f"state not computable: {ctx['state_error']}"
        return ctx["state"] in ctx["spec"]["allowed_states"], ctx["state"]
    raise SystemExit(f"unknown check kind {kind}")


def grade(args):
    spec = json.loads((EVALS / "expected" / f"{args.case}.json").read_text(encoding="utf-8"))
    workdir = Path(args.workdir).resolve()
    answer = Path(args.answer).read_text(encoding="utf-8") if args.answer else ""
    ledgers = [Path(args.ledger)] if args.ledger else find_ledgers(workdir)
    ledger = state = state_error = None
    issues = []
    if ledgers:
        ledger = json.loads(ledgers[0].read_text(encoding="utf-8"))
        issues = core.validate(ledger)
        try:
            state = core.evaluate(ledger, _issues=issues)["state"]
        except core.LedgerError as exc:
            state_error = str(exc).splitlines()[0]
    ctx = {"answer": answer, "ledger": ledger, "workdir": workdir, "condition": args.condition, "spec": spec,
           "state": state, "state_error": state_error, "case_dir": EVALS / "cases" / args.case}
    results = []
    for check in spec["checks"]:
        ok, detail = run_check(check, ctx)
        results.append({"id": check["id"], "kind": check["kind"], "tags": check.get("tags", []),
                        "passed": ok, "detail": detail})

    def tagged(tag):
        return [r for r in results if tag in r["tags"] and r["passed"] is not None]

    errors = [i for i in issues if i.level == "error"]
    stats = json.loads(Path(args.run_stats).read_text(encoding="utf-8")) if args.run_stats else {}
    applicable = [r for r in results if r["passed"] is not None]
    return {
        "case": args.case, "condition": args.condition, "run": args.run or workdir.name,
        "checks": results,
        "metrics": {
            "correct": all(r["passed"] for r in tagged("correct")),
            "premature_conclusion": any(not r["passed"] for r in tagged("premature")),
            "counterexample_found": (all(r["passed"] for r in tagged("counterexample")) if tagged("counterexample") else None),
            "bureaucracy": (any(not r["passed"] for r in tagged("bureaucracy")) if tagged("bureaucracy") else None),
            "process_score": (sum(r["passed"] for r in tagged("process")) / len(tagged("process")) if tagged("process") else None),
            "unknowns_recorded": len(ledger.get("unknowns", [])) if ledger else None,
            "ledger_errors": len(errors) if ledger else None,
            "authority_mismatches": sum(1 for i in errors if i.code in AUTHORITY_CODES) if ledger else None,
            "computed_state": state,
            "checks_passed": f"{sum(bool(r['passed']) for r in applicable)}/{len(applicable)}",
            "tokens": stats.get("tokens"), "tool_calls": stats.get("tool_calls"), "seconds": stats.get("seconds"),
        },
    }


def summarize(paths):
    rows = [json.loads(Path(p).read_text(encoding="utf-8")) for p in paths]
    cols = ["correct", "premature_conclusion", "process_score", "counterexample_found", "bureaucracy",
            "computed_state", "checks_passed", "tokens", "tool_calls", "seconds"]
    out = ["| case | condition | run | " + " | ".join(cols) + " |", "|" + "---|" * (len(cols) + 3)]
    for r in sorted(rows, key=lambda r: (r["case"], r["condition"], r["run"])):
        m = r["metrics"]
        cells = ["—" if m[c] is None else (f"{m[c]:.2f}" if isinstance(m[c], float) else str(m[c])) for c in cols]
        out.append(f"| {r['case']} | {r['condition']} | {r['run']} | " + " | ".join(cells) + " |")
    by = {}
    for r in rows:
        by.setdefault(r["condition"], []).append(r["metrics"])
    out.append("")
    for cond, ms in sorted(by.items()):
        n = len(ms)
        out.append(f"- **{cond}**: {n} runs, correct {sum(m['correct'] for m in ms)}/{n}, "
                   f"premature conclusions {sum(m['premature_conclusion'] for m in ms)}/{n}")
    return "\n".join(out) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--case")
    p.add_argument("--condition", choices=["skill", "baseline"])
    p.add_argument("--workdir")
    p.add_argument("--answer", help="File with the agent's final answer")
    p.add_argument("--ledger", help="Ledger path (default: search the workdir)")
    p.add_argument("--run", help="Run label (default: workdir name)")
    p.add_argument("--run-stats", help="JSON with tokens, tool_calls, seconds")
    p.add_argument("--out", help="Write the result JSON here (refuses to overwrite)")
    p.add_argument("--summarize", nargs="+", metavar="RESULT_JSON")
    args = p.parse_args()
    if args.summarize:
        sys.stdout.write(summarize(args.summarize))
        return 0
    if not (args.case and args.condition and args.workdir):
        p.error("--case, --condition and --workdir are required (or use --summarize)")
    result = grade(args)
    text = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        if Path(args.out).exists():
            raise SystemExit(f"{args.out} exists")
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
