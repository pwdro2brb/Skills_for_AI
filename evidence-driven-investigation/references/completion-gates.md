# Completion gates and final states

Contents: 1. Final states · 2. Gates · 3. How the state is chosen · 4. Mode
requirements · 5. Obligations · 6. Validation codes

## 1. Final states

| State | Meaning |
| --- | --- |
| COMPLETE_VERIFIED | Every obligation closed by separate verification of the required authority; no critical or high item open; mode requirements met; limitations recorded. |
| COMPLETE_WITH_LIMITATIONS | Every critical obligation closed and verified, but something non-critical is open, waived or out of scope, or a mode requirement is unmet. |
| PARTIALLY_VERIFIED | Some obligation closed or some finding VERIFIED, but a closure gate fails. |
| MITIGATED_NOT_RESOLVED | A `mitigation` obligation is closed while a `root-cause` obligation is not. |
| BLOCKED | A critical obligation or critical unknown is BLOCKED (missing authority, access or environment). |
| INCONCLUSIVE | Nothing is verified. The evidence does not support a conclusion. |
| FAILED | A critical obligation was tested and FAILED. |

The state is computed by `scripts/evaluate_completion.py`. No field in the
ledger sets it. `conclusion.claimed_state` only records what the agent intends
to claim; the validator refuses it (code X01) when it differs from the
computed state.

## 2. Gates

| Gate | Passes when |
| --- | --- |
| G1 | At least one obligation exists. |
| G2 | Every critical obligation is CLOSED. |
| G3 | No critical unknown is OPEN, INVESTIGATING, BLOCKED or CONTRADICTED. |
| G4 | No critical contradiction is OPEN or INVESTIGATING. |
| G5 | Every closed obligation has verification evidence disjoint from its construction evidence; in rigorous mode, also produced by a different tool or command. |
| G6 | The ledger records at least one limitation. |
| G7 | Every obligation is CLOSED (none open, blocked or WAIVED); no high or critical unknown is open or OUT_OF_SCOPE; no high or critical contradiction is open or OUT_OF_SCOPE. |
| G8 | The mode requirements below are met. |

## 3. How the state is chosen

The ledger must validate with no errors; otherwise nothing is evaluated (exit 2).
Then the first matching rule wins:

1. FAILED: some critical obligation is FAILED.
2. BLOCKED: some critical obligation or critical unknown is BLOCKED.
3. COMPLETE_VERIFIED: G1 to G8 all pass.
4. COMPLETE_WITH_LIMITATIONS: G1 to G6 pass.
5. MITIGATED_NOT_RESOLVED: a mitigation obligation is closed and a root-cause obligation is not.
6. PARTIALLY_VERIFIED: some obligation is closed or some finding is VERIFIED.
7. INCONCLUSIVE: otherwise.

`evaluate_completion.py` prints every gate, its failures, and the reasons for
the state. Report those reasons when the state is not COMPLETE_VERIFIED.

## 4. Mode requirements (G8)

| Mode | Requirements |
| --- | --- |
| light | None. (Light mode normally has no ledger at all.) |
| investigative | At least two hypotheses that are not out of scope, at least one of them not `primary`. |
| rigorous | Hypotheses of kinds `primary`, `null` and `alternative`; a DONE probe with purpose `counterexample-search`; an active `review` evidence record whose `collected_by` differs from every construction collector (or, without construction records, from every observation collector); every verification record used by closed obligations and VERIFIED findings is `reproducible`. |

## 5. Obligations

An obligation can be CLOSED only when the validator accepts all of:

- active verification evidence that meets `required_authority`;
- active evidence for every required case (`case_evidence`);
- every blocking unknown RESOLVED or OUT_OF_SCOPE;
- every blocking contradiction RESOLVED or OUT_OF_SCOPE;
- every dependency obligation CLOSED;
- verification evidence disjoint from construction evidence;
- if `applies_to` is set, every verification record is about that artifact.

FAILED needs the verification evidence that showed the failure and a rationale.
BLOCKED and WAIVED need a rationale. A WAIVED major or minor obligation keeps
the state at COMPLETE_WITH_LIMITATIONS at best; a WAIVED critical obligation
fails G2, so the state is at most PARTIALLY_VERIFIED. Waiving never counts as
verifying.

## 6. Validation codes

Errors block writes (when newly introduced) and evaluation. Warnings do not,
unless `validate_ledger.py --strict`.

| Code | Problem |
| --- | --- |
| V001 | Schema violation (fix these first; semantic checks run after) |
| V002 | Duplicate ID |
| V003 | ID in the wrong collection |
| V004 | Broken, wrong-kind or self reference |
| V005 | Record edited outside the scripts (digest mismatch) |
| V006 | Forbidden cycle (unknown or obligation dependencies, evidence derivation) |
| V010-V013 | Invalid authority extension (missing rationale, override, unknown authority) |
| V014 | Unknown claim type or authority in a requirement |
| E01 | DERIVED without `derived_from` (warning: OBSERVED with `derived_from`) |
| E02, E03 | Unknown authority; authority incompatible with source type |
| E04 | Missing tool/command (executed sources) or source (documents, user reports) |
| E05 | Missing or malformed artifact identity |
| E06 | Reproducible without a command |
| E07 | Invalidation status and record disagree |
| E08 | The same record both supported and contradicted |
| E09 | `derived_from` points to a later record |
| E11 | User observation with an authority other than `user-report` |
| E12 | Inconsistent output capture (shown > total, or "full" that is not full) |
| H02-H06 | Hypothesis status without the evidence it requires; high confidence without support |
| H07 | Same evidence supports and contradicts |
| H08 | Malformed prediction or prediction result without evidence |
| H09 | Duplicate hypothesis statement (warning) |
| H10 | OUT_OF_SCOPE without rationale |
| H11 | Hypothesis without predictions (warning) |
| P01, P02 | Probe without hypotheses, or expected results not covering exactly them |
| P03, P04 | Risky probe without `requires_authorization`; run without authorization |
| P05 | DONE without result/outcome; ABANDONED without reason |
| P06 | Probe cannot discriminate (warning) |
| P07 | Unknown observation authority |
| U01 | RESOLVED without qualifying evidence or rationale |
| U02-U05 | Contradicted, out-of-scope, blocked or overlapping evidence rules |
| U07 | RESOLVED while a dependency is open |
| C01-C04 | Contradiction without evidence; invalid resolution; explanation status without evidence |
| O02 | CLOSED without authority, cases, or with open blockers or dependencies |
| O03, O04 | FAILED, BLOCKED or WAIVED without the required rationale or evidence |
| O06 | Case evidence for an undeclared case |
| O07 | Verification about a different artifact than `applies_to` (stale proof) |
| O08 | Same evidence used for construction and verification |
| F01-F08 | Finding status without the evidence it requires |
| F09 | VERIFIED finding whose verification evidence is construction evidence |
| W01 | Investigative or rigorous ledger without obligations (warning) |
| W02 | Rigorous ledger without a measurement-error hypothesis (warning) |
| X01 | `claimed_state` differs from the computed state. Refused when the claim is set; when later evidence makes a claim stale, the write goes through with a warning, `validate_ledger.py` keeps reporting the error, and evaluation still runs |
