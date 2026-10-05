# Source research — October 5, 2026

Research-only recommendation: **build original bounded serial/probe transitions**, not adopt/fork a production decorator library. No application/upstream/test execution, installation or repository initialization. PLAN.md contains the selected contract, alternatives, threat model, hand expectations and approval gates. No safety certification/exhaustive ecosystem claim.

## Reuse/access

Read coordinator 03:19 selection, current instructions/shared STARTUP, rate-limit plan/state and retry-idempotency plan's attempt/completion/side-effect boundaries. Read relevant vault Rate-limit Admission Lab and Exact Admission Budgets milestone; Home/Integration and Python Input and Serialization Boundaries already consulted in this workstream. Targeted local circuit.breaker source/Markdown search excluding private/Git/vendor/environments/GLPI found no dedicated model. Broader half.open matches were interval terminology in framing/rate-limit docs, not breaker reuse. Reuse only reviewed bounded parser/file/sink concepts after approval; preserve adjacent labs and blocked retry verification.

**Connected GitHub repository search succeeded** for this task: found fabfuel/circuitbreaker, danielfm/pybreaker and others. Strongest two inspected through public pinned REST snapshots. Prior transport failures do not describe this successful search. Web search transport failed; official Microsoft page opened successfully afterward. One source inventory approval timed out; one permitted retry succeeded. Initial bulk source URL interpolation returned404; corrected the diagnosed path construction and then retrieved all13 nonempty snapshots. No access bypass, source execution or fallback install. Ignored inert `.b64`/`.txt` snapshots and SHA256 manifest retained. Firecrawl was not called (current free eligibility unverified); no Scorecard retrieved, neither absence is a safety verdict.

## Actual candidates

| Candidate | Identity/license/maintenance | Fit decision |
| --- | --- | --- |
| [danielfm/pybreaker](https://github.com/danielfm/pybreaker) | Nonarchived main; push/inspected head Sept25,2026, [2b0b965f](https://github.com/danielfm/pybreaker/tree/2b0b965fcfc7705ca9a776c614ea6cb3ec3fe783). LICENSE actual BSD-3-Clause. | Maintained relevant reference for thresholds/reset/success progress; wrapper/time/storage contract differs. |
| [fabfuel/circuitbreaker](https://github.com/fabfuel/circuitbreaker) | Nonarchived develop; pushed March31,2025, inspected [f7f216c0](https://github.com/fabfuel/circuitbreaker/tree/f7f216c05abf8eac3e024b859bf0e7fb0245b835). API NOASSERTION resolved from actual LICENSE.rst/setup.py: BSD-3-Clause. | Compact live-clock decorator reference; not this declared serial pending-probe profile. |

Repository push/commit metadata, source/package manifest versions and open PRs are maintenance evidence, not released-artifact verification or safety proof. No release/wheel/advisory/hosted-results audit performed.

### pybreaker inspected evidence

[Source](https://github.com/danielfm/pybreaker/blob/2b0b965fcfc7705ca9a776c614ea6cb3ec3fe783/src/pybreaker/__init__.py): counted failures open at threshold; open call checks datetime versus opened_at+reset_timeout, allowing equality; half-open success counter closes at configured threshold. Excluded exceptions use the success handler, which resets failures. This differs from our explicit neutral ignored outcome. Optional Redis/Tornado imports/storage, real callable execution and locks make it unsuitable as an inert model dependency.

[Actual tests](https://github.com/danielfm/pybreaker/blob/2b0b965fcfc7705ca9a776c614ea6cb3ec3fe783/tests/pybreaker_test.py) include half-open threaded trial test and threshold/shared-storage concerns; read the test bodies, not run them. [README](https://github.com/danielfm/pybreaker/blob/2b0b965fcfc7705ca9a776c614ea6cb3ec3fe783/README.rst) documents failure/reset configuration and success_threshold. [pyproject](https://github.com/danielfm/pybreaker/blob/2b0b965fcfc7705ca9a776c614ea6cb3ec3fe783/pyproject.toml) declares no mandatory runtime dependency list, optional test packages, Flit build and pytest/type/lint tooling. Tool setup includes a pre-commit-install hook; never execute it blindly.

[CodeQL workflow](https://github.com/danielfm/pybreaker/blob/2b0b965fcfc7705ca9a776c614ea6cb3ec3fe783/.github/workflows/codeql-analysis.yml) inspected: mutable checkoutv2/CodeQLv1 references. Do not copy that pinning. Bounded current PR sample: [108](https://github.com/danielfm/pybreaker/pull/108),105,104. Read PR108 body reporting shared recovery counter resets; claimed tests are author's reports, not our verification. This model has one breaker/no shared Redis instance and does not reproduce that issue. No vulnerability conclusion from a title/report.

### circuitbreaker inspected evidence

[Source](https://github.com/fabfuel/circuitbreaker/blob/f7f216c05abf8eac3e024b859bf0e7fb0245b835/circuitbreaker.py): expected-exception predicate, failure count/reset, live monotonic opening/recovery and calculated half-open state; decorators call actual sync/async/generator functions or fallback. Noncounted exceptions take reset behavior rather than our neutral ignored policy. Avoid adopting callable/fallback machinery for an offline teaching trace.

[Functional tests](https://github.com/fabfuel/circuitbreaker/blob/f7f216c05abf8eac3e024b859bf0e7fb0245b835/tests/test_functional.py) inspect threshold opening, blocked calls, timed half-open retry/failure and successful reset; [unit tests](https://github.com/fabfuel/circuitbreaker/blob/f7f216c05abf8eac3e024b859bf0e7fb0245b835/tests/test_unit.py) inspect predicates/types/config. Read, not executed. [setup.py](https://github.com/fabfuel/circuitbreaker/blob/f7f216c05abf8eac3e024b859bf0e7fb0245b835/setup.py) version2.1.3 declares no install_requires; source imports inspected are standard library. Build uses setuptools; no wheel/supply-chain installation verified.

[Build workflow](https://github.com/fabfuel/circuitbreaker/blob/f7f216c05abf8eac3e024b859bf0e7fb0245b835/.github/workflows/build.yml) has Python3.8–3.13 Ubuntu pytest/lint, mutable checkout/setup-pythonv2 and a lint step allowing warning exits. Hosted results not inspected/run. Open PR71 requests consecutive half-open successes; issue70 requests time-based failure resets; PR68 naming. Read [issue70](https://github.com/fabfuel/circuitbreaker/issues/70) body as a feature request, not a confirmed vulnerability. Our rule deliberately has no failure aging and labels that assumption.

## Primary context, licenses and limitations

[Microsoft circuit-breaker pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) explains closed/open/half-open failure/recovery gating and the distinction from retry. Its illustrated closed counter periodically resets over time; our chosen counted-failure streak has no aging. Our profile supplies scripted observations, not real faults or availability evidence; its one pending closed call and explicit neutral ignored policy are choices, not claimed universal behavior. Queue capacity and rate budgets teach separate mechanisms.

Both inspected BSD-3-Clause licenses require retaining copyright/conditions/disclaimer in source or appropriate binary materials and disallow using contributor names for endorsement without permission. No upstream implementation copy proposed; preserve source links/AI disclosure and choose own appropriate license after code approval. Do not infer security from dependency count or tests/CI presence.

Local Ollama qwen3.5:2b supplied one comparison draft in6046ms with45-second deadline, stop completion/no helper warning. Raw brief/output under ignored .drafts; reviewed scope statements, removed its awkward assurance about not simulating real requests. No rule/math/oracle delegated, no remote inference, price/routing changes or paid fallback. Laya schema unsuitable.

No application/tests/oracle execution exists yet. Proposed caps/report fit/semantic precedence require stage1 freeze and actual checks after approval. Linux/other interpreters/hosted/real probes/concurrency/durable outcome truth/service recovery remain unverified and outside the research authorization.
