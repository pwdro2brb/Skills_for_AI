#!/usr/bin/env python3
"""Add or update a finding (F-0001, ...): one material claim of the conclusion.

Every material claim gets exactly one epistemic status:
OBSERVED, DERIVED, INFERRED, ASSUMED, CONTRADICTED, UNKNOWN, VERIFIED, REJECTED,
OUT_OF_SCOPE. Each status has its own evidence requirement; VERIFIED requires a
claim_type and verification evidence meeting its authority. An INFERRED finding
never becomes VERIFIED by being restated: it needs new verification evidence.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

STATUSES = ["OBSERVED", "DERIVED", "INFERRED", "ASSUMED", "CONTRADICTED", "UNKNOWN", "VERIFIED", "REJECTED", "OUT_OF_SCOPE"]

EPILOG = """\
Examples:
  python scripts/record_finding.py --ledger inv.json --status OBSERVED \\
      --claim "The export fails only for rows without tz" --evidence E-0005 \\
      --scope "the 20 rows of fixtures/sample.csv"

  python scripts/record_finding.py --ledger inv.json --status INFERRED \\
      --claim "Production failures have the same cause" --hypothesis H-0001 --evidence E-0005 \\
      --scope "production, by analogy; not observed"

  python scripts/record_finding.py --ledger inv.json --id F-0001 --update --status VERIFIED \\
      --claim-type root-cause-identified --verification E-0008

Statuses and what each requires: references/evidence-model.md
"""


def main() -> int:
    p = core.base_parser("record_finding.py", __doc__, EPILOG)
    p.add_argument("--id", help="Existing finding to update (requires --update)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--claim")
    p.add_argument("--status", choices=STATUSES, help="Epistemic status")
    p.add_argument("--claim-type", help="Claim type from the authority matrix")
    p.add_argument("--evidence", action="append", default=[], help="Evidence the claim rests on")
    p.add_argument("--verification", action="append", default=[], help="Verification evidence (for VERIFIED)")
    p.add_argument("--contradicting", action="append", default=[], help="Contradicting evidence")
    p.add_argument("--hypothesis", action="append", default=[])
    p.add_argument("--unknown", action="append", default=[])
    p.add_argument("--contradiction", action="append", default=[])
    p.add_argument("--rationale")
    p.add_argument("--scope", help="Exactly what the claim covers")
    p.add_argument("--input", type=Path, help="JSON object or list of new findings")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)
    lists = (("evidence", "evidence"), ("verification", "verification_evidence"),
             ("contradicting", "contradicting_evidence"), ("hypothesis", "hypotheses"),
             ("unknown", "unknowns"), ("contradiction", "contradictions"))

    if args.id:
        core.require_update_flag(args)
        f = core.get_record(ledger, args.id, "findings")
        fields = {}
        for flag, field in (("claim", "claim"), ("status", "epistemic_status"), ("claim_type", "claim_type"),
                            ("rationale", "rationale"), ("scope", "scope")):
            if getattr(args, flag) is not None:
                fields[field] = getattr(args, flag)
        for flag, field in lists:
            vals = core.csv_list(getattr(args, flag))
            if vals:
                fields[field] = core.add_unique(f[field], vals)
        old = f["epistemic_status"]
        core.update_record(f, fields, at)
        core.commit(args.ledger, before, ledger)
        print(f"updated {f['id']} ({old} -> {f['epistemic_status']})" if old != f["epistemic_status"] else f"updated {f['id']}")
        return 0

    items = core.read_input(args.input)
    if not items:
        if not (args.claim and args.status and args.scope):
            p.error("new findings need --claim, --status and --scope (or --input)")
        items = [{"claim": args.claim, "epistemic_status": args.status, "claim_type": args.claim_type,
                  "rationale": args.rationale or "", "scope": args.scope,
                  **{field: core.csv_list(getattr(args, flag)) for flag, field in lists}}]
    created = []
    for item in items:
        rec = core.make_record(ledger, "findings", at, item)
        created.append(rec["id"])
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    return 0


if __name__ == "__main__":
    core.run(main)
