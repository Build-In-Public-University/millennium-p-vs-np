# Literature review: Observation factorization and succinct identifiability

- Generated: `2026-07-30T03:36:13.358355+00:00`
- Records: **10**
- Citation edges: **248**
- Coverage gap: **245 unresolved provider references**
- Open-access PDFs available: **4**
- Full texts extracted locally: **2**
- Claims linked: **2/4**

## Problem

Determine which parts of the observation-factorization framework are established under quotient factorization, sufficient statistics, information ordering, noninterference, functional dependence, and distributed function computation; identify whether the BAD-FIBER NP-completeness result has any residual novelty.

## Claim connections

### T-01 — overlaps

- Claim: An exact observation-restricted solver exists iff the task is constant on every observation fiber.
- Source: `doi:10.1109/iccad.2007.4397270` — Scalable exploration of functional dependency by interpolation and incremental SAT solving
- Locator: local-text:88-100
- Assessment: This proposition is the exact constant-on-observation-fibers criterion: no base-function value may occur with both target values. T-01 is therefore directly anticipated in the Boolean setting.

### T-01 — overlaps

- Claim: An exact observation-restricted solver exists iff the task is constant on every observation fiber.
- Source: `doi:10.1109/tc.2010.12` — To SAT or Not to SAT: Scalable Exploration of Functional Dependency
- Locator: local-text:96-130
- Assessment: This journal extension restates the exact fiber-disjointness criterion, so it independently confirms that T-01 is established terminology and mathematics rather than a new observation-factorization theorem.

### T-11 — overlaps

- Claim: For succinct Boolean circuits, BAD-FIBER is NP-complete and exact CIRCUIT-IDENTIFIABLE is coNP-complete.
- Source: `doi:10.1109/iccad.2007.4397270` — Scalable exploration of functional dependency by interpolation and incremental SAT solving
- Locator: local-text:135-169
- Assessment: Theorem 3 is the same bad-fiber witness architecture: two disjoint input copies, equal base outputs, and opposite target outputs. It establishes SAT iff a violating fiber exists and UNSAT iff factorization holds, but does not state NP-completeness or coNP-completeness.

### T-11 — overlaps

- Claim: For succinct Boolean circuits, BAD-FIBER is NP-complete and exact CIRCUIT-IDENTIFIABLE is coNP-complete.
- Source: `doi:10.1109/tc.2010.12` — To SAT or Not to SAT: Scalable Exploration of Functional Dependency
- Locator: local-text:160-205
- Assessment: The journal version gives the same polynomial-size two-copy CNF and SAT/UNSAT criterion. This removes novelty from the witness construction. No complexity-class theorem or NP/coNP completeness claim appears in the inspected full text.

## Complexity assessment: T-11

- BAD-FIBER: **NP-complete**
- CIRCUIT-IDENTIFIABLE: **coNP-complete**
- Substantive novelty: **falsified**
- Exact named prior publication: **not_found_in_bounded_search**
- Assessment: The exact BAD-FIBER name or f=h(G) complexity theorem was not found. Nevertheless, the classification is an immediate linear-size corollary of standard Circuit-SAT and is not defensible as a substantive theorem contribution. Search absence is not evidence that the exact wording is historically new.
- Proof receipt: Circuit-SAT many-one reduces to BAD-FIBER in linear size, so BAD-FIBER is NP-hard and therefore NP-complete. Exact CIRCUIT-IDENTIFIABLE is its complement by the constant-on-fibers criterion, so it is coNP-complete.

## Completeness boundary

“All references” means all provider-reported bibliography edges within the declared
expansion depth and record cap. Metadata can be complete while local full text remains
unavailable because a source is closed, missing, malformed, or not exposed by the provider.
