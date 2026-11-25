import sys

NAMES = b"Forest\0Ice Caves\0Desert\0Lava Lake\0"


def main(path):
    d = open(path, "rb").read()
    if d[:4] != b"LVL1":
        print("bad magic")
        return
    off = d[0x10]
    level_no = d[0x14]
    end = NAMES.find(b"\0", off)
    name = NAMES[off:end].decode("latin-1") if 0 <= off < len(NAMES) else "?"
    print(f"level #{level_no}: {name!r}, lives={d[0x18]}")


if __name__ == "__main__":
    main(sys.argv[1])
