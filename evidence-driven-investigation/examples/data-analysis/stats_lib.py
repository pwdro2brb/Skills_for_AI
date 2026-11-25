"""Small, explicit statistics helpers (standard library only)."""
import csv
import math
import statistics


def load(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def diff_ci(a, b):
    """Difference of means a-b with a Welch 95% interval (normal approximation)."""
    d = statistics.mean(a) - statistics.mean(b)
    se = math.sqrt(statistics.variance(a) / len(a) + statistics.variance(b) / len(b))
    return d, d - 1.96 * se, d + 1.96 * se


def fmt(d, lo, hi):
    return f"{d:+.2f} min (95% CI {lo:+.2f} to {hi:+.2f})"
