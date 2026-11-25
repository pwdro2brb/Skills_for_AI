# What is byte 8 of the TSAV save file?

**Computed final state:** `COMPLETE_VERIFIED` (mode: investigative)

The agent's claimed state matches the computed state.

## 1. Objective

Establish what byte 8 of the toy engine's save files means, then write a codec that round-trips saves and can edit speed without the engine rejecting the file

## 2. Scope

In scope:

- TSAV saves produced by toy_engine.py in this folder

Out of scope:

- reading the engine's source (treated as a black box)

Domains: reverse-engineering

## 3. Result

Byte 8 is not the speed. It is a checksum (sum of bytes 9..27 mod 256) that changes whenever the speed byte (10) changes. Changing byte 8 alone makes the engine reject the save; a codec that recomputes it produces edits the engine loads. Bytes 5 and 9 remain unknown and are preserved verbatim.

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
| G8 | yes | Mode requirements are met | — |

Why this state:

- all gates passed

## 4. Findings by epistemic status

| ID | Status | Claim | Scope | Evidence | Claim type |
|---|---|---|---|---|---|
| F-0001 | VERIFIED | Byte 8 is a checksum: sum of bytes 9..27 modulo 256 | TSAV version 1 saves from this engine | E-0004, E-0003, E-0002 | field-semantics |
| F-0003 | VERIFIED | save_codec.py round-trips saves and produces edits the engine accepts | four samples and one edit | E-0007, E-0006 | format-reconstructed |
| F-0004 | UNKNOWN | Meaning of bytes 5 and 9 | preserved verbatim by the codec | — | — |
| F-0002 | REJECTED | Byte 8 is the speed | TSAV version 1 | against E-0003 | — |

## 5. Observations and derivations

| ID | Status | Claim | Scope |
|---|---|---|---|
| E-0001 | OBSERVED | User reports: byte 8 changes every time the speed is changed in-game, so it is probably the speed | the user's observation and interpretation; no files attached |
| E-0002 | OBSERVED | s1 (speed 100) vs s2 (same save after in-game speed change to 120): only offsets 6, 8 and 10 differ (6: 1->2, 8: 46->66, 10: 100->120); magic TSAV aligned in both | one pair of saves differing by one in-game edit |
| E-0003 | OBSERVED | With only byte 8 changed (46 -> 71), the engine rejects the save and loads defaults | one mutated copy of s1 |
| E-0004 | DERIVED | In all four samples byte 8 equals sum(bytes 9..27) mod 256 | four samples from one engine version |
| E-0008 | OBSERVED | Byte 5 is 2 and byte 9 is 90 (0x5A) in all four samples | four samples; constant values say nothing about meaning |

## 6. Hypotheses

| ID | Kind | Status | Statement | Predictions | Evidence +/− | Confidence |
|---|---|---|---|---|---|---|
| H-0001 | primary | REJECTED | Byte 8 encodes the vehicle speed | H-0001.P1 [refuted] If true, changing only byte 8 changes the loaded speed | +∅ / −E-0003 | low: |
| H-0002 | alternative | VERIFIED | Byte 8 is a checksum over the bytes after it | H-0002.P1 [confirmed] If true, changing only byte 8 makes the engine reject the save; H-0002.P2 [confirmed] If true, byte 8 equals a simple function of bytes 9..27 in every sample | +E-0003,E-0004,E-0006 / −∅ | high: mutation of byte 8 alone is rejected; the formula holds in 4/4 samples; a recomputed edit loads |
| H-0003 | alternative | REJECTED | Byte 8 is part of a save counter | H-0003.P1 [refuted] If true, changing only byte 8 loads normally with the same speed | +∅ / −E-0003 | low: |
| H-0004 | measurement-error | REJECTED | The diff is misaligned and the changing byte is not really at offset 8 | H-0004.P1 [refuted] If true, the magic bytes would not line up at offset 0 in both files | +∅ / −E-0002 | low: |

## 7. Probes and tests

| ID | Purpose | Status | Question | Expected by hypothesis | Cost/Risk | Authorization | Result | Outcome |
|---|---|---|---|---|---|---|---|---|
| P-0001 | discriminate | DONE | What happens when only byte 8 changes? | H-0001: engine loads a different speed; H-0002: engine rejects the save; H-0003: engine loads speed 100 unchanged | low/low/reversible | not required | E-0003 | rejected: only H-0002 predicted this |
| P-0002 | verify | DONE | Does a speed edit with a recomputed checksum load? | H-0002: engine loads the edited speed | low/low/reversible | not required | E-0006 | loaded speed=200 |

## 8. Evidence

| ID | Status | Epistemic | Source type | Authority | Claim | Tool / command | Artifact | Scope | Role / by | Limitations |
|---|---|---|---|---|---|---|---|---|---|---|
| E-0001 | ACTIVE | OBSERVED | user-observation | user-report | User reports: byte 8 changes every time the speed is changed in-game, so it is probably the speed | user message | — | the user's observation and interpretation; no files attached | observation / single-agent | — |
| E-0002 | ACTIVE | OBSERVED | static | byte-inspection | s1 (speed 100) vs s2 (same save after in-game speed change to 120): only offsets 6, 8 and 10 differ (6: 1->2, 8: 46->66, 10: 100->120); magic TSAV aligned in both | hexdiff.py: python hexdiff.py work/s1.sav work/s2.sav | sha256:cb4ae1cca992… (work/s2.sav) | one pair of saves differing by one in-game edit | observation / single-agent | — |
| E-0003 | ACTIVE | OBSERVED | runtime | controlled-mutation | With only byte 8 changed (46 -> 71), the engine rejects the save and loads defaults | toy_engine.py: python mutate.py work/s1.sav work/m8.sav 8 71 && python toy_engine.py load work/m8.sav | sha256:cb6250d0a39c… (work/m8.sav) | one mutated copy of s1 | observation / single-agent | — |
| E-0004 | ACTIVE | DERIVED | calculation | independent-calculation | In all four samples byte 8 equals sum(bytes 9..27) mod 256 | checksum_check.py: python checksum_check.py work/s1.sav work/s2.sav work/s3.sav work/s4.sav | — | four samples from one engine version | observation / single-agent | — |
| E-0005 | ACTIVE | OBSERVED | static | static-analysis | save_codec.py written: layout from E-0002, checksum rule from E-0004, bytes 5 and 9 copied verbatim | python: python -c "import save_codec; [print(k, v) for k, v in save_codec.LAYOUT.items()]" | sha256:525167484f3e… (save_codec.py) | the codec's declared layout; says nothing about whether it works | construction / single-agent | — |
| E-0006 | ACTIVE | OBSERVED | runtime | runtime-trace | A save edited by save_codec.py (speed 200, checksum recomputed per H-0002) loads with speed=200 | toy_engine.py: python save_codec.py set-speed work/s1.sav 200 work/edited.sav && python toy_engine.py load work/edited.sav | sha256:7389f46f31c9… (work/edited.sav) | one edited save, one engine version | verification / single-agent | — |
| E-0007 | ACTIVE | OBSERVED | test | round-trip-comparison | parse+write is byte-identical for s1, s2, s3 (empty name) and s4 (16-character name) | save_codec.py: python save_codec.py roundtrip work/s1.sav work/s2.sav work/s3.sav work/s4.sav | sha256:525167484f3e… (save_codec.py) | four samples; unknown bytes copied verbatim | verification / single-agent | — |
| E-0008 | ACTIVE | OBSERVED | static | byte-inspection | Byte 5 is 2 and byte 9 is 90 (0x5A) in all four samples | python: python -c "import glob; ...print byte 5 and byte 9 of work/s*.sav" | sha256:532ecc47a8a0… (work/s4.sav) | four samples; constant values say nothing about meaning | observation / single-agent | — |

## 9. Contradictions

**C-0001** (medium, RESOLVED)

- A: Byte 8 is the speed (user) [E-0001]
- B: Changing byte 8 alone makes the engine reject the file [E-0003]
- Resolution: Both observations are right; the interpretation was not. Byte 8 co-varies with speed because it is a checksum over bytes 9..27, which include the speed byte (E-0004) [E-0004]

| Explanation | Status | Evidence | Detail |
|---|---|---|---|
| version | untested | — | The two sides describe different versions of the artifact, document or dataset. |
| environment | untested | — | The observations were made in different environments or configurations. |
| tool-error | ruled-out | E-0002 | A tool produced a wrong or partial result. |
| interpretation | supported | E-0004 | The same observation was interpreted differently. |
| nondeterminism | untested | — | The behavior is nondeterministic (timing, ordering, randomness). |
| sample-size | untested | — | One side rests on too few cases. |
| more-complex-hypothesis | untested | — | Both are partly right; a more complex explanation covers both. |
| tampered-data | untested | — | One of the inputs was altered or corrupted. |
| ambiguous-definition | untested | — | The sides use a term or measurement differently. |
| authority-mismatch | untested | — | One side has weaker authority than the claim it is used for. |

## 10. Residual unknowns

| ID | Severity | Status | Question | Required authority | Resolution / blocker | Recommended probes |
|---|---|---|---|---|---|---|
| U-0001 | medium | OPEN | What do byte 5 (2 in every sample) and byte 9 (0x5A in every sample) mean? | field-semantics | — | mutate each byte alone and observe the engine |

## 11. Obligations

| ID | Severity | Kind | Status | Claim | Required authority | Cases (evidence) | Construction | Verification | Rationale |
|---|---|---|---|---|---|---|---|---|---|
| O-0001 | critical | analysis | CLOSED | The meaning of byte 8 is established | field-semantics | byte 8: E-0003,E-0004 | — | E-0003, E-0002 | — |
| O-0002 | critical | reconstruction | CLOSED | save_codec.py preserves every save byte for byte, unknown bytes included | parser-preserves-file | normal: E-0007; after in-game edit: E-0007; empty name: E-0007; 16-character name: E-0007 | E-0005 | E-0007 | — |
| O-0003 | critical | reconstruction | CLOSED | Saves edited by save_codec.py load in the engine with the new speed | format-reconstructed | speed edited: E-0006 | E-0005 | E-0007, E-0006 | — |

## 12. Limitations

- Synthetic format with one engine version; samples cover four saves
- Behavior observed only through the engine's load output
- Out of scope: reading the engine's source (treated as a black box)

## 13. Reproduction

- [E-0002] `python hexdiff.py work/s1.sav work/s2.sav` — hexdiff.py
- [E-0003] `python mutate.py work/s1.sav work/m8.sav 8 71 && python toy_engine.py load work/m8.sav` — toy_engine.py
- [E-0004] `python checksum_check.py work/s1.sav work/s2.sav work/s3.sav work/s4.sav` — checksum_check.py
- [E-0005] `python -c "import save_codec; [print(k, v) for k, v in save_codec.LAYOUT.items()]"` — python
- [E-0006] `python save_codec.py set-speed work/s1.sav 200 work/edited.sav && python toy_engine.py load work/edited.sav` — toy_engine.py
- [E-0007] `python save_codec.py roundtrip work/s1.sav work/s2.sav work/s3.sav work/s4.sav` — save_codec.py
- [E-0008] `python -c "import glob; ...print byte 5 and byte 9 of work/s*.sav"` — python

Not reproducible by command: E-0001.

## 14. Authority extensions and warnings

No authority extensions; the base matrix applies.

No validation warnings.

## 15. Final state

`COMPLETE_VERIFIED`. Every obligation is closed by separate verification of the required authority; no critical or high item is open.

---

<sub>Generated by scripts/generate_report.py from ledger digest `1cf68ea317b407a85fc68a3696c89782f26da6f6cd918ae494e94db7e8a407d4`. The final state is computed from the ledger by scripts/evaluate_completion.py; it is not written by the agent.</sub>
