#!/usr/bin/env python3
"""Plan, authorize, complete or rank probes (P-0001, ...).

A probe is an experiment chosen because it discriminates between hypotheses:
each hypothesis predicts a different result. Irreversible, high-risk, external
or sensitive probes are marked as requiring authorization and cannot be marked
RUNNING or DONE until an authorization is recorded. Recording a probe does not
execute anything.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  python scripts/record_probe.py --ledger inv.json \\
      --question "Do rows without tz always fail?" --discriminates H-0001,H-0002 \\
      --expect "H-0001=every row without tz fails" --expect "H-0002=failures independent of tz" \\
      --change "tz present/absent" --control "same data, same runner, same seed" \\
      --cost low --risk low --observation-authority controlled-mutation \\
      --criterion "H-0001 survives only if 10/10 tz-less rows fail and 0/10 others fail"

  python scripts/record_probe.py --ledger inv.json --rank          # best next probes first

  python scripts/record_probe.py --ledger inv.json --id P-0001 --update --status DONE \\
      --result E-0005 --outcome "10/10 tz-less rows failed, 0/10 others: H-0002 contradicted"

  # A risky probe must be authorized by the user before it runs
  python scripts/record_probe.py --ledger inv.json --id P-0002 --update \\
      --authorize-by "user (chat, 2026-01-31)" --authorization-scope "staging DB only"
"""


def main() -> int:
    p = core.base_parser("record_probe.py", __doc__, EPILOG)
    p.add_argument("--id", help="Existing probe to update (requires --update)")
    p.add_argument("--update", action="store_true")
    p.add_argument("--rank", action="store_true", help="List PLANNED probes, most informative and cheapest first")
    p.add_argument("--question")
    p.add_argument("--purpose", default="discriminate",
                   choices=["discriminate", "counterexample-search", "reproduce", "measure", "verify", "explore"])
    p.add_argument("--discriminates", action="append", default=[], help="Hypothesis IDs this probe tests")
    p.add_argument("--expect", action="append", default=[], help="H-ID=expected result if that hypothesis is true")
    p.add_argument("--change", action="append", default=[], help="Variable changed on purpose")
    p.add_argument("--control", action="append", default=[], help="Variable held fixed")
    p.add_argument("--cost", choices=["low", "medium", "high"])
    p.add_argument("--risk", choices=["low", "medium", "high"])
    p.add_argument("--reversibility", choices=["reversible", "partially-reversible", "irreversible"])
    p.add_argument("--external", action="store_true", help="Touches systems outside the local working copy")
    p.add_argument("--sensitive", action="store_true", help="Involves credentials, personal data or security actions")
    p.add_argument("--not-repeatable", action="store_true")
    p.add_argument("--observation-authority", help="Authority tag the observation will have")
    p.add_argument("--criterion", help="How the result will be interpreted, decided before running")
    p.add_argument("--status", choices=["PLANNED", "RUNNING", "DONE", "ABANDONED"])
    p.add_argument("--authorize-by", help="Who authorized this probe (the user, not the agent)")
    p.add_argument("--authorization-scope", help="What exactly was authorized")
    p.add_argument("--result", action="append", default=[], help="Result evidence IDs")
    p.add_argument("--outcome", help="Interpretation of the result against the criterion")
    p.add_argument("--abandon-reason")
    p.add_argument("--input", type=Path, help="JSON object or list of new probes")
    args = p.parse_args()

    if args.rank:
        ledger = core.load_ledger(args.ledger)
        ranked = core.rank_probes(ledger)
        if not ranked:
            print("no PLANNED probes")
        for score, pr in ranked:
            flag = " [needs authorization]" if pr["requires_authorization"] and not pr["authorization"] else ""
            print(f"{pr['id']} score={score} cost={pr['cost']} risk={pr['risk']} "
                  f"tests={','.join(pr['discriminates'])}{flag}: {pr['question']}")
        return 0

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)

    if args.id:
        core.require_update_flag(args)
        pr = core.get_record(ledger, args.id, "probes")
        fields = {}
        for flag, field in (("status", "status"), ("outcome", "outcome"), ("abandon_reason", "abandon_reason"),
                            ("question", "question"), ("criterion", "interpretation_criterion"),
                            ("cost", "cost"), ("risk", "risk"), ("reversibility", "reversibility"),
                            ("observation_authority", "observation_authority")):
            if getattr(args, flag) is not None:
                fields[field] = getattr(args, flag)
        if args.result:
            fields["result_evidence"] = core.add_unique(pr["result_evidence"], core.csv_list(args.result))
        if args.expect:
            exp = dict(pr["expected_by_hypothesis"])
            exp.update(dict(core.parse_pairs(args.expect, "--expect")))
            fields["expected_by_hypothesis"] = exp
        if args.discriminates:
            fields["discriminates"] = core.add_unique(pr["discriminates"], core.csv_list(args.discriminates))
        if args.authorize_by:
            if not args.authorization_scope:
                raise core.LedgerError("--authorize-by requires --authorization-scope")
            fields["authorization"] = {"granted_by": args.authorize_by, "at": at, "scope": args.authorization_scope}
        for flag in ("external", "sensitive"):
            if getattr(args, flag):
                fields[flag] = True
        merged = {**pr, **fields}
        risky = merged["reversibility"] == "irreversible" or merged["risk"] == "high" or merged["external"] or merged["sensitive"]
        if risky and not pr["requires_authorization"]:
            fields["requires_authorization"] = True
        core.update_record(pr, fields, at)
        core.commit(args.ledger, before, ledger)
        print(f"updated {pr['id']} ({pr['status']})")
        return 0

    items = core.read_input(args.input)
    if not items:
        if not (args.question and args.discriminates and args.expect and args.criterion):
            p.error("new probes need --question, --discriminates, --expect for each hypothesis and --criterion")
        items = [{
            "question": args.question, "purpose": args.purpose,
            "discriminates": core.csv_list(args.discriminates),
            "expected_by_hypothesis": dict(core.parse_pairs(args.expect, "--expect")),
            "variables_changed": args.change, "variables_controlled": args.control,
            "cost": args.cost or "low", "risk": args.risk or "low",
            "reversibility": args.reversibility or "reversible",
            "external": args.external, "sensitive": args.sensitive, "repeatable": not args.not_repeatable,
            "observation_authority": args.observation_authority or "",
            "interpretation_criterion": args.criterion,
        }]
    created = []
    for item in items:
        risky = (item.get("reversibility") == "irreversible" or item.get("risk") == "high"
                 or item.get("external") or item.get("sensitive"))
        if risky:
            item["requires_authorization"] = True
        if item.get("status") not in (None, "PLANNED"):
            raise core.LedgerError("new probes start as PLANNED; update the status after it runs")
        rec = core.make_record(ledger, "probes", at, item)
        created.append(rec["id"] + (" (requires authorization before running)" if risky else ""))
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    return 0


if __name__ == "__main__":
    core.run(main)
