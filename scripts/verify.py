"""Reproduce fixed local checks and four isolated semantic mutations.

Runs only reviewed owned Python/tests and installed Bandit, never upstream code.
Evidence must use a fresh folder. Failed checks remain recorded; no auto retries.
Six narrow subprocess scanner exceptions are documented in VERIFICATION.md.
"""

import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess  # nosec B404: fixed owned Python/tests and installed scanner commands.
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from breaker_lab import model, render  # noqa: E402
from tests.support import FIXTURE_SHA, cases, document, encode  # noqa: E402

MUTATIONS = {
    "deny-cooldown-equality": ('if action.time_ms < state.opened_at_ms + policy.cooldown_ms:',
                               'if action.time_ms <= state.opened_at_ms + policy.cooldown_ms:', 1),
    "admission-time-opening": ('_open(state, action.time_ms, summary, transitions)',
                               '_open(state, pending.admitted_at_ms, summary, transitions)', 2),
    "early-recovery-close": ('if state.recovery_success_streak >= policy.success_threshold:',
                             'if state.recovery_success_streak >= 1:', 1),
    "allow-unowned-completion": ('if pending is None or pending.attempt_id != action.attempt_id:\n        raise LabError("trace.invalid")',
                                 'if pending is None:\n        pending = Pending(action.attempt_id, "closed", action.time_ms)', 1),
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args, cwd, destination):
    # Caller constructs argv from fixed modules/flags and owned artifact paths.
    child = subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True,  # nosec B603
                           text=True, encoding="utf-8", errors="replace", timeout=40, check=False)
    text = child.stdout + child.stderr
    normalized = text.replace(str(ROOT), "<workspace>")
    destination.write_text(normalized, encoding="utf-8", newline="\n")
    return child.returncode, text


def check_mutations(evidence):
    source = ROOT / "breaker_lab" / "core.py"
    original = source.read_bytes()
    text = original.decode("utf-8")
    results = []
    base = ROOT / ".test-tmp"
    base.mkdir(exist_ok=True)
    for name, (old, new, count) in MUTATIONS.items():
        if text.count(old) != count:
            raise ValueError("mutation target mismatch")
        with tempfile.TemporaryDirectory(dir=base) as folder:
            copy = Path(folder)
            for directory in ("breaker_lab", "tests"):
                (copy / directory).mkdir()
                for file in (ROOT / directory).glob("*.py"):
                    shutil.copyfile(file, copy / directory / file.name)
            (copy / "fixtures").mkdir()
            shutil.copyfile(ROOT / "fixtures" / "cases.json", copy / "fixtures" / "cases.json")
            mutated = copy / "breaker_lab" / "core.py"
            mutated.write_text(text.replace(old, new), encoding="utf-8", newline="\n")
            try:
                code, output = run(["-B", "-m", "unittest", "tests.test_model.ModelTests.test_full_frozen_hand_reports", "-v"],
                                   copy, evidence / (name + ".log"))
                detected = code == 1 and "FAIL:" in output and "AssertionError" in output
            finally:
                mutated.write_bytes(original)
            restored = mutated.read_bytes() == original and source.read_bytes() == original
            results.append({"mutation": name, "exit": code, "assertion_detected": detected,
                            "copy_restored_original_unchanged": restored})
    return results


def check_demos(evidence):
    base = ROOT / ".test-tmp"
    base.mkdir(exist_ok=True)
    results = []
    with tempfile.TemporaryDirectory(dir=base) as folder:
        target = Path(folder) / "demos"
        code, _ = run(["scripts/make_demo.py", str(target)], ROOT, evidence / "demo-create.log")
        if code != 0:
            raise ValueError("demo creation failed")
        before = {path.name: digest(path) for path in target.glob("*.json")}
        for case in cases():
            name = case["name"]
            code, output = run(["-m", "breaker_lab", str(target / (name + ".json"))], ROOT,
                               evidence / ("demo-" + name + ".json"))
            report = json.loads(output) if code in (0, 2) else {}
            expected_exit = 2 if case["expected"]["status"] == "error" else 0
            passed = code == expected_exit and report == case["expected"]
            results.append({"name": name, "exit": code, "full_expected_report_match": passed})
        code, _ = run(["scripts/make_demo.py", str(target)], ROOT, evidence / "demo-existing-refused.log")
        after = {path.name: digest(path) for path in target.glob("*.json")}
        results.append({"name": "refuse-existing-directory", "exit": code,
                        "full_expected_report_match": code == 2 and before == after})
    return results


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        return 2
    evidence = Path(args[0])
    evidence.mkdir(parents=False, exist_ok=False)
    records = {"python": sys.version.split()[0], "platform": sys.platform, "fixture_sha256": FIXTURE_SHA}
    files = sorted(path for folder in ("breaker_lab", "tests", "scripts")
                   for path in (ROOT / folder).glob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path.relative_to(ROOT)))
    records["syntax_files"] = len(files)
    for name, flags in (("normal", []), ("optimized", ["-O"])):
        code, _ = run([*flags, "-m", "unittest", "discover", "-s", "tests", "-v"], ROOT,
                      evidence / (name + ".log"))
        records[name + "_exit"] = code
    code, _ = run(["-m", "bandit", "-r", "breaker_lab", "tests", "scripts", "-f", "json",
                   "-o", str(evidence / "bandit.json")], ROOT, evidence / "bandit-command.log")
    records["bandit_exit"] = code
    scanner = json.loads((evidence / "bandit.json").read_text(encoding="utf-8"))
    records["bandit_findings"] = len(scanner["results"])
    records["bandit_analysis_errors"] = len(scanner["errors"])
    records["bandit_narrow_skips"] = scanner["metrics"]["_totals"]["skipped_tests"]
    records["mutations"] = check_mutations(evidence)
    records["demos"] = check_demos(evidence)
    max_doc = document([(kind,index,3600000,outcome) for index in range(64)
                        for kind,outcome in (("attempt",None),("complete","ignored"))], (5,60000,3))
    records["max_trace"] = {"input_bytes": len(encode(max_doc)),
                            "report_bytes": len(render(model(encode(max_doc))).encode())}
    records["source_sha256"] = {str(path.relative_to(ROOT)).replace("\\", "/"): digest(path) for path in files}
    passed = (records["normal_exit"] == records["optimized_exit"] == records["bandit_exit"] == 0
              and records["bandit_findings"] == records["bandit_analysis_errors"] == 0
              and all(item["assertion_detected"] and item["copy_restored_original_unchanged"]
                      for item in records["mutations"])
              and all(item["full_expected_report_match"] for item in records["demos"]))
    records["status"] = "pass" if passed else "fail"
    (evidence / "results.json").write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": records["status"], "normal_exit": records["normal_exit"],
                      "optimized_exit": records["optimized_exit"], "bandit_exit": records["bandit_exit"]}))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
