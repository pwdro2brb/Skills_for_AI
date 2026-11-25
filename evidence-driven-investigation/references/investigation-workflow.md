# Investigation workflow

Contents: 1. The loop · 2. Framing · 3. Observing · 4. Hypotheses · 5. Choosing
probes · 6. Running probes · 7. Seeking contradiction · 8. Refining · 9. Building
and verifying · 10. Concluding · 11. Worked mini-example · 12. Anti-patterns

## 1. The loop

```
frame -> observe -> hypothesize -> predict -> probe -> record evidence
      -> seek contradiction -> refine (loop back) -> build -> verify independently
      -> classify findings -> evaluate -> report
```

The loop repeats until either the obligations close or the evidence available
cannot move the state any further (BLOCKED or INCONCLUSIVE are legitimate end
points). Each pass should change something in the ledger. If a pass adds
nothing, stop and report the current computed state.

## 2. Framing

- Restate the objective as a question that has an observable answer. "Why is it
  slow?" becomes "Which operation accounts for the added latency between v1.3
  and v1.4 on the benchmark in `bench/`?"
- List what is **in** scope and what is **out** (`--scope-in`, `--scope-out`).
  Out-of-scope items appear in the report as limitations.
- Write completion criteria, then turn each into an obligation with a required
  authority (a claim type from `authority-matrix.json`) and required cases.
  An obligation without a required authority is a wish.
- Choose the mode. When unsure between two modes, pick the stricter one for
  the parts that are risky and say so.

## 3. Observing

- Record what you see before explaining it. "The log line at 12:00:03 is
  `KeyError: 'tz'`" is evidence. "The timezone handling is broken" is a
  hypothesis.
- Identify the artifact (`--artifact-file` computes its SHA-256; or a commit,
  version or URL). Without identity, nobody can tell later what was observed.
- Keep the command that reproduces the observation (`--command`) and mark
  `--reproducible` only if running it again would give the same observation.
- When you quote part of an output, record the whole output with
  `--output-file` and declare `--shown-lines` and `--capture-method`
  (`head`, `tail`, `grep`, `summary`). Silent truncation hides contradicting lines.
- Write `--scope` as the boundary of the evidence: which files, inputs,
  platform, version, sample. Scope is what keeps evidence from being stretched.

## 4. Hypotheses

See `hypothesis-model.md`. Minimum: a primary hypothesis and a competing one
(alternative or null). Each has predictions that could fail. Record
confounders you know about.

## 5. Choosing probes

A good probe is one whose result changes what you believe. Before running it,
record:

| Field | Question it answers |
| --- | --- |
| `discriminates` | Which hypotheses does it test? |
| `expected_by_hypothesis` | What does each hypothesis predict? If they predict the same thing, the probe cannot discriminate (the validator warns). |
| `variables_changed` / `variables_controlled` | What changes on purpose, what is held fixed? |
| `cost`, `risk`, `reversibility`, `external`, `sensitive` | What could it cost or break? Risky probes require authorization. |
| `repeatable` | Can it be run again with the same result? |
| `observation_authority` | What authority will the result have? |
| `interpretation_criterion` | How will the result be read, decided before seeing it? |

Order: high discrimination, low cost, low risk, reversible first.
`record_probe.py --rank` sorts planned probes by that rule. Prefer one probe
that splits hypotheses over several that confirm the favorite.

## 6. Running probes

- Run the real tool. A probe that was only planned establishes nothing.
- Record the result as evidence even when it is negative or boring. Negative
  results are often the most informative ones.
- Mark the probe DONE with its result evidence and an outcome that reads the
  result against the criterion written in step 5.
- Update predictions (`--prediction-result H-0001.P1=confirmed:E-0007`) and
  hypothesis statuses. SUPPORTED needs supporting evidence; REJECTED needs
  contradicting evidence.

## 7. Seeking contradiction

Ask, for the leading hypothesis: "What would I see if this were false?" Then
look for it. Typical searches:

- the same symptom without the suspected cause;
- the suspected cause without the symptom;
- a different version, environment, input size or seed;
- the edge cases the explanation would predict to fail;
- independent sources for every claim taken from a single source.

When two pieces of evidence conflict, record a contradiction
(`contradiction-handling.md`). When a question cannot be answered yet, record an
unknown (`residual-unknowns.md`).

## 8. Refining

- When a prediction fails, the hypothesis is contradicted. Revise it into a new,
  narrower hypothesis or reject it. Do not add exceptions until it fits.
- When all hypotheses fail, generate new ones from the observations that
  surprised you.
- Avoid chained speculation ("maybe A, so maybe B, so C"). Each step that is not
  observed is a separate hypothesis that needs its own probe.

## 9. Building and verifying

- Build only when the leading hypothesis has survived probes designed to break
  it. Record the build work as `--role construction`.
- Verify by a route that could fail independently of the build: a different
  test, the packaged artifact, another tool, another agent. Record it as
  `--role verification` and attach it to the obligation with the case evidence.
- Compare the reconstruction or fix against the original behavior, not against
  your expectation of it.
- Close the obligation. The script refuses if authority, cases, blockers,
  dependencies or separation are missing, and says which.

## 10. Concluding

- Record each claim you will make in the answer as a finding with its epistemic
  status. Leave nothing material unclassified.
- Add limitations: what was not tested, which environment, which assumptions.
- Run `evaluate_completion.py`. Report its state; explain what would be needed
  to reach a stronger one.
- Revisit the original question list: answered, partially answered or open.
  A broad investigation is not complete while required questions remain open.

## 11. Worked mini-example

Symptom: `export_csv()` fails "sometimes".

```
E-0001 OBSERVED  test run: 7/50 failures, all KeyError 'tz'          [unit-test]
H-0001 primary   rows without a tz field fail
       P1 if true, every tz-less row fails, no row with tz fails
H-0002 null      failures are independent of row content (runner flakiness)
       P1 if true, the failure rate is the same with fixed input
P-0001 discriminate H-0001/H-0002, change: tz present/absent, control: same data, seed, runner
       expected H-0001: 10/10 tz-less fail, 0/10 others fail
       expected H-0002: similar rates in both groups
E-0002 OBSERVED  10/10 tz-less rows fail, 0/10 others fail           [controlled-mutation]
=> H-0001.P1 confirmed, H-0002 rejected (E-0002 contradicts it)
O-0001 critical  "export handles missing tz"  required: function-works, cases: tz present, tz missing
E-0003 construction  patch defaulting tz to UTC                     [static-analysis]
E-0004 verification  50/50 runs pass, both cases                    [unit-test]
F-0001 VERIFIED  "export no longer fails on rows without tz" (function-works, E-0004)
F-0002 INFERRED  "production failures have the same cause" (H-0001; not observed in production)
U-0001 high      "does the packaged build behave the same?" required: works-in-final-package
=> computed state: COMPLETE_WITH_LIMITATIONS (U-0001 open, high)
```

The answer leads with the computed state and says plainly that the
production cause is inferred, not observed, and the packaged build was not tested.

## 12. Anti-patterns

- Choosing a cause before any discriminating probe.
- One hypothesis only, then searching for confirmation.
- Recording interpretations as evidence ("the parser is buggy").
- Quoting the five convenient lines of a 2,000-line log without declaring it.
- Saying "verified" because the code looks right.
- Resolving a contradiction by trusting the source you prefer.
- Closing an investigation because the files were created.
- Building a ledger for a one-line rename (use light mode).
