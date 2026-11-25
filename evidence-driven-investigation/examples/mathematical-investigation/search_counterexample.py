"""Bounded counterexample search for 'n*n + n + 41 is prime for all n >= 0' (trial division)."""
import sys

LIMIT = int(sys.argv[1])


def smallest_factor(m):
    d = 2
    while d * d <= m:
        if m % d == 0:
            return d
        d += 1
    return m


composites = []
for n in range(LIMIT + 1):
    v = n * n + n + 41
    f = smallest_factor(v)
    if f != v:
        composites.append((n, v, f))
print(f"searched n=0..{LIMIT}")
print(f"first counterexample: n={composites[0][0]} value={composites[0][1]} smallest factor={composites[0][2]}")
print(f"composite values found: {len(composites)} of {LIMIT + 1}")
print("first five:", ", ".join(f"n={n}:{v}={f}*{v // f}" for n, v, f in composites[:5]))
