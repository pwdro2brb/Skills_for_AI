# Evals

Seven cases that compare an agent **with** and **without** this skill. The
grader is deterministic; the model runs are not part of this repository and
have **not been executed yet**. This folder is the protocol and the tooling.

| Case | What it tests | Correct outcome |
| --- | --- | --- |
| `case-01-ambiguous-bug` | Ambiguous bug with red herrings (DST, off-by-one) | Day/month ambiguity found by a discriminating probe and fixed |
| `case-02-misleading-correlation` | Correlation vs causation, confounding, leakage | No campaign effect within strata; `coupon_redeemed` leaks the outcome |
| `case-03-binary-field` | A byte that changes with a behavior | Byte 0x10 is a name-table offset; only controlled mutation shows it |
| `case-04-false-conjecture` | Numerical cases vs proof | False: 5777 (and 5993) are counterexamples |
| `case-05-simple-task` | Bureaucracy on a trivial task | Light mode: rename, run, short answer, no ledger |
| `case-06-insufficient-evidence` | Refusing to invent a cause | 137 = SIGKILL; root cause INCONCLUSIVE/BLOCKED |
| `case-07-contradictory-sources` | Conflicting docs | 3 retries (installed 2.8.1 predates the 3.0 change) |

`cases/<case>/` holds the prompt (`PROMPT.md`) and fixtures, all synthetic.
`expected/<case>.json` holds the ground truth and the checks.

## Avoiding contamination

The agent under test must not see `evals/` or `examples/`. Install the skill
for the runs from the package (`tools/package_skill.py` builds a zip with only
the runtime files: `SKILL.md`, `agents/`, `references/`, `schemas/`,
`scripts/`, `templates/`), and copy only `cases/<case>/` into each run folder.
Never copy `expected/`.

## Protocol

For each case, each condition (`baseline`, `skill`) and each repetition
(at least 3; agent runs vary):

1. Create a fresh folder and copy `cases/<case>/` into it.
2. Start a fresh agent session in that folder, with the skill installed
   (`skill`) or not (`baseline`). Same model, same settings, same tools.
3. Send the content of `PROMPT.md` as the only user message. Do not help.
4. Save the agent's final message as `answer.md` in the run folder.
5. Record what your harness measures in `stats.json`:
   `{"tokens": 12345, "tool_calls": 17, "seconds": 84.2}`.
6. Grade:

```
python evals/grade.py --case case-04-false-conjecture --condition skill \
    --workdir runs/case-04/skill-1 --answer runs/case-04/skill-1/answer.md \
    --run-stats runs/case-04/skill-1/stats.json --out results/case-04-skill-1.json
```

7. Summarize all results:

```
python evals/grade.py --summarize results/*.json > results/summary.md
```

## Metrics

| Metric (plan) | How it is measured |
| --- | --- |
| Premature conclusion rate | Any failed check tagged `premature` (claiming a cause, proof or effect the evidence does not support) |
| Claims without evidence | `ledger_errors` (the validator refuses unsupported statuses); for baseline, read the answers |
| Counterexample discovery | Checks tagged `counterexample` (case 4) |
| Unknowns identified | `unknowns_recorded`, plus checks tagged `unknowns` |
| Correct tool use | Checks tagged `process` (probes run, hypotheses competing) |
| Claim/authority match | `authority_mismatches` and checks tagged `authority` |
| Tokens, calls, time | `tokens`, `tool_calls`, `seconds` from `stats.json` |
| Correct conclusion rate | `correct`: every check tagged `correct` passed |
| Report quality | Not automated: rate `answer.md` and the report by hand (rubric below) |
| Bureaucracy on simple tasks | `bureaucracy` (case 5: a ledger was created, or the answer is long) |

Ledger checks (`ledger_*`, `evidence_regex`, `state_in`) apply only to the
`skill` condition; answer and file checks apply to both, so the comparison is on
equal terms. Answer checks are regular expressions: they catch the main facts
and the most common wrong claims, not every phrasing. Read the failing answers
before drawing conclusions, and adjust patterns if they misjudge a correct
answer (and record that you did).

## Report quality rubric (human)

Score 0-2 each: states the computed state or an honest equivalent; separates
observed from inferred; lists open unknowns; states limitations; gives a way to
reproduce; is proportionate to the task.

## What this does not measure

- Whether the skill helps on tasks unlike these seven.
- Long-horizon investigations (days, many sessions).
- Agents that cannot run code (the skill's manual mode).
- Statistical significance: with a handful of runs per cell, report counts,
  not percentages with false precision.
