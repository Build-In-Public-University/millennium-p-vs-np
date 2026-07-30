from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from literature_review.pipeline import (
    attach_local_pdf,
    build_review_contract,
    discover,
    download_open_access,
    expand_references,
    extract_downloads,
    initialize_review,
    normalize_openalex_work,
    render_report,
    validate_review,
)


NOW = "2026-07-29T23:00:00+00:00"


def _work(
    openalex_id: str,
    *,
    doi: str | None = None,
    title: str = "Observation and task dependence",
    references: list[str] | None = None,
    pdf_url: str | None = None,
) -> dict[str, Any]:
    return {
        "id": f"https://openalex.org/{openalex_id}",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "title": title,
        "publication_year": 2024,
        "authorships": [
            {"author": {"id": "https://openalex.org/A1", "display_name": "Ada Example"}}
        ],
        "primary_location": {
            "landing_page_url": f"https://example.org/{openalex_id}",
            "pdf_url": pdf_url,
            "source": {"display_name": "Journal of Examples"},
            "license": "cc-by" if pdf_url else None,
        },
        "best_oa_location": {
            "landing_page_url": f"https://example.org/{openalex_id}",
            "pdf_url": pdf_url,
            "license": "cc-by" if pdf_url else None,
        }
        if pdf_url
        else None,
        "open_access": {"is_oa": bool(pdf_url), "oa_status": "gold" if pdf_url else "closed"},
        "referenced_works": [f"https://openalex.org/{item}" for item in references or []],
        "abstract_inverted_index": {"A": [0], "small": [1], "abstract": [2]},
        "type": "article",
        "language": "en",
    }


def _contract() -> dict[str, Any]:
    return build_review_contract(
        slug="observation-factorization",
        title="Observation factorization prior-work audit",
        problem="Determine where observation-relative identifiability already exists.",
        claims=[
            {
                "claim_id": "T-01",
                "text": "Exact inference exists iff the task is constant on observation fibers.",
            }
        ],
        queries=["functional dependence observation map", "noninterference Boolean circuits"],
        expansion_depth=1,
        max_records=50,
    )


def test_initialize_review_writes_shareable_contract_and_empty_ledgers(tmp_path: Path) -> None:
    review_dir = initialize_review(tmp_path, _contract())

    contract = json.loads((review_dir / "review.json").read_text())
    assert contract["schema_version"] == "literature-review/v0.1"
    assert contract["acquisition"]["execute_required"] is True
    assert contract["retrieval"]["full_text_policy"] == "open_access_or_user_supplied"
    assert contract["expansion"]["direction"] == "references"
    assert contract["claims"][0]["claim_id"] == "T-01"
    assert (review_dir / "records.jsonl").read_text() == ""
    assert (review_dir / "edges.jsonl").read_text() == ""
    assert (review_dir / "claim_links.jsonl").read_text() == ""


def test_openalex_normalization_preserves_identifiers_oa_and_all_reference_ids() -> None:
    record = normalize_openalex_work(
        _work(
            "W1",
            doi="10.1000/ABC.1",
            references=["W2", "W3"],
            pdf_url="https://example.org/paper.pdf",
        ),
        retrieved_at=NOW,
    )

    assert record["record_id"] == "doi:10.1000/abc.1"
    assert record["provider_ids"] == {"openalex": ["W1"]}
    assert record["doi"] == "10.1000/abc.1"
    assert record["abstract"] == "A small abstract"
    assert record["referenced_provider_ids"] == ["openalex:W2", "openalex:W3"]
    assert record["open_access"]["pdf_url"] == "https://example.org/paper.pdf"
    assert record["provenance"]["provider"] == "openalex"
    assert record["discovered_by_queries"] == []


def test_discovery_is_zero_network_without_execute_and_deduplicates_by_doi(tmp_path: Path) -> None:
    review_dir = initialize_review(tmp_path, _contract())
    calls: list[str] = []

    class Client:
        def search(self, query: str, per_page: int) -> list[dict[str, Any]]:
            calls.append(query)
            return [
                _work("W1", doi="10.1000/shared", references=["W2"]),
                _work("W9", doi="10.1000/shared", title="Duplicate provider record"),
            ]

    plan = discover(review_dir, Client(), execute=False, retrieved_at=NOW)
    assert plan["mode"] == "dry_run"
    assert plan["network_calls"] == 0
    assert calls == []
    assert (review_dir / "records.jsonl").read_text() == ""

    receipt = discover(review_dir, Client(), execute=True, retrieved_at=NOW)
    records = [json.loads(line) for line in (review_dir / "records.jsonl").read_text().splitlines()]
    assert calls == _contract()["discovery"]["queries"]
    assert receipt["records_added"] == 1
    assert len(records) == 1
    assert records[0]["record_id"] == "doi:10.1000/shared"
    assert set(records[0]["provider_ids"]["openalex"]) == {"W1", "W9"}
    assert records[0]["discovered_by_queries"] == sorted(_contract()["discovery"]["queries"])


def test_reference_expansion_resolves_every_provider_edge_within_contract_cap(
    tmp_path: Path,
) -> None:
    review_dir = initialize_review(tmp_path, _contract())

    class DiscoveryClient:
        def search(self, query: str, per_page: int) -> list[dict[str, Any]]:
            return [_work("W1", doi="10.1000/seed", references=["W2", "W3"])]

    discover(review_dir, DiscoveryClient(), execute=True, retrieved_at=NOW)
    calls: list[str] = []

    class ExpansionClient:
        def get_work(self, openalex_id: str) -> dict[str, Any]:
            calls.append(openalex_id)
            return {
                "W2": _work("W2", doi="10.1000/ref-2"),
                "W3": _work("W3", title="Reference without DOI"),
            }[openalex_id]

    dry = expand_references(review_dir, ExpansionClient(), execute=False, retrieved_at=NOW)
    assert dry["network_calls"] == 0
    assert calls == []

    receipt = expand_references(review_dir, ExpansionClient(), execute=True, retrieved_at=NOW)
    records = [json.loads(line) for line in (review_dir / "records.jsonl").read_text().splitlines()]
    edges = [json.loads(line) for line in (review_dir / "edges.jsonl").read_text().splitlines()]
    assert calls == ["W2", "W3"]
    assert receipt["references_requested"] == 2
    assert receipt["references_resolved"] == 2
    assert receipt["truncated"] is False
    assert len(records) == 3
    assert len(edges) == 2
    assert {edge["target_provider_id"] for edge in edges} == {"openalex:W2", "openalex:W3"}


def test_download_requires_execute_hashes_pdf_and_records_metadata_only_gaps(
    tmp_path: Path,
) -> None:
    review_dir = initialize_review(tmp_path, _contract())
    records = [
        normalize_openalex_work(
            _work("W1", doi="10.1000/open", pdf_url="https://example.org/open.pdf"),
            retrieved_at=NOW,
        ),
        normalize_openalex_work(_work("W2", doi="10.1000/closed"), retrieved_at=NOW),
    ]
    (review_dir / "records.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records)
    )
    calls: list[str] = []
    pdf = b"%PDF-1.7\nsmall fixture\n%%EOF\n"

    def fetch(url: str) -> tuple[bytes, str, str]:
        calls.append(url)
        return pdf, "application/pdf", url

    dry = download_open_access(review_dir, fetch, execute=False, retrieved_at=NOW)
    assert dry["network_calls"] == 0
    assert calls == []

    receipt = download_open_access(review_dir, fetch, execute=True, retrieved_at=NOW)
    artifacts = [
        json.loads(line) for line in (review_dir / "artifacts.jsonl").read_text().splitlines()
    ]
    assert calls == ["https://example.org/open.pdf"]
    assert receipt["downloaded"] == 1
    assert receipt["metadata_only"] == 1
    downloaded = next(row for row in artifacts if row["status"] == "downloaded")
    closed = next(row for row in artifacts if row["status"] == "metadata_only")
    path = review_dir / downloaded["local_path"]
    assert path.read_bytes() == pdf
    assert downloaded["sha256"] == hashlib.sha256(pdf).hexdigest()
    assert closed["reason"] == "no_open_access_pdf"


def test_download_rejects_non_pdf_payload(tmp_path: Path) -> None:
    review_dir = initialize_review(tmp_path, _contract())
    record = normalize_openalex_work(
        _work("W1", pdf_url="https://example.org/not-really.pdf"), retrieved_at=NOW
    )
    (review_dir / "records.jsonl").write_text(json.dumps(record) + "\n")

    def fetch(url: str) -> tuple[bytes, str, str]:
        return b"<html>login wall</html>", "text/html", url

    receipt = download_open_access(review_dir, fetch, execute=True, retrieved_at=NOW)
    artifact = json.loads((review_dir / "artifacts.jsonl").read_text())
    assert receipt["failed"] == 1
    assert artifact["status"] == "failed"
    assert artifact["reason"] == "response_was_not_pdf"


def test_attach_user_supplied_pdf_uses_same_hash_contract_without_network(
    tmp_path: Path,
) -> None:
    review_dir = initialize_review(tmp_path, _contract())
    record = normalize_openalex_work(_work("W1", doi="10.1000/local"), retrieved_at=NOW)
    (review_dir / "records.jsonl").write_text(json.dumps(record) + "\n")
    source = tmp_path / "supplied.pdf"
    source.write_bytes(b"%PDF-1.7\nuser supplied\n%%EOF\n")

    receipt = attach_local_pdf(
        review_dir,
        record_id="doi:10.1000/local",
        source=source,
        license_name="user-authorized-local-review",
        attached_at=NOW,
    )

    artifact = json.loads((review_dir / "artifacts.jsonl").read_text())
    assert receipt["network_calls"] == 0
    assert artifact["status"] == "downloaded"
    assert artifact["source_kind"] == "user_supplied"
    assert artifact["source_name"] == "supplied.pdf"
    assert "pytest-" not in json.dumps(artifact)
    assert validate_review(review_dir)["valid"] is True


def test_extract_validate_and_report_connect_claims_to_local_artifacts(tmp_path: Path) -> None:
    review_dir = initialize_review(tmp_path, _contract())
    record = normalize_openalex_work(
        _work("W1", doi="10.1000/open", references=["W2"], pdf_url="https://x/p.pdf"),
        retrieved_at=NOW,
    )
    (review_dir / "records.jsonl").write_text(json.dumps(record, sort_keys=True) + "\n")
    pdf = b"%PDF-1.7\nfixture\n%%EOF\n"

    download_open_access(
        review_dir,
        lambda url: (pdf, "application/pdf", url),
        execute=True,
        retrieved_at=NOW,
    )

    def extractor(source: Path, target: Path) -> None:
        assert source.read_bytes().startswith(b"%PDF-")
        target.write_text("The task is constant on each observation fiber.\n")

    extract_receipt = extract_downloads(review_dir, extractor=extractor, extracted_at=NOW)
    assert extract_receipt["extracted"] == 1

    link = {
        "schema_version": "literature-claim-link/v0.1",
        "claim_id": "T-01",
        "record_id": "doi:10.1000/open",
        "relationship": "overlaps",
        "locator": "local-text:1",
        "evidence": "The task is constant on each observation fiber.",
        "assessment": "Terminology overlap; theorem equivalence still requires review.",
        "reviewed_at": NOW,
    }
    (review_dir / "claim_links.jsonl").write_text(json.dumps(link, sort_keys=True) + "\n")

    validation = validate_review(review_dir)
    assert validation["valid"] is True
    assert validation["hashes_checked"] == 2

    report = render_report(review_dir, generated_at=NOW)
    assert report["records"] == 1
    assert report["reference_edges"] == 1
    assert report["references_unresolved"] == 1
    assert report["claims_linked"] == 1
    assert report["full_text_extracted"] == 1
    markdown = (review_dir / "REPORT.md").read_text()
    assert "T-01" in markdown
    assert "overlaps" in markdown
    assert "1 unresolved provider references" in markdown

    text_path = next((review_dir / "artifacts/text").glob("*.txt"))
    text_path.write_text("tampered\n")
    invalid = validate_review(review_dir)
    assert invalid["valid"] is False
    assert any("sha256 mismatch" in error for error in invalid["errors"])


def test_claim_links_reject_unknown_relationships(tmp_path: Path) -> None:
    review_dir = initialize_review(tmp_path, _contract())
    (review_dir / "claim_links.jsonl").write_text(
        json.dumps(
            {
                "claim_id": "T-01",
                "record_id": "openalex:W1",
                "relationship": "proves-everything",
            }
        )
        + "\n"
    )

    validation = validate_review(review_dir)
    assert validation["valid"] is False
    assert any("invalid relationship" in error for error in validation["errors"])
