"""Print every offset where two files differ (byte inspection)."""
import sys

a, b = open(sys.argv[1], "rb").read(), open(sys.argv[2], "rb").read()
print(f"{sys.argv[1]} ({len(a)} bytes) vs {sys.argv[2]} ({len(b)} bytes)")
print(f"magic {a[:4]!r} vs {b[:4]!r}")
for i in range(max(len(a), len(b))):
    x = a[i] if i < len(a) else None
    y = b[i] if i < len(b) else None
    if x != y:
        print(f"offset {i:2d} (0x{i:02X}): {x!r:>4} -> {y!r:>4}")
