# Review: observation factorization and succinct identifiability

- **Status:** contract frozen; acquisition not executed
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

## Next authorized network steps

Inspect plans first:

```bash
python3 -m literature_review.pipeline discover \
  --review literature/observation-factorization
python3 -m literature_review.pipeline expand \
  --review literature/observation-factorization
python3 -m literature_review.pipeline download \
  --review literature/observation-factorization
```

Then, only with explicit approval, repeat each phase with `--execute`.

After acquisition and extraction, review sources individually and write
`claim_links.jsonl`. Search ranking and abstract similarity do not establish
support or novelty.
