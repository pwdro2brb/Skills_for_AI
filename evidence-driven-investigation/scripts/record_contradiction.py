#!/usr/bin/env python3
"""Record or update a contradiction (C-0001, ...) between claims or evidence.

Contradictions are never deleted. A new contradiction gets a checklist of the
standard explanations to examine (version, environment, tool error,
interpretation, nondeterminism, sample size, more complex hypothesis, tampered
data, ambiguous definition, authority mismatch). RESOLVED requires new evidence
that supports one explanation; picking the more convincing side is refused.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

CATEGORIES = {
    "version": "The two sides describe different versions of the artifact, document or dataset.",
    "environment": "The observations were made in different environments or configurations.",
    "tool-error": "A tool produced a wrong or partial result.",
    "interpretation": "The same observation was interpreted differently.",
    "nondeterminism": "The behavior is nondeterministic (timing, ordering, randomness).",
    "sample-size": "One side rests on too few cases.",
    "more-complex-hypothesis": "Both are partly right; a more complex explanation covers both.",
    "tampered-data": "One of the inputs was altered or corrupted.",
    "ambiguous-definition": "The sides use a term or measurement differently.",
    "authority-mismatch": "One side has weaker authority than the claim it is used for.",
}

EPILOG = """\
Examples:
  python scripts/record_contradiction.py --ledger inv.json --severity high \\
      --claim-a "Docs say the default timeout is 30 s" --evidence-a E-0002 \\
      --claim-b "Runtime trace shows a 10 s timeout" --evidence-b E-0005

  # Examine explanations: CATEGORY=status[:E-ids]; status is untested|ruled-out|supported
  python scripts/record_contradiction.py --ledger inv.json --id C-0001 --update \\
      --explanation-status "environment=ruled-out:E-0006" \\
      --explanation-status "version=supported:E-0007"

  python scripts/record_contradiction.py --ledger inv.json --id C-0001 --update --status RESOLVED \\
      --resolution "Docs describe v2.x; the trace is v3.1, whose changelog (E-0007) lowered the default" \\
      --resolution-evidence E-0007

Categories: """ + ", ".join(CATEGORIES)


def main() -> int:
    p = core.base_parser("record_contradiction.py", __doc__, EPILOG)
    p.add_argument("--id", help="Existing contradiction to update (requires --update)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--claim-a")
    p.add_argument("--claim-b")
    p.add_argument("--evidence-a", action="append", default=[])
    p.add_argument("--evidence-b", action="append", default=[])
    p.add_argument("--severity", choices=["low", "medium", "high", "critical"])
    p.add_argument("--explanation", action="append", default=[],
                   help="CATEGORY=specific explanation text (adds or replaces the text)")
    p.add_argument("--explanation-status", action="append", default=[],
                   help="CATEGORY=untested|ruled-out|supported[:E-ids]")
    p.add_argument("--no-checklist", action="store_true", help="Do not pre-fill the standard explanation checklist")
    p.add_argument("--status", choices=["OPEN", "INVESTIGATING", "RESOLVED", "OUT_OF_SCOPE"])
    p.add_argument("--resolution")
    p.add_argument("--resolution-evidence", action="append", default=[])
    p.add_argument("--input", type=Path, help="JSON object or list of new contradictions")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)

    def apply_explanations(expl):
        expl = [dict(x) for x in expl]
        by_cat = {x["category"]: x for x in expl}
        for cat, text in core.parse_pairs(args.explanation, "--explanation"):
            if cat not in CATEGORIES and cat != "other":
                raise core.LedgerError(f"unknown category '{cat}' (use one of {', '.join(CATEGORIES)}, other)")
            if cat in by_cat:
                by_cat[cat]["explanation"] = text
            else:
                by_cat[cat] = {"category": cat, "explanation": text, "status": "untested", "evidence": []}
                expl.append(by_cat[cat])
        for cat, spec in core.parse_pairs(args.explanation_status, "--explanation-status"):
            status, _, evs = spec.partition(":")
            if cat not in by_cat:
                raise core.LedgerError(f"no explanation '{cat}' yet; add it with --explanation {cat}=TEXT")
            if status not in ("untested", "ruled-out", "supported"):
                raise core.LedgerError(f"invalid explanation status '{status}'")
            by_cat[cat]["status"] = status
            by_cat[cat]["evidence"] = core.add_unique(by_cat[cat]["evidence"], core.csv_list([evs]))
        return expl

    if args.id:
        core.require_update_flag(args)
        c = core.get_record(ledger, args.id, "contradictions")
        fields = {}
        for flag, field in (("claim_a", "claim_a"), ("claim_b", "claim_b"), ("severity", "severity"),
                            ("status", "status"), ("resolution", "resolution")):
            if getattr(args, flag) is not None:
                fields[field] = getattr(args, flag)
        for flag, field in (("evidence_a", "evidence_a"), ("evidence_b", "evidence_b"),
                            ("resolution_evidence", "resolution_evidence")):
            vals = core.csv_list(getattr(args, flag))
            if vals:
                fields[field] = core.add_unique(c[field], vals)
        expl = apply_explanations(c["possible_explanations"])
        if expl != c["possible_explanations"]:
            fields["possible_explanations"] = expl
        core.update_record(c, fields, at)
        core.commit(args.ledger, before, ledger)
        print(f"updated {c['id']} ({c['status']})")
        return 0

    items = core.read_input(args.input)
    if not items:
        if not (args.claim_a and args.claim_b):
            p.error("new contradictions need --claim-a and --claim-b (or --input)")
        checklist = [] if args.no_checklist else [
            {"category": k, "explanation": v, "status": "untested", "evidence": []} for k, v in CATEGORIES.items()]
        items = [{
            "claim_a": args.claim_a, "claim_b": args.claim_b,
            "evidence_a": core.csv_list(args.evidence_a), "evidence_b": core.csv_list(args.evidence_b),
            "severity": args.severity or "medium", "possible_explanations": apply_explanations(checklist),
        }]
    created = []
    for item in items:
        if item.get("status") not in (None, "OPEN"):
            raise core.LedgerError("new contradictions start OPEN; resolve them with --update and new evidence")
        rec = core.make_record(ledger, "contradictions", at, item)
        created.append(rec["id"])
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    return 0


if __name__ == "__main__":
    core.run(main)
