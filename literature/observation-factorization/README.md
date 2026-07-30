# Review: observation factorization and succinct identifiability

- **Status:** revisions 1 and 2 rejected before expansion; revision 3 exact-seed design frozen but not executed
- **Problem contract:** `review.json`
- **Theory under review:** `../../papers/observation-factorization-v0.1.md`
- **Theorem ledger:** `../../evidence/theorem-ledger-v0.7.md`

## Purpose

Determine which parts of the observation-factorization framework are established
under quotient factorization, sufficient statistics, statistical experiment
ordering, noninterference, functional dependence, and distributed function
computation. The sharpest novelty test is T-11: whether succinct Boolean-circuit
bad-fiber detection is already a known dependency or information-flow
verification problem.

## Frozen claims

- `T-01` — exact factorization through observation fibers;
- `T-03` — communication cost can vary while the effective observation remains
  fixed;
- `T-11` — NP-complete bad-fiber detection and coNP-complete exact
  identifiability for Boolean circuits;
- `T-BAYES` — finite zero-one Bayes risk decomposes over observation fibers.

## Acquisition boundary

- Five search formulations;
- 25 results per formulation;
- backward bibliography expansion only;
- one reference-expansion level;
- 500 normalized records maximum;
- full text only from exposed open-access PDF locations or user-supplied files.

These limits may leave relevant literature outside the review. Any expansion
must version the contract rather than silently enlarging it after favorable or
unfavorable papers appear.

## Discovery revision history

- Revision 1 returned 124 unique records and 9,643 reference edges but admitted
  severe cross-domain noise. Eighty-three records lacked even broad topical
  keywords; obvious false positives included CHARMM molecular simulation and
  high-energy-physics papers containing the word “factorized.”
- Revision 1 was rejected before reference expansion or PDF retrieval. Its
  normalized records, receipt, hashes, and audit remain under
  `history/discovery-r1/`.
- Revision 2 narrows all five searches and adds record-level query provenance.
  A deterministic title/abstract screen retained 55 of 122 records (45.08%),
  below the frozen 60% gate. Query-level candidate rates were 24%, 91.67%,
  44%, 32%, and 32%, respectively. Expansion and PDF retrieval remain blocked.
- Revision 3 is specified in `revision-3-design.json`. It replaces keyword search
  with ten exact DOI seeds across noninterference, Boolean functional dependency,
  classical functional decomposition, statistical experiments, and distributed
  function computation. Crossref resolved all ten identifiers. The design has
  not been ingested into the active corpus.

## Next authorized step

Review and approve `revision-3-design.json`, then implement exact-DOI ingestion
with seed-level provenance. Do not emulate exact lookup with keyword search. Run
only the ten seed lookups, inspect every resolved seed, and obtain a later
approval before reference expansion or PDF retrieval.

After acquisition and extraction, review sources individually and write
`claim_links.jsonl`. Search ranking and abstract similarity do not establish
support or novelty.
