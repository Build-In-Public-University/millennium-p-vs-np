# Local literature review workbench

This directory holds reproducible literature reviews. The workbench converts a
problem or body of work into a bounded citation graph, local open-access corpus,
and explicit claim-to-source connections.

## Invariants

1. **Claims precede search.** `review.json` freezes the problem, claims, queries,
   expansion depth, and record cap before acquisition.
2. **Dry run is the default.** Discovery, reference expansion, and downloads make
   zero network calls unless `--execute` is supplied.
3. **Metadata is broader than full text.** Every provider-reported reference
   within the declared boundary receives an edge. Closed or missing papers remain
   `metadata_only`; they are not silently omitted.
4. **Retrieval is lawful and bounded.** The downloader accepts only an exposed
   open-access PDF URL or a user-supplied local file. It rejects HTML login walls,
   enforces a 50 MB cap, and records the source URL, license field, byte count, and
   SHA-256 digest.
5. **Raw reading material stays local.** PDFs and extracted text live under
   `artifacts/` and are ignored by Git. Normalized metadata, citation edges, claim
   links, reports, and hashes are tracked and shareable.
6. **Search results are leads, not evidence.** A paper connects to a theory claim
   only through a reviewed row in `claim_links.jsonl` with a relationship,
   locator, evidence excerpt, and assessment.
7. **Completeness is scoped.** “All references” means all provider-reported
   bibliography edges within the frozen depth and record cap. Provider omissions,
   unresolved IDs, paywalls, malformed PDFs, and truncation remain visible.

## Layout

Each review directory contains:

```text
review.json          frozen question, claims, queries, and bounds
records.jsonl        normalized paper metadata and provenance
edges.jsonl          directed bibliography edges
claim_links.jsonl    human-reviewed theory/source relationships
artifacts.jsonl      local PDF/text hashes and retrieval status
receipts/*.json      phase receipts
report.json          machine-readable coverage summary
REPORT.md            human-readable claim and coverage report
artifacts/pdfs/      local PDFs; ignored by Git
artifacts/text/      local extracted text; ignored by Git
```

## Create a review

```bash
python3 -m literature_review.pipeline init \
  --root literature \
  --slug example-review \
  --title "Example review" \
  --problem "Which known results subsume this claim?" \
  --claim "C-01=The exact claim to test." \
  --query "first search formulation" \
  --query "second search formulation" \
  --depth 1 \
  --max-records 500 \
  --per-query 25
```

Do not broaden claims, depth, or caps after reading outcomes without versioning
`review.json` and logging why.

## Acquisition sequence

Set a review path once:

```bash
REVIEW=literature/example-review
```

### 1. Inspect zero-network plans

```bash
python3 -m literature_review.pipeline discover --review "$REVIEW"
python3 -m literature_review.pipeline expand --review "$REVIEW"
python3 -m literature_review.pipeline download --review "$REVIEW"
```

### 2. Discover seed papers

This is the first network boundary:

```bash
python3 -m literature_review.pipeline discover \
  --review "$REVIEW" \
  --execute
```

The initial adapter uses the public OpenAlex API. It normalizes DOI, arXiv, and
OpenAlex identifiers and deduplicates DOI-equivalent records.

### 3. Pull bibliography references

```bash
python3 -m literature_review.pipeline expand \
  --review "$REVIEW" \
  --execute
```

Expansion follows `referenced_works`, not papers that cite the seed. It repeats
until the declared depth is exhausted, the record cap is reached, or no further
provider records resolve. Receipts distinguish requested, resolved, remaining,
failed, and truncated references.

### 4. Download exposed open-access PDFs

```bash
python3 -m literature_review.pipeline download \
  --review "$REVIEW" \
  --execute
```

A DOI landing page is not treated as a PDF. A response must begin with the PDF
magic bytes `%PDF-`; HTML access walls are recorded as failures.

### 5. Attach a user-supplied lawful PDF

When metadata exists but OpenAlex exposes no PDF, attach a file you are
authorized to use locally:

```bash
python3 -m literature_review.pipeline attach \
  --review "$REVIEW" \
  --record-id "doi:10.1000/example" \
  --pdf "/path/to/source.pdf" \
  --license "user-authorized-local-review"
```

The receipt stores the source filename, authorization label, local artifact
path, and hash—not the original absolute path.

### 6. Extract text locally

Requires `pdftotext` from Poppler:

```bash
python3 -m literature_review.pipeline extract --review "$REVIEW"
```

Extraction uses `pdftotext -layout`. PDF and text hashes remain in
`artifacts.jsonl` so local files can be validated later without committing them.

## Connect literature to claims

Review the local text or lawful source, then append one JSON object per line to
`claim_links.jsonl`:

```json
{
  "schema_version": "literature-claim-link/v0.1",
  "claim_id": "C-01",
  "record_id": "doi:10.1000/example",
  "relationship": "overlaps",
  "locator": "page 4, Theorem 2",
  "evidence": "Short source-preserving excerpt.",
  "assessment": "Same factorization under different terminology; novelty reduced.",
  "reviewed_at": "2026-07-29T00:00:00+00:00"
}
```

Allowed relationships:

- `supports` — establishes the claim under matching assumptions;
- `contradicts` — supplies a result or counterexample against it;
- `overlaps` — materially similar, but equivalence is incomplete or uncertain;
- `context` — adjacent definitions, methods, or history;
- `unresolved` — relevant lead not yet adjudicated.

Do not use `supports` from an abstract alone. Record the theorem, section, page,
or stable local-text locator used for the judgment.

## Validate and report

```bash
python3 -m literature_review.pipeline report --review "$REVIEW"
python3 -m literature_review.pipeline validate --review "$REVIEW"
```

Validation checks:

- unique record IDs;
- citation edges synchronized with record bibliographies;
- claim and record foreign keys;
- allowed relationship vocabulary;
- artifact path containment;
- PDF and extracted-text SHA-256 hashes.

`REPORT.md` summarizes citation coverage, unresolved references, open-access
availability, extracted full text, and claim relationships. It does not perform
the intellectual judgment. That part remains annoyingly human.

## Sharing

Commit and share:

- the workbench code and tests;
- `review.json`;
- normalized metadata and citation edges;
- claim links and assessments;
- retrieval/validation receipts and hashes;
- reports.

Do not commit downloaded material merely because it was reachable. Redistribute
only when its license and repository policy permit it. Another researcher can
rerun acquisition, validate hashes when the source is unchanged, and see exactly
which sources were unavailable.

## Adapter boundary

The normalized record and edge schemas are provider-neutral. OpenAlex is the
first adapter because it combines identifiers, bibliography edges, and
open-access locations. Future adapters may add Crossref, arXiv, Semantic Scholar,
OpenCitations, local BibTeX/RIS, or user-supplied PDFs without changing claim
links or reports.
