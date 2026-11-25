"""Shared logic for the evidence-driven-investigation scripts.

Standard library only (Python 3.9+). Every script in this folder is a thin
command-line wrapper around the functions here, so the rules live in one place:

* reading and atomically writing the ledger,
* allocating stable IDs (E-0001, H-0001, ...),
* JSON Schema validation (the subset of Draft 2020-12 used by ../schemas),
* semantic validation (authority matching, closure rules, cycles, digests),
* computing the final state of an investigation,
* invalidating evidence and reopening what depended on it.

Nothing here decides what to investigate. That is the agent's job.
"""

from __future__ import annotations

import argparse
import copy
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence, Set, Tuple

SKILL_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = SKILL_ROOT / "schemas"
MATRIX_PATH = SKILL_ROOT / "references" / "authority-matrix.json"

SCHEMA_VERSION = 1

FINAL_STATES = (
    "COMPLETE_VERIFIED",
    "COMPLETE_WITH_LIMITATIONS",
    "PARTIALLY_VERIFIED",
    "MITIGATED_NOT_RESOLVED",
    "BLOCKED",
    "INCONCLUSIVE",
    "FAILED",
)

COLLECTIONS = (
    "evidence",
    "hypotheses",
    "probes",
    "unknowns",
    "contradictions",
    "obligations",
    "findings",
)
PREFIX = {
    "evidence": "E",
    "hypotheses": "H",
    "probes": "P",
    "unknowns": "U",
    "contradictions": "C",
    "obligations": "O",
    "findings": "F",
}
COLLECTION_BY_PREFIX = {v: k for k, v in PREFIX.items()}
SCHEMA_FILE = {
    "evidence": "evidence.schema.json",
    "hypotheses": "hypothesis.schema.json",
    "probes": "probe.schema.json",
    "unknowns": "unknown.schema.json",
    "contradictions": "contradiction.schema.json",
    "obligations": "obligation.schema.json",
    "findings": "finding.schema.json",
}
ID_RE = re.compile(r"^([EHPUCOF])-(\d{4,})$")
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
DATE_TIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$"
)

# Source types whose evidence must name the tool and the exact command, and
# must identify the artifact it was taken from.
EXECUTED_SOURCE_TYPES = {"runtime", "test", "static", "calculation", "formal-proof"}
ARTIFACT_REQUIRED_SOURCE_TYPES = {"runtime", "test", "static", "formal-proof"}

OPEN_UNKNOWN = {"OPEN", "INVESTIGATING", "BLOCKED", "CONTRADICTED"}
CLOSED_UNKNOWN = {"RESOLVED", "OUT_OF_SCOPE"}
OPEN_CONTRADICTION = {"OPEN", "INVESTIGATING"}
CLOSED_CONTRADICTION = {"RESOLVED", "OUT_OF_SCOPE"}


class LedgerError(Exception):
    """An error the user must fix. Scripts print it and exit with exit_code."""

    def __init__(self, message: str, exit_code: int = 2):
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Time, JSON and files
# ---------------------------------------------------------------------------


def now_iso(explicit: Optional[str] = None) -> str:
    """Timestamp for new records.

    Priority: explicit --timestamp, then EDI_FIXED_TIME, then the clock.
    A fixed time makes the same command sequence produce identical bytes.
    """
    value = explicit or os.environ.get("EDI_FIXED_TIME")
    if value:
        if not DATE_TIME_RE.match(value):
            raise LedgerError(
                f"Invalid timestamp {value!r}; use ISO-8601 like 2026-01-31T12:00:00Z"
            )
        return value
    return (
        _dt.datetime.now(_dt.timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def dump(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def compute_digest(record: Dict[str, Any]) -> str:
    body = {k: v for k, v in record.items() if k != "record_digest"}
    return hashlib.sha256(canonical(body).encode("utf-8")).hexdigest()


def ledger_digest(ledger: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical(ledger).encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, path)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def load_json(path: Path, what: str = "file") -> Any:
    path = Path(path)
    if not path.exists():
        raise LedgerError(f"{what} not found: {path}")
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as exc:
        raise LedgerError(f"{what} is not valid JSON ({path}): {exc}")


def load_ledger(path: Path) -> Dict[str, Any]:
    ledger = load_json(path, "Ledger")
    if not isinstance(ledger, dict) or ledger.get("schema_version") != SCHEMA_VERSION:
        raise LedgerError(
            f"{path} is not an investigation ledger (expected schema_version {SCHEMA_VERSION})"
        )
    return ledger


# ---------------------------------------------------------------------------
# Minimal JSON Schema validator (subset of Draft 2020-12)
# ---------------------------------------------------------------------------

SUPPORTED_KEYWORDS = {
    "$schema", "$id", "$defs", "$ref", "title", "description",
    "type", "properties", "required", "additionalProperties",
    "enum", "const", "pattern", "minLength", "minItems", "uniqueItems",
    "items", "format", "minimum",
}

_TYPE_CHECK = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "boolean": lambda v: isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "null": lambda v: v is None,
}


class SchemaValidator:
    def __init__(self, schema_dir: Path = SCHEMA_DIR):
        self.schema_dir = Path(schema_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def schema(self, name: str) -> Dict[str, Any]:
        if name not in self._cache:
            self._cache[name] = load_json(self.schema_dir / name, "Schema")
        return self._cache[name]

    def validate(self, instance: Any, schema_name: str) -> List[str]:
        errors: List[str] = []
        root = self.schema(schema_name)
        self._check(instance, root, root, "$", errors)
        return errors

    def _resolve(self, ref: str, root: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        file_part, _, frag = ref.partition("#")
        doc = self.schema(file_part) if file_part else root
        node: Any = doc
        if frag:
            for part in frag.lstrip("/").split("/"):
                node = node[part]
        return node, doc

    def _check(self, value: Any, schema: Dict[str, Any], root: Dict[str, Any], path: str, errors: List[str]) -> None:
        if "$ref" in schema:
            target, doc = self._resolve(schema["$ref"], root)
            self._check(value, target, doc, path, errors)
            return
        types = schema.get("type")
        if types is not None:
            tlist = types if isinstance(types, list) else [types]
            if not any(_TYPE_CHECK[t](value) for t in tlist):
                errors.append(f"{path}: expected {' or '.join(tlist)}, got {type(value).__name__}")
                return
        if "const" in schema and value != schema["const"]:
            errors.append(f"{path}: must be {schema['const']!r}")
        if "enum" in schema and value not in schema["enum"]:
            allowed = ", ".join("null" if e is None else str(e) for e in schema["enum"])
            errors.append(f"{path}: {value!r} is not one of: {allowed}")
        if isinstance(value, str):
            if "minLength" in schema and len(value.strip()) < schema["minLength"]:
                errors.append(f"{path}: must not be empty")
            if "pattern" in schema and not re.search(schema["pattern"], value):
                errors.append(f"{path}: {value!r} does not match {schema['pattern']}")
            if schema.get("format") == "date-time" and not DATE_TIME_RE.match(value):
                errors.append(f"{path}: {value!r} is not an ISO-8601 date-time")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                errors.append(f"{path}: must be >= {schema['minimum']}")
        if isinstance(value, list):
            if "minItems" in schema and len(value) < schema["minItems"]:
                errors.append(f"{path}: needs at least {schema['minItems']} item(s)")
            if schema.get("uniqueItems"):
                seen = [canonical(v) for v in value]
                if len(seen) != len(set(seen)):
                    errors.append(f"{path}: items must be unique")
            if "items" in schema:
                for i, item in enumerate(value):
                    self._check(item, schema["items"], root, f"{path}[{i}]", errors)
        if isinstance(value, dict):
            props = schema.get("properties", {})
            for req in schema.get("required", []):
                if req not in value:
                    errors.append(f"{path}: missing required field '{req}'")
            addl = schema.get("additionalProperties", True)
            for key, item in value.items():
                if key in props:
                    self._check(item, props[key], root, f"{path}.{key}", errors)
                elif addl is False:
                    errors.append(f"{path}: unknown field '{key}'")
                elif isinstance(addl, dict):
                    self._check(item, addl, root, f"{path}.{key}", errors)


def unsupported_keywords(schema: Any, found: Optional[Set[str]] = None, inside_properties: bool = False) -> Set[str]:
    """Keywords used in a schema that SchemaValidator does not implement."""
    found = set() if found is None else found
    if isinstance(schema, dict):
        for key, value in schema.items():
            if not inside_properties and key not in SUPPORTED_KEYWORDS:
                found.add(key)
            if key in ("properties", "$defs"):
                for sub in value.values():
                    unsupported_keywords(sub, found)
            elif isinstance(value, (dict, list)) and key not in ("enum", "const", "required"):
                unsupported_keywords(value, found)
    elif isinstance(schema, list):
        for item in schema:
            unsupported_keywords(item, found)
    return found


# ---------------------------------------------------------------------------
# Authority matrix
# ---------------------------------------------------------------------------


def load_matrix() -> Dict[str, Any]:
    return load_json(MATRIX_PATH, "Authority matrix")


def effective_matrix(ledger: Dict[str, Any], base: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Base matrix plus the investigation's own extensions (never overrides)."""
    matrix = copy.deepcopy(base if base is not None else load_matrix())
    ext = ledger.get("authority_extensions") or {}
    for kind in ("authorities", "claim_types"):
        for key, value in (ext.get(kind) or {}).items():
            if key not in matrix[kind]:
                item = dict(value)
                item["extension"] = True
                matrix[kind][key] = item
    return matrix


def requirement_kind(requirement: Optional[str], matrix: Dict[str, Any]) -> Optional[str]:
    if not requirement:
        return None
    if requirement in matrix["claim_types"]:
        return "claim_type"
    if requirement in matrix["authorities"]:
        return "authority"
    return None


def _assign(reqs: List[Dict[str, Any]], pool: List[Dict[str, Any]], used: Set[str]) -> bool:
    """Backtracking assignment: each requirement needs `min` distinct records."""
    if not reqs:
        return True
    req, rest = reqs[0], reqs[1:]
    candidates = [e for e in pool if e["authority"] in req["authorities"] and e["id"] not in used]
    need = req["min"]
    if len(candidates) < need:
        return False

    def choose(start: int, picked: List[str]) -> bool:
        if len(picked) == need:
            return _assign(rest, pool, used | set(picked))
        for i in range(start, len(candidates)):
            if choose(i + 1, picked + [candidates[i]["id"]]):
                return True
        return False

    return choose(0, [])


def authority_satisfied(
    requirement: Optional[str],
    evidence: Sequence[Dict[str, Any]],
    matrix: Dict[str, Any],
    observed_only: bool = False,
) -> Tuple[bool, str]:
    """Does this set of evidence meet the requirement (claim type or authority tag)?"""
    pool = [e for e in evidence if e.get("status") == "ACTIVE"]
    if observed_only:
        pool = [e for e in pool if e.get("epistemic_status") == "OBSERVED"]
    if not pool:
        return False, "no active evidence" + (" with OBSERVED status" if observed_only else "")
    kind = requirement_kind(requirement, matrix)
    if requirement is None or requirement == "":
        return True, "no specific authority required"
    if kind is None:
        return False, f"unknown claim type or authority '{requirement}'"
    if kind == "authority":
        ok = any(e["authority"] == requirement for e in pool)
        have = sorted({e["authority"] for e in pool})
        return ok, ("" if ok else f"requires authority '{requirement}', have {have}")
    clauses = matrix["claim_types"][requirement]["any_of"]
    for clause in clauses:
        if _assign(list(clause), pool, set()):
            return True, ""
    have = sorted({e["authority"] for e in pool})
    wanted = " OR ".join(
        " AND ".join(f"{r['min']}x[{'|'.join(r['authorities'])}]" for r in clause) for clause in clauses
    )
    return False, f"claim type '{requirement}' requires {wanted}; have {have}"


# ---------------------------------------------------------------------------
# Ledger helpers
# ---------------------------------------------------------------------------


def empty_ledger(meta: Dict[str, Any]) -> Dict[str, Any]:
    ledger: Dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "investigation": meta,
        "limitations": [],
        "authority_extensions": {"rationale": "", "authorities": {}, "claim_types": {}},
        "conclusion": {"summary": "", "claimed_state": None},
    }
    for name in COLLECTIONS:
        ledger[name] = []
    return ledger


def index(ledger: Dict[str, Any]) -> Dict[str, Tuple[str, Dict[str, Any]]]:
    out: Dict[str, Tuple[str, Dict[str, Any]]] = {}
    for name in COLLECTIONS:
        for rec in ledger.get(name, []):
            if isinstance(rec, dict) and isinstance(rec.get("id"), str):
                out.setdefault(rec["id"], (name, rec))
    return out


def next_id(ledger: Dict[str, Any], collection: str) -> str:
    prefix = PREFIX[collection]
    highest = 0
    for rec in ledger.get(collection, []):
        m = ID_RE.match(str(rec.get("id", "")))
        if m and m.group(1) == prefix:
            highest = max(highest, int(m.group(2)))
    return f"{prefix}-{highest + 1:04d}"


def get_record(ledger: Dict[str, Any], record_id: str, collection: Optional[str] = None) -> Dict[str, Any]:
    m = ID_RE.match(record_id or "")
    if not m:
        raise LedgerError(f"'{record_id}' is not a valid ID (expected like E-0001)")
    coll = COLLECTION_BY_PREFIX[m.group(1)]
    if collection and coll != collection:
        raise LedgerError(f"'{record_id}' is not a {collection} ID")
    for rec in ledger.get(coll, []):
        if rec.get("id") == record_id:
            return rec
    raise LedgerError(f"{record_id} does not exist in the ledger")


def defaults(collection: str, at: str) -> Dict[str, Any]:
    """Every field of a new record, with neutral values. Scripts overwrite what the agent supplies."""
    stamp = {"created_at": at, "updated_at": at, "history": []}
    if collection == "evidence":
        return {
            "claim": "", "epistemic_status": "OBSERVED", "source_type": "", "authority": "", "source": "",
            "artifact_identity": {"kind": "none", "value": ""}, "tool": "", "command_or_method": "",
            "timestamp": at, "scope": "", "limitations": [], "supports": [], "contradicts": [],
            "reproducible": False, "derived_from": [], "role": "observation", "collected_by": "single-agent",
            "status": "ACTIVE", "history": [],
        }
    if collection == "hypotheses":
        return {
            "statement": "", "kind": "primary", "alternatives": [], "prior_basis": "", "predictions": [],
            "supporting_evidence": [], "contradicting_evidence": [], "verification_evidence": [],
            "claim_type": None, "confounders": [], "status": "PROPOSED", "status_rationale": "", "next_probe": "",
            "confidence": {"label": "low", "rationale": ""}, **stamp,
        }
    if collection == "probes":
        return {
            "question": "", "purpose": "discriminate", "discriminates": [], "variables_changed": [],
            "variables_controlled": [], "expected_by_hypothesis": {}, "cost": "low", "risk": "low",
            "reversibility": "reversible", "external": False, "sensitive": False, "repeatable": True,
            "observation_authority": "", "interpretation_criterion": "", "requires_authorization": False,
            "authorization": None, "status": "PLANNED", "result_evidence": [], "outcome": "",
            "abandon_reason": "", **stamp,
        }
    if collection == "unknowns":
        return {
            "question": "", "status": "OPEN", "severity": "medium", "domain": "", "supporting_evidence": [],
            "contradicting_evidence": [], "required_authority": None, "requires_observation": False,
            "required_environment": "", "recommended_probes": [], "dependencies": [], "blocked_reason": "",
            "resolution_evidence": [], "resolution_rationale": "", **stamp,
        }
    if collection == "contradictions":
        return {
            "claim_a": "", "claim_b": "", "evidence_a": [], "evidence_b": [], "severity": "medium",
            "possible_explanations": [], "status": "OPEN", "resolution": "", "resolution_evidence": [], **stamp,
        }
    if collection == "obligations":
        return {
            "claim": "", "owner": "", "kind": "behavior", "severity": "critical", "required_cases": [],
            "case_evidence": {}, "required_authority": "", "applies_to": None, "construction_evidence": [],
            "verification_evidence": [], "status": "OPEN", "status_rationale": "", "blocking_unknowns": [],
            "blocking_contradictions": [], "dependencies": [], **stamp,
        }
    if collection == "findings":
        return {
            "claim": "", "epistemic_status": "INFERRED", "claim_type": None, "evidence": [],
            "verification_evidence": [], "contradicting_evidence": [], "hypotheses": [], "unknowns": [],
            "contradictions": [], "rationale": "", "scope": "", **stamp,
        }
    raise LedgerError(f"unknown collection {collection}")


OPTIONAL_FIELDS = {"evidence": {"environment", "output_capture"}}


def make_record(ledger: Dict[str, Any], collection: str, at: str, fields: Dict[str, Any]) -> Dict[str, Any]:
    """Create, seal and append a new record with the next free ID."""
    rec = defaults(collection, at)
    allowed = set(rec) | OPTIONAL_FIELDS.get(collection, set())
    for key, value in fields.items():
        if key in ("id", "record_digest", "history", "created_at", "updated_at", "invalidation"):
            raise LedgerError(f"field '{key}' is managed by the scripts and cannot be supplied")
        if collection == "evidence" and key == "status" and value != "ACTIVE":
            raise LedgerError("new evidence is always ACTIVE; use --invalidate afterwards")
        if key not in allowed:
            raise LedgerError(f"unknown field '{key}' for {collection} (allowed: {', '.join(sorted(allowed))})")
        rec[key] = value
    rec["id"] = next_id(ledger, collection)
    rec["history"] = [{"at": at, "action": "created", "detail": ""}]
    seal(rec)
    ledger[collection].append(rec)
    return rec


def update_record(rec: Dict[str, Any], fields: Dict[str, Any], at: str, detail: str = "") -> List[str]:
    """Apply field changes to an existing record; returns the names of fields that changed."""
    changed = []
    for key, value in fields.items():
        if key in ("id", "record_digest", "history", "created_at", "updated_at"):
            raise LedgerError(f"field '{key}' is managed by the scripts and cannot be set")
        if key not in rec:
            raise LedgerError(f"unknown field '{key}' for {rec['id']}")
        if rec[key] != value:
            rec[key] = value
            changed.append(key)
    if not changed:
        raise LedgerError(f"no change: {rec['id']} already has these values")
    touch(rec, at, "updated", detail or ", ".join(changed))
    return changed


def seal(record: Dict[str, Any]) -> Dict[str, Any]:
    record["record_digest"] = compute_digest(record)
    return record


def touch(record: Dict[str, Any], at: str, action: str, detail: str = "") -> None:
    if "updated_at" in record:
        record["updated_at"] = at
    record.setdefault("history", []).append({"at": at, "action": action, "detail": detail})
    seal(record)


def evidence_by_ids(ledger: Dict[str, Any], ids: Iterable[str]) -> List[Dict[str, Any]]:
    wanted = set(ids)
    return [e for e in ledger.get("evidence", []) if e.get("id") in wanted]


def active_ids(ledger: Dict[str, Any], ids: Iterable[str]) -> List[str]:
    return [e["id"] for e in evidence_by_ids(ledger, ids) if e.get("status") == "ACTIVE"]


# ---------------------------------------------------------------------------
# Semantic validation
# ---------------------------------------------------------------------------


class Issue:
    __slots__ = ("level", "code", "record", "message")

    def __init__(self, level: str, code: str, record: str, message: str):
        self.level, self.code, self.record, self.message = level, code, record, message

    def key(self) -> Tuple[str, str, str, str]:
        return (self.level, self.code, self.record, self.message)

    def as_dict(self) -> Dict[str, str]:
        return {"level": self.level, "code": self.code, "record": self.record, "message": self.message}

    def __str__(self) -> str:
        return f"{self.level.upper()} {self.code} {self.record}: {self.message}"


def iter_refs(collection: str, rec: Dict[str, Any]) -> Iterator[Tuple[str, str, str]]:
    """Yield (field, referenced_id, allowed_prefixes) for every reference in a record."""

    def lst(field: str, allowed: str) -> Iterator[Tuple[str, str, str]]:
        for ref in rec.get(field) or []:
            yield field, ref, allowed

    if collection == "evidence":
        yield from lst("supports", "HPUCOF")
        yield from lst("contradicts", "HPUCOF")
        yield from lst("derived_from", "E")
    elif collection == "hypotheses":
        yield from lst("alternatives", "H")
        for f in ("supporting_evidence", "contradicting_evidence", "verification_evidence"):
            yield from lst(f, "E")
        for p in rec.get("predictions") or []:
            for ref in p.get("evidence") or []:
                yield "predictions.evidence", ref, "E"
    elif collection == "probes":
        yield from lst("discriminates", "H")
        yield from lst("result_evidence", "E")
        for key in (rec.get("expected_by_hypothesis") or {}):
            yield "expected_by_hypothesis", key, "H"
    elif collection == "unknowns":
        for f in ("supporting_evidence", "contradicting_evidence", "resolution_evidence"):
            yield from lst(f, "E")
        yield from lst("dependencies", "U")
    elif collection == "contradictions":
        for f in ("evidence_a", "evidence_b", "resolution_evidence"):
            yield from lst(f, "E")
        for x in rec.get("possible_explanations") or []:
            for ref in x.get("evidence") or []:
                yield "possible_explanations.evidence", ref, "E"
    elif collection == "obligations":
        for f in ("construction_evidence", "verification_evidence"):
            yield from lst(f, "E")
        for refs in (rec.get("case_evidence") or {}).values():
            for ref in refs or []:
                yield "case_evidence", ref, "E"
        yield from lst("blocking_unknowns", "U")
        yield from lst("blocking_contradictions", "C")
        yield from lst("dependencies", "O")
    elif collection == "findings":
        for f in ("evidence", "verification_evidence", "contradicting_evidence"):
            yield from lst(f, "E")
        yield from lst("hypotheses", "H")
        yield from lst("unknowns", "U")
        yield from lst("contradictions", "C")


def _find_cycle(graph: Dict[str, List[str]]) -> Optional[List[str]]:
    WHITE, GREY, BLACK = 0, 1, 2
    color = {n: WHITE for n in graph}
    stack: List[str] = []

    def visit(n: str) -> Optional[List[str]]:
        color[n] = GREY
        stack.append(n)
        for m in graph.get(n, []):
            if m not in color:
                continue
            if color[m] == GREY:
                return stack[stack.index(m):] + [m]
            if color[m] == WHITE:
                found = visit(m)
                if found:
                    return found
        stack.pop()
        color[n] = BLACK
        return None

    for node in sorted(graph):
        if color[node] == WHITE:
            found = visit(node)
            if found:
                return found
    return None


def validate(ledger: Dict[str, Any], validator: Optional[SchemaValidator] = None) -> List[Issue]:
    """All structural and semantic problems in the ledger. Errors block evaluation."""
    validator = validator or SchemaValidator()
    issues: List[Issue] = []

    def err(code: str, rid: str, msg: str) -> None:
        issues.append(Issue("error", code, rid, msg))

    def warn(code: str, rid: str, msg: str) -> None:
        issues.append(Issue("warning", code, rid, msg))

    for msg in validator.validate(ledger, "investigation.schema.json"):
        err("V001", "ledger", f"schema: {msg}")
    if issues:
        return issues  # structural errors first; semantic rules assume a well-formed ledger

    try:
        matrix = effective_matrix(ledger)
    except LedgerError as exc:
        err("V010", "matrix", str(exc))
        return issues

    ext = ledger.get("authority_extensions") or {}
    if (ext.get("authorities") or ext.get("claim_types")) and not str(ext.get("rationale", "")).strip():
        err("V011", "authority_extensions", "extensions need a rationale")
    base = load_matrix()
    for kind in ("authorities", "claim_types"):
        for key in (ext.get(kind) or {}):
            if key in base[kind]:
                err("V012", "authority_extensions", f"extension '{key}' would override the base matrix; choose a new name")
    for key, ct in (ext.get("claim_types") or {}).items():
        for clause in ct.get("any_of", []):
            for req in clause:
                for a in req.get("authorities", []):
                    if a not in matrix["authorities"]:
                        err("V013", "authority_extensions", f"claim type '{key}' uses unknown authority '{a}'")

    # IDs: duplicates and prefixes
    seen: Dict[str, str] = {}
    for name in COLLECTIONS:
        for rec in ledger.get(name, []):
            rid = rec.get("id", "?")
            m = ID_RE.match(str(rid))
            if not m or COLLECTION_BY_PREFIX.get(m.group(1)) != name:
                err("V003", str(rid), f"ID does not belong in '{name}'")
            if rid in seen:
                err("V002", str(rid), "duplicate ID")
            seen[rid] = name
            if rec.get("record_digest") and compute_digest(rec) != rec["record_digest"]:
                err("V005", str(rid), "record_digest mismatch: the record was edited outside the scripts. "
                    "Re-record it through the scripts, or run validate_ledger.py --reseal after reviewing the edit")
    idx = index(ledger)

    # References
    for name in COLLECTIONS:
        for rec in ledger.get(name, []):
            for field, ref, allowed in iter_refs(name, rec):
                m = ID_RE.match(str(ref))
                if not m or m.group(1) not in allowed:
                    err("V004", rec.get("id", "?"), f"{field}: '{ref}' is not a valid reference here")
                elif ref not in idx:
                    err("V004", rec.get("id", "?"), f"{field}: '{ref}' does not exist")
                elif ref == rec.get("id"):
                    err("V004", rec.get("id", "?"), f"{field}: a record cannot reference itself")

    ev = {e["id"]: e for e in ledger.get("evidence", []) if "id" in e}

    def active(ids: Iterable[str]) -> List[Dict[str, Any]]:
        return [ev[i] for i in ids if i in ev and ev[i].get("status") == "ACTIVE"]

    def known_requirement(rid: str, field: str, value: Optional[str]) -> None:
        if value and requirement_kind(value, matrix) is None:
            err("V014", rid, f"{field} '{value}' is neither a claim type nor an authority in the matrix")

    # Cycles
    for coll, field in (("unknowns", "dependencies"), ("obligations", "dependencies"), ("evidence", "derived_from")):
        graph = {r["id"]: list(r.get(field) or []) for r in ledger.get(coll, []) if "id" in r}
        cyc = _find_cycle(graph)
        if cyc:
            err("V006", cyc[0], f"forbidden cycle in {coll}.{field}: {' -> '.join(cyc)}")

    # Evidence
    for e in ledger.get("evidence", []):
        rid = e.get("id", "?")
        st, auth = e.get("source_type"), e.get("authority")
        if auth not in matrix["authorities"]:
            err("E02", rid, f"authority '{auth}' is not in the authority matrix")
        elif st not in matrix["authorities"][auth]["source_types"]:
            err("E03", rid, f"authority '{auth}' cannot come from source_type '{st}' "
                f"(allowed: {matrix['authorities'][auth]['source_types']})")
        if e.get("epistemic_status") == "DERIVED" and not e.get("derived_from"):
            err("E01", rid, "DERIVED evidence must list derived_from")
        if e.get("epistemic_status") == "OBSERVED" and e.get("derived_from"):
            warn("E01", rid, "OBSERVED evidence lists derived_from; should it be DERIVED?")
        for parent in e.get("derived_from") or []:
            pm, sm = ID_RE.match(parent), ID_RE.match(rid)
            if pm and sm and int(pm.group(2)) >= int(sm.group(2)):
                err("E09", rid, f"derived_from {parent} must be an earlier evidence record")
        if st in EXECUTED_SOURCE_TYPES:
            if not str(e.get("tool", "")).strip():
                err("E04", rid, f"source_type '{st}' requires 'tool'")
            if not str(e.get("command_or_method", "")).strip():
                err("E04", rid, f"source_type '{st}' requires 'command_or_method'")
        if st in ("document", "user-observation") and not str(e.get("source", "")).strip():
            err("E04", rid, f"source_type '{st}' requires 'source'")
        ai = e.get("artifact_identity") or {}
        if st in ARTIFACT_REQUIRED_SOURCE_TYPES and ai.get("kind") in (None, "none"):
            err("E05", rid, f"source_type '{st}' requires artifact_identity (hash, commit, version or file)")
        if ai.get("kind") == "sha256" and not SHA256_RE.match(str(ai.get("value", ""))):
            err("E05", rid, "artifact_identity sha256 value must be 64 lowercase hex characters")
        if ai.get("kind") not in (None, "none") and not str(ai.get("value", "")).strip():
            err("E05", rid, "artifact_identity value is empty")
        if st == "document" and ai.get("kind") in (None, "none"):
            warn("E05", rid, "document evidence without URL, version or hash is hard to re-check")
        if e.get("reproducible") and not str(e.get("command_or_method", "")).strip():
            err("E06", rid, "reproducible evidence must record command_or_method")
        if e.get("status") == "INVALIDATED" and not e.get("invalidation"):
            err("E07", rid, "INVALIDATED evidence needs an invalidation reason")
        if e.get("status") == "ACTIVE" and e.get("invalidation"):
            err("E07", rid, "ACTIVE evidence carries an invalidation record")
        if set(e.get("supports") or []) & set(e.get("contradicts") or []):
            err("E08", rid, "the same record cannot be both supported and contradicted")
        if st == "user-observation" and auth != "user-report":
            err("E11", rid, "user-observation evidence must use authority 'user-report'")
        oc = e.get("output_capture")
        if oc and oc.get("shown_lines", 0) > oc.get("total_lines", 0):
            err("E12", rid, "output_capture.shown_lines exceeds total_lines")
        if oc and oc.get("method") == "full" and oc.get("shown_lines") != oc.get("total_lines"):
            err("E12", rid, "output_capture method 'full' must show every line; declare head/tail/grep/summary")

    # Hypotheses
    statements: Dict[str, str] = {}
    for h in ledger.get("hypotheses", []):
        rid, status = h.get("id", "?"), h.get("status")
        sup, con = active(h.get("supporting_evidence") or []), active(h.get("contradicting_evidence") or [])
        if set(h.get("supporting_evidence") or []) & set(h.get("contradicting_evidence") or []):
            err("H07", rid, "the same evidence cannot both support and contradict")
        if status == "REJECTED" and not con:
            err("H02", rid, "REJECTED requires active contradicting_evidence")
        if status == "CONTRADICTED" and not con:
            err("H06", rid, "CONTRADICTED requires active contradicting_evidence")
        if status == "SUPPORTED" and not sup:
            err("H05", rid, "SUPPORTED requires active supporting_evidence")
        if status == "VERIFIED":
            known_requirement(rid, "claim_type", h.get("claim_type"))
            if not h.get("claim_type"):
                err("H03", rid, "VERIFIED requires a claim_type so authority can be checked")
            else:
                ok, why = authority_satisfied(h["claim_type"], active(h.get("verification_evidence") or []), matrix)
                if not ok:
                    err("H03", rid, f"VERIFIED without sufficient verification_evidence: {why}")
        if status == "OUT_OF_SCOPE" and not str(h.get("status_rationale", "")).strip():
            err("H10", rid, "OUT_OF_SCOPE requires status_rationale")
        conf = (h.get("confidence") or {}).get("label")
        if conf == "high" and (not sup or status in ("CONTRADICTED", "REJECTED")):
            err("H04", rid, "confidence 'high' requires active supporting evidence and no contradiction")
        if conf in ("moderate", "high") and not str((h.get("confidence") or {}).get("rationale", "")).strip():
            err("H04", rid, f"confidence '{conf}' requires a rationale")
        for p in h.get("predictions") or []:
            if not str(p.get("id", "")).startswith(f"{rid}.P"):
                err("H08", rid, f"prediction id '{p.get('id')}' must start with {rid}.P")
            if p.get("result") in ("confirmed", "refuted") and not active(p.get("evidence") or []):
                err("H08", rid, f"prediction {p.get('id')} marked {p.get('result')} without active evidence")
        norm = " ".join(str(h.get("statement", "")).lower().split())
        if norm in statements:
            warn("H09", rid, f"same statement as {statements[norm]}; merge or differentiate")
        statements.setdefault(norm, rid)
        if status in ("PROPOSED", "TESTING") and not h.get("predictions"):
            warn("H11", rid, "hypothesis has no observable predictions yet")

    # Probes
    hyp_ids = {h.get("id") for h in ledger.get("hypotheses", [])}
    for p in ledger.get("probes", []):
        rid, status = p.get("id", "?"), p.get("status")
        disc = list(p.get("discriminates") or [])
        exp = p.get("expected_by_hypothesis") or {}
        if not disc:
            err("P01", rid, "a probe must name the hypotheses it tests (discriminates)")
        if set(exp) != set(disc):
            err("P02", rid, f"expected_by_hypothesis must cover exactly {sorted(disc)}; has {sorted(exp)}")
        if p.get("purpose") == "discriminate":
            if len(disc) < 2:
                warn("P06", rid, "purpose 'discriminate' with fewer than 2 hypotheses")
            elif len({" ".join(str(v).lower().split()) for v in exp.values()}) < 2:
                warn("P06", rid, "every hypothesis predicts the same outcome; this probe cannot discriminate")
        risky = p.get("reversibility") == "irreversible" or p.get("risk") == "high" or p.get("external") or p.get("sensitive")
        if risky and not p.get("requires_authorization"):
            err("P03", rid, "irreversible, high-risk, external or sensitive probes must set requires_authorization")
        if status in ("RUNNING", "DONE") and p.get("requires_authorization") and not p.get("authorization"):
            err("P04", rid, f"{status} without recorded authorization")
        if status == "DONE":
            if not active(p.get("result_evidence") or []):
                err("P05", rid, "DONE requires active result_evidence")
            if not str(p.get("outcome", "")).strip():
                err("P05", rid, "DONE requires an outcome (interpretation against the criterion)")
        if status == "ABANDONED" and not str(p.get("abandon_reason", "")).strip():
            err("P05", rid, "ABANDONED requires abandon_reason")
        if p.get("observation_authority") and p["observation_authority"] not in matrix["authorities"]:
            err("P07", rid, f"observation_authority '{p['observation_authority']}' is not in the matrix")
        for h in disc:
            if h not in hyp_ids:
                pass  # already reported as broken reference

    # Unknowns
    for u in ledger.get("unknowns", []):
        rid, status = u.get("id", "?"), u.get("status")
        known_requirement(rid, "required_authority", u.get("required_authority"))
        if set(u.get("supporting_evidence") or []) & set(u.get("contradicting_evidence") or []):
            err("U05", rid, "the same evidence cannot both support and contradict")
        if status == "RESOLVED":
            res = active(u.get("resolution_evidence") or [])
            if not res:
                err("U01", rid, "RESOLVED requires active resolution_evidence (inference does not close an unknown)")
            else:
                ok, why = authority_satisfied(u.get("required_authority"), res, matrix,
                                              observed_only=bool(u.get("requires_observation")))
                if not ok:
                    err("U01", rid, f"resolution evidence lacks required authority: {why}")
            if not str(u.get("resolution_rationale", "")).strip():
                err("U01", rid, "RESOLVED requires resolution_rationale")
            for dep in u.get("dependencies") or []:
                d = idx.get(dep)
                if d and d[1].get("status") not in CLOSED_UNKNOWN:
                    err("U07", rid, f"RESOLVED while dependency {dep} is still {d[1].get('status')}")
        if status == "CONTRADICTED" and not active(u.get("contradicting_evidence") or []):
            err("U02", rid, "CONTRADICTED requires active contradicting_evidence")
        if status == "OUT_OF_SCOPE" and not str(u.get("resolution_rationale", "")).strip():
            err("U03", rid, "OUT_OF_SCOPE requires resolution_rationale (it will appear in the report)")
        if status == "BLOCKED" and not str(u.get("blocked_reason", "")).strip():
            err("U04", rid, "BLOCKED requires blocked_reason")

    # Contradictions
    for c in ledger.get("contradictions", []):
        rid, status = c.get("id", "?"), c.get("status")
        sides = set(c.get("evidence_a") or []) | set(c.get("evidence_b") or [])
        if not sides:
            err("C01", rid, "a contradiction must cite evidence on at least one side")
        for x in c.get("possible_explanations") or []:
            if x.get("status") in ("ruled-out", "supported") and not active(x.get("evidence") or []):
                err("C03", rid, f"explanation '{x.get('category')}' marked {x.get('status')} without active evidence")
        if status == "RESOLVED":
            new = [e for e in active(c.get("resolution_evidence") or []) if e["id"] not in sides]
            if not new:
                err("C02", rid, "RESOLVED requires new active resolution_evidence beyond the conflicting evidence itself "
                    "(choosing the more convincing side is not a resolution)")
            if not any(x.get("status") == "supported" for x in c.get("possible_explanations") or []):
                err("C02", rid, "RESOLVED requires at least one explanation with status 'supported'")
            if not str(c.get("resolution", "")).strip():
                err("C02", rid, "RESOLVED requires a resolution text")
        if status == "OUT_OF_SCOPE" and not str(c.get("resolution", "")).strip():
            err("C04", rid, "OUT_OF_SCOPE requires a resolution text explaining why")

    # Obligations
    obl = {o["id"]: o for o in ledger.get("obligations", []) if "id" in o}
    for o in ledger.get("obligations", []):
        rid, status = o.get("id", "?"), o.get("status")
        known_requirement(rid, "required_authority", o.get("required_authority"))
        cases = list(o.get("required_cases") or [])
        ce = o.get("case_evidence") or {}
        for key in ce:
            if key not in cases:
                err("O06", rid, f"case_evidence has '{key}' which is not a required case")
        overlap = set(o.get("verification_evidence") or []) & set(o.get("construction_evidence") or [])
        if overlap:
            err("O08", rid, f"evidence {sorted(overlap)} is both construction and verification; verification must be separate")
        if status == "CLOSED":
            ver = active(o.get("verification_evidence") or [])
            if not ver:
                err("O02", rid, "CLOSED requires active verification_evidence")
            else:
                ok, why = authority_satisfied(o.get("required_authority"), ver, matrix)
                if not ok:
                    err("O02", rid, f"verification lacks required authority: {why}")
            for case in cases:
                if not active(ce.get(case) or []):
                    err("O02", rid, f"required case '{case}' has no active evidence")
            for uid in o.get("blocking_unknowns") or []:
                u = idx.get(uid)
                if u and u[1].get("status") not in CLOSED_UNKNOWN:
                    err("O02", rid, f"closed with blocker {uid} still {u[1].get('status')}")
            for cid in o.get("blocking_contradictions") or []:
                cc = idx.get(cid)
                if cc and cc[1].get("status") not in CLOSED_CONTRADICTION:
                    err("O02", rid, f"closed with blocker {cid} still {cc[1].get('status')}")
            for dep in o.get("dependencies") or []:
                if dep in obl and obl[dep].get("status") != "CLOSED":
                    err("O02", rid, f"closed while dependency {dep} is {obl[dep].get('status')}")
            target = o.get("applies_to")
            if target:
                for e in ver:
                    if (e.get("artifact_identity") or {}).get("value") != target:
                        err("O07", rid, f"verification {e['id']} is about "
                            f"'{(e.get('artifact_identity') or {}).get('value')}', not applies_to '{target}' (stale proof)")
        if status == "FAILED":
            if not active(o.get("verification_evidence") or []):
                err("O03", rid, "FAILED requires the verification_evidence that showed the failure")
            if not str(o.get("status_rationale", "")).strip():
                err("O03", rid, "FAILED requires status_rationale")
        if status in ("WAIVED", "BLOCKED") and not str(o.get("status_rationale", "")).strip():
            err("O04", rid, f"{status} requires status_rationale")

    # Findings
    for f in ledger.get("findings", []):
        rid, st = f.get("id", "?"), f.get("epistemic_status")
        basis = active(f.get("evidence") or [])
        known_requirement(rid, "claim_type", f.get("claim_type"))
        if st == "OBSERVED" and not any(e.get("epistemic_status") == "OBSERVED" for e in basis):
            err("F01", rid, "OBSERVED finding must cite active OBSERVED evidence")
        if st == "DERIVED" and not any(e.get("epistemic_status") == "DERIVED" for e in basis):
            err("F02", rid, "DERIVED finding must cite active DERIVED evidence")
        if st == "INFERRED" and not (basis or f.get("hypotheses")):
            err("F03", rid, "INFERRED finding must cite the evidence or hypotheses it is inferred from")
        if st in ("ASSUMED", "OUT_OF_SCOPE") and not str(f.get("rationale", "")).strip():
            err("F04", rid, f"{st} finding requires a rationale")
        if st == "CONTRADICTED" and not (f.get("contradictions") or active(f.get("contradicting_evidence") or [])):
            err("F05", rid, "CONTRADICTED finding must cite a contradiction or contradicting evidence")
        if st == "UNKNOWN" and not f.get("unknowns"):
            err("F06", rid, "UNKNOWN finding must cite the unknown (U-) that tracks it")
        if st == "VERIFIED":
            builders = [e["id"] for e in active(f.get("verification_evidence") or []) if e.get("role") == "construction"]
            if builders:
                err("F09", rid, f"construction evidence {builders} cannot verify a finding; verify it by a separate route")
            if not f.get("claim_type"):
                err("F07", rid, "VERIFIED finding requires claim_type")
            else:
                ok, why = authority_satisfied(f["claim_type"], active(f.get("verification_evidence") or []), matrix)
                if not ok:
                    err("F07", rid, f"VERIFIED without sufficient verification_evidence: {why}")
        if st == "REJECTED" and not active(f.get("contradicting_evidence") or []):
            err("F08", rid, "REJECTED finding requires active contradicting_evidence")

    # Structure warnings
    mode = ledger["investigation"].get("mode")
    if mode in ("investigative", "rigorous"):
        if not ledger.get("obligations"):
            warn("W01", "ledger", "no obligations: completion cannot be verified until requirements become obligations")
        if mode == "rigorous" and not any(h.get("kind") == "measurement-error" for h in ledger.get("hypotheses", [])):
            warn("W02", "ledger", "rigorous mode: consider a measurement-error/interpretation-error hypothesis, "
                 "or record why it does not apply in limitations")

    claimed = (ledger.get("conclusion") or {}).get("claimed_state")
    if claimed and not any(i.level == "error" for i in issues):
        computed = evaluate(ledger, _issues=issues)["state"]
        if claimed != computed:
            err("X01", "conclusion", f"claimed_state {claimed} does not match the computed state {computed}")
    return issues


def errors_only(issues: Iterable[Issue]) -> List[Issue]:
    return [i for i in issues if i.level == "error"]


# ---------------------------------------------------------------------------
# Completion
# ---------------------------------------------------------------------------

GATE_TEXT = {
    "G1": "At least one obligation exists",
    "G2": "Every critical obligation is CLOSED",
    "G3": "No critical unknown is open",
    "G4": "No critical contradiction is open",
    "G5": "Verification is separate from construction for every closed obligation",
    "G6": "Limitations are recorded",
    "G7": "Nothing outside the critical set is pending, waived or out of scope",
    "G8": "Mode requirements are met",
}


def evaluate(ledger: Dict[str, Any], _issues: Optional[List[Issue]] = None) -> Dict[str, Any]:
    """Compute the final state. Never reads a stored final state."""
    issues = _issues if _issues is not None else validate(ledger)
    errs = [i for i in errors_only(issues) if i.code != "X01"]  # a stale claim never hides the computed state
    if errs:
        raise LedgerError(
            "Ledger has validation errors; fix them before evaluating:\n" + "\n".join(str(i) for i in errs),
            exit_code=2,
        )
    mode = ledger["investigation"]["mode"]
    obligations = ledger.get("obligations", [])
    unknowns = ledger.get("unknowns", [])
    contradictions = ledger.get("contradictions", [])
    findings = ledger.get("findings", [])
    hypotheses = ledger.get("hypotheses", [])
    ev = {e["id"]: e for e in ledger.get("evidence", [])}

    crit = [o for o in obligations if o["severity"] == "critical"]
    closed = [o for o in obligations if o["status"] == "CLOSED"]
    gates: Dict[str, Tuple[bool, List[str]]] = {}

    def gate(gid: str, failures: List[str]) -> None:
        gates[gid] = (not failures, failures)

    gate("G1", [] if obligations else ["no obligations recorded"])
    gate("G2", [f"{o['id']} is {o['status']}" for o in crit if o["status"] != "CLOSED"])
    gate("G3", [f"{u['id']} is {u['status']}" for u in unknowns
                if u["severity"] == "critical" and u["status"] in OPEN_UNKNOWN])
    gate("G4", [f"{c['id']} is {c['status']}" for c in contradictions
                if c["severity"] == "critical" and c["status"] in OPEN_CONTRADICTION])

    g5: List[str] = []
    for o in closed:
        ver = set(o.get("verification_evidence") or [])
        con = set(o.get("construction_evidence") or [])
        if not ver:
            g5.append(f"{o['id']} has no verification evidence")
        if ver & con:
            g5.append(f"{o['id']} reuses construction evidence as verification")
        if mode == "rigorous":
            routes = {(ev[i].get("tool"), ev[i].get("command_or_method")) for i in con if i in ev}
            same = [i for i in sorted(ver) if i in ev and (ev[i].get("tool"), ev[i].get("command_or_method")) in routes]
            if same:
                g5.append(f"{o['id']}: verification {same} repeats the construction tool and command (not an independent route)")
    gate("G5", g5)
    gate("G6", [] if any(str(x).strip() for x in ledger.get("limitations", [])) else ["no limitations recorded"])

    g7: List[str] = []
    g7 += [f"{o['id']} ({o['severity']}) is {o['status']}" for o in obligations if o["status"] != "CLOSED"]
    g7 += [f"{u['id']} ({u['severity']}) is {u['status']}" for u in unknowns
           if u["severity"] in ("high", "critical") and u["status"] in OPEN_UNKNOWN | {"OUT_OF_SCOPE"}]
    g7 += [f"{c['id']} ({c['severity']}) is {c['status']}" for c in contradictions
           if c["severity"] in ("high", "critical") and c["status"] in OPEN_CONTRADICTION | {"OUT_OF_SCOPE"}]
    gate("G7", g7)

    g8: List[str] = []
    kinds = [h["kind"] for h in hypotheses if h["status"] != "OUT_OF_SCOPE"]
    if mode == "investigative":
        if len(kinds) < 2 or all(k == "primary" for k in kinds):
            g8.append("investigative mode needs at least 2 hypotheses, one of them not 'primary'")
    if mode == "rigorous":
        for needed in ("primary", "null", "alternative"):
            if needed not in kinds:
                g8.append(f"rigorous mode needs a '{needed}' hypothesis")
        if not any(p["purpose"] == "counterexample-search" and p["status"] == "DONE" for p in ledger.get("probes", [])):
            g8.append("rigorous mode needs a completed counterexample-search probe")
        reviews = [e for e in ev.values() if e["role"] == "review" and e["status"] == "ACTIVE"]
        builders = {e["collected_by"] for e in ev.values() if e["role"] == "construction"}
        if not builders:
            builders = {e["collected_by"] for e in ev.values() if e["role"] == "observation"}
        if not any(r["collected_by"] not in builders for r in reviews):
            g8.append("rigorous mode needs review evidence from a collector other than the producer(s) "
                      f"{sorted(builders) or ['(none)']}")
        ver_ids: Set[str] = set()
        for o in closed:
            ver_ids |= set(o.get("verification_evidence") or [])
        for f in findings:
            if f["epistemic_status"] == "VERIFIED":
                ver_ids |= set(f.get("verification_evidence") or [])
        not_repro = sorted(i for i in ver_ids if i in ev and not ev[i].get("reproducible"))
        if not_repro:
            g8.append(f"rigorous mode needs reproducible verification evidence; not reproducible: {not_repro}")
    gate("G8", g8)

    def ok(*ids: str) -> bool:
        return all(gates[g][0] for g in ids)

    reasons: List[str] = []
    failed = [o for o in crit if o["status"] == "FAILED"]
    blocked_o = [o for o in crit if o["status"] == "BLOCKED"]
    blocked_u = [u for u in unknowns if u["severity"] == "critical" and u["status"] == "BLOCKED"]
    verified_findings = [f for f in findings if f["epistemic_status"] == "VERIFIED"]
    mitig = [o for o in obligations if o["kind"] == "mitigation" and o["status"] == "CLOSED"]
    root_open = [o for o in obligations if o["kind"] == "root-cause" and o["status"] != "CLOSED"]

    if failed:
        state = "FAILED"
        reasons = [f"critical obligation {o['id']} FAILED: {o.get('status_rationale', '')}" for o in failed]
    elif blocked_o or blocked_u:
        state = "BLOCKED"
        reasons = [f"{x['id']} is BLOCKED: {x.get('status_rationale') or x.get('blocked_reason', '')}" for x in blocked_o + blocked_u]
    elif ok("G1", "G2", "G3", "G4", "G5", "G6") and ok("G7", "G8"):
        state = "COMPLETE_VERIFIED"
        reasons = ["all gates passed"]
    elif ok("G1", "G2", "G3", "G4", "G5", "G6"):
        state = "COMPLETE_WITH_LIMITATIONS"
        reasons = gates["G7"][1] + gates["G8"][1]
    elif mitig and root_open:
        state = "MITIGATED_NOT_RESOLVED"
        reasons = [f"mitigation {o['id']} closed" for o in mitig] + [f"root cause {o['id']} is {o['status']}" for o in root_open]
    elif closed or verified_findings:
        state = "PARTIALLY_VERIFIED"
        reasons = [msg for g in ("G1", "G2", "G3", "G4", "G5", "G6") for msg in gates[g][1]]
    else:
        state = "INCONCLUSIVE"
        reasons = ["no obligation is closed and no finding is VERIFIED"] + [
            msg for g in ("G1", "G2", "G3", "G4") for msg in gates[g][1]]

    counts = {name: len(ledger.get(name, [])) for name in COLLECTIONS}
    counts["evidence_active"] = sum(1 for e in ev.values() if e["status"] == "ACTIVE")
    counts["obligations_closed"] = len(closed)
    counts["unknowns_open"] = sum(1 for u in unknowns if u["status"] in OPEN_UNKNOWN)
    counts["contradictions_open"] = sum(1 for c in contradictions if c["status"] in OPEN_CONTRADICTION)
    return {
        "state": state,
        "mode": mode,
        "reasons": reasons,
        "gates": [
            {"id": gid, "description": GATE_TEXT[gid], "passed": gates[gid][0], "failures": gates[gid][1]}
            for gid in sorted(gates)
        ],
        "counts": counts,
        "warnings": [i.as_dict() for i in issues if i.level == "warning"],
        "ledger_digest": ledger_digest(ledger),
    }


# ---------------------------------------------------------------------------
# Invalidation
# ---------------------------------------------------------------------------


def invalidate_evidence(ledger: Dict[str, Any], eid: str, reason: str, at: str) -> List[str]:
    """Mark evidence INVALIDATED and reopen every conclusion that relied on it."""
    e = get_record(ledger, eid, "evidence")
    if e["status"] == "INVALIDATED":
        raise LedgerError(f"{eid} is already invalidated")
    if not reason.strip():
        raise LedgerError("--reason is required to invalidate evidence")
    e["status"] = "INVALIDATED"
    e["invalidation"] = {"at": at, "reason": reason}
    touch(e, at, "invalidated", reason)
    changes = [f"{eid}: INVALIDATED"]
    # A deterministic derivation from invalid input is invalid too.
    for child in ledger.get("evidence", []):
        if child["status"] == "ACTIVE" and eid in child.get("derived_from", []):
            changes += invalidate_evidence(ledger, child["id"], f"derived from {eid}, which was invalidated", at)
    note = f"reopened because {eid} was invalidated: {reason}"

    for u in ledger.get("unknowns", []):
        if u["status"] == "RESOLVED" and eid in u.get("resolution_evidence", []):
            u["status"] = "OPEN"
            touch(u, at, "reopened", note)
            changes.append(f"{u['id']}: RESOLVED -> OPEN")
    for c in ledger.get("contradictions", []):
        if c["status"] == "RESOLVED" and eid in c.get("resolution_evidence", []):
            c["status"] = "OPEN"
            touch(c, at, "reopened", note)
            changes.append(f"{c['id']}: RESOLVED -> OPEN")
    for o in ledger.get("obligations", []):
        uses = eid in o.get("verification_evidence", []) or any(eid in v for v in (o.get("case_evidence") or {}).values())
        if o["status"] in ("CLOSED", "FAILED") and uses:
            changes.append(f"{o['id']}: {o['status']} -> OPEN")
            o["status"] = "OPEN"
            touch(o, at, "reopened", note)
    for f in ledger.get("findings", []):
        if f["epistemic_status"] == "VERIFIED" and eid in f.get("verification_evidence", []):
            u = make_record(ledger, "unknowns", at, {
                "question": f"Does this still hold after {eid} was invalidated? {f['claim']}",
                "severity": "high",
                "required_authority": f.get("claim_type"),
                "domain": "reopened-finding",
            })
            f["epistemic_status"] = "UNKNOWN"
            f["unknowns"] = sorted(set(f.get("unknowns", [])) | {u["id"]})
            touch(f, at, "reopened", note)
            changes.append(f"{f['id']}: VERIFIED -> UNKNOWN (tracked by new {u['id']})")
    for h in ledger.get("hypotheses", []):
        relied = (h["status"] == "VERIFIED" and eid in h.get("verification_evidence", [])) or (
            h["status"] in ("REJECTED", "CONTRADICTED") and eid in h.get("contradicting_evidence", [])) or (
            h["status"] == "SUPPORTED" and eid in h.get("supporting_evidence", []))
        if relied:
            changes.append(f"{h['id']}: {h['status']} -> TESTING")
            h["status"] = "TESTING"
            touch(h, at, "reopened", note)
    return changes


# ---------------------------------------------------------------------------
# Probe ranking
# ---------------------------------------------------------------------------

_WEIGHT = {"low": 0, "medium": 1, "high": 2}


def rank_probes(ledger: Dict[str, Any]) -> List[Tuple[int, Dict[str, Any]]]:
    """Planned probes, most informative per unit of cost and risk first."""
    out = []
    for p in ledger.get("probes", []):
        if p.get("status") != "PLANNED":
            continue
        outcomes = {" ".join(str(v).lower().split()) for v in (p.get("expected_by_hypothesis") or {}).values()}
        score = 3 * max(len(outcomes) - 1, 0) + (2 if p.get("purpose") == "counterexample-search" else 0)
        score -= _WEIGHT.get(p.get("cost"), 1) + _WEIGHT.get(p.get("risk"), 1)
        score -= 3 if p.get("reversibility") == "irreversible" else 0
        out.append((score, p))
    out.sort(key=lambda sp: (-sp[0], sp[1]["id"]))
    return out


# ---------------------------------------------------------------------------
# Command-line helpers
# ---------------------------------------------------------------------------


def base_parser(prog: str, description: str, epilog: str = "") -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=prog, description=description, epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--ledger", required=True, type=Path, help="Path to investigation.json")
    parser.add_argument("--timestamp", help="ISO-8601 time to record (default: EDI_FIXED_TIME or now)")
    return parser


def csv_list(values: Optional[Sequence[str]]) -> List[str]:
    """Accept repeated flags and comma-separated values: --x A --x B,C -> [A, B, C]."""
    out: List[str] = []
    for v in values or []:
        for part in str(v).split(","):
            part = part.strip()
            if part and part not in out:
                out.append(part)
    return out


def read_input(path: Optional[Path]) -> List[Dict[str, Any]]:
    """--input FILE: a JSON object or a list of objects (e.g. a sub-agent's structured report)."""
    if path is None:
        return []
    data = load_json(path, "Input")
    items = data if isinstance(data, list) else [data]
    for i, item in enumerate(items):
        if not isinstance(item, dict):
            raise LedgerError(f"--input item {i} is not a JSON object")
    return items


def commit(path: Path, before: Dict[str, Any], after: Dict[str, Any], quiet: bool = False,
           claim_change: bool = False) -> List[Issue]:
    """Write `after` only if it introduces no new validation errors.

    A claimed state that becomes stale because of new evidence (X01) does not
    block the write; it is reported, and validate_ledger.py keeps flagging it
    until the claim is updated. Only update_investigation --claim-state
    (claim_change=True) is refused when the claim does not match.
    """
    old = {i.key() for i in validate(before)}
    issues = validate(after)
    new_errors = [i for i in errors_only(issues) if i.key() not in old and (claim_change or i.code != "X01")]
    if new_errors:
        raise LedgerError(
            "Refusing to write: the change introduces validation errors:\n" + "\n".join(str(i) for i in new_errors),
            exit_code=1,
        )
    atomic_write(path, dump(after))
    if not quiet:  # only warnings this change introduced, to keep output short
        for i in issues:
            if (i.level == "warning" or i.code == "X01") and i.key() not in old:
                print(str(i), file=sys.stderr)
    return issues


def run(main_fn) -> None:
    """Run a script's main() and turn LedgerError into a clear message and exit code."""
    for stream in (sys.stdout, sys.stderr):
        try:  # keep non-ASCII text from crashing on legacy Windows consoles
            stream.reconfigure(errors="replace")  # type: ignore[attr-defined]
        except (AttributeError, ValueError):
            pass
    try:
        code = main_fn()
    except LedgerError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(exc.exit_code)
    sys.exit(code or 0)


def parse_pairs(values: Optional[Sequence[str]], what: str, split_last: bool = False) -> List[Tuple[str, str]]:
    """Parse repeated KEY=VALUE arguments, keeping order.

    split_last splits at the last '=' (for free-text keys followed by IDs, e.g. case names).
    """
    out = []
    for v in values or []:
        key, sep, value = str(v).rpartition("=") if split_last else str(v).partition("=")
        if not sep or not key.strip():
            raise LedgerError(f"{what} expects KEY=VALUE, got {v!r}")
        out.append((key.strip(), value.strip()))
    return out


def add_unique(target: List[str], items: Iterable[str]) -> List[str]:
    out = list(target)
    for item in items:
        if item not in out:
            out.append(item)
    return out


def load_for_update(path: Path) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """Load the ledger and return (before, working_copy)."""
    ledger = load_ledger(path)
    return ledger, copy.deepcopy(ledger)


def require_update_flag(args: argparse.Namespace) -> None:
    if getattr(args, "id", None) and not getattr(args, "update", False):
        raise LedgerError(f"{args.id} already exists; pass --update to change it", exit_code=1)
