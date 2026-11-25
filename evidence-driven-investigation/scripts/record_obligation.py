#!/usr/bin/env python3
"""Add or update an obligation (O-0001, ...): a verifiable completion requirement.

An obligation closes only when its verification evidence (separate from the
construction evidence) meets the required authority, every required case has
evidence, and no blocking unknown, contradiction or dependency is open. A green
unit test cannot close an obligation that requires the packaged artifact.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  python scripts/record_obligation.py --ledger inv.json \\
      --claim "The writer preserves all unknown fields" --owner src/writer.py \\
      --kind reconstruction --severity critical --required-authority parser-preserves-file \\
      --case "normal file" --case "empty file" --case "truncated file" --case "round trip unchanged"

  # Attach evidence as it is produced
  python scripts/record_obligation.py --ledger inv.json --id O-0001 --update \\
      --add-construction E-0010 --add-verification E-0012 \\
      --case-evidence "normal file=E-0012" --case-evidence "empty file=E-0013"

  # Close (refused unless every rule holds), fail, block or waive with a rationale
  python scripts/record_obligation.py --ledger inv.json --id O-0001 --update --status CLOSED
  python scripts/record_obligation.py --ledger inv.json --id O-0002 --update --status BLOCKED \\
      --rationale "requires the signed release build, not available here"

Kinds: behavior, root-cause, fix, mitigation, regression, reconstruction, proof, analysis, documentation, other.
Severities: critical, major, minor. Statuses: OPEN, CLOSED, FAILED, BLOCKED, WAIVED.
"""


def main() -> int:
    p = core.base_parser("record_obligation.py", __doc__, EPILOG)
    p.add_argument("--id", help="Existing obligation to update (requires --update)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--claim")
    p.add_argument("--owner", help="File, module, component or person responsible")
    p.add_argument("--kind", choices=["behavior", "root-cause", "fix", "mitigation", "regression",
                                      "reconstruction", "proof", "analysis", "documentation", "other"])
    p.add_argument("--severity", choices=["critical", "major", "minor"])
    p.add_argument("--case", action="append", default=[], help="Required case (repeatable)")
    p.add_argument("--required-authority", help="Claim type or authority tag from the authority matrix")
    p.add_argument("--applies-to", help="Artifact identity value (hash, commit, version) the verification must be about")
    p.add_argument("--blocking-unknown", action="append", default=[])
    p.add_argument("--blocking-contradiction", action="append", default=[])
    p.add_argument("--depends-on", action="append", default=[], help="Obligation IDs that must close first")
    p.add_argument("--add-construction", action="append", default=[], help="Evidence produced while building the solution")
    p.add_argument("--add-verification", action="append", default=[], help="Evidence produced by the separate verification")
    p.add_argument("--case-evidence", action="append", default=[], help="CASE=E-1,E-2")
    p.add_argument("--status", choices=["OPEN", "CLOSED", "FAILED", "BLOCKED", "WAIVED"])
    p.add_argument("--rationale", help="Required for FAILED, BLOCKED and WAIVED")
    p.add_argument("--input", type=Path, help="JSON object or list of new obligations")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)

    if args.id:
        core.require_update_flag(args)
        o = core.get_record(ledger, args.id, "obligations")
        fields = {}
        for flag, field in (("claim", "claim"), ("owner", "owner"), ("kind", "kind"), ("severity", "severity"),
                            ("required_authority", "required_authority"), ("applies_to", "applies_to"),
                            ("status", "status"), ("rationale", "status_rationale")):
            if getattr(args, flag) is not None:
                fields[field] = getattr(args, flag)
        for flag, field in (("add_construction", "construction_evidence"), ("add_verification", "verification_evidence"),
                            ("blocking_unknown", "blocking_unknowns"), ("blocking_contradiction", "blocking_contradictions"),
                            ("depends_on", "dependencies")):
            vals = core.csv_list(getattr(args, flag))
            if vals:
                fields[field] = core.add_unique(o[field], vals)
        if args.case:
            fields["required_cases"] = core.add_unique(o["required_cases"], args.case)
        if args.case_evidence:
            ce = {k: list(v) for k, v in o["case_evidence"].items()}
            for case, evs in core.parse_pairs(args.case_evidence, "--case-evidence", split_last=True):
                ce[case] = core.add_unique(ce.get(case, []), core.csv_list([evs]))
            fields["case_evidence"] = ce
        core.update_record(o, fields, at)
        core.commit(args.ledger, before, ledger)
        print(f"updated {o['id']} ({o['status']})")
        return 0

    items = core.read_input(args.input)
    if not items:
        if not (args.claim and args.required_authority):
            p.error("new obligations need --claim and --required-authority (or --input)")
        items = [{
            "claim": args.claim, "owner": args.owner or "", "kind": args.kind or "behavior",
            "severity": args.severity or "critical", "required_cases": args.case,
            "required_authority": args.required_authority, "applies_to": args.applies_to,
            "blocking_unknowns": core.csv_list(args.blocking_unknown),
            "blocking_contradictions": core.csv_list(args.blocking_contradiction),
            "dependencies": core.csv_list(args.depends_on),
        }]
    created = []
    for item in items:
        if item.get("status") not in (None, "OPEN"):
            raise core.LedgerError("new obligations start OPEN; close them with --update after verification")
        rec = core.make_record(ledger, "obligations", at, item)
        created.append(rec["id"])
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    return 0


if __name__ == "__main__":
    core.run(main)
