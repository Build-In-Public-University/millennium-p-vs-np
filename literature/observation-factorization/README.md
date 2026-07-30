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

## Full-text result

- Revision 4 targeted exactly the two SAT functional-dependency papers and Karp's
  classical decomposition paper. Two author-hosted PDFs were retrieved and
  extracted; Karp remained publisher-closed and is recorded as metadata-only.
- Both retrieved papers use the exact form `f = h(g1, ..., gn)` and state the
  necessary-and-sufficient disjoint-fiber criterion. `T-01` is directly anticipated
  in the Boolean setting.
- Both build the same two-copy bad-fiber formula used by `T-11`: disjoint input
  copies, equal base-function outputs, and opposite target outputs. They state that
  dependency holds exactly when this formula is unsatisfiable, and the journal
  version describes linear-time circuit-to-CNF conversion.
- Neither inspected full text states NP-completeness of bad-fiber existence or
  coNP-completeness of dependency. This removes novelty from the witness
  construction, not necessarily from the explicit unrestricted complexity
  classification.
- Karp and Curtis place `T-01` in a classical Boolean functional-decomposition
  lineage, but the targeted Karp full text was not available for inspection.
- Blackwell and Torgersen directly occupy the comparison-of-experiments and
  decision-risk substrate around `T-BAYES`.
- Orlitsky and Roche directly separate computing a function from the bits needed
  to communicate it, placing `T-03` in an established information-theory lineage.
- Hyperproperties and noninterference provide established bad-observation-pair
  language, but their abstracts do not establish the same circuit complexity result.

The four line-addressed claim receipts are in `claim_links.jsonl`; the bounded
assessment and its falsifiers are in `revision-4-full-text-assessment.json`.

## Next decision

The revision-4 full-text authorization has been consumed. Do not expand all 248
references yet. The narrow remaining question is whether prior complexity
literature already classifies unrestricted Boolean functional dependency / the
two-copy bad-fiber SAT problem as NP-complete or coNP-complete. A bounded search for
that classification is more informative than undirected citation expansion.
