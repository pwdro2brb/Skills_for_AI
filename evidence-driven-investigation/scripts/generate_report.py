#!/usr/bin/env python3
"""Generate a Markdown report from the ledger.

The final state in the report is always recomputed by evaluate_completion
logic, never copied from the ledger. Contradictions, unknowns, out-of-scope
items and limitations are always shown, including resolved ones.

Formats: concise (for the user) and rigorous (full audit trail).
Output is deterministic for a given ledger. Refuses to overwrite --out
without --force. An invalid ledger is refused unless --allow-invalid, in which
case the report says the state could not be computed and lists the errors.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

TEMPLATES = core.SKILL_ROOT / "templates"

EPILOG = """\
Examples:
  python scripts/generate_report.py --ledger inv.json                       # concise, to stdout
  python scripts/generate_report.py --ledger inv.json --format rigorous --out report.md
"""

FINDING_ORDER = ["VERIFIED", "OBSERVED", "DERIVED", "INFERRED", "ASSUMED", "UNKNOWN",
                 "CONTRADICTED", "REJECTED", "OUT_OF_SCOPE"]

MEANING = {
    "COMPLETE_VERIFIED": "Every obligation is closed by separate verification of the required authority; no critical or high item is open.",
    "COMPLETE_WITH_LIMITATIONS": "Every critical obligation is closed and verified, but some non-critical item is open, waived or out of scope, or a mode requirement is unmet. Read the limitations.",
    "PARTIALLY_VERIFIED": "Some obligations or findings are verified, but at least one closure gate fails. The conclusion is not complete.",
    "MITIGATED_NOT_RESOLVED": "A mitigation is verified but the root cause is not established.",
    "BLOCKED": "A critical obligation or unknown needs authority, access or an environment that is not available.",
    "INCONCLUSIVE": "The evidence does not support a conclusion. Nothing critical is verified.",
    "FAILED": "A critical obligation was tested and failed.",
}


def cell(value) -> str:
    text = ", ".join(value) if isinstance(value, list) else ("" if value is None else str(value))
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ").strip() or "—"


def table(headers, rows) -> str:
    if not rows:
        return "_None._"
    out = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    out += ["| " + " | ".join(cell(v) for v in row) + " |" for row in rows]
    return "\n".join(out)


def bullets(items, empty="_None recorded._") -> str:
    items = [str(i) for i in items if str(i).strip()]
    return "\n".join(f"- {i}" for i in items) if items else empty


def artifact(e) -> str:
    a = e["artifact_identity"]
    if a["kind"] == "none":
        return "—"
    value = a["value"][:12] + "…" if a["kind"] == "sha256" else a["value"]
    return f"{a['kind']}:{value}" + (f" ({a['path']})" if a.get("path") else "")


def render_invalid(ledger, errors) -> str:
    """Minimal report for a ledger that fails validation: no record is trusted."""
    meta = ledger.get("investigation") or {}
    return (f"# {meta.get('title', 'Investigation')}\n\n**Computed final state:** `NOT_COMPUTABLE`\n\n"
            f"The ledger is invalid, so no state can be computed and no record is reported as established.\n\n"
            f"## Objective\n\n{meta.get('objective', '—')}\n\n## Validation errors\n\n{bullets(errors)}\n\n"
            f"Fix the errors (scripts/validate_ledger.py) and generate the report again.\n")


def render(ledger, fmt, result, errors) -> str:
    if errors:
        return render_invalid(ledger, errors)
    meta = ledger["investigation"]
    ev = ledger["evidence"]
    state = result["state"] if result else "NOT_COMPUTABLE"
    claimed = ledger["conclusion"].get("claimed_state")
    if errors:
        claim_check = "**The ledger is invalid; the final state could not be computed.**\n\n" + bullets(errors)
    elif claimed and claimed != state:
        claim_check = f"**Warning:** the agent claimed `{claimed}`, which does not match the computed state."
    elif claimed:
        claim_check = "The agent's claimed state matches the computed state."
    else:
        claim_check = ""

    findings_rows = [(f["id"], f["epistemic_status"], f["claim"], f["scope"],
                      list(dict.fromkeys(f["evidence"] + f["verification_evidence"]))
                      + [f"against {x}" for x in f["contradicting_evidence"]], f.get("claim_type"))
                     for f in sorted(ledger["findings"], key=lambda f: (FINDING_ORDER.index(f["epistemic_status"]), f["id"]))]
    findings = table(["ID", "Status", "Claim", "Scope", "Evidence", "Claim type"], findings_rows)

    open_u = [u for u in ledger["unknowns"] if u["status"] not in core.CLOSED_UNKNOWN]
    open_c = [c for c in ledger["contradictions"] if c["status"] not in core.CLOSED_CONTRADICTION]
    oos = [u for u in ledger["unknowns"] if u["status"] == "OUT_OF_SCOPE"]
    open_items = table(["ID", "Severity", "Status", "Question / conflict"],
                       [(u["id"], u["severity"], u["status"], u["question"]) for u in open_u]
                       + [(c["id"], c["severity"], c["status"], f"{c['claim_a']} ⟷ {c['claim_b']}") for c in open_c]
                       + [(u["id"], u["severity"], "OUT_OF_SCOPE", f"{u['question']} — {u['resolution_rationale']}") for u in oos])

    lims = list(ledger["limitations"]) + [f"[{e['id']}] {lim}" for e in ev if e["status"] == "ACTIVE" for lim in e["limitations"]]
    lims += [f"Out of scope: {s}" for s in meta["scope_out"]]
    lims += [f"{o['id']} WAIVED: {o['status_rationale']}" for o in ledger["obligations"] if o["status"] == "WAIVED"]

    repro = [f"[{e['id']}] `{e['command_or_method']}`" + (f" — {e['tool']}" if e["tool"] else "")
             for e in ev if e["status"] == "ACTIVE" and e["reproducible"]]
    not_repro = [e["id"] for e in ev if e["status"] == "ACTIVE" and not e["reproducible"]]
    reproduction = bullets(repro, "_No evidence is marked reproducible._")
    if not_repro:
        reproduction += f"\n\nNot reproducible by command: {', '.join(not_repro)}."

    reasons = ""
    if result:
        reasons = "Why this state:\n\n" + bullets(result["reasons"])

    values = {
        "title": meta["title"], "state": state, "mode": meta["mode"], "claim_check": claim_check,
        "objective": meta["objective"],
        "conclusion": ledger["conclusion"]["summary"] or "_No conclusion summary recorded._",
        "state_reasons": reasons, "findings": findings, "open_items": open_items,
        "limitations": bullets(lims), "reproduction": reproduction,
        "ledger_digest": core.ledger_digest(ledger),
        "state_meaning": MEANING.get(state, "The ledger must be fixed before a state can be computed."),
    }
    if fmt == "rigorous":
        values["scope"] = "In scope:\n\n" + bullets(meta["scope_in"]) + "\n\nOut of scope:\n\n" + bullets(meta["scope_out"]) \
            + ("\n\nCompletion criteria:\n\n" + bullets(meta["completion_criteria"]) if meta["completion_criteria"] else "") \
            + f"\n\nDomains: {', '.join(meta['domains']) or '—'}"
        values["gates"] = table(["Gate", "Passed", "Description", "Failures"],
                                [(g["id"], "yes" if g["passed"] else "**no**", g["description"], g["failures"])
                                 for g in result["gates"]]) if result else "_Not computed._"
        values["observations"] = table(
            ["ID", "Status", "Claim", "Scope"],
            [(e["id"], e["epistemic_status"], e["claim"], e["scope"]) for e in ev if e["status"] == "ACTIVE" and e["role"] == "observation"])
        hyp_rows = []
        for h in ledger["hypotheses"]:
            preds = "; ".join(f"{p['id']} [{p['result']}] {p['statement']}" for p in h["predictions"])
            hyp_rows.append((h["id"], h["kind"], h["status"], h["statement"], preds,
                             f"+{','.join(h['supporting_evidence']) or '∅'} / −{','.join(h['contradicting_evidence']) or '∅'}",
                             f"{h['confidence']['label']}: {h['confidence']['rationale']}"))
        values["hypotheses"] = table(["ID", "Kind", "Status", "Statement", "Predictions", "Evidence +/−", "Confidence"], hyp_rows)
        values["probes"] = table(
            ["ID", "Purpose", "Status", "Question", "Expected by hypothesis", "Cost/Risk", "Authorization", "Result", "Outcome"],
            [(p["id"], p["purpose"], p["status"], p["question"],
              "; ".join(f"{k}: {v}" for k, v in sorted(p["expected_by_hypothesis"].items())),
              f"{p['cost']}/{p['risk']}/{p['reversibility']}",
              (p["authorization"] or {}).get("granted_by", "required, not granted" if p["requires_authorization"] else "not required"),
              p["result_evidence"], p["outcome"] or p["abandon_reason"]) for p in ledger["probes"]])
        values["evidence"] = table(
            ["ID", "Status", "Epistemic", "Source type", "Authority", "Claim", "Tool / command", "Artifact", "Scope", "Role / by", "Limitations"],
            [(e["id"], e["status"] + (f" ({e['invalidation']['reason']})" if e["status"] == "INVALIDATED" else ""),
              e["epistemic_status"], e["source_type"], e["authority"], e["claim"],
              f"{e['tool']}: {e['command_or_method']}" if e["tool"] else e["command_or_method"] or e["source"],
              artifact(e), e["scope"], f"{e['role']} / {e['collected_by']}", e["limitations"]) for e in ev])
        con_parts = []
        for c in ledger["contradictions"]:
            ex = table(["Explanation", "Status", "Evidence", "Detail"],
                       [(x["category"], x["status"], x["evidence"], x["explanation"]) for x in c["possible_explanations"]])
            con_parts.append(f"**{c['id']}** ({c['severity']}, {c['status']})\n\n- A: {c['claim_a']} [{', '.join(c['evidence_a']) or '—'}]\n"
                             f"- B: {c['claim_b']} [{', '.join(c['evidence_b']) or '—'}]\n"
                             f"- Resolution: {c['resolution'] or '—'} [{', '.join(c['resolution_evidence']) or '—'}]\n\n{ex}")
        values["contradictions"] = "\n\n".join(con_parts) or "_None recorded._"
        values["unknowns"] = table(
            ["ID", "Severity", "Status", "Question", "Required authority", "Resolution / blocker", "Recommended probes"],
            [(u["id"], u["severity"], u["status"], u["question"],
              (u["required_authority"] or "—") + (" (observation only)" if u["requires_observation"] else ""),
              f"{u['resolution_rationale']} [{', '.join(u['resolution_evidence'])}]" if u["status"] in core.CLOSED_UNKNOWN else u["blocked_reason"],
              u["recommended_probes"]) for u in ledger["unknowns"]])
        values["obligations"] = table(
            ["ID", "Severity", "Kind", "Status", "Claim", "Required authority", "Cases (evidence)", "Construction", "Verification", "Rationale"],
            [(o["id"], o["severity"], o["kind"], o["status"], o["claim"], o["required_authority"],
              "; ".join(f"{c}: {','.join(o['case_evidence'].get(c, [])) or 'MISSING'}" for c in o["required_cases"]),
              o["construction_evidence"], o["verification_evidence"], o["status_rationale"]) for o in ledger["obligations"]])
        ext = ledger["authority_extensions"]
        if ext["authorities"] or ext["claim_types"]:
            values["extensions"] = (f"Rationale: {ext['rationale']}\n\n"
                                    + bullets([f"authority `{k}`: {v['description']} ({v['rationale']})" for k, v in ext["authorities"].items()]
                                              + [f"claim type `{k}`: {v['description']} ({v['rationale']})" for k, v in ext["claim_types"].items()]))
        else:
            values["extensions"] = "No authority extensions; the base matrix applies."
        values["warnings"] = ("Validation warnings:\n\n" + bullets(f"{w['code']} {w['record']}: {w['message']}" for w in result["warnings"])
                              if result and result["warnings"] else "No validation warnings.")
    template = (TEMPLATES / f"{fmt}-report.md").read_text(encoding="utf-8")
    for key, value in values.items():
        template = template.replace("{{" + key + "}}", value)
    lines = [ln.rstrip() for ln in template.splitlines()]
    text, blank = [], False
    for ln in lines:  # collapse runs of blank lines left by empty sections
        if ln == "" and blank:
            continue
        text.append(ln)
        blank = ln == ""
    return "\n".join(text).strip() + "\n"


def main() -> int:
    p = core.base_parser("generate_report.py", __doc__, EPILOG)
    p.add_argument("--format", default="concise", choices=["concise", "rigorous"])
    p.add_argument("--out", type=Path, help="Write to this file instead of stdout")
    p.add_argument("--force", action="store_true", help="Overwrite --out if it exists")
    p.add_argument("--allow-invalid", action="store_true", help="Report on an invalid ledger (state not computed)")
    args = p.parse_args()

    ledger = core.load_ledger(args.ledger)
    issues = core.validate(ledger)
    errors = [str(i) for i in issues if i.level == "error" and i.code != "X01"]  # a stale claim is shown, not fatal
    if errors and not args.allow_invalid:
        raise core.LedgerError("Ledger is invalid; fix it or pass --allow-invalid:\n" + "\n".join(errors), exit_code=2)
    if errors and args.format == "rigorous":
        raise core.LedgerError("the rigorous report needs a valid ledger; use --format concise --allow-invalid", exit_code=2)
    result = None if errors else core.evaluate(ledger, _issues=issues)
    text = render(ledger, args.format, result, errors)
    if args.out:
        if args.out.exists() and not args.force:
            raise core.LedgerError(f"{args.out} exists; use --force to overwrite", exit_code=1)
        core.atomic_write(args.out, text)
        print(f"wrote {args.out} ({result['state'] if result else 'NOT_COMPUTABLE'})")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    core.run(main)
