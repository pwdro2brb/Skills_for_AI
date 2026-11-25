"""Pre-registered causal design: difference within each device stratum, and the
stratum-size-weighted average of those differences (standardization on device)."""
import sys
from stats_lib import diff_ci, fmt, load

rows = load(sys.argv[1])
total, weighted = len(rows), 0.0
for device in ("desktop", "mobile"):
    group = [r for r in rows if r["device"] == device]
    on = [float(r["session_minutes"]) for r in group if r["dark_mode"] == "1"]
    off = [float(r["session_minutes"]) for r in group if r["dark_mode"] == "0"]
    d, lo, hi = diff_ci(on, off)
    weighted += d * len(group) / total
    print(f"{device}: n_on={len(on)} n_off={len(off)} difference {fmt(d, lo, hi)}")
print(f"device-standardized difference: {weighted:+.2f} min")
