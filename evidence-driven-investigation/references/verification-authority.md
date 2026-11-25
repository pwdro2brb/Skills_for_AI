# Verification authority

Data: `references/authority-matrix.json` (read by the scripts).

Contents: Two vocabularies · Core matrix · Three separate checks · Extending the matrix · What matching cannot do

Authority matching answers one question: is this kind of evidence strong
enough for this kind of claim? A compiler run can show that code compiles; it
cannot show the program behaves correctly. The matrix makes that explicit so
the scripts can refuse closures that rest on the wrong kind of evidence.

## Two vocabularies

- **Authorities** tag evidence: `unit-test`, `runtime-trace`, `static-analysis`,
  `primary-source`, `formal-proof`, `controlled-experiment`... Each lists the
  `source_type`s it can come from (a `runtime-trace` must come from `runtime`).
- **Claim types** tag what is being claimed: `function-works`,
  `code-executed`, `theorem-valid`, `causal-effect`... Each lists alternative
  clauses (`any_of`); a clause is a set of requirements, each needing N distinct
  active evidence records with one of the listed authorities. One record never
  counts twice in the same clause.

`required_authority` on obligations and unknowns accepts either a claim type
or a single authority tag.

## Core matrix

| Claim | Claim type | Minimum evidence |
| --- | --- | --- |
| The code compiles | `code-compiles` | `compiler` |
| The function works | `function-works` | a test run (`unit-test`, `integration-test`, `property-test`, `packaged-artifact-test`) |
| It works in the final package | `works-in-final-package` | `packaged-artifact-test` |
| Something is statically referenced | `static-reference` | `static-analysis` or `byte-inspection` |
| The code executed | `code-executed` | `runtime-trace` |
| A behavior was observed | `behavior-observed` | `runtime-trace`, `controlled-mutation`, `packaged-artifact-test` or `integration-test` |
| X is the root cause | `root-cause-identified` | `controlled-mutation` or `controlled-experiment` |
| No regression | `regression-absent` | a test run on the existing behavior |
| Performance claim | `performance-claim` | `benchmark` |
| The parser preserves the file | `parser-preserves-file` | `round-trip-comparison` |
| A field means X | `field-semantics` | `controlled-mutation` AND one of `static-analysis`, `runtime-trace`, `round-trip-comparison`, `byte-inspection` |
| A reconstruction matches the original | `format-reconstructed` | `round-trip-comparison` AND one of `packaged-artifact-test`, `runtime-trace`, `controlled-mutation` |
| The calculation is correct | `calculation-correct` | `independent-calculation` or `symbolic-computation` |
| A conjecture is false | `conjecture-refuted` | (`counterexample-search` or `numerical-test`) AND (`independent-calculation` or `symbolic-computation`) |
| A theorem holds | `theorem-valid` | `reviewed-proof`, or `formal-proof` AND `formalization-review` |
| A historical claim is true | `historical-claim` | 1 `primary-source`, or 2 `secondary-source` |
| A document says X | `source-states` | `primary-source` or `secondary-source` |
| Two variables are associated | `correlation-exists` | `descriptive-statistics`, `statistical-test` or `observational-data` |
| A difference is real | `statistical-difference` | `statistical-test` |
| An intervention caused an effect | `causal-effect` | `controlled-experiment`, or `causal-design` AND `sensitivity-analysis` |
| A model generalizes | `model-generalizes` | `holdout-evaluation` AND `leakage-check` |
| Data matches a schema | `data-schema-valid` | `schema-validation` |
| The user reported X | `user-reported` | `user-report` |

Note what is absent on purpose: no claim type accepts `observational-data`
for causation, `numerical-test` for a theorem, `static-analysis` for execution,
`unit-test` for the packaged artifact, `emulation` for real hardware, or
`user-report` for anything but the report itself.

## Three separate checks

Borrowed from REA's obligation ledgers:

1. **Authenticity**: the evidence is what it says it is. Hashes, record digests
   and commands support this.
2. **Authority**: the evidence is the right kind for the claim. The matrix.
3. **Applicability**: the evidence is about the current artifact. Set
   `applies_to` on an obligation (a hash, commit or version) and the validator
   refuses verification evidence about any other artifact. Old evidence stays
   as provenance but cannot close an obligation about a new version.

## Extending the matrix

Domain adapters and individual investigations add authorities or claim types
through the ledger, never by editing the base file mid-investigation:

```json
{
  "rationale": "Hardware-in-the-loop rig is the only authority for timing on the device",
  "authorities": {
    "hil-measurement": {
      "description": "Timing measured on the physical device in the HIL rig",
      "source_types": ["runtime"],
      "rationale": "Emulator timing differs from the device by up to 20%"
    }
  },
  "claim_types": {
    "device-timing": {
      "description": "A timing property holds on the device",
      "rationale": "Separates device claims from emulator claims",
      "any_of": [[{"authorities": ["hil-measurement"], "min": 1}]]
    }
  }
}
```

```
python scripts/update_investigation.py --ledger L --extend-authority extension.json
```

Extensions cannot override base entries, need a rationale, and appear in the
rigorous report. An extension that weakens a claim (for example accepting
`unit-test` for "works in production") is visible to every reader of the report.

## What matching cannot do

The scripts compare labels. If evidence is labelled `runtime-trace` with
`source_type: runtime` but was actually a reading of source code, the script
accepts it. Coherence is checked; truth is not. The report shows the tool and
command of every record so a reviewer can catch mislabelling.
