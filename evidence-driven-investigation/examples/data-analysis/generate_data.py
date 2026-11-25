"""Generate sessions.csv: synthetic usage data with a built-in confounder.

Ground truth (hidden from the investigation, documented here for readers):
device drives both dark-mode adoption and session length; dark mode itself has
no effect. Uses only random.random() so the file is identical on every Python.
"""
import math
import random

rng = random.Random(20261125)


def normal(mu, sigma):  # Box-Muller from random(), stable across versions
    u1, u2 = rng.random(), rng.random()
    return mu + sigma * math.sqrt(-2 * math.log(1 - u1)) * math.cos(2 * math.pi * u2)


with open("sessions.csv", "w", encoding="utf-8", newline="\n") as fh:
    fh.write("user_id,device,dark_mode,session_minutes\n")
    for uid in range(1, 2001):
        desktop = rng.random() < 0.45
        dark = rng.random() < (0.70 if desktop else 0.20)
        minutes = max(0.5, normal(31.0 if desktop else 12.0, 6.0))
        fh.write(f"{uid},{'desktop' if desktop else 'mobile'},{int(dark)},{minutes:.1f}\n")
