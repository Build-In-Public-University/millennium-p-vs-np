# Secret-scanner bypass audit

- Audited at: `2026-07-30T01:30:18Z`
- Scope: staged revision-3 exact-seed implementation, active corpus, and revision-2 archive
- Scanner findings: 29 high-entropy strings
- Finding class: public PDF and institutional-repository URLs
- Staged files independently audited: 21
- Public URLs inspected for embedded credentials or credential-shaped query parameters: 413
- Credential-shaped findings: 0
- JSON/JSONL parse failures: 0
- Approval: explicit one-time user approval in the current session
- Bypass: `GIT_ALLOW_SECRETS=1` for this commit only

The scanner was not disabled globally. The bypass is limited to the commit containing these provenance records.
