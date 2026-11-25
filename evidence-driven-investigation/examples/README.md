# Examples

Four investigations produced by running the skill's scripts exactly as an agent
would, with real probes. Every file in each folder's `outputs/`, every ledger,
completion result and report is real output. `tests/test_examples.py` rebuilds
them from `build_example.py` and checks they are byte-identical.

| Example | Mode | Computed state | What it shows |
| --- | --- | --- | --- |
| [software-debugging](software-debugging/) | investigative | `COMPLETE_VERIFIED` | Two independent causes behind one symptom; root cause by controlled mutation; fix verified separately from construction; an assumption tracked as an unknown |
| [reverse-engineering](reverse-engineering/) | investigative | `COMPLETE_VERIFIED` | A byte that changes with the speed is a checksum, not the speed; user claim recorded as a contradiction and resolved with new evidence; codec round trip |
| [mathematical-investigation](mathematical-investigation/) | **rigorous** | `COMPLETE_WITH_LIMITATIONS` | n²+n+41 is prime for 40 cases and fails at n=40; numerical cases refused as proof; independent check; **no independent critic, so the skill refuses COMPLETE_VERIFIED** |
| [data-analysis](data-analysis/) | investigative | `COMPLETE_WITH_LIMITATIONS` | A strong association explained by a confounder; analysis plan recorded before running; causal claim kept INFERRED; open measurement unknown |

Each folder contains:

- the fixtures and probe programs (synthetic, written for the example);
- `build_example.py`: the exact sequence of script calls;
- `investigation.json`: the ledger;
- `completion.json`: output of `evaluate_completion.py --json`;
- `report.md` and `report-rigorous.md`: output of `generate_report.py`;
- `outputs/`: captured probe outputs, including the **refusals** the scripts
  produced when the example tried to close something too early
  (`refusal-*.txt`).

Rebuild one:

```
cd examples/software-debugging
python build_example.py
```

The timestamps are fixed (`EDI_FIXED_TIME`) and every file is written with LF
line endings, so a rebuild is meant to produce the same bytes on any platform.
Verified on Linux with Python 3.9, 3.11, 3.12 and 3.13; not yet on Windows or macOS.

Do not give these folders to an agent being evaluated (see `../evals/README.md`).
