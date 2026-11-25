"""Probe P-0001: run average_price on every store file and report the outcome.

Prints only the exception type (messages differ between Python versions).
Usage: python probe_stores.py MODULE_DIR
"""
import csv
import importlib
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1] if len(sys.argv) > 1 else ".")
pricing = importlib.import_module("pricing")
for name in ("store_a.csv", "store_b.csv", "store_c.csv"):
    with open(name, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    try:
        result = f"ok average={pricing.average_price(rows):.2f}"
    except Exception as exc:  # report the failure, do not hide it
        result = f"raises {type(exc).__name__}"
    print(f"{name}: read {len(rows)} rows -> {result}")
