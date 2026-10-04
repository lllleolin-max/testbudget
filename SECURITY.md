# Security and reporting

The package runs no supplied commands, accesses no network and creates no credentials. JSON is untrusted evidence; identities, strict types, finite durations, duplicate keys and size/state limits are checked. Do not place secrets, raw customer payloads or private source paths in IDs or history. Reports include IDs, histories and outcomes; store them with runner-log access controls.

Digests detect accidental plan changes and are not signatures or provenance authentication. A malicious producer can invent history/outcomes; this tool cannot attest execution. CLI accepts operator-chosen paths and is not an OS sandbox. Single-writer atomic snapshots protect file replacement, not concurrent lost updates. Search is exponential; set max_states conservatively and isolate externally for strict resource/time guarantees.

Version 0.2 uses bounded unit/requirement preparation rather than caching all
subsets. Every history row is still validated, including rows excluded from
prior-only training. The 100,000-attempt, 20-unit exact-search and max_states
limits remain in force. A large retained Pareto frontier and exact integer bit
length can still require substantial work and memory. Faster subset evaluation
does not authenticate evidence or guarantee complete search under a state limit.

Report correctness/security defects in a private channel to the repository maintainer when available; otherwise open a minimal non-sensitive issue without private traces or secrets. Include version/commit, supported environment, minimized request and observed behavior. This project has no established security response SLA.
