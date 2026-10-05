# Learning

- Breaker admission depends on declared failure/recovery history; queues depend on waiting capacity and rate limits on budgets.
- Completion owns an outcome. An admitted but unfinished attempt is not a failure, and a rejected attempt has no completed observation.
- Cooldown origin and equality, counted versus ignored outcomes, recovery threshold and probe ownership are contract choices rather than consequences of the algorithm's name.
- Scripted pending probes can teach slot behavior without proving concurrency, real service recovery or effects.

Optional future exercise: why does a probe failure at12ms postpone the next allowed probe until22ms under the proposed10ms cooldown, even though the original breaker opened at1ms?

Verified implementation lessons:

- An attempt's admission time and its observation time differ. The delayed-completion frozen case and opening-origin mutant detect a cooldown wrongly started at admission.
- Validation order matters: the whole structure is admitted before any semantic replay; a late extra field beats an earlier ownership error. Late semantic errors return no provisional report.
- Native APIs need their own admission boundary. A bounded byte parser alone does not reject caller cycles, aliases, custom subclasses or huge integers before serialization. Exact-type checks and bounded visits cover those tested cases without executing custom hooks.
- Independent hand expectations and a table oracle check different representations. Four intentional mutations must produce assertion failures, with original source preserved; passing finite tests is still not a proof of all traces.
- Scanner findings require interpretation. Bandit treated a variable named token containing the invented action symbol A as a possible credential; clearer symbol naming resolves that false positive without hiding a rule.
- Output success includes flush. Actual broken-pipe tests check that failed stdout/stderr buffers do not convert the intended error exit2 into CPython's shutdown exit120.

Answer to the exercise: failed probe completion opens a new episode at12ms; eligibility is12+10=22ms. The original1ms opening no longer controls the cooldown. No real request or health observation was performed.
