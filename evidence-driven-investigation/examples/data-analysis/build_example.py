"""Build the data-analysis example: a strong association that is not a causal effect.

The analysis plan is recorded before the analyses run; claims quote the recorded
outputs. sessions.csv is synthetic (see generate_data.py).

Run:  python build_example.py            (rebuilds the outputs in this folder)
      python build_example.py OUT_DIR    (builds a copy elsewhere; used by the tests)
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _example_runner import Example, write_lf  # noqa: E402

ex = Example(HERE, sys.argv[1] if len(sys.argv) > 1 else None)
E = ex.edi


def lines(rel):
    return ex.read(rel).strip().splitlines()


E("init_investigation", "--id", "dark-mode-sessions", "--title", "Does dark mode make sessions longer?",
  "--objective", "Determine whether enabling dark mode causes longer sessions, using sessions.csv",
  "--mode", "investigative", "--domain", "data-analysis",
  "--scope-in", "sessions.csv (2000 users, one snapshot)", "--scope-out", "running a randomized experiment",
  "--criterion", "the association is quantified with uncertainty",
  "--criterion", "the causal reading is tested against measured confounders, with a sensitivity check",
  "--limitation", "Observational snapshot: only measured confounders can be adjusted for",
  "--limitation", "Synthetic data; conclusions illustrate the method, not real users")
E("record_evidence", "--claim", "Product team reports that dark-mode users have much longer sessions and asks whether to turn it on by default",
  "--source-type", "user-observation", "--authority", "user-report", "--source", "user request",
  "--scope", "the request; no analysis attached")

E("record_obligation", "--claim", "sessions.csv matches the expected schema", "--kind", "analysis", "--severity", "major",
  "--required-authority", "data-schema-valid", "--case", "columns and types", "--owner", "sessions.csv")
E("record_obligation", "--claim", "The association between dark mode and session length is quantified with a 95% interval",
  "--kind", "analysis", "--required-authority", "correlation-exists", "--case", "all users", "--depends-on", "O-0001")
E("record_obligation", "--claim", "The causal reading is tested against the device confounder with a causal design and a sensitivity analysis",
  "--kind", "analysis", "--required-authority", "causal-effect", "--case", "desktop", "--case", "mobile", "--depends-on", "O-0002")

out = ex.probe("p0-schema", "schema_check.py", "sessions.csv")
E("record_evidence", "--claim", lines(out)[0], "--source-type", "test", "--authority", "schema-validation",
  "--tool", "python", "--command", "python schema_check.py sessions.csv", "--artifact-file", "sessions.csv",
  "--output-file", out, "--capture-method", "full", "--reproducible", "--role", "verification",
  "--scope", "column names, allowed values, ranges, unique ids")
E("record_obligation", "--id", "O-0001", "--update", "--add-verification", "E-0002",
  "--case-evidence", "columns and types=E-0002", "--status", "CLOSED")

E("record_hypothesis", "--kind", "primary", "--statement", "Dark mode causes longer sessions",
  "--prior-basis", "the product team's observation (E-0001)",
  "--prediction", "If true, dark-mode users have longer sessions overall AND within each device type",
  "--confounder", "device type (desktop sessions are longer and desktop users may prefer dark mode)")
E("record_hypothesis", "--kind", "alternative", "--alternative", "H-0001",
  "--statement", "Device type drives both dark-mode use and session length; dark mode itself has no effect",
  "--prior-basis", "desktop and mobile differ in both habits",
  "--prediction", "If true, the overall difference shrinks to about zero within each device type")
E("record_hypothesis", "--kind", "null", "--alternative", "H-0001",
  "--statement", "There is no association between dark mode and session length",
  "--prior-basis", "conservative default", "--prediction", "If true, the overall 95% interval includes zero")
E("record_hypothesis", "--kind", "measurement-error", "--alternative", "H-0001",
  "--statement", "Session length is measured differently on desktop and mobile clients",
  "--prior-basis", "mobile apps often stop timers when backgrounded",
  "--prediction", "If true, the instrumentation documentation or client code shows different session definitions")

E("record_probe", "--question", "Is there an association, and does it survive stratification by device?",
  "--discriminates", "H-0001,H-0002,H-0003",
  "--expect", "H-0001=positive overall difference that remains positive within both devices",
  "--expect", "H-0002=positive overall difference that is near zero within both devices",
  "--expect", "H-0003=overall interval includes zero",
  "--change", "stratification on device", "--control", "same data, same estimator (difference of means, Welch 95% CI)",
  "--observation-authority", "causal-design",
  "--criterion", "decided before running: an effect 'remains' if both within-device intervals exclude zero in the same "
  "direction; 'near zero' if both include zero. Only these two analyses plus the sensitivity check are run.")

out = ex.probe("p1-describe", "describe.py", "sessions.csv")
d = lines(out)
E("record_evidence", "--epistemic-status", "DERIVED", "--derived-from", "E-0002",
  "--claim", f"All users: {d[2]}; {d[3]}; {d[4]}", "--source-type", "calculation", "--authority", "descriptive-statistics",
  "--tool", "python", "--command", "python describe.py sessions.csv", "--output-file", out, "--capture-method", "full",
  "--reproducible", "--role", "verification", "--scope", "all 2000 users, unadjusted",
  "--supports", "H-0001,H-0002", "--contradicts", "H-0003")
E("record_obligation", "--id", "O-0002", "--update", "--add-verification", "E-0003",
  "--case-evidence", "all users=E-0003", "--status", "CLOSED")

out = ex.probe("p1-stratify", "stratify.py", "sessions.csv")
s = lines(out)
E("record_evidence", "--epistemic-status", "DERIVED", "--derived-from", "E-0002",
  "--claim", f"Within device: {s[0]}; {s[1]}; {s[2]}", "--source-type", "calculation", "--authority", "causal-design",
  "--tool", "python", "--command", "python stratify.py sessions.csv", "--output-file", out, "--capture-method", "full",
  "--reproducible", "--role", "verification", "--scope", "adjusts for device only; unmeasured confounders remain",
  "--supports", "H-0002", "--contradicts", "H-0001")
out = ex.probe("p2-sensitivity", "sensitivity.py", "sessions.csv")
v = lines(out)
E("record_evidence", "--epistemic-status", "DERIVED", "--derived-from", "E-0002",
  "--claim", f"Other summaries agree: {v[0]}; {v[1]}", "--source-type", "calculation", "--authority", "sensitivity-analysis",
  "--tool", "python", "--command", "python sensitivity.py sessions.csv", "--output-file", out, "--capture-method", "full",
  "--reproducible", "--role", "verification", "--scope", "median and trimmed means within device", "--supports", "H-0002")
E("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", "E-0003,E-0004,E-0005",
  "--outcome", "overall difference positive with an interval excluding zero; both within-device intervals include zero: "
  "matches H-0002, contradicts H-0001 and H-0003")
E("record_obligation", "--id", "O-0003", "--update", "--add-verification", "E-0004,E-0005",
  "--case-evidence", "desktop=E-0004,E-0005", "--case-evidence", "mobile=E-0004,E-0005", "--status", "CLOSED")

E("record_hypothesis", "--id", "H-0001", "--update", "--prediction-result", "H-0001.P1=refuted:E-0004",
  "--status", "CONTRADICTED", "--status-rationale", "not REJECTED: measurement differences (H-0004) are untested")
E("record_hypothesis", "--id", "H-0002", "--update", "--prediction-result", "H-0002.P1=confirmed:E-0004",
  "--status", "SUPPORTED", "--confidence", "moderate",
  "--confidence-rationale", "matches the pre-registered pattern and survives the sensitivity check; unmeasured confounders remain")
E("record_hypothesis", "--id", "H-0003", "--update", "--prediction-result", "H-0003.P1=refuted:E-0003", "--status", "REJECTED")

E("record_unknown", "--question", "Is session_minutes defined the same way on desktop and mobile clients?",
  "--severity", "high", "--domain", "instrumentation", "--required-authority", "primary-source", "--requires-observation",
  "--probe", "read the analytics instrumentation spec or client code for both platforms")
E("record_hypothesis", "--id", "H-0004", "--update", "--status", "TESTING", "--next-probe", "U-0001")
E("record_unknown", "--question", "Could an unmeasured variable (age, plan type, usage purpose) confound the within-device comparison?",
  "--severity", "medium", "--domain", "study design", "--required-authority", "controlled-experiment",
  "--probe", "an A/B test that assigns dark mode at random")

E("record_finding", "--status", "VERIFIED", "--claim", "Dark-mode users have longer sessions overall",
  "--claim-type", "correlation-exists", "--verification", "E-0003", "--scope", "all 2000 users, unadjusted")
E("record_finding", "--status", "DERIVED", "--claim", "Within each device type the difference is near zero (both 95% intervals include zero)",
  "--evidence", "E-0004,E-0005", "--scope", "adjusted for device only")
E("record_finding", "--status", "INFERRED", "--claim", "Turning dark mode on by default would not lengthen sessions",
  "--evidence", "E-0004,E-0005", "--hypothesis", "H-0002", "--unknown", "U-0001,U-0002",
  "--scope", "a causal prediction from observational data; not tested by intervention")
E("update_investigation", "--conclusion",
  "The association is real but explained by device: desktop users both prefer dark mode and have longer sessions. Within "
  "each device type the difference is near zero, and other summaries agree. Do not expect longer sessions from enabling "
  "dark mode by default. This is inferred from observational data; an A/B test would settle it, and the session metric's "
  "definition per platform (U-0001) is unverified.", "--claim-state", "COMPLETE_WITH_LIMITATIONS")
print(ex.finish(rigorous=True))
