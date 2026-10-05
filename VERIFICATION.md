# Local verification — October 5, 2026

Environment: Windows CPython 3.13.7, installed Bandit 1.9.4. No package installation or upstream execution. Final command `python scripts/verify.py docs/verification/final` exited 0. Complete logs and 11 source-file SHA256 receipts are in that directory; `results.json` is the machine-readable authoritative record.

| Check | Result | Evidence |
| --- | --- | --- |
| AST syntax | PASS, 11 Python files | final/results.json |
| Normal unittest | PASS, 31 tests, exit 0 | final/normal.log |
| Optimized unittest | PASS, 31 tests, exit 0 | final/optimized.log |
| Bandit application/tests/scripts | PASS, exit 0, zero findings/errors, six narrow skips | final/bandit.json |
| Frozen full hand reports | PASS, 13 cases, byte hash checked | tests/support.py, fixtures/SHA256.txt |
| Independent transition table | PASS, 1,024 four-symbol tails across four threshold sets | tests/test_model.py |
| Isolated mutation checks | PASS, four assertion failures detected; copies restored/original unchanged | final/results.json and mutation logs |
| Demo CLI | PASS, 13 exact full reports/errors; overwrite refusal preserves hashes | final/demo-* and results.json |
| Maximum-cardinality sample | PASS, 128 actions/64 completions; 14,216 input and 77,053 output bytes | final/results.json |
| ECC self-review | PASS, no unresolved actionable defect | REVIEW.md |
| Types/dedicated lint | NOT RUN; no configured checker executed | AST/Bandit are separate checks |
| Linux/other Python versions/hosted CI/CodeQL | NOT RUN | Only actual Windows runtime verified |
| Git history/staged diff/remote protections | NOT APPLICABLE | No repository authorized/initialized |
| Real calls, clocks, services, concurrency/durability | NOT APPLICABLE | Outside approved synthetic profile |

The hand fixtures were fully expanded and sealed before application code, with SHA256 `95f24e80b3c2198904ba03dd32f4d8696122f1a9d4ed66920f19294d25529e64`. The table oracle imports no production transitions and uses declared observation rules, numeric modes and time subtraction. Tests include invalid ownership/overlap, timestamp ties/late structure, cycles/aliases/custom hooks, native huge integers, Unicode/duplicate/float gates, exact resource bounds, frozen records, unchanged caller input and independent snapshots.

Mutation targets change cooldown equality, opening origin from completion to admission, recovery closing before the configured threshold, and acceptance of unowned completions. Each must fail via an assertion against frozen hand reports, not merely crash. They run in isolated copies and do not weaken the working application. Matching source text assumes LF line endings.

Coordinator receipt review clarified the raw mutant logs: assertion failures are2/2/3/1 respectively; the cooldown-equality mutant additionally produces4 errors. Every mutant has meaningful detecting assertions, but the mutated suites are not error-free. Final unmutated normal/optimized suites pass without errors. No independent audit or coordinator full-suite rerun was performed.

CLI checks include late-error/no-success-prefix, fixed diagnostics without argument/input/exception reflection, valid denied exit 0, help flush errors, regular-file byte caps, simulated short/boolean/closed/raising/flush-failing sinks and actual subprocess pipes closed for stdout, stderr and both. CPython shutdown flushing retains exit 2. Finite tests do not prove arbitrary races, memory exhaustion or transactional delivery.

The maximum-cardinality sample is not a claim of the largest possible encoded report: it uses 64 ignored attempt/completion pairs at the maximum admitted time. The oversized-render test is an injected defensive guard beyond schema-reachable fixtures; it is not a naturally admitted huge report.

## Scanner history and exceptions

The preserved first combined run `docs/verification/stage3/results.json` failed only Bandit B105 at the table generator's `token == "A"`. This is an invented action symbol, not a credential. Renamed `token` to `symbol`; no suppression was added. The subsequent full final run passed. Initial normal-test evidence is also retained.

Six narrow harness annotations remain: two B404 subprocess imports (tests/test_cli.py and scripts/verify.py), three B603 fixed owned test-child launches and one B603 fixed verifier runner. No application suppression exists. All argv are constructed for the selected local Python/module/tests/scanner, with no shell or input-selected command. The unsuppressed control `python -m bandit -r breaker_lab tests scripts --ignore-nosec -f json -o docs/verification/bandit-control.json` exited 1 with exactly those six warnings, zero analysis errors and no application findings. This explains the exceptions; it does not certify subprocess safety generally.

Local source/document credential-pattern inspection is a narrow hygiene check, not a comprehensive secret scan. Research snapshots, raw drafts and temporary runtime files stay separately ignored. Parent/shared projects are outside this change. No commit, push, repository, release, merge or deployment was performed.
