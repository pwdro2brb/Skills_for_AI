"""Tests for the evidence-driven-investigation scripts.

Run from the skill folder:  python -m unittest discover -s tests -v
Standard library only. If the optional `jsonschema` package is installed, the
schemas are also checked against the official Draft 2020-12 validator.
"""

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import ledger_core as core  # noqa: E402

try:
    import jsonschema  # type: ignore
except ImportError:  # optional
    jsonschema = None

FIXED = "2026-01-01T00:00:00Z"
ALL_SCRIPTS = ["init_investigation", "update_investigation", "record_evidence", "record_hypothesis",
               "record_probe", "record_unknown", "record_contradiction", "record_obligation",
               "record_finding", "validate_ledger", "evaluate_completion", "generate_report"]


class Workspace:
    """A temporary folder with a ledger, driven only through the public scripts."""

    def __init__(self, test: unittest.TestCase):
        self.test = test
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.ledger = self.dir / "inv.json"
        self.env = dict(os.environ, EDI_FIXED_TIME=FIXED, PYTHONIOENCODING="utf-8")

    def close(self):
        self.tmp.cleanup()

    def run(self, script, *args, ok=True, ledger=True):
        cmd = [sys.executable, str(SCRIPTS / f"{script}.py")]
        if ledger:
            cmd += ["--ledger", str(self.ledger)]
        cmd += [str(a) for a in args]
        proc = subprocess.run(cmd, cwd=self.dir, env=self.env, capture_output=True, text=True, encoding="utf-8")
        if ok is True and proc.returncode != 0:
            self.test.fail(f"{script} {args} failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
        if ok is False and proc.returncode == 0:
            self.test.fail(f"{script} {args} unexpectedly succeeded:\n{proc.stdout}")
        return proc

    def file(self, name, text):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def data(self):
        return json.loads(self.ledger.read_text(encoding="utf-8"))

    def state(self):
        proc = self.run("evaluate_completion", "--json")
        return json.loads(proc.stdout)

    # --- building blocks -------------------------------------------------
    def init(self, mode="investigative", *extra):
        self.run("init_investigation", "--id", "t", "--title", "T", "--objective", "Find the cause",
                 "--mode", mode, "--domain", "software", "--limitation", "test fixture", *extra)

    def evidence(self, claim, authority, source_type, role="observation", by="single-agent",
                 command=None, artifact="code.py", extra=()):
        if not (self.dir / artifact).exists():
            self.file(artifact, "print('hello')\n")
        args = ["--claim", claim, "--authority", authority, "--source-type", source_type,
                "--scope", "fixture only", "--role", role, "--collected-by", by]
        if source_type not in ("document", "user-observation"):
            args += ["--tool", "python", "--command", command or f"python {claim}", "--artifact-file", artifact]
        else:
            args += ["--source", "doc.txt", "--artifact-kind", "url", "--artifact-value", "https://example.org/doc"]
        proc = self.run("record_evidence", *args, *extra)
        return proc.stdout.strip()

    def two_hypotheses(self):
        self.run("record_hypothesis", "--kind", "primary", "--statement", "A causes it",
                 "--prior-basis", "seen in logs", "--prediction", "removing A removes the failure")
        self.run("record_hypothesis", "--kind", "alternative", "--statement", "B causes it",
                 "--prior-basis", "plausible", "--alternative", "H-0001", "--prediction", "removing B removes it")

    def verified_obligation(self, severity="critical", kind="fix"):
        oid = self.run("record_obligation", "--claim", "fix works", "--kind", kind, "--severity", severity,
                       "--required-authority", "function-works", "--case", "normal").stdout.strip()
        c = self.evidence(f"patch for {oid}", "static-analysis", "static", role="construction",
                          command=f"diff {oid}")
        v = self.evidence(f"tests pass for {oid}", "unit-test", "test", role="verification",
                          command=f"pytest {oid}")
        self.run("record_obligation", "--id", oid, "--update", "--add-construction", c,
                 "--add-verification", v, "--case-evidence", f"normal={v}", "--status", "CLOSED")
        return oid, c, v


class Base(unittest.TestCase):
    def setUp(self):
        self.ws = Workspace(self)

    def tearDown(self):
        self.ws.close()


# ---------------------------------------------------------------------------


class TestSchemasAndMatrix(unittest.TestCase):
    def test_schemas_only_use_keywords_the_validator_implements(self):
        for path in sorted(core.SCHEMA_DIR.glob("*.schema.json")):
            schema = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(core.unsupported_keywords(schema), set(), path.name)

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_schemas_are_valid_draft_2020_12(self):
        for path in sorted(core.SCHEMA_DIR.glob("*.schema.json")):
            jsonschema.Draft202012Validator.check_schema(json.loads(path.read_text(encoding="utf-8")))

    @unittest.skipIf(jsonschema is None, "jsonschema not installed")
    def test_builtin_validator_agrees_with_jsonschema(self):
        ws = Workspace(self)
        try:
            ws.init()
            ws.two_hypotheses()
            ws.verified_obligation()
            good = ws.data()
        finally:
            ws.close()
        store = {p.name: json.loads(p.read_text(encoding="utf-8")) for p in core.SCHEMA_DIR.glob("*.json")}
        registry_kwargs = {}
        try:
            from referencing import Registry, Resource  # type: ignore
            registry = Registry().with_resources((name, Resource.from_contents(s)) for name, s in store.items())
            registry_kwargs = {"registry": registry}
        except ImportError:
            registry_kwargs = {"resolver": jsonschema.RefResolver("", store["investigation.schema.json"], store=store)}
        official = jsonschema.Draft202012Validator(store["investigation.schema.json"],
                                                   format_checker=None, **registry_kwargs)
        mutations = [
            lambda d: d,
            lambda d: d["evidence"][0].__setitem__("epistemic_status", "INFERRED"),
            lambda d: d["evidence"][0].pop("scope"),
            lambda d: d["hypotheses"][0].__setitem__("extra", 1),
            lambda d: d["obligations"][0].__setitem__("severity", "huge"),
            lambda d: d["investigation"].__setitem__("mode", "fast"),
            lambda d: d["evidence"][0].__setitem__("id", "E-1"),
            lambda d: d.__setitem__("schema_version", 2),
            lambda d: d["evidence"][0]["artifact_identity"].__setitem__("kind", "md5"),
            lambda d: d["conclusion"].__setitem__("claimed_state", "DONE"),
        ]
        for i, mutate in enumerate(mutations):
            doc = copy.deepcopy(good)
            mutate(doc)
            ours = core.SchemaValidator().validate(doc, "investigation.schema.json")
            theirs = list(official.iter_errors(doc))
            self.assertEqual(bool(ours), bool(theirs), f"mutation {i}: ours={ours} theirs={[e.message for e in theirs]}")

    def test_matrix_claim_types_reference_known_authorities(self):
        m = core.load_matrix()
        for name, ct in m["claim_types"].items():
            self.assertTrue(ct["any_of"], name)
            for clause in ct["any_of"]:
                for req in clause:
                    self.assertGreaterEqual(req["min"], 1)
                    for a in req["authorities"]:
                        self.assertIn(a, m["authorities"], f"{name} uses unknown authority {a}")

    def test_one_record_never_counts_twice_in_a_clause(self):
        m = core.load_matrix()
        e1 = {"id": "E-0001", "status": "ACTIVE", "authority": "controlled-mutation", "epistemic_status": "OBSERVED"}
        e2 = {"id": "E-0002", "status": "ACTIVE", "authority": "byte-inspection", "epistemic_status": "OBSERVED"}
        self.assertFalse(core.authority_satisfied("field-semantics", [e1], m)[0])
        self.assertTrue(core.authority_satisfied("field-semantics", [e1, e2], m)[0])
        s1 = {"id": "E-0003", "status": "ACTIVE", "authority": "secondary-source", "epistemic_status": "OBSERVED"}
        s2 = dict(s1, id="E-0004")
        self.assertFalse(core.authority_satisfied("historical-claim", [s1], m)[0])
        self.assertTrue(core.authority_satisfied("historical-claim", [s1, s2], m)[0])
        self.assertFalse(core.authority_satisfied("historical-claim", [dict(s1, status="INVALIDATED"), s2], m)[0])

    def test_static_evidence_cannot_satisfy_runtime_claims(self):
        m = core.load_matrix()
        static = {"id": "E-0001", "status": "ACTIVE", "authority": "static-analysis", "epistemic_status": "OBSERVED"}
        unit = {"id": "E-0002", "status": "ACTIVE", "authority": "unit-test", "epistemic_status": "OBSERVED"}
        numeric = {"id": "E-0003", "status": "ACTIVE", "authority": "numerical-test", "epistemic_status": "OBSERVED"}
        corr = {"id": "E-0004", "status": "ACTIVE", "authority": "observational-data", "epistemic_status": "OBSERVED"}
        self.assertFalse(core.authority_satisfied("code-executed", [static], m)[0])
        self.assertFalse(core.authority_satisfied("works-in-final-package", [unit], m)[0])
        self.assertFalse(core.authority_satisfied("theorem-valid", [numeric], m)[0])
        self.assertFalse(core.authority_satisfied("causal-effect", [corr], m)[0])


class TestCommandLine(Base):
    def test_every_script_has_help(self):
        for name in ALL_SCRIPTS:
            proc = self.ws.run(name, "--help", ledger=False)
            self.assertIn("usage:", proc.stdout, name)

    def test_init_refuses_to_overwrite_and_validates_id(self):
        self.ws.init()
        proc = self.ws.run("init_investigation", "--id", "t", "--title", "T", "--objective", "O",
                           "--mode", "light", ok=False)
        self.assertIn("already exists", proc.stderr)
        self.ws.run("init_investigation", "--id", "t", "--title", "T", "--objective", "O", "--mode", "light", "--force")
        self.assertEqual(self.ws.data()["investigation"]["mode"], "light")
        self.assertEqual(self.ws.run("init_investigation", "--id", "Bad Id", "--title", "T", "--objective", "O",
                                     "--mode", "light", "--force", ok=False).returncode, 2)

    def test_init_output_matches_template(self):
        self.ws.run("init_investigation", "--id", "example", "--title", "Example", "--objective", "Describe the objective",
                    "--mode", "investigative")
        template = json.loads((ROOT / "templates" / "investigation-ledger.json").read_text(encoding="utf-8"))
        self.assertEqual(self.ws.data(), template)

    def test_missing_ledger_is_a_clear_error(self):
        proc = self.ws.run("validate_ledger", ok=False)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("not found", proc.stderr)


class TestEvidence(Base):
    def setUp(self):
        super().setUp()
        self.ws.init()

    def test_hashes_are_computed_by_the_script(self):
        p = self.ws.file("target.bin", "abc")
        self.ws.evidence("bytes", "byte-inspection", "static", artifact="target.bin")
        rec = self.ws.data()["evidence"][0]
        self.assertEqual(rec["artifact_identity"]["value"], hashlib.sha256(p.read_bytes()).hexdigest())
        self.assertEqual(rec["record_digest"], core.compute_digest(rec))

    def test_runtime_evidence_needs_tool_command_and_artifact(self):
        proc = self.ws.run("record_evidence", "--claim", "ran", "--source-type", "runtime",
                           "--authority", "runtime-trace", "--scope", "s", ok=False)
        self.assertIn("E04", proc.stderr)
        self.assertIn("E05", proc.stderr)

    def test_authority_must_match_source_type(self):
        proc = self.ws.run("record_evidence", "--claim", "read code", "--source-type", "static",
                           "--authority", "runtime-trace", "--tool", "cat", "--command", "cat x",
                           "--artifact-kind", "file", "--artifact-value", "x", "--scope", "s", ok=False)
        self.assertIn("E03", proc.stderr)

    def test_derived_needs_parents_and_duplicates_are_refused(self):
        proc = self.ws.run("record_evidence", "--claim", "rate", "--epistemic-status", "DERIVED",
                           "--source-type", "calculation", "--authority", "independent-calculation",
                           "--tool", "python", "--command", "7/50", "--scope", "s", ok=False)
        self.assertIn("E01", proc.stderr)
        self.ws.evidence("same", "unit-test", "test", command="pytest")
        proc = self.ws.run("record_evidence", "--claim", "same", "--source-type", "test", "--authority", "unit-test",
                           "--tool", "python", "--command", "pytest", "--artifact-file", "code.py", "--scope", "s", ok=False)
        self.assertIn("identical", proc.stderr)

    def test_truncated_output_is_disclosed(self):
        self.ws.file("out.txt", "\n".join(f"line {i}" for i in range(100)) + "\n")
        self.ws.evidence("long output", "runtime-trace", "runtime",
                         extra=("--output-file", "out.txt", "--shown-lines", "10", "--capture-method", "tail"))
        oc = self.ws.data()["evidence"][0]["output_capture"]
        self.assertEqual((oc["total_lines"], oc["shown_lines"], oc["method"]), (100, 10, "tail"))

    def test_hand_edit_is_detected_and_reseal_requires_explicit_flag(self):
        self.ws.evidence("observed", "runtime-trace", "runtime")
        data = self.ws.data()
        data["evidence"][0]["claim"] = "something stronger"
        self.ws.ledger.write_text(json.dumps(data), encoding="utf-8")
        proc = self.ws.run("validate_ledger", ok=False)
        self.assertIn("V005", proc.stdout)
        self.ws.run("validate_ledger", "--reseal")
        self.assertEqual(self.ws.data()["evidence"][0]["history"][-1]["action"], "resealed")


class TestRules(Base):
    def setUp(self):
        super().setUp()
        self.ws.init()
        self.ws.two_hypotheses()

    def test_unknown_resolution_needs_qualifying_observation(self):
        self.ws.run("record_unknown", "--question", "Does it run in the package?", "--severity", "critical",
                    "--required-authority", "works-in-final-package", "--requires-observation")
        unit = self.ws.evidence("unit tests pass", "unit-test", "test")
        proc = self.ws.run("record_unknown", "--id", "U-0001", "--update", "--status", "RESOLVED",
                           "--resolution-evidence", unit, "--rationale", "tests pass", ok=False)
        self.assertIn("U01", proc.stderr)
        proc = self.ws.run("record_unknown", "--id", "U-0001", "--update", "--status", "RESOLVED", ok=False)
        self.assertIn("inference does not close", proc.stderr)
        pkg = self.ws.evidence("wheel runs", "packaged-artifact-test", "test", command="pip install x.whl && run")
        self.ws.run("record_unknown", "--id", "U-0001", "--update", "--status", "RESOLVED",
                    "--resolution-evidence", pkg, "--rationale", "observed on the wheel")

    def test_contradiction_cannot_be_resolved_by_choosing_a_side(self):
        a = self.ws.evidence("docs say 30", "primary-source", "document")
        b = self.ws.evidence("trace says 10", "runtime-trace", "runtime")
        self.ws.run("record_contradiction", "--claim-a", "timeout 30", "--evidence-a", a,
                    "--claim-b", "timeout 10", "--evidence-b", b, "--severity", "high")
        c = self.ws.data()["contradictions"][0]
        self.assertEqual(len(c["possible_explanations"]), 10)
        proc = self.ws.run("record_contradiction", "--id", "C-0001", "--update", "--status", "RESOLVED",
                           "--resolution", "runtime wins", "--resolution-evidence", b, ok=False)
        self.assertIn("C02", proc.stderr)
        v = self.ws.evidence("changelog: v3 lowered default to 10", "primary-source", "document")
        self.ws.run("record_contradiction", "--id", "C-0001", "--update", "--explanation-status", f"version=supported:{v}",
                    "--status", "RESOLVED", "--resolution", "docs are v2, trace is v3", "--resolution-evidence", v)
        self.assertEqual(self.ws.data()["contradictions"][0]["status"], "RESOLVED")

    def test_obligation_closure_rules(self):
        self.ws.run("record_unknown", "--question", "blocker?", "--severity", "high")
        self.ws.run("record_obligation", "--claim", "works when packaged", "--required-authority", "works-in-final-package",
                    "--case", "normal", "--blocking-unknown", "U-0001")
        unit = self.ws.evidence("unit pass", "unit-test", "test", role="verification")
        proc = self.ws.run("record_obligation", "--id", "O-0001", "--update", "--add-verification", unit,
                           "--case-evidence", f"normal={unit}", "--status", "CLOSED", ok=False)
        self.assertIn("lacks required authority", proc.stderr)
        self.assertIn("U-0001 still OPEN", proc.stderr)
        pkg = self.ws.evidence("pkg pass", "packaged-artifact-test", "test", role="verification")
        proc = self.ws.run("record_obligation", "--id", "O-0001", "--update", "--add-verification", pkg,
                           "--add-construction", pkg, ok=False)
        self.assertIn("O08", proc.stderr)
        proc = self.ws.run("record_obligation", "--id", "O-0001", "--update", "--add-verification", pkg,
                           "--status", "CLOSED", ok=False)
        self.assertIn("required case 'normal'", proc.stderr)

    def test_risky_probe_requires_authorization(self):
        proc = self.ws.run("record_probe", "--question", "drop the table?", "--discriminates", "H-0001,H-0002",
                           "--expect", "H-0001=x", "--expect", "H-0002=y", "--criterion", "c",
                           "--reversibility", "irreversible")
        self.assertIn("requires authorization", proc.stdout)
        self.assertTrue(self.ws.data()["probes"][0]["requires_authorization"])
        e = self.ws.evidence("result", "runtime-trace", "runtime")
        proc = self.ws.run("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", e,
                           "--outcome", "o", ok=False)
        self.assertIn("P04", proc.stderr)
        self.ws.run("record_probe", "--id", "P-0001", "--update", "--authorize-by", "user", "--authorization-scope", "test db")
        self.ws.run("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", e, "--outcome", "o")

    def test_expected_results_must_cover_tested_hypotheses(self):
        proc = self.ws.run("record_probe", "--question", "q", "--discriminates", "H-0001,H-0002",
                           "--expect", "H-0001=x", "--criterion", "c", ok=False)
        self.assertIn("P02", proc.stderr)

    def test_no_promotion_without_verification(self):
        e = self.ws.evidence("pattern seen", "static-analysis", "static")
        self.ws.run("record_finding", "--status", "INFERRED", "--claim", "A is the cause", "--evidence", e,
                    "--scope", "fixture")
        proc = self.ws.run("record_finding", "--id", "F-0001", "--update", "--status", "VERIFIED",
                           "--claim-type", "root-cause-identified", ok=False)
        self.assertIn("F07", proc.stderr)
        proc = self.ws.run("record_hypothesis", "--id", "H-0001", "--update", "--status", "VERIFIED",
                           "--claim-type", "root-cause-identified", "--add-verification", e, ok=False)
        self.assertIn("H03", proc.stderr)
        proc = self.ws.run("record_hypothesis", "--id", "H-0001", "--update", "--confidence", "high",
                           "--confidence-rationale", "feels right", ok=False)
        self.assertIn("H04", proc.stderr)

    def test_alternatives_are_linked_both_ways(self):
        d = self.ws.data()
        self.assertEqual(d["hypotheses"][0]["alternatives"], ["H-0002"])
        self.assertEqual(d["hypotheses"][1]["alternatives"], ["H-0001"])

    def test_cycles_and_broken_references_are_errors(self):
        self.ws.run("record_unknown", "--question", "a")
        self.ws.run("record_unknown", "--question", "b", "--depends-on", "U-0001")
        proc = self.ws.run("record_unknown", "--id", "U-0001", "--update", "--depends-on", "U-0002", ok=False)
        self.assertIn("V006", proc.stderr)
        proc = self.ws.run("record_finding", "--status", "OBSERVED", "--claim", "x", "--evidence", "E-0099",
                           "--scope", "s", ok=False)
        self.assertIn("V004", proc.stderr)


class TestCompletion(Base):
    def test_state_cannot_be_written_by_hand(self):
        self.ws.init()
        proc = self.ws.run("update_investigation", "--claim-state", "COMPLETE_VERIFIED", ok=False)
        self.assertIn("X01", proc.stderr)
        data = self.ws.data()
        data["conclusion"]["claimed_state"] = "COMPLETE_VERIFIED"
        data["status"] = "COMPLETE_VERIFIED"
        self.ws.ledger.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.ws.run("evaluate_completion", ok=False).returncode, 2)

    def test_complete_verified_then_with_limitations(self):
        self.ws.init()
        self.ws.two_hypotheses()
        self.ws.verified_obligation()
        self.assertEqual(self.ws.state()["state"], "COMPLETE_VERIFIED")
        self.ws.run("record_obligation", "--claim", "docs updated", "--severity", "minor", "--kind", "documentation",
                    "--required-authority", "source-states")
        r = self.ws.state()
        self.assertEqual(r["state"], "COMPLETE_WITH_LIMITATIONS")
        self.assertIn("O-0002 (minor) is OPEN", " ".join(r["reasons"]))

    def test_partially_verified(self):
        self.ws.init()
        self.ws.two_hypotheses()
        self.ws.verified_obligation()
        self.ws.run("record_obligation", "--claim", "second", "--required-authority", "function-works")
        self.assertEqual(self.ws.state()["state"], "PARTIALLY_VERIFIED")

    def test_mitigated_not_resolved(self):
        self.ws.init()
        self.ws.two_hypotheses()
        self.ws.run("record_obligation", "--claim", "root cause", "--kind", "root-cause",
                    "--required-authority", "root-cause-identified")
        self.ws.verified_obligation(severity="major", kind="mitigation")
        self.assertEqual(self.ws.state()["state"], "MITIGATED_NOT_RESOLVED")

    def test_blocked_inconclusive_failed(self):
        self.ws.init()
        self.ws.two_hypotheses()
        self.ws.run("record_obligation", "--claim", "explain", "--required-authority", "root-cause-identified")
        self.assertEqual(self.ws.state()["state"], "INCONCLUSIVE")
        self.ws.run("record_unknown", "--question", "need prod logs", "--severity", "critical")
        self.ws.run("record_unknown", "--id", "U-0001", "--update", "--status", "BLOCKED",
                    "--blocked-reason", "no access to production logs")
        self.assertEqual(self.ws.state()["state"], "BLOCKED")
        e = self.ws.evidence("fix did not help", "unit-test", "test", role="verification")
        self.ws.run("record_obligation", "--id", "O-0001", "--update", "--add-verification", e,
                    "--status", "FAILED", "--rationale", "failure persists")
        self.assertEqual(self.ws.state()["state"], "FAILED")

    def test_missing_limitations_block_complete(self):
        self.ws.run("init_investigation", "--id", "t", "--title", "T", "--objective", "O", "--mode", "investigative")
        self.ws.two_hypotheses()
        self.ws.verified_obligation()
        r = self.ws.state()
        self.assertEqual(r["state"], "PARTIALLY_VERIFIED")
        self.assertIn("no limitations recorded", r["reasons"])

    def test_investigative_mode_needs_a_competing_hypothesis(self):
        self.ws.init()
        self.ws.run("record_hypothesis", "--kind", "primary", "--statement", "A", "--prior-basis", "b",
                    "--prediction", "p")
        self.ws.verified_obligation()
        r = self.ws.state()
        self.assertEqual(r["state"], "COMPLETE_WITH_LIMITATIONS")
        self.assertIn("at least 2 hypotheses", " ".join(r["reasons"]))

    def test_rigorous_mode_gates(self):
        self.ws.init("rigorous")
        self.ws.two_hypotheses()
        oid, c, v = self.ws.verified_obligation()
        reasons = " ".join(self.ws.state()["reasons"])
        for text in ("'null' hypothesis", "counterexample-search", "review evidence", "reproducible"):
            self.assertIn(text, reasons)
        self.ws.run("record_hypothesis", "--kind", "null", "--statement", "nothing changed", "--prior-basis", "default",
                    "--prediction", "same failure rate")
        e = self.ws.evidence("searched 1000 inputs, none breaks fix", "counterexample-search", "test",
                             command="python search.py --n 1000")
        self.ws.run("record_probe", "--question", "any input breaking the fix?", "--purpose", "counterexample-search",
                    "--discriminates", "H-0001", "--expect", "H-0001=no counterexample", "--criterion", "0 failures")
        self.ws.run("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", e, "--outcome", "none found")
        self.ws.evidence("critic found no flaw in the fix", "independent-review", "document", by="critic", role="review")
        v2 = self.ws.evidence("tests pass, rerun", "unit-test", "test", role="verification", command="pytest -p",
                              extra=("--reproducible",))
        self.ws.run("record_obligation", "--id", oid, "--update", "--add-verification", v2)
        r = self.ws.state()
        self.assertEqual(r["state"], "COMPLETE_WITH_LIMITATIONS")
        # every other rigorous requirement is now met; the first verification record is still not reproducible
        self.assertEqual(len(r["reasons"]), 1)
        self.assertIn(f"not reproducible: ['{v}']", r["reasons"][0])

    def test_rigorous_happy_path(self):
        self.ws.init("rigorous")
        self.ws.two_hypotheses()
        self.ws.run("record_hypothesis", "--kind", "null", "--statement", "no effect", "--prior-basis", "default",
                    "--prediction", "same rate")
        self.ws.run("record_obligation", "--claim", "fix", "--required-authority", "function-works", "--case", "normal")
        c = self.ws.evidence("patch", "static-analysis", "static", role="construction", command="git diff")
        v = self.ws.evidence("suite passes", "unit-test", "test", role="verification", by="verifier",
                             command="pytest -q", extra=("--reproducible",))
        s = self.ws.evidence("1000 random inputs, 0 failures", "counterexample-search", "test", by="verifier",
                             command="python fuzz.py --seed 1 --n 1000", extra=("--reproducible",))
        self.ws.run("record_probe", "--question", "break the fix?", "--purpose", "counterexample-search",
                    "--discriminates", "H-0001", "--expect", "H-0001=no failing input", "--criterion", "0 failures")
        self.ws.run("record_probe", "--id", "P-0001", "--update", "--status", "DONE", "--result", s, "--outcome", "0/1000")
        self.ws.evidence("review: no flaw found", "independent-review", "document", role="review", by="critic")
        self.ws.run("record_obligation", "--id", "O-0001", "--update", "--add-construction", c, "--add-verification", v,
                    "--case-evidence", f"normal={v}", "--status", "CLOSED")
        self.assertEqual(self.ws.state()["state"], "COMPLETE_VERIFIED")
        self.ws.run("update_investigation", "--claim-state", "COMPLETE_VERIFIED", "--conclusion", "fixed")
        self.ws.run("validate_ledger", "--strict", ok=None)

    def test_rigorous_verification_must_use_an_independent_route(self):
        self.ws.init("rigorous")
        self.ws.two_hypotheses()
        self.ws.run("record_obligation", "--claim", "fix", "--required-authority", "function-works")
        c = self.ws.evidence("built and tested", "unit-test", "test", role="construction", command="pytest")
        v = self.ws.evidence("verified", "unit-test", "test", role="verification", command="pytest", artifact="other.py")
        self.ws.run("record_obligation", "--id", "O-0001", "--update", "--add-construction", c,
                    "--add-verification", v, "--status", "CLOSED")
        r = self.ws.state()
        g5 = [g for g in r["gates"] if g["id"] == "G5"][0]
        self.assertFalse(g5["passed"])
        self.assertEqual(r["state"], "PARTIALLY_VERIFIED")

    def test_invalidation_reopens_dependents(self):
        self.ws.init()
        self.ws.two_hypotheses()
        oid, c, v = self.ws.verified_obligation()
        self.ws.run("record_finding", "--status", "VERIFIED", "--claim", "fixed", "--claim-type", "function-works",
                    "--verification", v, "--scope", "fixture")
        self.ws.run("record_unknown", "--question", "q", "--required-authority", "unit-test")
        self.ws.run("record_unknown", "--id", "U-0001", "--update", "--status", "RESOLVED",
                    "--resolution-evidence", v, "--rationale", "r")
        self.assertEqual(self.ws.state()["state"], "COMPLETE_VERIFIED")
        proc = self.ws.run("record_evidence", "--invalidate", v, "--reason", "tested the wrong build")
        self.assertIn(f"{oid}: CLOSED -> OPEN", proc.stdout)
        self.assertIn("U-0001: RESOLVED -> OPEN", proc.stdout)
        self.assertIn("F-0001: VERIFIED -> UNKNOWN", proc.stdout)
        d = self.ws.data()
        self.assertEqual(d["findings"][0]["unknowns"], ["U-0002"])
        self.assertEqual(self.ws.state()["state"], "INCONCLUSIVE")


class TestAdversarial(Base):
    """Attempts to get a stronger conclusion than the evidence supports."""

    def setUp(self):
        super().setUp()
        self.ws.init()
        self.ws.two_hypotheses()

    def test_construction_cannot_verify_a_finding(self):
        c = self.ws.evidence("patched and ran the tests", "unit-test", "test", role="construction")
        proc = self.ws.run("record_finding", "--status", "VERIFIED", "--claim", "fixed", "--claim-type", "function-works",
                           "--verification", c, "--scope", "s", ok=False)
        self.assertIn("F09", proc.stderr)

    def test_stale_claim_does_not_block_invalidation_or_evaluation(self):
        oid, c, v = self.ws.verified_obligation()
        self.ws.run("update_investigation", "--claim-state", "COMPLETE_VERIFIED")
        proc = self.ws.run("record_evidence", "--invalidate", v, "--reason", "wrong build")
        self.assertIn("X01", proc.stderr)
        self.assertEqual(self.ws.state()["state"], "INCONCLUSIVE")
        self.assertIn("X01", self.ws.run("validate_ledger", ok=False).stdout)
        report = self.ws.run("generate_report").stdout
        self.assertIn("does not match the computed state", report)

    def test_invalidation_cascades_to_derived_evidence(self):
        e = self.ws.evidence("7/50 runs failed", "unit-test", "test")
        self.ws.run("record_evidence", "--epistemic-status", "DERIVED", "--derived-from", e, "--claim", "14% failure",
                    "--source-type", "calculation", "--authority", "independent-calculation", "--tool", "python",
                    "--command", "7/50", "--scope", "that sample")
        proc = self.ws.run("record_evidence", "--invalidate", e, "--reason", "counted the wrong log")
        self.assertIn("E-0002: INVALIDATED", proc.stdout)
        self.assertEqual([x["status"] for x in self.ws.data()["evidence"]], ["INVALIDATED", "INVALIDATED"])

    def test_hand_closed_obligation_is_caught_even_after_reseal(self):
        self.ws.run("record_obligation", "--claim", "works", "--required-authority", "works-in-final-package")
        data = self.ws.data()
        data["obligations"][0]["status"] = "CLOSED"
        self.ws.ledger.write_text(json.dumps(data), encoding="utf-8")
        self.ws.run("validate_ledger", "--reseal", ok=False)
        out = self.ws.run("validate_ledger", ok=False).stdout
        self.assertIn("O02", out)
        self.assertNotIn("V005", out)
        self.assertEqual(self.ws.run("evaluate_completion", ok=False).returncode, 2)

    def test_waived_critical_obligation_is_not_complete(self):
        self.ws.run("record_obligation", "--claim", "works", "--required-authority", "function-works")
        self.ws.run("record_obligation", "--id", "O-0001", "--update", "--status", "WAIVED", "--rationale", "no time")
        self.ws.verified_obligation()
        self.assertEqual(self.ws.state()["state"], "PARTIALLY_VERIFIED")

    def test_unknown_requiring_observation_rejects_derived_evidence(self):
        e = self.ws.evidence("count", "unit-test", "test")
        self.ws.run("record_evidence", "--epistemic-status", "DERIVED", "--derived-from", e, "--claim", "rate",
                    "--source-type", "calculation", "--authority", "independent-calculation", "--tool", "python",
                    "--command", "1/2", "--scope", "s")
        self.ws.run("record_unknown", "--question", "q", "--required-authority", "independent-calculation",
                    "--requires-observation")
        proc = self.ws.run("record_unknown", "--id", "U-0001", "--update", "--status", "RESOLVED",
                           "--resolution-evidence", "E-0002", "--rationale", "computed", ok=False)
        self.assertIn("OBSERVED", proc.stderr)


class TestReport(Base):
    def test_report_is_deterministic_recomputes_state_and_keeps_contradictions(self):
        self.ws.init()
        self.ws.two_hypotheses()
        a = self.ws.evidence("doc A", "primary-source", "document")
        b = self.ws.evidence("doc B", "secondary-source", "document")
        self.ws.run("record_contradiction", "--claim-a", "x", "--evidence-a", a, "--claim-b", "y", "--evidence-b", b)
        self.ws.verified_obligation()
        out1 = self.ws.run("generate_report", "--format", "rigorous").stdout
        out2 = self.ws.run("generate_report", "--format", "rigorous").stdout
        self.assertEqual(out1, out2)
        self.assertIn("`COMPLETE_VERIFIED`", out1)
        self.assertIn("C-0001", out1)
        self.assertIn("nondeterminism", out1)
        self.ws.run("generate_report", "--out", "r.md")
        self.assertIn("exists", self.ws.run("generate_report", "--out", "r.md", ok=False).stderr)

    def test_invalid_ledger_report_says_state_not_computable(self):
        self.ws.init()
        data = self.ws.data()
        data["evidence"].append({"id": "E-0001"})
        self.ws.ledger.write_text(json.dumps(data), encoding="utf-8")
        self.assertEqual(self.ws.run("generate_report", ok=False).returncode, 2)
        out = self.ws.run("generate_report", "--allow-invalid").stdout
        self.assertIn("NOT_COMPUTABLE", out)


if __name__ == "__main__":
    unittest.main()
