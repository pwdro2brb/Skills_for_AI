"""Build the rigorous mathematical example: a conjecture that holds for the first 40 cases.

Shows the rigorous gates at work. The computed state is COMPLETE_WITH_LIMITATIONS
on purpose: no independent critic reviewed this example, and the skill refuses
COMPLETE_VERIFIED without one. Claims about search results are taken from the
recorded outputs, not written in advance.

Run:  python build_example.py            (rebuilds the outputs in this folder)
      python build_example.py OUT_DIR    (builds a copy elsewhere; used by the tests)
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _example_runner import Example, write_lf  # noqa: E402

ex = Example(HERE, sys.argv[1] if len(sys.argv) > 1 else None)
E = ex.edi

E("init_investigation", "--id", "euler-polynomial", "--title", "Is n^2 + n + 41 prime for every n >= 0?",
  "--objective", "Decide, with adequate authority, whether n*n + n + 41 is prime for every integer n >= 0",
  "--mode", "rigorous", "--domain", "mathematics",
  "--scope-in", "integers n >= 0", "--scope-out", "whether infinitely many n give primes (open problem)",
  "--criterion", "the conjecture is either proven or refuted by a verified counterexample",
  "--limitation", "Computations use Python integers on one machine; algorithms are elementary and shown in full",
  "--limitation", "No independent human or agent reviewed this example")

# The obligation can close either way, so its claim type is an explicit, justified extension
ext = {"rationale": "The objective is to decide the conjecture; either a refutation or a proof closes it",
       "authorities": {},
       "claim_types": {"conjecture-decided": {
           "description": "A conjecture is either refuted by a verified counterexample or proven",
           "rationale": "Union of the base claim types conjecture-refuted and theorem-valid; adds no weaker clause",
           "any_of": [
               [{"authorities": ["counterexample-search", "numerical-test"], "min": 1},
                {"authorities": ["independent-calculation", "symbolic-computation"], "min": 1}],
               [{"authorities": ["reviewed-proof"], "min": 1}],
               [{"authorities": ["formal-proof"], "min": 1}, {"authorities": ["formalization-review"], "min": 1}]]}}}
write_lf(ex.dir / "outputs" / "authority-extension.json", json.dumps(ext, indent=2) + "\n")
E("update_investigation", "--extend-authority", "outputs/authority-extension.json")
E("record_obligation", "--claim", "The conjecture is decided", "--kind", "proof", "--required-authority", "conjecture-decided",
  "--case", "statement as given (all integers n >= 0)", "--owner", "ledger")

# Hypotheses: the conjecture, its negation, a conservative null, and measurement error
E("record_hypothesis", "--kind", "primary", "--statement", "n*n + n + 41 is prime for every integer n >= 0",
  "--prior-basis", "the claim under investigation (Euler's polynomial)",
  "--prediction", "If true, no counterexample exists for any n, in particular none up to 10000")
E("record_hypothesis", "--kind", "alternative", "--alternative", "H-0001",
  "--statement", "Some integer n >= 0 makes n*n + n + 41 composite",
  "--prior-basis", "most polynomial prime patterns break eventually; 41 is a suspicious constant",
  "--prediction", "If true, a bounded search finds n with a nontrivial factor, confirmed by an independent check")
E("record_hypothesis", "--kind", "null", "--alternative", "H-0001",
  "--statement", "The primes seen for small n carry no information about all n",
  "--prior-basis", "finitely many cases never establish a statement about infinitely many",
  "--prediction", "If true, any number of confirming small cases leaves the general claim undecided")
E("record_hypothesis", "--kind", "measurement-error", "--alternative", "H-0002",
  "--statement", "A bug in the primality code produces a false counterexample",
  "--prior-basis", "a single program could be wrong",
  "--prediction", "If true, an independent algorithm disagrees about the reported counterexample")

# Numerical cases first: evidence for H-0001, not a proof
out = ex.probe("p1-small-cases", "check_small.py", "40")
small = ex.read(out).strip()
E("record_evidence", "--claim", f"Trial division: {small}", "--source-type", "calculation", "--authority", "numerical-test",
  "--tool", "python", "--command", "python check_small.py 40", "--output-file", out, "--capture-method", "full",
  "--reproducible", "--scope", "n = 0..39 only", "--supports", "H-0001",
  "--limitation", "finite cases; says nothing about n >= 40")
refusal = ex.edi_expect_refusal("record_hypothesis", "--id", "H-0001", "--update", "--status", "VERIFIED",
                                "--claim-type", "theorem-valid", "--add-verification", "E-0001")
write_lf(ex.dir / "outputs" / "refusal-numerical-cases-as-proof.txt", refusal + "\n")
E("record_finding", "--status", "OBSERVED", "--claim", f"n*n + n + 41 is prime for n = 0..39 ({small})",
  "--evidence", "E-0001", "--scope", "n = 0..39")

# Counterexample search, then an independent check of what it finds
E("record_probe", "--question", "Is there a counterexample with n <= 10000?", "--purpose", "counterexample-search",
  "--discriminates", "H-0001,H-0002", "--expect", "H-0001=no composite value for n = 0..10000",
  "--expect", "H-0002=at least one composite value with an explicit factor",
  "--change", "n over 0..10000", "--control", "same polynomial and trial-division code",
  "--observation-authority", "counterexample-search",
  "--criterion", "any composite value refutes H-0001 once an independent check confirms it")
out = ex.probe("p2-search", "search_counterexample.py", "10000")
text = ex.read(out)
first = re.search(r"first counterexample: n=(\d+) value=(\d+) smallest factor=(\d+)", text)
count = re.search(r"composite values found: (\d+) of (\d+)", text)
n0, value, factor = first.groups()
E("record_evidence", "--claim", f"Searching n = 0..10000: first composite at n={n0} ({value} has factor {factor}); "
  f"{count.group(1)} of {count.group(2)} values are composite",
  "--source-type", "calculation", "--authority", "counterexample-search", "--tool", "python",
  "--command", "python search_counterexample.py 10000", "--output-file", out, "--capture-method", "full",
  "--reproducible", "--role", "verification", "--scope", "n = 0..10000, trial division",
  "--supports", "H-0002", "--contradicts", "H-0001")
E("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", "E-0002",
  "--outcome", f"composite at n={n0}: H-0001 refuted, pending the independent check")

E("record_probe", "--question", f"Is n={n0} really a counterexample?", "--purpose", "verify",
  "--discriminates", "H-0002,H-0004", "--expect", f"H-0002=an independent algorithm also finds {value} composite",
  "--expect", f"H-0004=an independent algorithm finds {value} prime",
  "--change", "algorithm (exact factor arithmetic + Miller-Rabin instead of trial division)",
  "--control", "same n", "--observation-authority", "independent-calculation",
  "--criterion", "agreement of both independent routes")
out = ex.probe("p3-independent", "verify_counterexample.py", n0)
E("record_evidence", "--claim", f"Independent route: {ex.read(out).strip().splitlines()[1]}; Miller-Rabin reports composite",
  "--source-type", "calculation", "--authority", "independent-calculation", "--tool", "python",
  "--command", f"python verify_counterexample.py {n0}", "--output-file", out, "--capture-method", "full",
  "--reproducible", "--role", "verification", "--scope", f"n = {n0} only",
  "--supports", "H-0002", "--contradicts", "H-0001")
E("record_probe", "--id", "P-0002", "--update", "--status", "DONE", "--result", "E-0003",
  "--outcome", "both routes agree: composite; H-0004 refuted")

for h, pred, res, status, extra in (
        ("H-0001", "H-0001.P1", "refuted", "REJECTED", ["--add-contradiction", "E-0002,E-0003"]),
        ("H-0002", "H-0002.P1", "confirmed", "VERIFIED", ["--add-support", "E-0002", "--claim-type", "conjecture-refuted",
                                                         "--add-verification", "E-0002,E-0003", "--confidence", "high",
                                                         "--confidence-rationale", "explicit factorization 41*41, checked twice"]),
        ("H-0004", "H-0004.P1", "refuted", "REJECTED", ["--add-contradiction", "E-0003"])):
    E("record_hypothesis", "--id", h, "--update", "--prediction-result", f"{pred}={res}:E-0002,E-0003", "--status", status, *extra)
E("record_hypothesis", "--id", "H-0003", "--update", "--prediction-result", "H-0003.P1=confirmed:E-0001",
  "--status", "SUPPORTED", "--add-support", "E-0001")

# Self-review is recorded honestly; it does not count as independent review
E("record_evidence", "--claim", "Self-review: the counterexample n=40 lies in the stated domain (integer, >= 0) and the tested "
  "expression is exactly n*n + n + 41", "--source-type", "document", "--authority", "independent-review",
  "--source", "review by the same agent that ran the search", "--role", "review", "--collected-by", "single-agent",
  "--artifact-kind", "file", "--artifact-value", "outputs/p3-independent.txt",
  "--scope", "statement/domain match only", "--limitation", "not independent: same agent as the producer")

E("record_obligation", "--id", "O-0001", "--update", "--add-verification", "E-0002,E-0003",
  "--case-evidence", "statement as given (all integers n >= 0)=E-0002,E-0003", "--status", "CLOSED")
E("record_finding", "--status", "VERIFIED", "--claim", f"The conjecture is false: n={n0} gives {value} = 41 * 41",
  "--claim-type", "conjecture-refuted", "--verification", "E-0002,E-0003", "--hypothesis", "H-0002",
  "--scope", "the statement as given")
E("record_finding", "--status", "REJECTED", "--claim", "The 40 prime values for n = 0..39 show the formula always gives primes",
  "--contradicting", "E-0002", "--scope", "the inference from finite cases")
E("record_unknown", "--question", "Does n*n + n + 41 take prime values for infinitely many n?", "--severity", "low",
  "--domain", "number theory")
E("record_unknown", "--id", "U-0001", "--update", "--status", "OUT_OF_SCOPE",
  "--rationale", "a different and open question (Bunyakovsky conjecture); not needed to decide the objective")

E("update_investigation", "--conclusion",
  f"Refuted. n*n + n + 41 is prime for n = 0..39 but n={n0} gives {value} = 41 * 41, found by a bounded search and "
  "confirmed by an independent algorithm. The 40 confirming cases were evidence for the pattern, never a proof. "
  "The state stops at COMPLETE_WITH_LIMITATIONS because no independent reviewer checked the work.",
  "--claim-state", "COMPLETE_WITH_LIMITATIONS")
print(ex.finish(rigorous=True))
