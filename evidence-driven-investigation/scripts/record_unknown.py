#!/usr/bin/env python3
"""Add or update a residual unknown (U-0001, ...).

An unknown is a bounded question the evidence does not yet answer. It is
closed only by evidence with the required authority (RESOLVED) or explicitly
excluded with a rationale (OUT_OF_SCOPE, which appears in the report).
Inference never resolves an unknown. A critical unknown that stays open
prevents a COMPLETE_* final state.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  python scripts/record_unknown.py --ledger inv.json \\
      --question "Does the packaged build use the same tz library version?" \\
      --severity high --domain software --required-authority works-in-final-package \\
      --requires-observation --environment "packaged wheel on Windows" \\
      --probe "install the wheel in a clean venv and run the export test"

  python scripts/record_unknown.py --ledger inv.json --id U-0001 --update --status RESOLVED \\
      --resolution-evidence E-0009 --rationale "E-0009 ran the packaged wheel: same library 2024.1"

  python scripts/record_unknown.py --ledger inv.json --id U-0002 --update --status BLOCKED \\
      --blocked-reason "needs access to the production logs, which the user has not provided"

Statuses: OPEN, INVESTIGATING, BLOCKED, CONTRADICTED, RESOLVED, OUT_OF_SCOPE.
Severities: low, medium, high, critical.
"""


def main() -> int:
    p = core.base_parser("record_unknown.py", __doc__, EPILOG)
    p.add_argument("--id", help="Existing unknown to update (requires --update)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--question")
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"])
    p.add_argument("--domain")
    p.add_argument("--required-authority", help="Claim type or authority tag that can close it")
    p.add_argument("--requires-observation", action="store_true", help="Only OBSERVED evidence can resolve it")
    p.add_argument("--environment", help="Environment needed to answer it")
    p.add_argument("--probe", action="append", default=[], help="Recommended probe (repeatable)")
    p.add_argument("--depends-on", action="append", default=[], help="Unknown IDs this one depends on")
    p.add_argument("--add-support", action="append", default=[])
    p.add_argument("--add-contradiction", action="append", default=[])
    p.add_argument("--status", choices=["OPEN", "INVESTIGATING", "BLOCKED", "CONTRADICTED", "RESOLVED", "OUT_OF_SCOPE"])
    p.add_argument("--resolution-evidence", action="append", default=[])
    p.add_argument("--rationale", help="Resolution or out-of-scope rationale")
    p.add_argument("--blocked-reason")
    p.add_argument("--input", type=Path, help="JSON object or list of new unknowns")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)

    if args.id:
        core.require_update_flag(args)
        u = core.get_record(ledger, args.id, "unknowns")
        fields = {}
        for flag, field in (("question", "question"), ("severity", "severity"), ("domain", "domain"),
                            ("required_authority", "required_authority"), ("environment", "required_environment"),
                            ("status", "status"), ("rationale", "resolution_rationale"),
                            ("blocked_reason", "blocked_reason")):
            if getattr(args, flag) is not None:
                fields[field] = getattr(args, flag)
        if args.requires_observation:
            fields["requires_observation"] = True
        for flag, field in (("add_support", "supporting_evidence"), ("add_contradiction", "contradicting_evidence"),
                            ("resolution_evidence", "resolution_evidence"), ("depends_on", "dependencies")):
            vals = core.csv_list(getattr(args, flag))
            if vals:
                fields[field] = core.add_unique(u[field], vals)
        if args.probe:
            fields["recommended_probes"] = core.add_unique(u["recommended_probes"], args.probe)
        core.update_record(u, fields, at)
        core.commit(args.ledger, before, ledger)
        print(f"updated {u['id']} ({u['status']})")
        return 0

    items = core.read_input(args.input)
    if not items:
        if not args.question:
            p.error("new unknowns need --question (or --input)")
        items = [{
            "question": args.question, "severity": args.severity or "medium", "domain": args.domain or "",
            "required_authority": args.required_authority, "requires_observation": args.requires_observation,
            "required_environment": args.environment or "", "recommended_probes": args.probe,
            "dependencies": core.csv_list(args.depends_on),
            "supporting_evidence": core.csv_list(args.add_support),
            "contradicting_evidence": core.csv_list(args.add_contradiction),
        }]
    created = []
    for item in items:
        if item.get("contradicting_evidence") and item.get("status") in (None, "OPEN"):
            item["status"] = "CONTRADICTED"
        rec = core.make_record(ledger, "unknowns", at, item)
        created.append(rec["id"])
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    return 0


if __name__ == "__main__":
    core.run(main)
