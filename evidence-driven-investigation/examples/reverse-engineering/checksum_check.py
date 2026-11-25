"""Test hypothesis H-0002 on each file: is byte 8 == sum(bytes 9..end) mod 256?"""
import sys

for path in sys.argv[1:]:
    d = open(path, "rb").read()
    calc = sum(d[9:]) & 0xFF
    print(f"{path}: byte8={d[8]} sum(bytes[9:])&0xFF={calc} {'MATCH' if calc == d[8] else 'DIFFERENT'}")
