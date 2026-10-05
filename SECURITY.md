# Security model

This is an offline synthetic teaching model, not a service protection or monitoring component. Trust the reviewed interpreter/application and treat input bytes as untrusted for parsing and report integrity. Invented labels and supplied outcomes do not authenticate provenance, identity, health or effects.

Admission applies fixed byte, depth, string, number, key, array and node-visit limits; duplicate decoded keys, floats, nonfinite numbers, surrogates and custom native objects are rejected. Structure is validated before replay. Completions require an owned pending admitted attempt; denied/unknown/duplicate completions invalidate the whole trace. Immutable admitted roles and fresh snapshots prevent caller mutation from silently rewriting outcome ownership. Report limits apply before return/emission. CLI diagnostics use a closed set of content-free codes.

Postdecode cardinality gates are not decoder preallocation isolation. Native caller allocations/concurrent mutation are not contained; the renderer expects internal reports. File checks do not eliminate path/descriptor races or blocking I/O. Successful bytes cannot be withdrawn after a later sink failure, and the diagnostic sink can itself fail. There are no hard CPU/RSS/I/O deadlines, VM boundaries, authenticated observations, concurrency guarantees or durable state.

Use only invented fixtures for this lab. Review changes to admission, ownership, error handling and time semantics manually before any adaptation to real untrusted evidence. Local tests/SAST/self-review do not establish production safety. Do not submit secrets, client/employer material or real incident payloads as fixtures. No hosted repository or disclosure endpoint is configured; do not publish sensitive reports.
