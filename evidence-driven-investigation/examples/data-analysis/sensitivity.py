"""Sensitivity analysis: does the within-device conclusion survive other summaries?
Median difference and 5%-trimmed mean difference, per device."""
import statistics
import sys
from stats_lib import load


def trimmed_mean(xs, cut=0.05):
    xs = sorted(xs)
    k = int(len(xs) * cut)
    return statistics.mean(xs[k:len(xs) - k])


rows = load(sys.argv[1])
for device in ("desktop", "mobile"):
    on = [float(r["session_minutes"]) for r in rows if r["device"] == device and r["dark_mode"] == "1"]
    off = [float(r["session_minutes"]) for r in rows if r["device"] == device and r["dark_mode"] == "0"]
    print(f"{device}: median difference {statistics.median(on) - statistics.median(off):+.2f} min; "
          f"5%-trimmed mean difference {trimmed_mean(on) - trimmed_mean(off):+.2f} min")
