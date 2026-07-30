# Review: observation factorization and succinct identifiability

- **Status:** revision 3 exact seeds ingested and screened; reference expansion and full-text retrieval remain unauthorized
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

## Current acquisition boundary

- Ten exact DOI seeds;
- zero keyword queries;
- zero reference-expansion levels;
- ten normalized records maximum before new approval;
- no full-text retrieval under the consumed seed-ingestion authorization.

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
  44%, 32%, and 32%, respectively. Its rejected corpus and receipts remain under
  `history/discovery-r2/`.
- Revision 3 is specified in `revision-3-design.json`. It replaces keyword search
  with ten exact DOI seeds across noninterference, Boolean functional dependency,
  classical functional decomposition, statistical experiments, and distributed
  function computation. OpenAlex resolved all ten identifiers with exact DOI
  provenance. All ten passed topical screening. The active corpus contains ten
  records and 248 recorded reference edges; none of those references were followed.

## Preliminary prior-art risk

- The two SAT functional-dependency papers use the exact form
  `f = h(g1, ..., gn)`. They are very-high-risk prior art for `T-01` and the first
  sources to inspect for `T-11`.
- Karp and Curtis place `T-01` in a classical Boolean functional-decomposition
  lineage.
- Blackwell and Torgersen directly occupy the comparison-of-experiments and
  decision-risk substrate around `T-BAYES`.
- Orlitsky and Roche directly separate computing a function from the bits needed
  to communicate it, placing `T-03` in an established information-theory lineage.
- Hyperproperties and noninterference provide established bad-observation-pair
  language, but their abstracts do not establish the same circuit complexity result.

These are metadata/abstract screening judgments, not claim-level evidence and not
findings of theorem equivalence.

## Next decision

The one-shot seed-ingestion authorization has been consumed. Decide whether to
authorize one bounded backward-reference expansion from these ten seeds. PDF
retrieval remains a separate later decision.

After acquisition and extraction, review sources individually and write
`claim_links.jsonl`. Search ranking and abstract similarity do not establish
support or novelty.
