"""Reconstructed codec for the TSAV format, written from the evidence in the ledger.

Unknown bytes (5 and 9) are kept verbatim; the writer never invents them.

  python save_codec.py roundtrip FILE...            parse + write, compare bytes
  python save_codec.py set-speed IN SPEED OUT       edit speed, recompute checksum
"""
import hashlib
import sys

LAYOUT = {  # offset: meaning, as established in the ledger
    "magic": (0, 4), "version": (4, 5), "unknown_5": (5, 6), "counter_le16": (6, 8),
    "checksum": (8, 9), "unknown_9": (9, 10), "speed": (10, 11), "color": (11, 12), "name": (12, 28),
}


def parse(data):
    return {k: data[a:b] for k, (a, b) in LAYOUT.items()}


def write(fields, recompute_checksum=False):
    body = b"".join(fields[k] for k in ("unknown_9", "speed", "color", "name"))
    checksum = bytes([sum(body) & 0xFF]) if recompute_checksum else fields["checksum"]
    return fields["magic"] + fields["version"] + fields["unknown_5"] + fields["counter_le16"] + checksum + body


if __name__ == "__main__":
    if sys.argv[1] == "roundtrip":
        for path in sys.argv[2:]:
            data = open(path, "rb").read()
            again = write(parse(data))
            same = "IDENTICAL" if again == data else "DIFFERENT"
            print(f"{path}: {same} sha256 {hashlib.sha256(data).hexdigest()[:16]} -> {hashlib.sha256(again).hexdigest()[:16]}")
    elif sys.argv[1] == "set-speed":
        fields = parse(open(sys.argv[2], "rb").read())
        fields["speed"] = bytes([int(sys.argv[3])])
        open(sys.argv[4], "wb").write(write(fields, recompute_checksum=True))
        print(f"{sys.argv[4]}: speed set to {sys.argv[3]}, checksum recomputed")
