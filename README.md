# Skills for AI

Agent Skills in the open [Agent Skills](https://agentskills.io/specification)
format, usable with Claude and other agents.

| Skill | What it does |
| --- | --- |
| [evidence-driven-investigation](evidence-driven-investigation/) | Evidence-gated investigation: competing hypotheses, recorded evidence with authority, residual unknowns, contradictions, obligations, and a final state computed by scripts. |

Build an installable zip of a skill (runtime files only):

```
python tools/package_skill.py evidence-driven-investigation
```
