#!/usr/bin/env python3
"""Add an evidence record (E-0001, ...) to the ledger, or invalidate one.

Evidence is immutable. To correct a record, invalidate it and record a new one;
invalidation reopens every conclusion that relied on it.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ledger_core as core  # noqa: E402

EPILOG = """\
Examples:
  # A test run; the script hashes the tested file and the captured output itself
  python scripts/record_evidence.py --ledger inv.json \\
      --claim "test_export fails 7 of 50 runs with KeyError 'tz'" \\
      --source-type test --authority unit-test --tool pytest \\
      --command "pytest tests/test_export.py --count 50" \\
      --artifact-file src/export.py --output-file logs/run1.txt --shown-lines 20 --capture-method tail \\
      --scope "Linux, Python 3.12, this commit only" --supports H-0001 --reproducible

  # A deterministic derivation from earlier evidence
  python scripts/record_evidence.py --ledger inv.json --epistemic-status DERIVED --derived-from E-0001 \\
      --claim "Failure rate 14% (7/50)" --source-type calculation --authority independent-calculation \\
      --tool python --command "7/50" --scope "Rate in E-0001's sample only"

  # Invalidate (reopens dependent unknowns, contradictions, obligations, findings, hypotheses)
  python scripts/record_evidence.py --ledger inv.json --invalidate E-0003 --reason "wrong build was tested"

  # Batch from a sub-agent's structured report (object or list, fields as in schemas/evidence.schema.json;
  # use "artifact_file" / "output_file" keys to have the script compute hashes)
  python scripts/record_evidence.py --ledger inv.json --input report.json

Authorities and the source types they accept: references/authority-matrix.json
"""

AUTO_LINK = {"H": ("hypotheses", "supporting_evidence", "contradicting_evidence"),
             "U": ("unknowns", "supporting_evidence", "contradicting_evidence"),
             "F": ("findings", "evidence", "contradicting_evidence")}


def capture(path: Path, shown: int, method: str, excerpt: str) -> dict:
    if not path.exists():
        raise core.LedgerError(f"--output-file not found: {path}")
    data = path.read_bytes()
    total = len(data.decode("utf-8", errors="replace").splitlines())
    shown = total if method == "full" else min(shown, total)
    out = {"path": path.as_posix(), "sha256": core.sha256_file(path), "total_lines": total,
           "shown_lines": shown, "method": method}
    if excerpt:
        out["excerpt"] = excerpt
    return out


def build(item: dict, at: str) -> dict:
    """Turn CLI/--input fields into evidence fields, computing hashes where files are given."""
    item = dict(item)
    art_file = item.pop("artifact_file", None)
    if art_file:
        p = Path(art_file)
        if not p.is_file():
            raise core.LedgerError(f"artifact file not found: {p}")
        item["artifact_identity"] = {"kind": "sha256", "value": core.sha256_file(p), "path": p.as_posix()}
    out_file = item.pop("output_file", None)
    if out_file:
        item["output_capture"] = capture(Path(out_file), int(item.pop("shown_lines", 0) or 0),
                                         item.pop("capture_method", "full"), item.pop("excerpt", ""))
    for k in ("shown_lines", "capture_method", "excerpt"):
        item.pop(k, None)
    item.setdefault("timestamp", at)
    return item


def is_duplicate(ledger: dict, rec: dict) -> str:
    key = (rec.get("claim"), rec.get("command_or_method"), (rec.get("artifact_identity") or {}).get("value"))
    for e in ledger["evidence"]:
        if e["status"] == "ACTIVE" and (e["claim"], e["command_or_method"], e["artifact_identity"].get("value")) == key:
            return e["id"]
    return ""


def link(ledger: dict, rec: dict, at: str) -> list:
    notes = []
    for field, side in (("supports", 1), ("contradicts", 2)):
        for ref in rec.get(field, []):
            prefix = ref.split("-")[0]
            if prefix in AUTO_LINK:
                coll, sup_field, con_field = AUTO_LINK[prefix]
                target = core.get_record(ledger, ref, coll)
                tf = sup_field if side == 1 else con_field
                if rec["id"] not in target[tf]:
                    target[tf] = target[tf] + [rec["id"]]
                    core.touch(target, at, "linked", f"{rec['id']} added to {tf}")
            else:
                notes.append(f"{rec['id']} {field} {ref}: attach it with the "
                             f"{'record_obligation' if prefix == 'O' else 'record_probe' if prefix == 'P' else 'record_contradiction'}.py script")
    return notes


def main() -> int:
    p = core.base_parser("record_evidence.py", __doc__, EPILOG)
    p.add_argument("--claim", help="Bounded description of what was observed (not an interpretation)")
    p.add_argument("--epistemic-status", default="OBSERVED", choices=["OBSERVED", "DERIVED"])
    p.add_argument("--source-type", choices=["runtime", "static", "document", "test", "calculation", "formal-proof", "user-observation"])
    p.add_argument("--authority", help="Authority tag from references/authority-matrix.json")
    p.add_argument("--source", default="", help="Exact origin: path, URL, citation or person")
    p.add_argument("--artifact-file", type=Path, help="File the evidence is about; its SHA-256 is computed")
    p.add_argument("--artifact-kind", choices=["sha256", "commit", "version", "url", "file", "none"])
    p.add_argument("--artifact-value", help="Hash, commit, version, URL or path (with --artifact-kind)")
    p.add_argument("--tool", default="")
    p.add_argument("--command", dest="command_or_method", default="", help="Command or procedure that reproduces it")
    p.add_argument("--environment", help="Platform, versions, configuration")
    p.add_argument("--scope", help="What this evidence actually supports (and so what it does not)")
    p.add_argument("--limitation", action="append", default=[])
    p.add_argument("--supports", action="append", default=[], help="IDs this evidence supports (comma or repeat)")
    p.add_argument("--contradicts", action="append", default=[], help="IDs this evidence contradicts")
    p.add_argument("--derived-from", action="append", default=[], help="Evidence IDs a DERIVED record was computed from")
    p.add_argument("--reproducible", action="store_true", help="The command reproduces the observation")
    p.add_argument("--role", default="observation", choices=["observation", "construction", "verification", "review"])
    p.add_argument("--collected-by", default="single-agent", help="Agent or person that produced it")
    p.add_argument("--output-file", type=Path, help="Captured tool output; its hash and line count are recorded")
    p.add_argument("--shown-lines", type=int, default=0, help="Lines of the output shown/quoted")
    p.add_argument("--capture-method", default="full", choices=["full", "head", "tail", "grep", "summary"])
    p.add_argument("--excerpt", default="", help="Short excerpt of the output")
    p.add_argument("--input", type=Path, help="JSON object or list of evidence objects")
    p.add_argument("--allow-duplicate", action="store_true", help="Record even if an identical active record exists")
    p.add_argument("--invalidate", metavar="E-ID", help="Invalidate this evidence record")
    p.add_argument("--reason", default="", help="Why the evidence is invalid (with --invalidate)")
    args = p.parse_args()

    before, ledger = core.load_for_update(args.ledger)
    at = core.now_iso(args.timestamp)

    if args.invalidate:
        changes = core.invalidate_evidence(ledger, args.invalidate, args.reason, at)
        core.commit(args.ledger, before, ledger)
        print("\n".join(changes))
        return 0

    items = core.read_input(args.input)
    if not items:
        missing = [n for n in ("claim", "source_type", "authority", "scope") if not getattr(args, n)]
        if missing:
            p.error("missing " + ", ".join("--" + m.replace("_", "-") for m in missing) + " (or use --input)")
        item = {
            "claim": args.claim, "epistemic_status": args.epistemic_status, "source_type": args.source_type,
            "authority": args.authority, "source": args.source, "tool": args.tool,
            "command_or_method": args.command_or_method, "scope": args.scope, "limitations": args.limitation,
            "supports": core.csv_list(args.supports), "contradicts": core.csv_list(args.contradicts),
            "derived_from": core.csv_list(args.derived_from), "reproducible": args.reproducible,
            "role": args.role, "collected_by": args.collected_by,
        }
        if args.environment:
            item["environment"] = args.environment
        if args.artifact_file:
            item["artifact_file"] = str(args.artifact_file)
        elif args.artifact_kind:
            item["artifact_identity"] = {"kind": args.artifact_kind, "value": args.artifact_value or ""}
        if args.output_file:
            item.update(output_file=str(args.output_file), shown_lines=args.shown_lines,
                        capture_method=args.capture_method, excerpt=args.excerpt)
        items = [item]

    created, notes = [], []
    for item in items:
        fields = build(item, at)
        dup = is_duplicate(ledger, {**core.defaults("evidence", at), **fields})
        if dup and not args.allow_duplicate:
            raise core.LedgerError(f"identical active evidence already recorded as {dup}; "
                                   "use --allow-duplicate if this is a deliberate repeat", exit_code=1)
        rec = core.make_record(ledger, "evidence", at, fields)
        notes += link(ledger, rec, at)
        created.append(rec["id"])
    core.commit(args.ledger, before, ledger)
    print(" ".join(created))
    for n in notes:
        print(f"note: {n}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    core.run(main)
