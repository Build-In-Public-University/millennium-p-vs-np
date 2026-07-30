# Discovery revision 1 — rejected seed set

- Decision: reject before reference expansion
- Records: 124 unique normalized works
- Reference edges: 9,643
- Broad keyword matches: 41 (including false positives)
- Broad keyword unmatched: 83
- Query provenance: unavailable in v0.1 records
- Expansion performed: no
- PDF retrieval performed: no
- Records SHA-256: `291ff83187af7fd40a1623a937ae5761a9048f620413255aebf5389582b1d2f9`
- Receipt SHA-256: `b12c583d264d5cfedd1de7f156692631e21aae03773228a7ae66dfc4f8f7f31e`

The search formulations admitted unrelated molecular simulation, high-energy
physics, algebraic geometry, medicine, and psychology. This snapshot is retained
as a published miss rather than silently replaced.

## Publication-safety receipt

The global pre-commit scanner flagged public OpenAlex `pdf_url` and
`landing_url` values as high-entropy base64-like strings. Before commit
`41dfa3f`, an independent structured-field audit found 65 high-entropy tokens:
all 65 occurred in those two public URL fields and zero occurred elsewhere.
A separate credential-pattern scan returned zero matches. The scanner's
documented `GIT_ALLOW_SECRETS=1` path was used for that metadata commit; no
credential or private artifact was knowingly bypassed.
