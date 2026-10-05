# Circuit-breaker Transition Lab

An offline Python teaching tool that explains circuit-breaker admission and recovery over invented attempt/completion records. Every report contains before/after snapshots, reasons, transitions and reconciled counts. Only a completed admitted attempt contributes an observation; denied and unfinished attempts cannot establish success or failure.

This implements the explicit `breaker-serial-probe/1` profile: one breaker, one pending attempt, exact integer milliseconds, counted failure/recovery thresholds and neutral ignored outcomes. It executes no requests or callbacks and uses no live clock. Reports label effects `unmodeled` and actual service health `unverified`.

## Run

Run from this directory with Python 3.11 or newer; verified here on Windows CPython 3.13.7. The application has no third-party runtime dependencies. Create a fresh demo directory, then replay a trace:

```powershell
python scripts/make_demo.py demos
python -m breaker_lab demos/cooldown-below-equal.json
```

The generator refuses an existing destination. It produces 13 invented inputs, including two deliberately invalid traces. A valid model exits 0 even when attempts are denied or remain pending. Errors exit 2 and emit a fixed JSON error code on stderr; a late invalid action produces no successful report prefix. Output delivery can fail or be partial.

In the cooldown demo, two observed failures open the breaker at 1ms. An attempt at 10ms is denied; at 11ms the 10ms cooldown has elapsed and one probe is admitted. The final state is half-open with an unfinished probe, so recovery has not been observed.

## Model

| State | Attempt | Completion of its admitted pending attempt |
| --- | --- | --- |
| Closed | Admit when no attempt is pending; overlap invalidates this profile | Success clears failures; failure counts toward opening; ignored is neutral |
| Open | Deny below `opened_at + cooldown`; equality enters half-open and admits a probe | No pending completion is legal |
| Half-open | Admit one probe; deny another while it is pending | Success counts toward closing; failure reopens at completion time; ignored preserves progress |

Times must be nondecreasing; ties follow array order. Opening and reopening start cooldown at failure **completion** time. Nothing advances without a supplied action. Opening/eligibility timestamps persist through half-open until closing or reopening. Counter rules have no time-based aging. Closed overlap is a whole-trace error, while half-open probe saturation is a valid denial.

Every completion must refer to the unique admitted, still-pending ID exactly once. Supplied outcomes and `synthetic` labels are declarations, not authenticated evidence. See [SCHEMA.md](SCHEMA.md) for exact fields, precedence, reasons, report shape and limits.

## Architecture and API

`admission.py` applies byte/lexical bounds, strict JSON decoding and a bounded exact-builtin tree walk. `core.py` validates the entire structure into frozen records, replays owned transitions in fresh state, then checks report size. `__main__.py` adds regular-file checks and checked output/error channels. No partial model is returned after a semantic error.

```python
from breaker_lab import model, model_document, render
from breaker_lab.admission import LabError

# raw is a bounded UTF-8 JSON bytes value matching SCHEMA.md.
report = model(raw)
text = render(report)
# model_document(document) admits an exact builtin JSON tree instead.
```

Native input admission rejects cycles, custom objects/subclasses, floats and oversized values before serialization. Acyclic aliases count on every visit. Caller inputs and returned snapshots are independent. Concurrent caller mutation is unsupported. `render` serializes internally produced reports; it is not an arbitrary-object input validator.

## Verify

```powershell
python -m unittest discover -s tests -v
python -O -m unittest discover -s tests -v
# Requires an already installed Bandit; choose a fresh evidence directory.
python scripts/verify.py docs/verification/my-run
```

The reusable verifier checks syntax, normal/optimized tests, Bandit, full demo reports, refusal to overwrite demos, a maximum-cardinality trace and four isolated semantic mutations. It records logs, exit codes and source hashes; mutation copies are restored and original source is checked unchanged. Keep source Python files with LF line endings: the mutation harness matches exact multiline source text.

Verified October 5, 2026: 31 tests pass in each mode, 13 frozen hand cases and 1,024 independently table-modeled traces, all four mutations detected, Bandit zero findings/errors with six narrow test-harness subprocess exceptions. [VERIFICATION.md](VERIFICATION.md) explains the exceptions, original scanner failure and remaining gaps; [REVIEW.md](REVIEW.md) records ECC self-review. These are finite checks, not formal proof.

## Security and limits

Input: 65,536 bytes, depth 8, encoded string-body 128 bytes, integer spelling 16 characters, arrays 128, object keys 1,024 and tree visits 4,096. Trace: 128 actions, 64 attempts and 64 completions. Report: 262,144 bytes, rejected rather than truncated. Cardinality checks after decoding do not prevent decoder allocation; limits do not guarantee hard CPU/RSS/I/O deadlines or isolate hostile files/native callers.

No real service calls, retries, timeouts, fallback, threads, distributed state, durable storage, authentication or deployment are modeled. A modeled closed state does not establish service health. File races and blocking I/O remain possible; output is nontransactional. See [SECURITY.md](SECURITY.md) before adapting this lab.

## Sources, license and learning

Built original transitions after comparing [pybreaker](https://github.com/danielfm/pybreaker) and [circuitbreaker](https://github.com/fabfuel/circuitbreaker). Their inspected callable/time/exception policies differ from this teaching profile; neither implementation is copied or installed. Pinned source/license/test/CI evidence and primary Microsoft context are in [RESEARCH.md](RESEARCH.md). Research describes the preimplementation stage; current results are in [STATE.md](STATE.md).

MIT licensed. Bounded parser, CLI and verification patterns are adapted from Jake's reviewed structured-log and rate-limit labs, also MIT. AI assistance: Codex researched, implemented, tested and self-reviewed; local Ollama drafted bounded comparison/usage prose that was reviewed and corrected. No remote drafting inference was used. The narrow installed ECC review skill was used; the full native ECC plugin is not installed.

Learning exercise: with a 10ms cooldown, explain why a failed probe completing at 12ms permits the next probe at 22ms even if the first opening occurred at 1ms. [LEARNING.md](LEARNING.md) records the concepts. Local implementation is complete; no repository, publication or hosted checks were created.

## Publication status

See [publication review](PUBLICATION.md) for the October 5 source snapshot, fresh local checks, evidence boundaries and current hosted-check distinction.
