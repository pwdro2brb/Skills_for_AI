"""Build the reverse-engineering example: a byte that changes with a behavior is not
necessarily that behavior. Synthetic format, generated locally; no third-party files.

Run:  python build_example.py            (rebuilds the outputs in this folder)
      python build_example.py OUT_DIR    (builds a copy elsewhere; used by the tests)
"""

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from _example_runner import Example, write_lf  # noqa: E402

ex = Example(HERE, sys.argv[1] if len(sys.argv) > 1 else None)
E = ex.edi
(ex.dir / "work").mkdir()

E("init_investigation", "--id", "tsav-byte-8", "--title", "What is byte 8 of the TSAV save file?",
  "--objective", "Establish what byte 8 of the toy engine's save files means, then write a codec that round-trips saves "
  "and can edit speed without the engine rejecting the file",
  "--mode", "investigative", "--domain", "reverse-engineering",
  "--scope-in", "TSAV saves produced by toy_engine.py in this folder",
  "--scope-out", "reading the engine's source (treated as a black box)",
  "--limitation", "Synthetic format with one engine version; samples cover four saves",
  "--limitation", "Behavior observed only through the engine's load output")
E("record_evidence", "--claim", "User reports: byte 8 changes every time the speed is changed in-game, so it is probably the speed",
  "--source-type", "user-observation", "--authority", "user-report", "--source", "user message",
  "--scope", "the user's observation and interpretation; no files attached")

# Samples: created by the engine itself (the only legitimate producer of the format)
ex.probe("samples", "-c", "import subprocess,sys;"
         "[subprocess.run([sys.executable,'toy_engine.py',*a]) for a in ("
         "['new','RACER','100','3','work/s1.sav'],['set-speed','work/s1.sav','120','work/s2.sav'],"
         "['new','','255','0','work/s3.sav'],['new','ABCDEFGHIJKLMNOP','7','9','work/s4.sav'])]")

# Obligations
E("record_obligation", "--claim", "The meaning of byte 8 is established", "--kind", "analysis",
  "--required-authority", "field-semantics", "--case", "byte 8", "--owner", "ledger")
E("record_obligation", "--claim", "save_codec.py preserves every save byte for byte, unknown bytes included",
  "--kind", "reconstruction", "--required-authority", "parser-preserves-file", "--owner", "save_codec.py",
  "--case", "normal", "--case", "after in-game edit", "--case", "empty name", "--case", "16-character name")
E("record_obligation", "--claim", "Saves edited by save_codec.py load in the engine with the new speed",
  "--kind", "reconstruction", "--required-authority", "format-reconstructed", "--owner", "save_codec.py",
  "--depends-on", "O-0001,O-0002", "--case", "speed edited")

# Observe
out = ex.probe("p1-hexdiff", "hexdiff.py", "work/s1.sav", "work/s2.sav")
E("record_evidence", "--claim", "s1 (speed 100) vs s2 (same save after in-game speed change to 120): only offsets 6, 8 and 10 differ "
  "(6: 1->2, 8: 46->66, 10: 100->120); magic TSAV aligned in both",
  "--source-type", "static", "--authority", "byte-inspection", "--tool", "hexdiff.py",
  "--command", "python hexdiff.py work/s1.sav work/s2.sav", "--artifact-file", "work/s2.sav",
  "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "one pair of saves differing by one in-game edit")

# Hypotheses about byte 8
E("record_hypothesis", "--kind", "primary", "--statement", "Byte 8 encodes the vehicle speed",
  "--prior-basis", "user report (E-0001); byte 8 changes with speed (E-0002)",
  "--prediction", "If true, changing only byte 8 changes the loaded speed")
E("record_hypothesis", "--kind", "alternative", "--alternative", "H-0001", "--statement",
  "Byte 8 is a checksum over the bytes after it", "--prior-basis", "byte 8 changed by +20 when byte 10 changed by +20 (E-0002)",
  "--prediction", "If true, changing only byte 8 makes the engine reject the save",
  "--prediction", "If true, byte 8 equals a simple function of bytes 9..27 in every sample")
E("record_hypothesis", "--kind", "alternative", "--alternative", "H-0001,H-0002", "--statement",
  "Byte 8 is part of a save counter", "--prior-basis", "offset 6 also changed by one save (E-0002)",
  "--prediction", "If true, changing only byte 8 loads normally with the same speed")
E("record_hypothesis", "--kind", "measurement-error", "--alternative", "H-0001", "--statement",
  "The diff is misaligned and the changing byte is not really at offset 8", "--prior-basis", "off-by-one is common in hex work",
  "--prediction", "If true, the magic bytes would not line up at offset 0 in both files")
E("record_hypothesis", "--id", "H-0004", "--update", "--add-contradiction", "E-0002", "--status", "REJECTED",
  "--prediction-result", "H-0004.P1=refuted:E-0002")

E("record_probe", "--question", "What happens when only byte 8 changes?", "--discriminates", "H-0001,H-0002,H-0003",
  "--expect", "H-0001=engine loads a different speed", "--expect", "H-0002=engine rejects the save",
  "--expect", "H-0003=engine loads speed 100 unchanged", "--change", "byte 8 only",
  "--control", "all other 27 bytes identical to s1", "--observation-authority", "controlled-mutation",
  "--criterion", "the engine's load line decides; any other change to the file invalidates the probe")
mut = ex.probe("p2-mutate", "mutate.py", "work/s1.sav", "work/m8.sav", "8", "71")
out = ex.probe("p2-load", "toy_engine.py", "load", "work/m8.sav")
E("record_evidence", "--claim", "With only byte 8 changed (46 -> 71), the engine rejects the save and loads defaults",
  "--source-type", "runtime", "--authority", "controlled-mutation", "--tool", "toy_engine.py",
  "--command", "python mutate.py work/s1.sav work/m8.sav 8 71 && python toy_engine.py load work/m8.sav",
  "--artifact-file", "work/m8.sav", "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "one mutated copy of s1", "--supports", "H-0002", "--contradicts", "H-0001,H-0003")
E("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", "E-0003",
  "--outcome", "rejected: only H-0002 predicted this")
for h, res, status in (("H-0001", "refuted", "REJECTED"), ("H-0003", "refuted", "REJECTED")):
    E("record_hypothesis", "--id", h, "--update", "--prediction-result", f"{h}.P1={res}:E-0003", "--status", status)

E("record_contradiction", "--severity", "medium", "--claim-a", "Byte 8 is the speed (user)", "--evidence-a", "E-0001",
  "--claim-b", "Changing byte 8 alone makes the engine reject the file", "--evidence-b", "E-0003")

out = ex.probe("p3-checksum", "checksum_check.py", "work/s1.sav", "work/s2.sav", "work/s3.sav", "work/s4.sav")
E("record_evidence", "--claim", "In all four samples byte 8 equals sum(bytes 9..27) mod 256",
  "--epistemic-status", "DERIVED", "--derived-from", "E-0002", "--source-type", "calculation",
  "--authority", "independent-calculation", "--tool", "checksum_check.py",
  "--command", "python checksum_check.py work/s1.sav work/s2.sav work/s3.sav work/s4.sav",
  "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "four samples from one engine version", "--supports", "H-0002")
E("record_contradiction", "--id", "C-0001", "--update", "--explanation-status", "interpretation=supported:E-0004",
  "--explanation-status", "tool-error=ruled-out:E-0002", "--status", "RESOLVED",
  "--resolution", "Both observations are right; the interpretation was not. Byte 8 co-varies with speed because it is a "
  "checksum over bytes 9..27, which include the speed byte (E-0004)", "--resolution-evidence", "E-0004")

out = ex.probe("construction-layout", "-c", "import save_codec; [print(k, v) for k, v in save_codec.LAYOUT.items()]")
E("record_evidence", "--claim", "save_codec.py written: layout from E-0002, checksum rule from E-0004, bytes 5 and 9 copied verbatim",
  "--source-type", "static", "--authority", "static-analysis", "--tool", "python", "--role", "construction",
  "--command", "python -c \"import save_codec; [print(k, v) for k, v in save_codec.LAYOUT.items()]\"",
  "--artifact-file", "save_codec.py", "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "the codec's declared layout; says nothing about whether it works")
E("record_probe", "--question", "Does a speed edit with a recomputed checksum load?", "--discriminates", "H-0002",
  "--expect", "H-0002=engine loads the edited speed", "--purpose", "verify", "--change", "byte 10 and byte 8 per H-0002",
  "--control", "all other bytes", "--observation-authority", "controlled-mutation",
  "--criterion", "load line shows speed 200 and no rejection")
ex.probe("p4-edit", "save_codec.py", "set-speed", "work/s1.sav", "200", "work/edited.sav")
out = ex.probe("p4-load", "toy_engine.py", "load", "work/edited.sav")
E("record_evidence", "--claim", "A save edited by save_codec.py (speed 200, checksum recomputed per H-0002) loads with speed=200",
  "--source-type", "runtime", "--authority", "runtime-trace", "--tool", "toy_engine.py", "--role", "verification",
  "--command", "python save_codec.py set-speed work/s1.sav 200 work/edited.sav && python toy_engine.py load work/edited.sav",
  "--artifact-file", "work/edited.sav", "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "one edited save, one engine version", "--supports", "H-0002")
E("record_probe", "--id", "P-0002", "--update", "--status", "DONE", "--result", "E-0006", "--outcome", "loaded speed=200")
E("record_hypothesis", "--id", "H-0002", "--update", "--prediction-result", "H-0002.P1=confirmed:E-0003",
  "--prediction-result", "H-0002.P2=confirmed:E-0004", "--status", "VERIFIED", "--claim-type", "field-semantics",
  "--add-verification", "E-0003,E-0002", "--confidence", "high",
  "--confidence-rationale", "mutation of byte 8 alone is rejected; the formula holds in 4/4 samples; a recomputed edit loads")
E("record_obligation", "--id", "O-0001", "--update", "--add-verification", "E-0003,E-0002",
  "--case-evidence", "byte 8=E-0003,E-0004", "--status", "CLOSED")

# Reconstruction: round trip, then behavior
out = ex.probe("verification-roundtrip", "save_codec.py", "roundtrip", "work/s1.sav", "work/s2.sav", "work/s3.sav", "work/s4.sav")
E("record_evidence", "--claim", "parse+write is byte-identical for s1, s2, s3 (empty name) and s4 (16-character name)",
  "--source-type", "test", "--authority", "round-trip-comparison", "--tool", "save_codec.py", "--role", "verification",
  "--command", "python save_codec.py roundtrip work/s1.sav work/s2.sav work/s3.sav work/s4.sav",
  "--artifact-file", "save_codec.py", "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "four samples; unknown bytes copied verbatim")
E("record_obligation", "--id", "O-0002", "--update", "--add-construction", "E-0005", "--add-verification", "E-0007",
  *[f"--case-evidence={c}=E-0007" for c in ("normal", "after in-game edit", "empty name", "16-character name")],
  "--status", "CLOSED")
E("record_obligation", "--id", "O-0003", "--update", "--add-construction", "E-0005", "--add-verification", "E-0007,E-0006",
  "--case-evidence", "speed edited=E-0006", "--status", "CLOSED")

# Unknown bytes stay unknown
out = ex.probe("p5-constant-bytes", "-c", "import glob; [print(p.replace('\\\\', '/'), 'byte5=%d byte9=%d' % (d[5], d[9])) "
               "for p in sorted(glob.glob('work/s*.sav')) for d in [open(p, 'rb').read()]]")
E("record_evidence", "--claim", "Byte 5 is 2 and byte 9 is 90 (0x5A) in all four samples",
  "--source-type", "static", "--authority", "byte-inspection", "--tool", "python",
  "--command", "python -c \"import glob; ...print byte 5 and byte 9 of work/s*.sav\"",
  "--artifact-file", "work/s4.sav", "--output-file", out, "--capture-method", "full", "--reproducible",
  "--scope", "four samples; constant values say nothing about meaning")
E("record_unknown", "--question", "What do byte 5 (2 in every sample) and byte 9 (0x5A in every sample) mean?",
  "--severity", "medium", "--domain", "format", "--required-authority", "field-semantics",
  "--add-support", "E-0008", "--probe", "mutate each byte alone and observe the engine")

E("record_finding", "--status", "VERIFIED", "--claim", "Byte 8 is a checksum: sum of bytes 9..27 modulo 256",
  "--claim-type", "field-semantics", "--verification", "E-0003,E-0002", "--evidence", "E-0004", "--hypothesis", "H-0002",
  "--scope", "TSAV version 1 saves from this engine")
E("record_finding", "--status", "REJECTED", "--claim", "Byte 8 is the speed", "--contradicting", "E-0003",
  "--hypothesis", "H-0001", "--scope", "TSAV version 1")
E("record_finding", "--status", "VERIFIED", "--claim", "save_codec.py round-trips saves and produces edits the engine accepts",
  "--claim-type", "format-reconstructed", "--verification", "E-0007,E-0006", "--scope", "four samples and one edit")
E("record_finding", "--status", "UNKNOWN", "--claim", "Meaning of bytes 5 and 9", "--unknown", "U-0001",
  "--scope", "preserved verbatim by the codec")
E("update_investigation", "--conclusion",
  "Byte 8 is not the speed. It is a checksum (sum of bytes 9..27 mod 256) that changes whenever the speed byte (10) "
  "changes. Changing byte 8 alone makes the engine reject the save; a codec that recomputes it produces edits the engine "
  "loads. Bytes 5 and 9 remain unknown and are preserved verbatim.", "--claim-state", "COMPLETE_VERIFIED")
print(ex.finish(rigorous=True))
