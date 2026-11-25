"""Schema validation: columns, types and ranges of sessions.csv."""
import sys
from stats_lib import load

rows = load(sys.argv[1])
problems = []
if list(rows[0]) != ["user_id", "device", "dark_mode", "session_minutes"]:
    problems.append(f"unexpected columns {list(rows[0])}")
ids = set()
for r in rows:
    if r["device"] not in ("desktop", "mobile"):
        problems.append(f"user {r['user_id']}: device {r['device']!r}")
    if r["dark_mode"] not in ("0", "1"):
        problems.append(f"user {r['user_id']}: dark_mode {r['dark_mode']!r}")
    if not 0 < float(r["session_minutes"]) < 600:
        problems.append(f"user {r['user_id']}: session_minutes {r['session_minutes']}")
    ids.add(r["user_id"])
if len(ids) != len(rows):
    problems.append("duplicate user_id")
print(f"{len(rows)} rows, {len(problems)} schema problems")
for p in problems[:20]:
    print(p)
