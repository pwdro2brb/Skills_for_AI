"""Verification for O-0002 and O-0003, run against the module in the given folder.

Prints one PASS/FAIL line per required case and a summary. Exit code 1 on failure.
Usage: python check_fix.py MODULE_DIR
"""
import importlib
import sys

sys.path.insert(0, sys.argv[1])
pricing = importlib.import_module("pricing")

cases = [
    ("dot decimal", lambda: pricing.average_price([{"price": "12.50"}, {"price": "7.50"}]) == 10.0),
    ("comma decimal", lambda: pricing.average_price([{"price": "12,50"}, {"price": "7,50"}]) == 10.0),
    ("thousands separator", lambda: pricing.parse_price("R$ 1.234,50") == 1234.5),
    ("R$ prefix", lambda: pricing.parse_price("R$ 30.00") == 30.0),
    ("empty store", lambda: pricing.average_price([]) is None),
    ("store_a unchanged", lambda: round(pricing.average_price(
        [{"price": "12.50"}, {"price": "R$ 30.00"}, {"price": "7.25"}]), 2) == 16.58),
]
failed = 0
for name, check in cases:
    try:
        ok = check()
    except Exception as exc:
        ok = False
        name += f" (raised {type(exc).__name__})"
    failed += not ok
    print(f"{'PASS' if ok else 'FAIL'} {name}")
print(f"{len(cases) - failed}/{len(cases)} passed")
sys.exit(1 if failed else 0)
