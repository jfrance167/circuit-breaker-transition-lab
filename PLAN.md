# Circuit-breaker transition lab — proposed plan

Tier 3, October 5, 2026. Research assigned03:19; stages1–4 approved03:42 under Jake's verified direct successor mandate. Approval/addendum recorded before application code. Sole writer: existing chat; separate directory, **no new repository**. Preserve completed labs, parent Git/shared tooling and original evidence. Scope cutoff October 6, 08:00 Eastern.

## Approved freeze addendum

Source: ../.private/coordination/2026-10-05/SUCCESSORS.md,03:42. Retain opened_at and derived eligible time throughout half_open until close clears both or probe failure replaces them; deny/ignored/success below K do not rebase them. Before snapshot last_action_time_ms is the prior supplied action time (null initially); after snapshot is current action time, including denials. Empty final state retains null last-action time. Derived eligible time may exceed admitted timestamp bounds.

Public APIs: model(raw exact bytes), model_document(exact native JSON tree) and render(internally produced report). Native/decoded tree admission accepts exact dict/list/str/int/bool/None only; dict keys exact str. Reject subclasses/custom objects without calling their conversion/iteration hooks, floats, cycles and lone surrogates. Depth8, keys1024, arrays128, visits4096 including keys/repeated aliases; count repeated acyclic aliases against budgets, reject active-path cycles. Integers have at most16 canonical characters (bit-length guard before spelling). Strings canonical UTF-8 JSON body<=128 bytes; raw additionally bounds original encoded spelling. Native input is canonically serialized only after bounded tree admission, then raw65536-byte gates apply; native caller allocation is not contained. Caller must not concurrently mutate the tree. Admitted actions/policies/pending roles are frozen records, no caller mutation.

Complete schema/status/reason/error precedence and full independent fixture reports freeze before application code. Structural validation of every action precedes fresh semantic replay; replay/render finishes before output. Closed overlap or a denied/unknown/duplicate completion yields trace.invalid for the whole trace. First failing admission gate determines closed error code; no unsupported-success category. Approved local code/tests/docs/vault only, no repository/CI/installs/external actions; retain all live/concurrency/effects limits.

## Problem, success and recommendation

Teach how declared failure observations, cooldown and recovery probes change a breaker policy. Recommend an original standard-library, bounded, scripted **single-breaker serial/probe model**, not a deployable library wrapper. Each attempt/completion action gets an auditable state transition; hand oracles and an independent transition table must agree. Reject malformed or impossible late actions before any report is emitted.

Observed outcomes here are invented declarations, not evidence of real service health, actual requests, response delivery or effects. `admit` means only model policy permits a scripted attempt. Explicitly distinguish attempt counts, admitted/denied attempts, supplied completed observations and unfinished pending attempts. Application effects remain `unmodeled`; actual availability/recovery remains `unverified`.

Compare with a queue-admission alternative: a bounded queue would model pending-work capacity/dequeue order and possibly waiting, without learning the same failure/recovery transitions. It would require its own ordering/cancellation assumptions. Choose the breaker as the distinct useful lesson. Existing rate-limit lab models cost budgets; retry-idempotency lab models scoped deduplication/effects. Do not import their budgets, work effects, retries or persistence into this lab.

Adopt/fork alternatives: inspected pybreaker and circuitbreaker execute guarded callables with live time and their own exception/concurrency/storage contracts. No package or borrowed implementation needed for this offline subset. Build original pure transitions and reuse reviewed owned parser/file/sink patterns only after approval, retaining attribution. See RESEARCH.md for actual candidate source/tests/license/dependencies/CI/maintenance.

## Scope and profile

Proposed profile `breaker-serial-probe/1`: one breaker, one pending admitted attempt at most. Closed calls must not overlap; an attempt while a closed attempt is pending invalidates the trace as out-of-profile (`trace.invalid`). This is not a breaker-based capacity denial. Half-open intentionally models one pending probe slot: a second attempt while that probe is pending is denied with `probe_in_flight`. This scripted interleaving is not real concurrency/locking/thread safety. Restriction avoids overlapping closed completions, old generations and late outcome ambiguity; those require a new plan.

No requests, callable execution, retries, queues, fallback functions, sleeps/live clocks, services, traffic, providers/quotas, real traces, timeout inference, failure percentages/rolling windows, manual resets, multi-breaker routing, threaded/distributed storage, persistence/durability, security authorization or deployment. Ordinary documentation/test files remain owned artifacts. No new repository or external action is currently authorized.

## Exact proposed input/status contract

One strict UTF-8 JSON document, root exactly `schema_version` (actual integer1), `source_kind` (literal `synthetic`), `profile` (literal above), `breaker_id` (ASCII `lab-breaker-NNNN`), `policy`, `actions`. Source-kind/label are declarations, not proof of provenance or authenticated identity. Policy fields exactly `failure_threshold` F actual integer1–5, `cooldown_ms` C integer1–60,000, `success_threshold` K integer1–3. All fields required; extras rejected. One policy/breaker per document; no defaults.

Each action requires unique ASCII `action_id:lab-action-NNNN`, `time_ms` actual integer0–3,600,000, and `kind`:

- `attempt`: additionally requires `attempt_id:lab-attempt-NNNN`, unique across all attempts including denied ones. No outcome field. Admission assigns immutable role `closed` or `probe` in pending state.
- `complete`: additionally requires `attempt_id` and `outcome:success|failure|ignored`. It must refer to the unique admitted, still-pending attempt, completing exactly once. Unknown, denied or already completed references invalidate the whole trace; no completion creates implicit work.

Action times globally nondecreasing; equal times use array order. No sorting, clamping or host time. A completion at the same time as a later attempt applies first if ordered first. Empty actions valid: closed initial state, no pending/observations. Unknown versions/profiles/kinds and malformed required values produce `schema.invalid`, not optimistic unsupported success. Booleans, floats/nonfinite values, duplicate decoded object keys/IDs, invalid Unicode and late malformed fields are rejected.

Proposed CLI `python -m breaker_lab FILE`: exit0/status `modeled` for a complete valid trace, even with denied attempts or an unfinished pending attempt; exit2/error JSON with closed code on stderr for any error, no successful report prefix. Help exit0 checked usage. Argument checks before file I/O; lexical byte/depth/string/numeric gates before strict JSON/tree admission; complete structural/schema/time/cardinality validation before replay. State-dependent reference/concurrency legality is checked throughout fresh in-memory replay; finish the entire replay and bounded render before any emission. A late semantic error discards all provisional output. First failing gate determines code, not an exhaustive defect classification.

Codes: arguments.invalid, input.io/encoding/invalid_json/number/duplicate/limit, schema.invalid, trace.invalid, output.error, internal.error. Native parser/path/argv/exception strings never appear in diagnostics. Full error/field precedence and source fixture bytes must be frozen in stage1 before application code.

## Transition rules to freeze

Initial: `closed`, `closed_failure_streak=0`, `recovery_success_streak=0`, `opened_at_ms=null`, pending=null. Closed failure streak counts only `failure` observations completed in closed role. It is retained at F during open/half-open for historical context and resets to0 on closing; probe failures do not increment this closed-only field. Recovery success streak counts only successful probes in the current half-open episode; ignored probes leave it unchanged. These are consecutive **counted** observations; ignored is neutral, not success and not evidence of health. No time-based aging/reset of counts.

1. **Closed attempt:** if pending is null, admit with role closed and record ID/time. No failure count changes yet. If a closed attempt is already pending, reject the entire trace as unsupported overlap.
2. **Closed completion:** release pending. Success resets closed failure streak to0. Ignored leaves it unchanged. Failure increments it; at `>=F`, open at the **completion** timestamp, set recovery streak0, leave pending null. Cooldown starts at observed failure/open time, not request time.
3. **Open attempt:** when `t < opened_at+C`, deny `cooldown_active`, create no pending work, and do not change opened_at/streaks. At `t >= opened_at+C`, lazily enter half_open with recovery streak0, then admit this attempt as its probe. Equality permits the probe. No automatic timer/transition occurs without an attempt. Derived eligible time may exceed the maximum admitted timestamp; do not clip it or fabricate eligibility.
4. **Half-open attempt:** pending probe absent => admit role probe; pending probe present => deny `probe_in_flight` and preserve it. A denied attempt cannot subsequently complete.
5. **Probe completion:** release pending. Failure immediately reopens at completion time, resets recovery streak0 and begins a new full cooldown. Success increments recovery streak; if `>=K`, close and reset both streaks0/opened_at null; otherwise remain half_open ready for another serial probe. Ignored neither closes nor reopens nor resets successes; remain half_open with slot released. It is a named policy choice that differs from candidate exception-as-success behavior.

Only completed admitted observations change counters/health policy. In-flight attempts at end remain pending/unobserved, never implicitly timed out, failed or successful. State snapshots include mode, both streaks, opened_at/derived eligible time, pending ID/role/admitted timestamp and last action timestamp. Final state is at the last supplied action; no silent advancement. `closed` does not mean actual service healthy; `open` does not prove unavailable. A supplied outcome is trusted only as invented model input.

## Report and resource bounds

One row for every action, including denied attempts, with validated invented IDs/time/kind, admission/observation reason, applied outcome if a legal completion, before/after snapshots and ordered transition labels. No outcome for denied attempts; no evaluated future result. Summary: attempts/admitted/denied, closed/probe admissions, completed success/failure/ignored observations, opens/closes/half-open entries and pending0/1. Reconcile attempts=admitted+denied; admitted=completed+pending; completed=sum outcome observations; admitted=closed+probe admissions. Include effects unmodeled/actual health unverified.

Proposed raw cap65,536 bytes; nesting8 containers, encoded string-body128 bytes, numeric spelling16 characters before conversion; strict UTF-8/Unicode and duplicate/float/nonfinite rejection. Postdecode arrays<=128 items and total object keys<=1,024; these cardinality gates are not preallocation guarantees. At most128 actions,64 attempts,64 completions; one breaker, one pending record, no retention/eviction. Seen IDs and report grow only within those caps. Largest derived eligibility<=3,660,000ms; counters<=64 and streaks bounded by policy. No loop over elapsed time or cooldown windows. Model immutable admitted data and fresh state, preserve caller input.

Checked stable regular input file; read at most cap+1. Complete compact JSON UTF-8 report cap262,144 bytes, fail before output instead of truncating. Stdout checked for short/failed/flush writes and error sink delivery may itself fail; preserve exit2 even with both dirty failed buffers. Output is nontransactional and can be partial. Test maximum permitted trace/report fit and label injected unreachable render guards honestly. Limits bound workload, not hard CPU/RSS/I/O deadlines or filesystem-race/same-user isolation. Use only invented fixtures.

## Independent oracle cases

Notation A(id,t)=attempt, C(id,t,outcome)=completion; action IDs distinct and implicit here only. Default F2,C10ms,K2. Stage1 must freeze full exact input fields, expected per-action states/counts/reasons and hashes before implementation; these hand expectations are design evidence, not executed results.

| Case | Script | Expected key result |
| --- | --- | --- |
| Counted failure threshold | A1@0,C1 failure@0,A2@1,C2 failure@1 | open at1, closed streak2, two observed failures; no pending |
| Closed success reset | failure pair@0, success pair@1, failure pair@2 | closed streak1, no open; admitted/completed3 |
| Ignored neutral | failure pair@0, ignored pair@1, failure pair@2 | open at2; ignored did not reset streak; observations1 ignored/2 failures |
| Cooldown below/equal | trip at1, A3@10,A4@11 | deny A3, admit probe A4, half_open/pending4; opened1, eligible11 |
| Pending probe bound | trip at1,A3@11,A4@11,C3 success@11 | A4 denied probe_in_flight; half_open/recovery streak1/pending null; denied A4 has no result |
| Recovery threshold | trip at1, success probe pairs@11 twice | close after second probe completion only; streaks0/opened null |
| Probe failure restarts cooldown | trip at1,A3@11,C3 failure@12,A4@21,A5@22 | reopen at12; A4 deny, A5 admit probe, not eligible from old opening1 |
| Ignored probe preserves progress | trip at1, success probe@11, ignored probe@11, success probe@11 | close only after last counted success; ignored releases slot and preserves recovery streak1 |
| No outcome/pending | A1@0 only | closed, admitted1/completed0/pending1, no success/failure/timeout inference |
| Invalid ownership | open-denied A3 followed by C3 success; unknown or duplicate completion | whole trace error, no report/counters emitted |
| Unsupported closed overlap | A1@0,A2@0 without completion | trace.invalid, no capacity-based policy denial invented |
| Completion/attempt tie | F1,C10,K1: A1@0,C1 failure@0,A2@0 | A2 denied; swapped C1 after A2 produces out-of-profile closed overlap, not the same valid trace |

Also empty trace; cooldown completion-time versus attempt-time; same-time probe completion/next attempt ordering; backwards/late invalid schema even behind denied actions; every bound at/over; missing/extra/null/bool/float/version fields; duplicate IDs/keys; Unicode; unfinished half-open probe; many denied attempts not extending cooldown. Independent second oracle should use an explicit transition table and action-role ownership, not production transition functions. Detect at least four targeted semantic mutations: cooldown `<` versus `<=`, admission-time rather than completion-time opening, closing before K successes, applying a denied completion. Restore changes or mutate isolated copies and verify original hashes. Finite tests, not formal proof.

## Threat model and stages

Trust reviewed owned interpreter/code and invented fixtures. Treat bytes as hostile for parsing/resource/report integrity. Risks: bool/int confusion, late-invalid partial reports, outcome laundering onto rejected IDs, stale cooldown/role misuse, accidental health/effects claims, probe-slot/resource exhaustion and reflected diagnostics. Mitigate fixed schema/limits, explicit ownership/roles, exact integer time, whole structural admission and semantic replay-before-output, independent oracles, closed errors and truthful labels. Authentic outcomes/identities, concurrency, external services/durability and real health monitoring are outside scope.

1. After approval, record addendum, freeze schema/status/trace legality and full independent fixtures/hashes. No code before this gate. Maintain STATE/DECISIONS/LEARNING.
2. Implement standard-library bounded admission and pure single-breaker transitions; prove ownership, threshold, ties, ignored outcomes and final pending semantics against hand/table oracles. Explain admission versus observation before this stage.
3. Implement small CLI, invented demos and fresh reusable verifier. Run normal/optimized, late-invalid/no-prefix, actual/simulated short/flush/closed sinks, max trace/report-fit and four assertion-detected restored mutations. Existing Windows CPython3.13.7/Bandit available; no runtime dependencies needed.
4. Actual ECC self-review/SAST, fix/rerun affected checks, final hashes/hygiene and README/license/attribution/AI disclosure/learning/vault evidence. Linux/other-runtime/hosted and formal proof remain unverified unless executed. No repository/remote/CI publication/deployment authority arises from research; any repository setup requires approval as part of reviewed implementation scope.

Worker: approved local Ollama tried once for bounded supplied-facts comparison, raw preserved/reviewed; no state rules/oracles/security judgments delegated. Removed awkward assurance language. Reviewed routing guide remains applicable; considered free OpenRouter public drafting but no necessary suitable remaining remote task/current price refresh. No remote calls/spending/fallback. Laya's tested advisory categorization/triage schemas do not fit state-machine research.
