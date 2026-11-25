#!/usr/bin/env python3
"""Compute the real final state of an investigation from its ledger.

The state is derived from obligations, unknowns, contradictions, hypotheses,
probes and evidence. No stored field can set it. Possible states, from
strongest to weakest: COMPLETE_VERIFIED, COMPLETE_WITH_LIMITATIONS,
PARTIALLY_VERIFIED, MITIGATED_NOT_RESOLVED, BLOCKED, INCONCLUSIVE, FAILED.

Exit codes: 0 evaluated, 2 ledger invalid (nothing evaluated),
3 evaluated but differs from --expect.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  python scripts/evaluate_completion.py --ledger inv.json
  python scripts/evaluate_completion.py --ledger inv.json --json
  python scripts/evaluate_completion.py --ledger inv.json --expect COMPLETE_VERIFIED   # CI gate

Gate definitions: references/completion-gates.md
"""


def main() -> int:
    p = core.base_parser("evaluate_completion.py", __doc__, EPILOG)
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.add_argument("--out", type=Path, help="Also write the JSON result to this file")
    p.add_argument("--force", action="store_true", help="Allow --out to overwrite an existing file")
    p.add_argument("--expect", choices=core.FINAL_STATES, help="Exit 3 unless the computed state equals this")
    args = p.parse_args()

    ledger = core.load_ledger(args.ledger)
    result = core.evaluate(ledger)
    text = json.dumps(result, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
    if args.out:
        if args.out.exists() and not args.force:
            raise core.LedgerError(f"{args.out} exists; use --force to overwrite", exit_code=1)
        core.atomic_write(args.out, text)
    if args.json:
        sys.stdout.write(text)
    else:
        print(f"STATE: {result['state']} (mode={result['mode']})")
        for g in result["gates"]:
            print(f"  [{'x' if g['passed'] else ' '}] {g['id']} {g['description']}")
            for f in g["failures"]:
                print(f"        - {f}")
        print("reasons:")
        for r in result["reasons"]:
            print(f"  - {r}")
        for w in result["warnings"]:
            print(f"warning {w['code']} {w['record']}: {w['message']}")
    if args.expect and result["state"] != args.expect:
        print(f"expected {args.expect}, computed {result['state']}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    core.run(main)
