#!/usr/bin/env python3
"""Create a new investigation ledger (investigation.json) with empty collections."""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Example:
  python scripts/init_investigation.py --ledger work/investigation.json \\
      --id flaky-export --title "Flaky CSV export" \\
      --objective "Find why export_csv() fails intermittently and fix it" \\
      --mode investigative --domain software \\
      --scope-in "export module" --scope-out "UI layer" \\
      --criterion "Failing test passes 50/50 runs after the fix" \\
      --limitation "Only tested on Linux"

Light mode normally needs no ledger at all: do the task, verify it, report.
Refuses to overwrite an existing file unless --force is given.
"""


def main() -> int:
    p = core.base_parser("init_investigation.py", __doc__, EPILOG)
    p.add_argument("--id", required=True, help="Short slug, lowercase letters, digits and hyphens")
    p.add_argument("--title", required=True)
    p.add_argument("--objective", required=True, help="What the investigation must answer or achieve")
    p.add_argument("--mode", required=True, choices=["light", "investigative", "rigorous"])
    p.add_argument("--scope-in", action="append", default=[], help="Repeatable: what is in scope")
    p.add_argument("--scope-out", action="append", default=[], help="Repeatable: what is explicitly excluded")
    p.add_argument("--domain", action="append", default=[],
                   choices=["software", "reverse-engineering", "mathematics", "data-analysis", "research", "other"])
    p.add_argument("--criterion", action="append", default=[], help="Repeatable: completion criterion (turn each into an obligation)")
    p.add_argument("--limitation", action="append", default=[], help="Repeatable: known limitation")
    p.add_argument("--force", action="store_true", help="Overwrite an existing ledger file")
    args = p.parse_args()

    if not re.match(r"^[a-z0-9][a-z0-9-]*$", args.id):
        raise core.LedgerError("--id must be lowercase letters, digits and hyphens (e.g. flaky-export)")
    if args.ledger.exists() and not args.force:
        raise core.LedgerError(f"{args.ledger} already exists; use --force to overwrite it", exit_code=1)
    at = core.now_iso(args.timestamp)
    meta = {
        "id": args.id,
        "title": args.title,
        "objective": args.objective,
        "scope_in": args.scope_in,
        "scope_out": args.scope_out,
        "mode": args.mode,
        "domains": list(dict.fromkeys(args.domain)),
        "completion_criteria": args.criterion,
        "created_at": at,
        "history": [{"at": at, "action": "created", "detail": f"mode={args.mode}"}],
    }
    ledger = core.empty_ledger(meta)
    ledger["limitations"] = args.limitation
    problems = core.errors_only(core.validate(ledger))
    if problems:
        raise core.LedgerError("\n".join(str(i) for i in problems), exit_code=1)
    core.atomic_write(args.ledger, core.dump(ledger))
    print(f"created {args.ledger} (mode={args.mode})")
    if args.mode == "light":
        print("note: light mode rarely needs a ledger; prefer: do -> verify -> report", file=sys.stderr)
    if args.criterion:
        print(f"next: turn each of the {len(args.criterion)} completion criteria into an obligation "
              "with record_obligation.py", file=sys.stderr)
    return 0


if __name__ == "__main__":
    core.run(main)
