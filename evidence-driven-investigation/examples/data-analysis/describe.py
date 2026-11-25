"""Descriptive analysis: session length by dark mode (all users)."""
import sys
from stats_lib import diff_ci, fmt, load

rows = load(sys.argv[1])
on = [float(r["session_minutes"]) for r in rows if r["dark_mode"] == "1"]
off = [float(r["session_minutes"]) for r in rows if r["dark_mode"] == "0"]
print(f"dark mode on: n={len(on)} mean={sum(on) / len(on):.2f} min")
print(f"dark mode off: n={len(off)} mean={sum(off) / len(off):.2f} min")
print(f"difference on-off: {fmt(*diff_ci(on, off))}")
for device in ("desktop", "mobile"):
    group = [r for r in rows if r["device"] == device]
    share = sum(r["dark_mode"] == "1" for r in group) / len(group)
    mean = sum(float(r["session_minutes"]) for r in group) / len(group)
    print(f"{device}: n={len(group)} dark-mode share={share:.0%} mean session={mean:.2f} min")
