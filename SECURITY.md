# Security and reporting

The package runs no supplied commands, accesses no network and creates no credentials. JSON is untrusted evidence; identities, strict types, finite durations, duplicate keys and size/state limits are checked. Do not place secrets, raw customer payloads or private source paths in IDs or history. Reports include IDs, histories and outcomes; store them with runner-log access controls.

Digests detect accidental plan changes and are not signatures or provenance authentication. A malicious producer can invent history/outcomes; this tool cannot attest execution. CLI accepts operator-chosen paths and is not an OS sandbox. Single-writer atomic snapshots protect file replacement, not concurrent lost updates. Search is exponential; set max_states conservatively and isolate externally for strict resource/time guarantees.

Report correctness/security defects in a private channel to the repository maintainer when available; otherwise open a minimal non-sensitive issue without private traces or secrets. Include version/commit, supported environment, minimized request and observed behavior. This project has no established security response SLA.
