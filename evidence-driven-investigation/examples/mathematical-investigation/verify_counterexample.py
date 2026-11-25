"""Independent check of a counterexample, by a different route than the search:
exact arithmetic of the factorization plus a deterministic Miller-Rabin test."""
import sys

n = int(sys.argv[1])
value = n * n + n + 41


def miller_rabin(m):
    if m < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if m % p == 0:
            return m == p
    d, r = m - 1, 0
    while d % 2 == 0:
        d //= 2
        r += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):  # deterministic for m < 3.3e24
        x = pow(a, d, m)
        if x in (1, m - 1):
            continue
        for _ in range(r - 1):
            x = pow(x, 2, m)
            if x == m - 1:
                break
        else:
            return False
    return True


print(f"n={n}: n*n+n+41 = {value}")
print(f"41*41 = {41 * 41}; equal: {41 * 41 == value}")
if n == 40:
    print(f"algebra: 40*40+40+41 = 40*41+41 = 41*41 = {40 * 41 + 41}")
print(f"Miller-Rabin says prime: {miller_rabin(value)}")
print(f"domain check: n is an integer >= 0: {isinstance(n, int) and n >= 0}")
