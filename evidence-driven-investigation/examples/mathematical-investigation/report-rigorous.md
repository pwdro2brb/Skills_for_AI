# Is n^2 + n + 41 prime for every n >= 0?

**Computed final state:** `COMPLETE_WITH_LIMITATIONS` (mode: rigorous)

The agent's claimed state matches the computed state.

## 1. Objective

Decide, with adequate authority, whether n*n + n + 41 is prime for every integer n >= 0

## 2. Scope

In scope:

- integers n >= 0

Out of scope:

- whether infinitely many n give primes (open problem)

Completion criteria:

- the conjecture is either proven or refuted by a verified counterexample

Domains: mathematics

## 3. Result

Refuted. n*n + n + 41 is prime for n = 0..39 but n=40 gives 1681 = 41 * 41, found by a bounded search and confirmed by an independent algorithm. The 40 confirming cases were evidence for the pattern, never a proof. The state stops at COMPLETE_WITH_LIMITATIONS because no independent reviewer checked the work.

### Completion gates

| Gate | Passed | Description | Failures |
|---|---|---|---|
| G1 | yes | At least one obligation exists | — |
| G2 | yes | Every critical obligation is CLOSED | — |
| G3 | yes | No critical unknown is open | — |
| G4 | yes | No critical contradiction is open | — |
| G5 | yes | Verification is separate from construction for every closed obligation | — |
| G6 | yes | Limitations are recorded | — |
| G7 | yes | Nothing outside the critical set is pending, waived or out of scope | — |
| G8 | **no** | Mode requirements are met | rigorous mode needs review evidence from a collector other than the producer(s) ['single-agent'] |

Why this state:

- rigorous mode needs review evidence from a collector other than the producer(s) ['single-agent']

## 4. Findings by epistemic status

| ID | Status | Claim | Scope | Evidence | Claim type |
|---|---|---|---|---|---|
| F-0002 | VERIFIED | The conjecture is false: n=40 gives 1681 = 41 * 41 | the statement as given | E-0002, E-0003 | conjecture-refuted |
| F-0001 | OBSERVED | n*n + n + 41 is prime for n = 0..39 (checked n=0..39: 40 prime, 0 not prime []) | n = 0..39 | E-0001 | — |
| F-0003 | REJECTED | The 40 prime values for n = 0..39 show the formula always gives primes | the inference from finite cases | against E-0002 | — |

## 5. Observations and derivations

| ID | Status | Claim | Scope |
|---|---|---|---|
| E-0001 | OBSERVED | Trial division: checked n=0..39: 40 prime, 0 not prime [] | n = 0..39 only |

## 6. Hypotheses

| ID | Kind | Status | Statement | Predictions | Evidence +/− | Confidence |
|---|---|---|---|---|---|---|
| H-0001 | primary | REJECTED | n*n + n + 41 is prime for every integer n >= 0 | H-0001.P1 [refuted] If true, no counterexample exists for any n, in particular none up to 10000 | +E-0001 / −E-0002,E-0003 | low: |
| H-0002 | alternative | VERIFIED | Some integer n >= 0 makes n*n + n + 41 composite | H-0002.P1 [confirmed] If true, a bounded search finds n with a nontrivial factor, confirmed by an independent check | +E-0002,E-0003 / −∅ | high: explicit factorization 41*41, checked twice |
| H-0003 | null | SUPPORTED | The primes seen for small n carry no information about all n | H-0003.P1 [confirmed] If true, any number of confirming small cases leaves the general claim undecided | +E-0001 / −∅ | low: |
| H-0004 | measurement-error | REJECTED | A bug in the primality code produces a false counterexample | H-0004.P1 [refuted] If true, an independent algorithm disagrees about the reported counterexample | +∅ / −E-0003 | low: |

## 7. Probes and tests

| ID | Purpose | Status | Question | Expected by hypothesis | Cost/Risk | Authorization | Result | Outcome |
|---|---|---|---|---|---|---|---|---|
| P-0001 | counterexample-search | DONE | Is there a counterexample with n <= 10000? | H-0001: no composite value for n = 0..10000; H-0002: at least one composite value with an explicit factor | low/low/reversible | not required | E-0002 | composite at n=40: H-0001 refuted, pending the independent check |
| P-0002 | verify | DONE | Is n=40 really a counterexample? | H-0002: an independent algorithm also finds 1681 composite; H-0004: an independent algorithm finds 1681 prime | low/low/reversible | not required | E-0003 | both routes agree: composite; H-0004 refuted |

## 8. Evidence

| ID | Status | Epistemic | Source type | Authority | Claim | Tool / command | Artifact | Scope | Role / by | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| E-0001 | ACTIVE | OBSERVED | calculation | numerical-test | Trial division: checked n=0..39: 40 prime, 0 not prime [] | python: python check_small.py 40 | — | n = 0..39 only | observation / single-agent | finite cases; says nothing about n >= 40 |
| E-0002 | ACTIVE | OBSERVED | calculation | counterexample-search | Searching n = 0..10000: first composite at n=40 (1681 has factor 41); 5852 of 10001 values are composite | python: python search_counterexample.py 10000 | — | n = 0..10000, trial division | verification / single-agent | — |
| E-0003 | ACTIVE | OBSERVED | calculation | independent-calculation | Independent route: 41*41 = 1681; equal: True; Miller-Rabin reports composite | python: python verify_counterexample.py 40 | — | n = 40 only | verification / single-agent | — |
| E-0004 | ACTIVE | OBSERVED | document | independent-review | Self-review: the counterexample n=40 lies in the stated domain (integer, >= 0) and the tested expression is exactly n*n + n + 41 | review by the same agent that ran the search | file:outputs/p3-independent.txt | statement/domain match only | review / single-agent | not independent: same agent as the producer |

## 9. Contradictions

_None recorded._

## 10. Residual unknowns

| ID | Severity | Status | Question | Required authority | Resolution / blocker | Recommended probes |
|---|---|---|---|---|---|---|
| U-0001 | low | OUT_OF_SCOPE | Does n*n + n + 41 take prime values for infinitely many n? | — | a different and open question (Bunyakovsky conjecture); not needed to decide the objective [] | — |

## 11. Obligations

| ID | Severity | Kind | Status | Claim | Required authority | Cases (evidence) | Construction | Verification | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| O-0001 | critical | proof | CLOSED | The conjecture is decided | conjecture-decided | statement as given (all integers n >= 0): E-0002,E-0003 | — | E-0002, E-0003 | — |

## 12. Limitations

- Computations use Python integers on one machine; algorithms are elementary and shown in full
- No independent human or agent reviewed this example
- [E-0001] finite cases; says nothing about n >= 40
- [E-0004] not independent: same agent as the producer
- Out of scope: whether infinitely many n give primes (open problem)

## 13. Reproduction

- [E-0001] `python check_small.py 40` — python
- [E-0002] `python search_counterexample.py 10000` — python
- [E-0003] `python verify_counterexample.py 40` — python

Not reproducible by command: E-0004.

## 14. Authority extensions and warnings

Rationale: The objective is to decide the conjecture; either a refutation or a proof closes it

- claim type `conjecture-decided`: A conjecture is either refuted by a verified counterexample or proven (Union of the base claim types conjecture-refuted and theorem-valid; adds no weaker clause)

No validation warnings.

## 15. Final state

`COMPLETE_WITH_LIMITATIONS`. Every critical obligation is closed and verified, but some non-critical item is open, waived or out of scope, or a mode requirement is unmet. Read the limitations.

---

<sub>Generated by scripts/generate_report.py from ledger digest `a171cdf37329df2d0273e113499082ec9b1e829df96fe57e4b0ce96023fa1a61`. The final state is computed from the ledger by scripts/evaluate_completion.py; it is not written by the agent.</sub>
