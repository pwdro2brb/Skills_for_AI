"""A toy 'game' that reads and writes its own save files. Treated as a black box.

The investigation runs this program and observes its output; it does not read
its source (in a real case you would only have a binary).

  python toy_engine.py new NAME SPEED COLOR OUT     create a save
  python toy_engine.py set-speed IN SPEED OUT       load, change speed in-game, save
  python toy_engine.py load FILE                    print what the game loads
"""
import struct
import sys

DEFAULT_SPEED = 100


def _checksum(body):
    return sum(body) & 0xFF


def _pack(counter, speed, color, name, flags=0x02):
    tail = bytes([0x5A, speed, color]) + name.encode("ascii")[:16].ljust(16, b"\0")
    return b"TSAV" + bytes([1, flags]) + struct.pack("<H", counter) + bytes([_checksum(tail)]) + tail


def load(data):
    if data[:4] != b"TSAV" or len(data) != 28:
        return None
    if _checksum(data[9:]) != data[8]:
        return None
    counter = struct.unpack("<H", data[6:8])[0]
    return {"counter": counter, "flags": data[5], "speed": data[10], "color": data[11],
            "name": data[12:28].rstrip(b"\0").decode("ascii")}


def main(argv):
    cmd = argv[0]
    if cmd == "new":
        name, speed, color, out = argv[1], int(argv[2]), int(argv[3]), argv[4]
        open(out, "wb").write(_pack(1, speed, color, name))
    elif cmd == "set-speed":
        state = load(open(argv[1], "rb").read())
        open(argv[3], "wb").write(_pack(state["counter"] + 1, int(argv[2]), state["color"], state["name"], state["flags"]))
    elif cmd == "load":
        state = load(open(argv[1], "rb").read())
        if state is None:
            print(f"{argv[1]}: save rejected (corrupt); defaults loaded: speed={DEFAULT_SPEED}")
        else:
            print(f"{argv[1]}: loaded speed={state['speed']} color={state['color']} name='{state['name']}'")


if __name__ == "__main__":
    main(sys.argv[1:])
