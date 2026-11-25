# Contradiction handling

Schema: `schemas/contradiction.schema.json`. Script: `scripts/record_contradiction.py`.

A contradiction (`C-0001`) records two claims that cannot both be true as
stated, with the evidence behind each side. Contradictions are never deleted
and always appear in the report, resolved or not.

## Record it as soon as you see it

```
python scripts/record_contradiction.py --ledger L --severity high \
    --claim-a "Docs: default timeout is 30 s" --evidence-a E-0002 \
    --claim-b "Trace: request aborted at 10 s" --evidence-b E-0005
```

The script pre-fills a checklist of standard explanations, each `untested`:

| Category | Question to ask |
| --- | --- |
| `version` | Do the sides describe different versions? |
| `environment` | Different platform, configuration, flags, data? |
| `tool-error` | Did a tool give a wrong or partial result? |
| `interpretation` | Is the same observation read two ways? |
| `nondeterminism` | Timing, ordering, randomness? |
| `sample-size` | Does one side rest on too few cases? |
| `more-complex-hypothesis` | Are both partly right under a richer explanation? |
| `tampered-data` | Was an input altered or corrupted? |
| `ambiguous-definition` | Do the sides use a term or measure differently? |
| `authority-mismatch` | Is one side weaker evidence than the claim it backs? |

Mark explanations as you test them:
`--explanation-status "version=supported:E-0007"` or `"environment=ruled-out:E-0006"`.
Ruled-out and supported both need evidence. Use `--explanation other=TEXT`
for anything else.

## Resolving

`RESOLVED` is accepted only when:

1. at least one explanation is `supported` with evidence;
2. the resolution evidence includes at least one active record that is **not**
   one of the two conflicting sides;
3. a resolution text explains which explanation holds and why.

So "the runtime trace is more convincing than the docs" is refused: it adds no
evidence. "The docs describe v2; the trace is v3.1, and the v3.0 changelog
(E-0007) lowered the default to 10 s" is accepted.

`OUT_OF_SCOPE` needs a text explaining why the conflict does not affect the
objective; it is reported.

## Severity

Use the same scale as unknowns. An open critical contradiction prevents any
COMPLETE_* state; an open high one limits the state to
COMPLETE_WITH_LIMITATIONS. Link a contradiction to the obligations it blocks
with `record_obligation.py --blocking-contradiction C-0001`.

## When it cannot be resolved

Leave it OPEN and say so in the answer. An unresolved contradiction honestly
reported is a valid outcome; a contradiction made to disappear is not.
