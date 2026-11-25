#!/usr/bin/env python3
"""Add or update a hypothesis (H-0001, ...).

A hypothesis must be falsifiable and carry observable predictions. Status
changes are checked against evidence: SUPPORTED needs supporting evidence,
REJECTED/CONTRADICTED need contradicting evidence, VERIFIED needs verification
evidence that meets the authority of its claim_type. Nothing is promoted
automatically.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  python scripts/record_hypothesis.py --ledger inv.json --kind primary \\
      --statement "export fails when the row's timezone is missing" \\
      --prior-basis "KeyError 'tz' in the traceback (E-0001)" \\
      --prediction "If true, rows without tz fail 100% of the time" \\
      --prediction "If true, adding tz to every row removes the failure"

  python scripts/record_hypothesis.py --ledger inv.json --kind null \\
      --statement "the failure is unrelated to row content (environmental)" --alternative H-0001 \\
      --prior-basis "intermittency could come from the runner"

  # Update: mark a prediction, add evidence, change status
  python scripts/record_hypothesis.py --ledger inv.json --id H-0001 --update \\
      --prediction-result H-0001.P1=confirmed:E-0004 --add-support E-0004 --status SUPPORTED \\
      --confidence moderate --confidence-rationale "prediction P1 confirmed by E-0004"

Kinds: primary, null (conservative / no-effect), alternative, measurement-error, other.
Statuses: PROPOSED, TESTING, SUPPORTED, CONTRADICTED, REJECTED, VERIFIED, OUT_OF_SCOPE.
"""

STATUSES = ["PROPOSED", "TESTING", "SUPPORTED", "CONTRADICTED", "REJECTED", "VERIFIED", "OUT_OF_SCOPE"]


def main() -> int:
    p = core.base_parser("record_hypothesis.py", __doc__, EPILOG)
    p.add_argument("--id", help="Existing hypothesis to update (requires --update)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--statement")
    p.add_argument("--kind", choices=["primary", "null", "alternative", "measurement-error", "other"])
    p.add_argument("--alternative", action="append", default=[], help="Competing hypothesis IDs (linked both ways)")
    p.add_argument("--prior-basis", help="Why this hypothesis is worth considering")
    p.add_argument("--prediction", action="append", default=[], help="Repeatable: observable prediction")
    p.add_argument("--confounder", action="append", default=[])
    p.add_argument("--claim-type", help="Claim type from the authority matrix (needed for VERIFIED)")
    p.add_argument("--next-probe", help="Next probe planned for this hypothesis")
    p.add_argument("--confidence", choices=["low", "moderate", "high"])
    p.add_argument("--confidence-rationale")
    p.add_argument("--status", choices=STATUSES)
    p.add_argument("--status-rationale")
    p.add_argument("--add-support", action="append", default=[])
    p.add_argument("--add-contradiction", action="append", default=[])
    p.add_argument("--add-verification", action="append", default=[])
    p.add_argument("--prediction-result", action="append", default=[],
                   help="PRED_ID=result[:E-1,E-2] with result in pending|confirmed|refuted|inconclusive")
    p.add_argument("--input", type=Path, help="JSON object or list of new hypotheses")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)

    if args.id:
        core.require_update_flag(args)
        h = core.get_record(ledger, args.id, "hypotheses")
        fields = {}
        if args.statement:
            fields["statement"] = args.statement
        if args.kind:
            fields["kind"] = args.kind
        if args.prior_basis:
            fields["prior_basis"] = args.prior_basis
        if args.claim_type:
            fields["claim_type"] = args.claim_type
        if args.next_probe is not None:
            fields["next_probe"] = args.next_probe
        if args.status:
            fields["status"] = args.status
        if args.status_rationale is not None:
            fields["status_rationale"] = args.status_rationale
        if args.confidence or args.confidence_rationale is not None:
            fields["confidence"] = {"label": args.confidence or h["confidence"]["label"],
                                    "rationale": args.confidence_rationale if args.confidence_rationale is not None
                                    else h["confidence"]["rationale"]}
        for flag, field in (("add_support", "supporting_evidence"), ("add_contradiction", "contradicting_evidence"),
                            ("add_verification", "verification_evidence"), ("confounder", "confounders")):
            vals = core.csv_list(getattr(args, flag)) if flag != "confounder" else getattr(args, flag)
            if vals:
                fields[field] = core.add_unique(h[field], vals)
        preds = [dict(x) for x in h["predictions"]]
        for text in args.prediction:
            preds.append({"id": f"{h['id']}.P{len(preds) + 1}", "statement": text, "result": "pending", "evidence": []})
        for pid, spec in core.parse_pairs(args.prediction_result, "--prediction-result"):
            result, _, evs = spec.partition(":")
            match = [x for x in preds if x["id"] == pid]
            if not match:
                raise core.LedgerError(f"{pid} is not a prediction of {h['id']}")
            if result not in ("pending", "confirmed", "refuted", "inconclusive"):
                raise core.LedgerError(f"invalid prediction result '{result}'")
            match[0]["result"] = result
            match[0]["evidence"] = core.add_unique(match[0]["evidence"], core.csv_list([evs]))
        if preds != h["predictions"]:
            fields["predictions"] = preds
        alts = core.csv_list(args.alternative)
        if not fields and not alts:
            raise core.LedgerError("nothing to update; pass at least one field to change")
        if fields:
            core.update_record(h, fields, at)
        for alt in alts:
            other = core.get_record(ledger, alt, "hypotheses")
            if alt not in h["alternatives"]:
                h["alternatives"] = h["alternatives"] + [alt]
                core.touch(h, at, "linked", f"alternative {alt}")
            if h["id"] not in other["alternatives"]:
                other["alternatives"] = other["alternatives"] + [h["id"]]
                core.touch(other, at, "linked", f"alternative {h['id']}")
        core.commit(args.ledger, before, ledger)
        print(f"updated {h['id']}")
        return 0

    items = core.read_input(args.input)
    if not items:
        if not (args.statement and args.kind and args.prior_basis):
            p.error("new hypotheses need --statement, --kind and --prior-basis (or --input)")
        items = [{
            "statement": args.statement, "kind": args.kind, "prior_basis": args.prior_basis,
            "alternatives": core.csv_list(args.alternative), "confounders": args.confounder,
            "claim_type": args.claim_type, "next_probe": args.next_probe or "",
            "confidence": {"label": args.confidence or "low", "rationale": args.confidence_rationale or ""},
            "_predictions": args.prediction,
        }]
    created = []
    for item in items:
        texts = item.pop("_predictions", None) or []
        rec = core.make_record(ledger, "hypotheses", at, item)
        if texts:
            rec["predictions"] = rec["predictions"] + [
                {"id": f"{rec['id']}.P{i}", "statement": t, "result": "pending", "evidence": []}
                for i, t in enumerate(texts, start=len(rec["predictions"]) + 1)]
            core.seal(rec)
        for alt in rec["alternatives"]:
            other = core.get_record(ledger, alt, "hypotheses")
            if rec["id"] not in other["alternatives"]:
                other["alternatives"] = other["alternatives"] + [rec["id"]]
                core.touch(other, at, "linked", f"alternative {rec['id']}")
        created.append(rec["id"])
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    return 0


if __name__ == "__main__":
    core.run(main)
