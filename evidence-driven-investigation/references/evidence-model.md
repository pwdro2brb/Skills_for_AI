# Evidence model

Contents: 1. What counts as evidence · 2. Fields · 3. Requirements by source
type · 4. Scope and strength · 5. Roles · 6. Immutability and invalidation ·
7. Findings and their statuses

## 1. What counts as evidence

An evidence record (`E-0001`) is one observation or one deterministic
derivation, with enough identity and provenance that someone else could check
it. Evidence is **only** `OBSERVED` or `DERIVED`:

- **OBSERVED**: obtained directly from a file, tool, execution, document or
  person.
- **DERIVED**: computed deterministically from identified evidence (rates from
  counts, a diff of two recorded outputs). Must list `derived_from`, which must
  point to earlier records.

Inferences, assumptions and conclusions are not evidence. They are hypotheses
(`hypothesis-model.md`) or findings (section 7).

## 2. Fields

Schema: `schemas/evidence.schema.json`.

| Field | Meaning |
| --- | --- |
| `claim` | Bounded description of what was observed. Not an interpretation. |
| `epistemic_status` | `OBSERVED` or `DERIVED`. |
| `source_type` | `runtime`, `static`, `document`, `test`, `calculation`, `formal-proof`, `user-observation`. |
| `authority` | Tag from `authority-matrix.json`; must be compatible with `source_type`. |
| `source` | Exact origin: path, URL, citation, person. |
| `artifact_identity` | `{kind, value, path?}`; kind is `sha256`, `commit`, `version`, `url`, `file` or `none`. |
| `tool`, `command_or_method` | What produced it and how to reproduce it. |
| `environment` | Platform, versions, configuration (recommended for runtime and test). |
| `timestamp` | When it was recorded (ISO-8601). |
| `scope` | What this evidence actually supports. |
| `limitations` | What it does not show. |
| `supports`, `contradicts` | IDs of hypotheses, unknowns, findings (linked automatically), obligations, probes or contradictions. |
| `reproducible` | True only if running the command again gives the same observation. |
| `role` | `observation`, `construction`, `verification` or `review`. |
| `collected_by` | Agent or person that produced it (`single-agent`, `verifier`, `critic`, `user`...). |
| `output_capture` | Hash, total and shown lines and truncation method of the captured output. |
| `status` | `ACTIVE` or `INVALIDATED` (with `invalidation.reason`). |
| `record_digest` | SHA-256 of the record; detects edits made outside the scripts. |

## 3. Requirements by source type

| Source type | Must have | Notes |
| --- | --- | --- |
| `runtime` | tool, command, artifact identity | Shows what happened in that execution, in that environment. |
| `test` | tool, command, artifact identity | Shows the tested unit in the test environment. |
| `static` | tool, command, artifact identity | Shows what is present or referenced. Never that it executed. |
| `calculation` | tool, command | Pure computation; `derived_from` if it uses earlier evidence. |
| `formal-proof` | tool, command, artifact identity | Proof checker run on an identified file. |
| `document` | source | Add a URL, version or hash so it can be found again. |
| `user-observation` | source; authority `user-report` | Recorded faithfully; weak authority for almost every claim. |

`reproducible: true` requires a command. A `sha256` value must be 64 lowercase
hex characters; prefer `--artifact-file` so the script computes it.

## 4. Scope and strength

Evidence never supports a claim stronger than its scope. The scripts enforce
the part they can (authority versus claim type); the rest is your discipline:

| Evidence | Does not establish |
| --- | --- |
| Static reference, string, symbol | That the code executes, or when |
| Unit test passing | That the packaged or deployed artifact works |
| A few numerical cases | A general theorem |
| A secondary source | What the primary source says, when it is available |
| Correlation in data | Causation |
| Behavior in an emulator or simulation | Behavior on real hardware or in the world |
| A search that found nothing | That the thing does not exist outside the searched area |
| Agreement between agents | Anything; agreement is not evidence |
| A sub-agent's summary | The underlying observation; record the raw output |

Write scope concretely: "these 20 rows of fixtures/sample.csv, Python 3.12,
Linux, commit a1b2c3", not "the export".

## 5. Roles

- `observation`: what you learned about the object.
- `construction`: work that produced the solution (a patch, a parser, a proof
  draft). Never closes the obligation it built.
- `verification`: the separate check that closes an obligation or verifies a
  finding. In rigorous mode it must use a different tool or command than any
  construction record of the same obligation, and be reproducible.
- `review`: a critique. In rigorous mode at least one review must come from a
  collector other than the producers.

## 6. Immutability and invalidation

Evidence is never edited. If it was wrong (wrong build, wrong file, tool bug),
invalidate it:

```
python scripts/record_evidence.py --ledger L --invalidate E-0007 --reason "ran against the old build"
```

Invalidation cascades to every record DERIVED from it, then reopens everything
that relied on any of them: resolved unknowns and
contradictions go back to OPEN, closed or failed obligations go back to OPEN,
VERIFIED findings become UNKNOWN with a new unknown tracking them, and
hypotheses that were verified, supported or rejected by it go back to TESTING.
Then record the corrected evidence as a new record.

## 7. Findings and their statuses

A finding (`F-0001`) is a material claim of the conclusion. Schema:
`schemas/finding.schema.json`.

| Status | Rule enforced by the validator |
| --- | --- |
| OBSERVED | cites active OBSERVED evidence |
| DERIVED | cites active DERIVED evidence |
| INFERRED | cites the evidence or hypotheses it is inferred from |
| ASSUMED | has a rationale |
| CONTRADICTED | cites a contradiction or contradicting evidence |
| UNKNOWN | cites the unknown (`U-`) tracking it |
| VERIFIED | has a claim type, and its verification evidence meets that claim type's authority |
| REJECTED | cites active contradicting evidence |
| OUT_OF_SCOPE | has a rationale |

There is no automatic promotion. Moving a finding from INFERRED to VERIFIED
needs verification evidence that satisfies the claim type; restating it more
confidently does not.
