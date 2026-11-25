# Does dark mode make sessions longer?

**Computed final state:** `COMPLETE_WITH_LIMITATIONS` (mode: investigative)

The agent's claimed state matches the computed state.

## 1. Objective

Determine whether enabling dark mode causes longer sessions, using sessions.csv

## 2. Scope

In scope:

- sessions.csv (2000 users, one snapshot)

Out of scope:

- running a randomized experiment

Completion criteria:

- the association is quantified with uncertainty
- the causal reading is tested against measured confounders, with a sensitivity check

Domains: data-analysis

## 3. Result

The association is real but explained by device: desktop users both prefer dark mode and have longer sessions. Within each device type the difference is near zero, and other summaries agree. Do not expect longer sessions from enabling dark mode by default. This is inferred from observational data; an A/B test would settle it, and the session metric's definition per platform (U-0001) is unverified.

### Completion gates

| Gate | Passed | Description | Failures |
|---|---|---|---|
| G1 | yes | At least one obligation exists | — |
| G2 | yes | Every critical obligation is CLOSED | — |
| G3 | yes | No critical unknown is open | — |
| G4 | yes | No critical contradiction is open | — |
| G5 | yes | Verification is separate from construction for every closed obligation | — |
| G6 | yes | Limitations are recorded | — |
| G7 | **no** | Nothing outside the critical set is pending, waived or out of scope | U-0001 (high) is OPEN |
| G8 | yes | Mode requirements are met | — |

Why this state:

- U-0001 (high) is OPEN

## 4. Findings by epistemic status

| ID | Status | Claim | Scope | Evidence | Claim type |
|---|---|---|---|---|---|
| F-0001 | VERIFIED | Dark-mode users have longer sessions overall | all 2000 users, unadjusted | E-0003 | correlation-exists |
| F-0002 | DERIVED | Within each device type the difference is near zero (both 95% intervals include zero) | adjusted for device only | E-0004, E-0005 | — |
| F-0003 | INFERRED | Turning dark mode on by default would not lengthen sessions | a causal prediction from observational data; not tested by intervention | E-0004, E-0005 | — |

## 5. Observations and derivations

| ID | Status | Claim | Scope |
|---|---|---|---|
| E-0001 | OBSERVED | Product team reports that dark-mode users have much longer sessions and asks whether to turn it on by default | the request; no analysis attached |

## 6. Hypotheses

| ID | Kind | Status | Statement | Predictions | Evidence +/− | Confidence |
|---|---|---|---|---|---|---|
| H-0001 | primary | CONTRADICTED | Dark mode causes longer sessions | H-0001.P1 [refuted] If true, dark-mode users have longer sessions overall AND within each device type | +E-0003 / −E-0004 | low: |
| H-0002 | alternative | SUPPORTED | Device type drives both dark-mode use and session length; dark mode itself has no effect | H-0002.P1 [confirmed] If true, the overall difference shrinks to about zero within each device type | +E-0003,E-0004,E-0005 / −∅ | moderate: matches the pre-registered pattern and survives the sensitivity check; unmeasured confounders remain |
| H-0003 | null | REJECTED | There is no association between dark mode and session length | H-0003.P1 [refuted] If true, the overall 95% interval includes zero | +∅ / −E-0003 | low: |
| H-0004 | measurement-error | TESTING | Session length is measured differently on desktop and mobile clients | H-0004.P1 [pending] If true, the instrumentation documentation or client code shows different session definitions | +∅ / −∅ | low: |

## 7. Probes and tests

| ID | Purpose | Status | Question | Expected by hypothesis | Cost/Risk | Authorization | Result | Outcome |
|---|---|---|---|---|---|---|---|---|
| P-0001 | discriminate | DONE | Is there an association, and does it survive stratification by device? | H-0001: positive overall difference that remains positive within both devices; H-0002: positive overall difference that is near zero within both devices; H-0003: overall interval includes zero | low/low/reversible | not required | E-0003, E-0004, E-0005 | overall difference positive with an interval excluding zero; both within-device intervals include zero: matches H-0002, contradicts H-0001 and H-0003 |

## 8. Evidence

| ID | Status | Epistemic | Source type | Authority | Claim | Tool / command | Artifact | Scope | Role / by | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| E-0001 | ACTIVE | OBSERVED | user-observation | user-report | Product team reports that dark-mode users have much longer sessions and asks whether to turn it on by default | user request | — | the request; no analysis attached | observation / single-agent | — |
| E-0002 | ACTIVE | OBSERVED | test | schema-validation | 2000 rows, 0 schema problems | python: python schema_check.py sessions.csv | sha256:7e98f4a70865… (sessions.csv) | column names, allowed values, ranges, unique ids | verification / single-agent | — |
| E-0003 | ACTIVE | DERIVED | calculation | descriptive-statistics | All users: difference on-off: +9.45 min (95% CI +8.56 to +10.34); desktop: n=880 dark-mode share=72% mean session=30.99 min; mobile: n=1120 dark-mode share=21% mean session=12.14 min | python: python describe.py sessions.csv | — | all 2000 users, unadjusted | verification / single-agent | — |
| E-0004 | ACTIVE | DERIVED | calculation | causal-design | Within device: desktop: n_on=630 n_off=250 difference -0.18 min (95% CI -1.02 to +0.67); mobile: n_on=238 n_off=882 difference -0.02 min (95% CI -0.85 to +0.81); device-standardized difference: -0.09 min | python: python stratify.py sessions.csv | — | adjusts for device only; unmeasured confounders remain | verification / single-agent | — |
| E-0005 | ACTIVE | DERIVED | calculation | sensitivity-analysis | Other summaries agree: desktop: median difference -0.70 min; 5%-trimmed mean difference -0.16 min; mobile: median difference +0.20 min; 5%-trimmed mean difference -0.01 min | python: python sensitivity.py sessions.csv | — | median and trimmed means within device | verification / single-agent | — |

## 9. Contradictions

_None recorded._

## 10. Residual unknowns

| ID | Severity | Status | Question | Required authority | Resolution / blocker | Recommended probes |
|---|---|---|---|---|---|---|
| U-0001 | high | OPEN | Is session_minutes defined the same way on desktop and mobile clients? | primary-source (observation only) | — | read the analytics instrumentation spec or client code for both platforms |
| U-0002 | medium | OPEN | Could an unmeasured variable (age, plan type, usage purpose) confound the within-device comparison? | controlled-experiment | — | an A/B test that assigns dark mode at random |

## 11. Obligations

| ID | Severity | Kind | Status | Claim | Required authority | Cases (evidence) | Construction | Verification | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| O-0001 | major | analysis | CLOSED | sessions.csv matches the expected schema | data-schema-valid | columns and types: E-0002 | — | E-0002 | — |
| O-0002 | critical | analysis | CLOSED | The association between dark mode and session length is quantified with a 95% interval | correlation-exists | all users: E-0003 | — | E-0003 | — |
| O-0003 | critical | analysis | CLOSED | The causal reading is tested against the device confounder with a causal design and a sensitivity analysis | causal-effect | desktop: E-0004,E-0005; mobile: E-0004,E-0005 | — | E-0004, E-0005 | — |

## 12. Limitations

- Observational snapshot: only measured confounders can be adjusted for
- Synthetic data; conclusions illustrate the method, not real users
- Out of scope: running a randomized experiment

## 13. Reproduction

- [E-0002] `python schema_check.py sessions.csv` — python
- [E-0003] `python describe.py sessions.csv` — python
- [E-0004] `python stratify.py sessions.csv` — python
- [E-0005] `python sensitivity.py sessions.csv` — python

Not reproducible by command: E-0001.

## 14. Authority extensions and warnings

No authority extensions; the base matrix applies.

No validation warnings.

## 15. Final state

`COMPLETE_WITH_LIMITATIONS`. Every critical obligation is closed and verified, but some non-critical item is open, waived or out of scope, or a mode requirement is unmet. Read the limitations.

---

<sub>Generated by scripts/generate_report.py from ledger digest `c9560e6e6951c992748722585f99e74726e3a10b5975d8916ef5f5bd63fb19aa`. The final state is computed from the ledger by scripts/evaluate_completion.py; it is not written by the agent.</sub>
