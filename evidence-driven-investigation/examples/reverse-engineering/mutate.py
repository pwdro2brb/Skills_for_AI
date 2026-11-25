"""Controlled mutation: copy IN to OUT changing exactly one byte."""
import sys

src, out, offset, value = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
data = bytearray(open(src, "rb").read())
old = data[offset]
data[offset] = value
open(out, "wb").write(bytes(data))
print(f"{out}: offset {offset} {old} -> {value}; all other {len(data) - 1} bytes identical to {src}")
