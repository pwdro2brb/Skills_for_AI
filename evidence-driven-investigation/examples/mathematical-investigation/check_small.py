"""Numerical test: is n*n + n + 41 prime for n = 0..N-1? (trial division)"""
import sys

N = int(sys.argv[1])


def is_prime(m):
    if m < 2:
        return False
    d = 2
    while d * d <= m:
        if m % d == 0:
            return False
        d += 1
    return True


bad = [n for n in range(N) if not is_prime(n * n + n + 41)]
print(f"checked n=0..{N - 1}: {N - len(bad)} prime, {len(bad)} not prime {bad[:10]}")
