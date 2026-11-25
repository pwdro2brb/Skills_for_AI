"""Construction evidence: unified diff between the original and the patched module."""
import difflib
import sys

a = open(sys.argv[1], encoding="utf-8").read().splitlines()
b = open(sys.argv[2], encoding="utf-8").read().splitlines()
print("\n".join(difflib.unified_diff(a, b, sys.argv[1], sys.argv[2], lineterm="")))
