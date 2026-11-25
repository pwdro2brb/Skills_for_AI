"""Probe P-0002: controlled mutations. Change one variable, hold everything else fixed.

Each line: case -> outcome. Uses the original pricing.py.
"""
import pricing


def outcome(rows):
    try:
        return f"ok {pricing.average_price(rows):.2f}"
    except Exception as exc:
        return f"raises {type(exc).__name__}"


base = [{"price": "12.50"}, {"price": "7.25"}]
cases = [
    ("baseline dot decimals", base),
    ("same rows, comma decimals only", [{"price": r["price"].replace(".", ",")} for r in base]),
    ("store_b rows with commas turned into dots", [{"price": "12.50"}, {"price": "R$ 30.00"}, {"price": "7.25"}]),
    ("store_b rows as exported (commas)", [{"price": "12,50"}, {"price": "R$ 30,00"}, {"price": "7,25"}]),
    ("empty list", []),
    ("empty list plus one valid row", [{"price": "10.00"}]),
]
for label, rows in cases:
    print(f"{label}: {outcome(rows)}")
