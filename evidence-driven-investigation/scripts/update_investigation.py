#!/usr/bin/env python3
"""Change investigation-level fields: mode, scope, criteria, limitations,
authority extensions and the conclusion summary.

The final state is never set here. --claim-state only records what the agent
intends to claim, so validate_ledger.py can refuse it when the computed state
differs.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  # Escalate when the task turns out to be riskier than it looked
  python scripts/update_investigation.py --ledger inv.json --mode rigorous \\
      --reason "the fix touches data migration; a wrong result loses user data"

  python scripts/update_investigation.py --ledger inv.json \\
      --add-limitation "Only the Linux build was exercised" --add-scope-out "Windows installer"

  # Domain-specific authority, with a mandatory rationale (see references/domain-adapters.md)
  python scripts/update_investigation.py --ledger inv.json --extend-authority extension.json

  python scripts/update_investigation.py --ledger inv.json \\
      --conclusion "Root cause verified; packaged build not tested" --claim-state COMPLETE_WITH_LIMITATIONS
"""


def main() -> int:
    p = core.base_parser("update_investigation.py", __doc__, EPILOG)
    p.add_argument("--mode", choices=["light", "investigative", "rigorous"])
    p.add_argument("--reason", help="Why the mode changes (required with --mode)")
    p.add_argument("--add-limitation", action="append", default=[])
    p.add_argument("--add-criterion", action="append", default=[])
    p.add_argument("--add-scope-in", action="append", default=[])
    p.add_argument("--add-scope-out", action="append", default=[])
    p.add_argument("--extend-authority", type=Path,
                   help="JSON with {rationale, authorities: {...}, claim_types: {...}} to merge into authority_extensions")
    p.add_argument("--conclusion", help="Narrative conclusion summary for the report")
    p.add_argument("--claim-state", choices=list(core.FINAL_STATES) + ["none"],
                   help="State the agent intends to claim; must equal the computed state to validate")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)
    meta = ledger["investigation"]
    done = []

    if args.mode and args.mode != meta["mode"]:
        if not (args.reason or "").strip():
            raise core.LedgerError("--mode requires --reason")
        meta["history"].append({"at": at, "action": "mode", "detail": f"{meta['mode']} -> {args.mode}: {args.reason}"})
        done.append(f"mode {meta['mode']} -> {args.mode}")
        meta["mode"] = args.mode
    for flag, field in (("add_criterion", "completion_criteria"), ("add_scope_in", "scope_in"), ("add_scope_out", "scope_out")):
        vals = getattr(args, flag)
        if vals:
            meta[field] = core.add_unique(meta[field], vals)
            meta["history"].append({"at": at, "action": field, "detail": "; ".join(vals)})
            done.append(f"{field} +{len(vals)}")
    if args.add_limitation:
        ledger["limitations"] = core.add_unique(ledger["limitations"], args.add_limitation)
        done.append(f"limitations +{len(args.add_limitation)}")
    if args.extend_authority:
        ext = core.load_json(args.extend_authority, "Extension")
        if not str(ext.get("rationale", "")).strip():
            raise core.LedgerError("authority extensions need a top-level 'rationale'")
        cur = ledger["authority_extensions"]
        cur["rationale"] = (cur["rationale"] + " | " if cur["rationale"] else "") + ext["rationale"]
        for kind in ("authorities", "claim_types"):
            for key, value in (ext.get(kind) or {}).items():
                if key in cur[kind]:
                    raise core.LedgerError(f"extension '{key}' already exists")
                cur[kind][key] = value
        meta["history"].append({"at": at, "action": "authority_extension", "detail": ext["rationale"]})
        done.append("authority extensions merged")
    if args.conclusion is not None:
        ledger["conclusion"]["summary"] = args.conclusion
        done.append("conclusion summary")
    if args.claim_state:
        ledger["conclusion"]["claimed_state"] = None if args.claim_state == "none" else args.claim_state
        done.append(f"claimed_state {args.claim_state}")
    if not done:
        raise core.LedgerError("nothing to update")
    core.commit(args.ledger, before, ledger, claim_change=bool(args.claim_state))
    print("; ".join(done))
    return 0


if __name__ == "__main__":
    core.run(main)
