#!/usr/bin/env python3
"""Build an installable zip of a skill with only its runtime files.

  python tools/package_skill.py evidence-driven-investigation

Writes dist/<skill>-<version>.zip containing <skill>/SKILL.md, agents/,
references/, schemas/, scripts/, templates/, LICENSE and README.md. Tests,
evals, examples and maintainer docs are left out, so an agent using the
installed skill never sees eval answers. The zip is deterministic (fixed
timestamps, sorted entries).
"""
import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RUNTIME = ["SKILL.md", "LICENSE", "README.md", "agents", "references", "schemas", "scripts", "templates"]


def main(name: str) -> int:
    skill = ROOT / name
    meta = (skill / "SKILL.md").read_text(encoding="utf-8")
    version = re.search(r'version:\s*"?([\w.\-]+)"?', meta).group(1)
    if not re.search(rf"^name:\s*{re.escape(name)}\s*$", meta, re.M):
        raise SystemExit(f"SKILL.md name does not match folder {name}")
    files = []
    for item in RUNTIME:
        p = skill / item
        files += [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.is_file() and "__pycache__" not in f.parts)
    out = ROOT / "dist" / f"{name}-{version}.zip"
    out.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in sorted(files):
            info = zipfile.ZipInfo(f"{name}/{f.relative_to(skill).as_posix()}", date_time=(2026, 1, 1, 0, 0, 0))
            info.external_attr = (0o755 if f.suffix == ".py" else 0o644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            zf.writestr(info, f.read_bytes())
    print(f"{out.relative_to(ROOT)}: {len(files)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "evidence-driven-investigation"))
