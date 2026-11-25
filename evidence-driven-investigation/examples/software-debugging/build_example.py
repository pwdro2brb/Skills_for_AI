"""Build the software-debugging example: a bug with two competing (and both real) causes.

Run:  python build_example.py            (rebuilds the outputs in this folder)
      python build_example.py OUT_DIR    (builds a copy elsewhere; used by the tests)
"""

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _example_runner import Example, write_lf  # noqa: E402

ex = Example(HERE, sys.argv[1] if len(sys.argv) > 1 else None)
E = ex.edi

# 1. Frame -------------------------------------------------------------------
E("init_investigation", "--id", "average-price-crash", "--title", "average_price crashes for some stores",
  "--objective", "Find why average_price() crashes for some stores, fix it, and verify the fix",
  "--mode", "investigative", "--domain", "software",
  "--scope-in", "pricing.py and the three store exports in this folder",
  "--scope-out", "other modules that parse prices",
  "--criterion", "every cause of the crash is identified by intervention",
  "--criterion", "average_price handles all observed store formats",
  "--criterion", "existing store averages are unchanged",
  "--limitation", "Only the three sample exports were examined; real exports may use other formats",
  "--limitation", "Tested with a single Python interpreter on one platform")
E("record_evidence", "--claim", "User reports that average_price crashes for some stores, not all",
  "--source-type", "user-observation", "--authority", "user-report", "--source", "bug report from the user",
  "--scope", "the user's description only; which stores and how it crashes are not stated")

# 2. Obligations from the criteria ---------------------------------------------
E("record_obligation", "--claim", "Every cause of the crash is identified by intervention", "--kind", "root-cause",
  "--required-authority", "root-cause-identified", "--case", "store_b", "--case", "store_c", "--owner", "pricing.py")
E("record_obligation", "--claim", "average_price handles every observed store format", "--kind", "fix",
  "--required-authority", "function-works", "--owner", "pricing.py", "--depends-on", "O-0001",
  "--case", "dot decimal", "--case", "comma decimal", "--case", "thousands separator",
  "--case", "R$ prefix", "--case", "empty store")
E("record_obligation", "--claim", "Averages of stores that worked before are unchanged", "--kind", "regression",
  "--severity", "major", "--required-authority", "regression-absent", "--case", "store_a", "--owner", "pricing.py")

# 3. Observe before explaining ---------------------------------------------------
out = ex.probe("p1-stores", "probe_stores.py", ".")
E("record_evidence", "--claim", "store_a: 3 rows, ok; store_b: 3 rows, raises ValueError; store_c: 0 rows, raises ZeroDivisionError",
  "--source-type", "runtime", "--authority", "runtime-trace", "--tool", "python", "--command", "python probe_stores.py .",
  "--artifact-file", "pricing.py", "--output-file", out, "--capture-method", "full",
  "--scope", "the three sample exports with the original pricing.py", "--reproducible",
  "--limitation", "exception messages not compared (they differ across Python versions)")

# 4. Competing hypotheses ----------------------------------------------------------
E("record_hypothesis", "--kind", "primary", "--statement", "Prices with a decimal comma make parse_price raise ValueError",
  "--prior-basis", "store_b raises ValueError and its prices use commas (E-0002)",
  "--prediction", "If true, converting only the commas to dots removes the error, and adding commas to working rows creates it")
E("record_hypothesis", "--kind", "alternative", "--alternative", "H-0001",
  "--statement", "Stores with no orders make average_price divide by zero",
  "--prior-basis", "store_c has 0 rows and raises ZeroDivisionError (E-0002)",
  "--prediction", "If true, an empty list raises ZeroDivisionError and one valid row removes it")
E("record_hypothesis", "--kind", "measurement-error", "--alternative", "H-0001,H-0002",
  "--statement", "The failures come from reading the CSV files (encoding/quoting), not from pricing.py",
  "--prior-basis", "store_b quotes its fields; the crash could be in the reader",
  "--prediction", "If true, the failing files are not read into the expected number of rows")

# 5. A discriminating probe -----------------------------------------------------------
E("record_probe", "--question", "Which variable produces each failure?", "--discriminates", "H-0001,H-0002,H-0003",
  "--expect", "H-0001=only the comma variants raise ValueError",
  "--expect", "H-0002=only the empty list raises ZeroDivisionError",
  "--expect", "H-0003=in-memory rows never fail; only file reading fails",
  "--change", "decimal separator", "--change", "number of rows", "--control", "same values, same module, no file I/O",
  "--observation-authority", "controlled-mutation",
  "--criterion", "a hypothesis survives only if flipping its variable alone flips the outcome")

# Gate demo: closing the root-cause obligation now is refused (no verification evidence)
refusal = ex.edi_expect_refusal("record_obligation", "--id", "O-0001", "--update", "--status", "CLOSED")
write_lf(ex.dir / "outputs" / "refusal-close-without-evidence.txt", refusal + "\n")

out = ex.probe("p2-mutations", "probe_mutations.py")
E("record_evidence", "--claim", "Comma decimals alone raise ValueError and dots alone succeed; the empty list alone raises "
  "ZeroDivisionError and one row alone succeeds; in-memory rows fail the same way as the files",
  "--source-type", "runtime", "--authority", "controlled-mutation", "--tool", "python", "--command", "python probe_mutations.py",
  "--artifact-file", "pricing.py", "--output-file", out, "--capture-method", "full", "--role", "verification",
  "--scope", "the original pricing.py, six controlled inputs", "--reproducible",
  "--supports", "H-0001,H-0002", "--contradicts", "H-0003")
E("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", "E-0003",
  "--outcome", "H-0001 and H-0002 both predicted their flips; H-0003 predicted no in-memory failure and was wrong")
E("record_hypothesis", "--id", "H-0001", "--update", "--prediction-result", "H-0001.P1=confirmed:E-0003",
  "--status", "SUPPORTED", "--confidence", "high", "--confidence-rationale", "flipping only the separator flips the outcome (E-0003)")
E("record_hypothesis", "--id", "H-0002", "--update", "--prediction-result", "H-0002.P1=confirmed:E-0003",
  "--status", "SUPPORTED", "--confidence", "high", "--confidence-rationale", "flipping only the row count flips the outcome (E-0003)")
E("record_hypothesis", "--id", "H-0003", "--update", "--prediction-result", "H-0003.P1=refuted:E-0002,E-0003", "--status", "REJECTED")
E("record_obligation", "--id", "O-0001", "--update", "--add-verification", "E-0003",
  "--case-evidence", "store_b=E-0003", "--case-evidence", "store_c=E-0003", "--status", "CLOSED")

# 6. Open questions found on the way ----------------------------------------------------------
E("record_unknown", "--question", "What should average_price return for a store with no orders?", "--severity", "medium",
  "--domain", "product decision", "--required-authority", "user-report",
  "--probe", "ask the user or the product owner")
E("record_unknown", "--question", "Do real exports also use US thousands separators such as '1,234.50'?",
  "--severity", "medium", "--domain", "data formats", "--required-authority", "primary-source",
  "--probe", "inspect a sample of real exports from every store")

# 7. Build the fix in a copy, then verify by a separate route ------------------------------------
(ex.dir / "work").mkdir()
shutil.copy(ex.dir / "fixed_pricing.py", ex.dir / "work" / "pricing.py")
out = ex.probe("construction-diff", "show_patch.py", "pricing.py", "work/pricing.py")
E("record_evidence", "--claim", "Patch: parse_price accepts comma decimals with dot thousands; average_price returns None for no orders",
  "--source-type", "static", "--authority", "static-analysis", "--tool", "difflib", "--command", "python show_patch.py pricing.py work/pricing.py",
  "--artifact-file", "work/pricing.py", "--output-file", out, "--capture-method", "full", "--role", "construction",
  "--scope", "the textual change only; says nothing about behavior", "--reproducible")
out = ex.probe("verification-checks", "check_fix.py", "work")
E("record_evidence", "--claim", "6/6 required cases pass on work/pricing.py, including store_a's unchanged average 16.58",
  "--source-type", "test", "--authority", "unit-test", "--tool", "python", "--command", "python check_fix.py work",
  "--artifact-file", "work/pricing.py", "--output-file", out, "--capture-method", "full", "--role", "verification",
  "--scope", "six inputs on the patched module; not the deployed application", "--reproducible")
E("record_obligation", "--id", "O-0002", "--update", "--add-construction", "E-0004", "--add-verification", "E-0005",
  *[f"--case-evidence={c}=E-0005" for c in ("dot decimal", "comma decimal", "thousands separator", "R$ prefix", "empty store")],
  "--status", "CLOSED")
E("record_obligation", "--id", "O-0003", "--update", "--add-construction", "E-0004", "--add-verification", "E-0005",
  "--case-evidence", "store_a=E-0005", "--status", "CLOSED")

# 8. Findings, conclusion, evaluation ------------------------------------------------------------
E("record_finding", "--status", "OBSERVED", "--claim", "store_b raises ValueError and store_c raises ZeroDivisionError; store_a works",
  "--evidence", "E-0002", "--scope", "the three sample exports, original module")
E("record_finding", "--status", "VERIFIED", "--claim", "Decimal-comma prices cause the ValueError",
  "--claim-type", "root-cause-identified", "--verification", "E-0003", "--hypothesis", "H-0001", "--scope", "original module")
E("record_finding", "--status", "VERIFIED", "--claim", "Stores without orders cause the ZeroDivisionError",
  "--claim-type", "root-cause-identified", "--verification", "E-0003", "--hypothesis", "H-0002", "--scope", "original module")
E("record_finding", "--status", "VERIFIED", "--claim", "The patched module handles every observed format and empty stores",
  "--claim-type", "function-works", "--verification", "E-0005", "--scope", "six tested inputs, patched module in work/")
E("record_finding", "--status", "ASSUMED", "--claim", "Returning None for a store without orders is acceptable",
  "--rationale", "no specification; None avoids inventing a price. Tracked as U-0001 for the user to decide",
  "--unknown", "U-0001", "--scope", "average_price on empty input")
E("update_investigation", "--conclusion",
  "There were two independent causes, not one: decimal commas (store_b) and stores without orders (store_c). "
  "Both were confirmed by controlled mutation and fixed; the fix passes all six required cases. "
  "The empty-store return value is an assumption the user should confirm.",
  "--claim-state", "COMPLETE_VERIFIED")
print(ex.finish(rigorous=True))
