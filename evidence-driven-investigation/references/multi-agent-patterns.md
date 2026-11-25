# Multi-agent patterns (optional)

The skill works with a single agent. Use sub-agents only when the platform
offers them and a task has a clear boundary that benefits from a fresh or
independent context. More agents is not more rigor.

## Roles

| Role | Delegated question (example) | Returns |
| --- | --- | --- |
| Coordinator | Owns the canonical ledger, the mode and the final report | — |
| Observer | "Inventory the fields of `sample.bin` with offsets and hashes" | Evidence records |
| Hypothesis generator | "Given E-0001..E-0006, list competing explanations with predictions" | Hypotheses |
| Researcher | "Find the primary source for the default timeout of library X v3" | Evidence with sources |
| Experimenter | "Run probe P-0003 exactly as recorded" | Evidence + probe outcome |
| Implementer | "Implement the fix for O-0001" | Construction evidence |
| Adversarial critic | "Find the weakest point of this conclusion and how it could be wrong" | Review evidence, new unknowns or contradictions |
| Counterexample searcher | "Search for an input that breaks claim F-0002 within bounds B" | Counterexample-search evidence |
| Verifier | "Verify O-0001 without reading the implementer's notes" | Verification evidence |
| Synthesizer | "Draft the report from the ledger" | Draft only; the coordinator checks it |

## Rules

1. Do not create sub-agents to increase volume. Delegate only bounded tasks.
2. Give each agent one bounded question, the relevant IDs and the evidence it
   may rely on, not the whole conversation.
3. Separate the agent that proposes from the one that critiques, and the one
   that builds from the one that verifies. Record their identities in
   `collected_by` (`implementer`, `verifier`, `critic`...).
4. Require structured returns: JSON records matching the schemas, so the
   coordinator can import them with `--input report.json`. Prose summaries are
   interpreted evidence; ask for the raw outputs and commands.
5. Preserve provenance: sub-agent evidence keeps its tool, command, artifact
   hash and scope. The coordinator does not rewrite it.
6. Agreement between agents is not evidence. Two agents that read the same
   code and agree add no authority beyond one reading.
7. Deduplicate: the coordinator merges equivalent hypotheses (the validator
   warns on identical statements) and refuses duplicate evidence.
8. Summaries must not drop limitations, unknowns or contradictions. The
   coordinator compares the sub-agent's report with the records it imports.
9. Only the coordinator writes the canonical ledger. Sub-agents return records;
   they do not edit the ledger directly. This avoids concurrent writes and keeps
   one history.

## Independence in rigorous mode

The rigorous gate needs review evidence whose `collected_by` differs from the
producers. An independent critic is one that did not produce the work and does
not receive the producer's reasoning, only the claim and the evidence. If the
platform has no sub-agents, a person can act as critic, or the investigation
reports COMPLETE_WITH_LIMITATIONS with "no independent review" as a limitation.

## Prompt skeleton for a delegated task

```
Question: <one bounded question>
Context: <IDs and short claims of the relevant ledger records>
You may use: <tools, files, read-only or not>
Do not: <modify X, contact external services, ...>
Return: a JSON list of evidence records with fields
  claim, source_type, authority, tool, command_or_method, artifact_identity,
  scope, limitations, reproducible, collected_by="<role>"
Also list: anything you could not determine (as questions) and anything that
contradicts the context you were given.
```
