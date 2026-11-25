# Residual unknowns

Schema: `schemas/unknown.schema.json`. Script: `scripts/record_unknown.py`.

An unknown (`U-0001`) is a bounded question the evidence does not answer yet.
Recording it is how an investigation stays honest about what it has not
established. Unknowns are never deleted.

## Write the question so it can be answered

Bad: "Is the export reliable?" Good: "Does the packaged wheel 2.4.1 on Windows
use the same timezone library version as the dev environment?"

Fill in what would answer it:

- `required_authority`: the claim type or authority tag that can close it
  (`works-in-final-package`, `primary-source`...).
- `requires_observation`: set it when only a direct observation can answer
  (DERIVED evidence will not resolve it).
- `required_environment`: where the answer has to be observed.
- `recommended_probes`: what you would do to answer it.
- `dependencies`: other unknowns that must be answered first (cycles are refused).

## Severity

| Severity | Use when | Effect on the final state |
| --- | --- | --- |
| critical | A wrong answer would invalidate the conclusion | Open: no COMPLETE_* state. BLOCKED: state BLOCKED. |
| high | It materially limits the conclusion | Open or out of scope: at most COMPLETE_WITH_LIMITATIONS |
| medium | It qualifies the conclusion | Reported |
| low | Worth noting | Reported |

## Statuses

| Status | Rule |
| --- | --- |
| OPEN | Default |
| INVESTIGATING | A probe is under way |
| BLOCKED | Needs `blocked_reason`: authority, access or an environment that is not available |
| CONTRADICTED | Needs contradicting evidence; created automatically when contradicting evidence is given |
| RESOLVED | Needs active resolution evidence meeting `required_authority` (observed-only if `requires_observation`), a rationale, and resolved dependencies |
| OUT_OF_SCOPE | Needs a rationale; always shown in the report |

## Rules

- Inference never closes an unknown. A resolution cites evidence.
- An absent result closes nothing by itself: "no reference found" resolves an
  unknown only within the searched scope, and the scope must say so.
- Invalidating the resolution evidence reopens the unknown automatically.
- An unknown can be closed as out of scope, but the report lists it, and a
  high or critical one keeps the state at COMPLETE_WITH_LIMITATIONS at best.
- When the user cannot provide what a critical unknown needs, mark it BLOCKED
  and report BLOCKED. Do not guess the answer to unblock the investigation.
