#!/usr/bin/env python3
"""Check a ledger for structural and semantic errors.

Checks include: schema conformance, duplicate IDs, broken references,
forbidden cycles, invalid states, evidence without required tool/command/
artifact hash, authority not matching the claim, unknowns resolved without
qualifying evidence, obligations closed with open blockers, contradictions
"resolved" without new evidence, records edited outside the scripts, and a
claimed final state that differs from the computed one.

Exit codes: 0 valid, 1 errors found (or warnings with --strict), 2 unreadable.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  python scripts/validate_ledger.py --ledger inv.json
  python scripts/validate_ledger.py --ledger inv.json --json --strict

  # After a person reviewed a manual edit and accepts it, recompute its digest
  python scripts/validate_ledger.py --ledger inv.json --reseal

Error codes are listed in references/completion-gates.md.
"""


def main() -> int:
    p = core.base_parser("validate_ledger.py", __doc__, EPILOG)
    p.add_argument("--json", action="store_true", help="Machine-readable output")
    p.add_argument("--strict", action="store_true", help="Treat warnings as errors")
    p.add_argument("--reseal", action="store_true",
                   help="Recompute digests of records edited by hand (after reviewing the edits)")
    args = p.parse_args()

    ledger = core.load_ledger(args.ledger)
    if args.reseal:
        at = core.now_iso(args.timestamp)
        resealed = []
        for name in core.COLLECTIONS:
            for rec in ledger.get(name, []):
                if isinstance(rec, dict) and rec.get("record_digest") != core.compute_digest(rec):
                    core.touch(rec, at, "resealed", "manual edit accepted after review")
                    resealed.append(rec.get("id", "?"))
        if resealed:
            core.atomic_write(args.ledger, core.dump(ledger))
        print(f"resealed: {', '.join(resealed) or 'nothing'}", file=sys.stderr)

    issues = core.validate(ledger)
    errors = [i for i in issues if i.level == "error"]
    warnings = [i for i in issues if i.level == "warning"]
    if args.json:
        print(json.dumps({"valid": not errors, "errors": [i.as_dict() for i in errors],
                          "warnings": [i.as_dict() for i in warnings]}, indent=2, sort_keys=True))
    else:
        for i in errors + warnings:
            print(str(i))
        counts = {c: len(ledger.get(c, [])) for c in core.COLLECTIONS}
        summary = ", ".join(f"{v} {k}" for k, v in counts.items())
        print(f"{'VALID' if not errors else 'INVALID'}: {len(errors)} error(s), {len(warnings)} warning(s) [{summary}]")
    return 1 if errors or (args.strict and warnings) else 0


if __name__ == "__main__":
    core.run(main)
