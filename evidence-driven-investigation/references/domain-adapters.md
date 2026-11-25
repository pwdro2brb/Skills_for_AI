# Domain adapters

Contents: A. Software engineering · B. Reverse engineering · C. Mathematics ·
D. Data analysis · E. Writing a new adapter

Each adapter says which tools give which authority, which claim types to use,
and the traps typical of the domain. Claim types and authorities are in
`authority-matrix.json`; extend it per investigation when a domain needs more
(`verification-authority.md`).

## A. Software engineering

| Tool | Authority | Typical claim type |
| --- | --- | --- |
| Compiler, build system | `compiler` | `code-compiles` |
| Linter, type checker | `linter`, `type-checker` | (supporting evidence) |
| Unit, integration, property tests | `unit-test`, `integration-test`, `property-test` | `function-works`, `regression-absent` |
| Fuzzer | `fuzzing` | (counterexample search for robustness claims) |
| Benchmark with repetitions | `benchmark` | `performance-claim` |
| Static analysis, code reading | `static-analysis` | `static-reference` |
| Debugger, logs, tracing, profiler | `runtime-trace` | `code-executed`, `behavior-observed` |
| Reproduce, change one thing, revert | `controlled-mutation` | `root-cause-identified` |
| Running the built package or deployed artifact | `packaged-artifact-test` | `works-in-final-package` |

Practices:

- Reproduce before explaining. Record the failing command and its full output.
- For intermittent failures, record the failure rate with the sample size, then
  probe with fixed seeds and inputs to separate content from environment.
- A root cause is established by intervention: removing it removes the failure
  and restoring it brings the failure back. Reading the code is a hypothesis.
- Verify the fix on the artifact users run when that is the claim; a passing
  unit test closes only `function-works`.
- Add regression obligations for behavior the fix could break.

## B. Reverse engineering

| Tool | Authority | Typical claim type |
| --- | --- | --- |
| Hex dump, hashes, strings, magic numbers | `byte-inspection` | `static-reference` |
| Disassembler, decompiler, symbol and cross-reference analysis | `static-analysis` | `static-reference` |
| Comparing two identified versions | `version-diff` | (supporting evidence) |
| Trace, instrumentation, debugger | `runtime-trace` | `code-executed`, `behavior-observed` |
| Emulator | `emulation` | only claims about the emulated behavior |
| Changing one field and observing the behavior | `controlled-mutation` | `field-semantics` (with a second authority) |
| Parse then re-serialize and compare bytes | `round-trip-comparison` | `parser-preserves-file`, `format-reconstructed` |
| Running the reconstructed artifact against the original | `packaged-artifact-test` | `format-reconstructed` |

Practices:

- Hash every input before touching it, and work on copies.
- A field that changes together with a behavior is a correlation. Competing
  explanations: a counter, a checksum, a derived value, a different field
  changing with it, or coincidence. Establish meaning by controlled mutation:
  change only that field, keep everything else byte-identical, observe.
- Static presence of a code path or address does not show it executes.
- Keep unknown fields as unknowns and preserve them byte for byte in any
  writer. Do not name a field until its meaning is established.
- Compare a reconstruction with the original behavior on declared cases
  (normal, empty, truncated, maximum value, unchanged round trip).
- Limits: interoperability, preservation, debugging, authorized research and
  artifacts the user owns. No unauthorized access, malware, evasion or
  offensive exploitation (`safety-boundaries.md`). Use synthetic or legally
  redistributable samples in shared fixtures.

## C. Mathematics

| Tool | Authority | Typical claim type |
| --- | --- | --- |
| Evaluating finite cases | `numerical-test` | evidence for or against; never a proof |
| Bounded search for counterexamples | `counterexample-search` | `conjecture-refuted` (with an independent check) |
| Computer algebra | `symbolic-computation` | `calculation-correct` |
| Recomputing with an independent tool or method | `independent-calculation` | `calculation-correct`, `conjecture-refuted` |
| SAT/SMT solver | `sat-smt` | claims about the stated encoding |
| Lean, Coq, Isabelle | `formal-proof` | `theorem-valid` (with `formalization-review`) |
| Proof reviewed by someone else | `reviewed-proof` | `theorem-valid` |
| Checking the formal statement matches the original | `formalization-review` | part of `theorem-valid` |

Practices:

- Numerical cases are evidence for a hypothesis, not a general proof. Record
  the range checked; an empty search bounds where no counterexample exists.
- Search for counterexamples beyond the obvious range, including large values,
  boundary values and structured cases (squares, primes, powers of two).
- A counterexample must be checked by an independent computation before the
  conjecture is recorded as refuted.
- A formal proof proves the formal statement. Review that the formal statement
  says what the original claim says (quantifiers, domains, edge cases).
- Record the exact statement being tested; many "contradictions" are two
  slightly different statements.

## D. Data analysis

| Tool | Authority | Typical claim type |
| --- | --- | --- |
| Schema validation | `schema-validation` | `data-schema-valid` |
| Counts, distributions, correlations | `descriptive-statistics` | `correlation-exists` |
| Pre-specified statistical test with effect size and interval | `statistical-test` | `statistical-difference` |
| Held-out evaluation | `holdout-evaluation` | `model-generalizes` (with `leakage-check`) |
| Leakage check | `leakage-check` | `model-generalizes` |
| Re-running under varied assumptions | `sensitivity-analysis` | `causal-effect` (with `causal-design`) |
| Randomized or controlled intervention | `controlled-experiment` | `causal-effect` |
| Quasi-experimental design with stated assumptions | `causal-design` | `causal-effect` (with `sensitivity-analysis`) |
| Observational association | `observational-data` | `correlation-exists` only |

Practices:

- Record the dataset hash, row count, filters, seed and library versions.
- Decide metrics, tests and thresholds before looking at outcomes. Record the
  analysis plan as a probe with its interpretation criterion. Changing the
  metric after seeing the result is a new probe, and the first result stays in
  the ledger.
- No p-hacking: report every test run, not only the significant ones; correct
  for multiple comparisons when several tests are run.
- For an association, keep alternatives alive: confounding (a third variable
  drives both), reverse causation, selection bias, leakage, chance. Stratify on
  measured confounders and say which confounders are unmeasured.
- Report effect sizes and uncertainty (intervals), not only p-values.
- For predictive claims, keep a held-out set untouched until the end and check
  that no feature encodes the target or future information.
- For sequential testing over many probes (as in POPPER), use a method with
  error control such as e-values; record the method as evidence.

## E. Writing a new adapter

An adapter is a section like the ones above, plus authority extensions when
needed. For each domain answer:

1. Which tools produce observations, and which authority does each have?
2. Which claims are typical, and what is the minimum evidence for each?
3. Which evidence is commonly over-stretched (the "does not establish" list)?
4. Which hypotheses are commonly forgotten (confounders, measurement errors)?
5. Which actions are risky and need authorization?

Write extensions as JSON (`verification-authority.md`), add them with
`update_investigation.py --extend-authority`, and add a section here when the
adapter is reusable. Keep adapter text short: the agent already knows the
domain; the adapter only says what counts as evidence in it.
