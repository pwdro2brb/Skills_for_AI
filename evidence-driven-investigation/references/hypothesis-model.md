# Hypothesis model

Schema: `schemas/hypothesis.schema.json`. Script: `scripts/record_hypothesis.py`.

## A good hypothesis

- **Falsifiable**: some observation would show it is false. "Something in the
  environment" is not falsifiable until you say what and how it would show.
- **Specific**: names a mechanism, a variable or a location.
- **Explanatory**: accounts for the observations already recorded, including
  the inconvenient ones.
- **Predictive**: implies observations you have not made yet.

## The minimum set

| Kind | Role | Required |
| --- | --- | --- |
| `primary` | The current best explanation | Always |
| `alternative` | A different mechanism that also fits the observations | Investigative: this or `null` |
| `null` | The conservative explanation: no effect, chance, nothing changed, the system works as documented | Rigorous: always |
| `measurement-error` | The observation itself is wrong: tool bug, wrong build, misread output, instrumentation artifact | Rigorous: this or a limitation saying why it does not apply |
| `other` | Anything else worth tracking | Optional |

Link competing hypotheses with `--alternative` (the link is made both ways).

## Predictions

Each prediction is one sentence: "If H-0001 is true, we expect X under
condition Y." Good predictions differ between hypotheses; that difference is
what probes exploit. A prediction is `pending` until evidence marks it
`confirmed`, `refuted` or `inconclusive`; confirmed and refuted require
evidence.

## Statuses

| Status | Meaning | Rule |
| --- | --- | --- |
| PROPOSED | Recorded, not yet tested | Should have predictions |
| TESTING | A probe is running or planned | Should have predictions |
| SUPPORTED | Survived probes so far | Needs active supporting evidence |
| CONTRADICTED | Some evidence is incompatible, not yet decided | Needs contradicting evidence |
| REJECTED | Falsified | Needs contradicting evidence |
| VERIFIED | Established with adequate authority | Needs a claim type and verification evidence meeting it |
| OUT_OF_SCOPE | No longer relevant to the objective | Needs a status rationale |

SUPPORTED is not VERIFIED. Most hypotheses end as SUPPORTED or REJECTED; the
claim that ends up VERIFIED is usually a narrower finding or an obligation.

## Confidence

`confidence` is a label (`low`, `moderate`, `high`) with a rationale, not a
probability. Do not write numbers unless an explicit statistical model produced
them (then record that model's output as evidence). The validator refuses
`high` without supporting evidence or with a contradiction, and `moderate` or
`high` without a rationale.

## Confounders

List known confounders (`--confounder`): variables that could produce the same
observations without the hypothesized mechanism. Each confounder is a
candidate for an alternative hypothesis or a controlled variable in a probe.

## When everything fails

If every hypothesis is rejected, return to the observations that surprised you
and generate new ones. Record a `measurement-error` hypothesis if you have not:
when nothing fits, the observation is often what is wrong.
