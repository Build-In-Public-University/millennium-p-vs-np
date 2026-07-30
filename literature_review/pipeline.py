from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import time
from collections.abc import Callable, Iterable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote


UTC = timezone.utc
SCHEMA_VERSION = "literature-review/v0.1"
RECORD_SCHEMA = "literature-record/v0.1"
EDGE_SCHEMA = "literature-citation-edge/v0.1"
ARTIFACT_SCHEMA = "literature-artifact/v0.1"
RELATIONSHIPS = {"supports", "contradicts", "overlaps", "context", "unresolved"}


class DiscoveryClient(Protocol):
    def search(self, query: str, per_page: int) -> list[dict[str, Any]]: ...


class ExpansionClient(Protocol):
    def get_work(self, openalex_id: str) -> dict[str, Any]: ...


class ExactSeedClient(Protocol):
    def get_doi(self, doi: str) -> dict[str, Any]: ...


FetchBytes = Callable[[str], tuple[bytes, str, str]]
Extractor = Callable[[Path, Path], None]


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not slug:
        raise ValueError("slug must contain at least one letter or digit")
    return slug


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSON at {path}:{number}: {exc.msg}") from exc
        if not isinstance(row, dict):
            raise ValueError(f"expected object at {path}:{number}")
        rows.append(row)
    return rows


def _write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]], *, key: str | None = None) -> None:
    materialized = [dict(row) for row in rows]
    if key is not None:
        materialized.sort(key=lambda row: str(row.get(key) or ""))
    body = "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in materialized)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body)


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _load_contract(review_dir: Path) -> dict[str, Any]:
    path = review_dir / "review.json"
    if not path.exists():
        raise FileNotFoundError(f"review contract not found: {path}")
    value = json.loads(path.read_text())
    if value.get("schema_version") != SCHEMA_VERSION:
        raise ValueError(f"unsupported literature review schema: {value.get('schema_version')!r}")
    return value


def build_review_contract(
    *,
    slug: str,
    title: str,
    problem: str,
    claims: list[dict[str, str]],
    queries: list[str],
    expansion_depth: int = 1,
    max_records: int = 500,
    max_results_per_query: int = 25,
) -> dict[str, Any]:
    slug = _safe_slug(slug)
    if not title.strip() or not problem.strip():
        raise ValueError("title and problem are required")
    claim_ids = [str(claim.get("claim_id") or "") for claim in claims]
    if not claims or any(not item for item in claim_ids) or len(claim_ids) != len(set(claim_ids)):
        raise ValueError("claims need unique non-empty claim_id values")
    clean_queries = [query.strip() for query in queries if query.strip()]
    if not clean_queries:
        raise ValueError("at least one discovery query is required")
    if expansion_depth < 0 or max_records < 1 or max_results_per_query < 1:
        raise ValueError("expansion depth must be non-negative and limits must be positive")
    return {
        "schema_version": SCHEMA_VERSION,
        "slug": slug,
        "title": title.strip(),
        "problem": problem.strip(),
        "claims": claims,
        "discovery": {
            "provider": "openalex",
            "queries": clean_queries,
            "max_results_per_query": max_results_per_query,
        },
        "expansion": {
            "direction": "references",
            "depth": expansion_depth,
            "max_records": max_records,
            "completeness_claim": "provider_reported_references_within_declared_depth_and_cap",
        },
        "retrieval": {
            "full_text_policy": "open_access_or_user_supplied",
            "closed_or_unknown_access": "metadata_only",
            "local_artifacts_tracked_by_git": False,
            "max_pdf_bytes": 50_000_000,
        },
        "acquisition": {
            "execute_required": True,
            "dry_run_default": True,
            "raw_provider_responses_persisted": False,
            "normalized_metadata_and_hash_receipts_persisted": True,
        },
        "claim_relationships": sorted(RELATIONSHIPS),
    }


def initialize_review(root: Path, contract: Mapping[str, Any]) -> Path:
    if contract.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("initialize_review requires a literature-review/v0.1 contract")
    review_dir = root.expanduser().resolve() / str(contract["slug"])
    if (review_dir / "review.json").exists():
        raise FileExistsError(f"review already exists: {review_dir}")
    review_dir.mkdir(parents=True, exist_ok=True)
    _write_json(review_dir / "review.json", contract)
    for name in ("records.jsonl", "edges.jsonl", "claim_links.jsonl", "artifacts.jsonl"):
        (review_dir / name).write_text("")
    for name in ("artifacts/pdfs", "artifacts/text", "receipts"):
        (review_dir / name).mkdir(parents=True, exist_ok=True)
    (review_dir / "artifacts/.gitkeep").write_text("")
    return review_dir


def _normalize_doi(value: Any) -> str | None:
    if not value:
        return None
    doi = str(value).strip().lower()
    doi = re.sub(r"^https?://(?:dx\.)?doi\.org/", "", doi)
    doi = re.sub(r"^doi:\s*", "", doi)
    return doi or None


def _openalex_id(value: Any) -> str:
    identifier = str(value or "").rstrip("/").split("/")[-1]
    if not re.fullmatch(r"W\d+", identifier):
        raise ValueError(f"invalid OpenAlex work id: {value!r}")
    return identifier


def _abstract_from_inverted(index: Any) -> str | None:
    if not isinstance(index, dict) or not index:
        return None
    positioned: list[tuple[int, str]] = []
    for word, positions in index.items():
        if isinstance(positions, list):
            positioned.extend((int(position), str(word)) for position in positions)
    return " ".join(word for _, word in sorted(positioned)) or None


def _arxiv_id(work: Mapping[str, Any]) -> str | None:
    ids = work.get("ids")
    if not isinstance(ids, dict):
        return None
    value = ids.get("arxiv")
    if not value:
        return None
    return str(value).rstrip("/").split("/")[-1]


def normalize_openalex_work(
    work: Mapping[str, Any],
    *,
    retrieved_at: str,
    discovery_depth: int = 0,
    discovery_query: str | None = None,
) -> dict[str, Any]:
    openalex_id = _openalex_id(work.get("id"))
    doi = _normalize_doi(work.get("doi"))
    arxiv_id = _arxiv_id(work)
    record_id = f"doi:{doi}" if doi else f"arxiv:{arxiv_id}" if arxiv_id else f"openalex:{openalex_id}"
    raw_best = work.get("best_oa_location")
    raw_primary = work.get("primary_location")
    best: dict[str, Any] = dict(raw_best) if isinstance(raw_best, Mapping) else {}
    primary: dict[str, Any] = dict(raw_primary) if isinstance(raw_primary, Mapping) else {}
    location = best or primary
    raw_source = primary.get("source")
    source: dict[str, Any] = dict(raw_source) if isinstance(raw_source, Mapping) else {}
    references = sorted(
        {
            f"openalex:{_openalex_id(reference)}"
            for reference in work.get("referenced_works") or []
        }
    )
    authors: list[dict[str, Any]] = []
    for authorship in work.get("authorships") or []:
        author = authorship.get("author") if isinstance(authorship, dict) else None
        if not isinstance(author, dict):
            continue
        author_id = str(author.get("id") or "").rstrip("/").split("/")[-1] or None
        authors.append({"name": author.get("display_name"), "openalex_id": author_id})
    raw_open_access = work.get("open_access")
    open_access: dict[str, Any] = (
        dict(raw_open_access) if isinstance(raw_open_access, Mapping) else {}
    )
    return {
        "schema_version": RECORD_SCHEMA,
        "record_id": record_id,
        "provider_ids": {"openalex": [openalex_id]},
        "doi": doi,
        "arxiv_id": arxiv_id,
        "title": str(work.get("title") or "").strip(),
        "authors": authors,
        "year": work.get("publication_year"),
        "venue": source.get("display_name"),
        "type": work.get("type"),
        "language": work.get("language"),
        "abstract": _abstract_from_inverted(work.get("abstract_inverted_index")),
        "referenced_provider_ids": references,
        "discovery_depth": discovery_depth,
        "discovered_by_queries": [discovery_query] if discovery_query else [],
        "open_access": {
            "is_oa": bool(open_access.get("is_oa")),
            "status": open_access.get("oa_status"),
            "pdf_url": location.get("pdf_url"),
            "landing_url": location.get("landing_page_url"),
            "license": location.get("license"),
        },
        "provenance": {
            "provider": "openalex",
            "provider_record_id": openalex_id,
            "source_url": f"https://api.openalex.org/works/{openalex_id}",
            "retrieved_at": retrieved_at,
        },
    }


def _merge_record(existing: dict[str, Any], incoming: Mapping[str, Any]) -> dict[str, Any]:
    merged = dict(existing)
    provider_ids = {
        provider: list(values)
        for provider, values in (existing.get("provider_ids") or {}).items()
    }
    for provider, values in (incoming.get("provider_ids") or {}).items():
        provider_ids[provider] = sorted(set(provider_ids.get(provider, [])) | set(values))
    merged["provider_ids"] = provider_ids
    merged["referenced_provider_ids"] = sorted(
        set(existing.get("referenced_provider_ids") or [])
        | set(incoming.get("referenced_provider_ids") or [])
    )
    merged["discovered_by_queries"] = sorted(
        set(existing.get("discovered_by_queries") or [])
        | set(incoming.get("discovered_by_queries") or [])
    )
    merged["discovered_by_seed_dois"] = sorted(
        set(existing.get("discovered_by_seed_dois") or [])
        | set(incoming.get("discovered_by_seed_dois") or [])
    )
    merged["discovery_depth"] = min(
        int(existing.get("discovery_depth", 0)), int(incoming.get("discovery_depth", 0))
    )
    if not merged.get("abstract") and incoming.get("abstract"):
        merged["abstract"] = incoming["abstract"]
    if not merged.get("open_access", {}).get("pdf_url") and incoming.get("open_access", {}).get(
        "pdf_url"
    ):
        merged["open_access"] = incoming["open_access"]
    return merged


def _merge_records(
    existing: Iterable[Mapping[str, Any]], incoming: Iterable[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {str(row["record_id"]): dict(row) for row in existing}
    for row in incoming:
        record_id = str(row["record_id"])
        if record_id in by_id:
            by_id[record_id] = _merge_record(by_id[record_id], row)
        else:
            by_id[record_id] = dict(row)
    return [by_id[key] for key in sorted(by_id)]


def _provider_record_map(records: Iterable[Mapping[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for record in records:
        for provider, values in (record.get("provider_ids") or {}).items():
            for value in values:
                result[f"{provider}:{value}"] = str(record["record_id"])
    return result


def _edges(records: Iterable[Mapping[str, Any]]) -> list[dict[str, Any]]:
    rows = list(records)
    provider_map = _provider_record_map(rows)
    edges: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for record in rows:
        source = str(record["record_id"])
        for target in record.get("referenced_provider_ids") or []:
            key = (source, str(target))
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                {
                    "schema_version": EDGE_SCHEMA,
                    "source_record_id": source,
                    "target_provider_id": target,
                    "target_record_id": provider_map.get(str(target)),
                    "relationship": "references",
                }
            )
    return sorted(edges, key=lambda row: (row["source_record_id"], row["target_provider_id"]))


def _sync_edges(review_dir: Path, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edges = _edges(records)
    _write_jsonl(review_dir / "edges.jsonl", edges)
    return edges


def _receipt(review_dir: Path, phase: str, value: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {"schema_version": "literature-acquisition-receipt/v0.1", "phase": phase, **value}
    _write_json(review_dir / "receipts" / f"{phase}.json", receipt)
    return receipt


def discover(
    review_dir: Path,
    client: DiscoveryClient,
    *,
    execute: bool,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    contract = _load_contract(review_dir)
    discovery = contract["discovery"]
    queries = list(discovery["queries"])
    if not execute:
        return {
            "mode": "dry_run",
            "network_calls": 0,
            "queries": queries,
            "max_results_per_query": discovery["max_results_per_query"],
        }
    retrieved_at = retrieved_at or _now()
    existing = _read_jsonl(review_dir / "records.jsonl")
    incoming: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    calls = 0
    for query in queries:
        try:
            works = client.search(query, int(discovery["max_results_per_query"]))
            calls += 1
            incoming.extend(
                normalize_openalex_work(
                    work,
                    retrieved_at=retrieved_at,
                    discovery_depth=0,
                    discovery_query=query,
                )
                for work in works
            )
        except Exception as exc:  # provider failure is recorded without losing prior queries
            failures.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})
    merged = _merge_records(existing, incoming)
    max_records = int(contract["expansion"]["max_records"])
    truncated = len(merged) > max_records
    merged = merged[:max_records]
    _write_jsonl(review_dir / "records.jsonl", merged, key="record_id")
    edges = _sync_edges(review_dir, merged)
    return _receipt(
        review_dir,
        "discover",
        {
            "mode": "execute",
            "retrieved_at": retrieved_at,
            "network_calls": calls,
            "queries_attempted": len(queries),
            "records_before": len(existing),
            "records_after": len(merged),
            "records_added": max(0, len(merged) - len(existing)),
            "reference_edges": len(edges),
            "failures": failures,
            "truncated": truncated,
        },
    )


def search_complexity_gap(
    review_dir: Path,
    client: DiscoveryClient,
    *,
    plan_path: Path,
    execute: bool,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    plan = json.loads(plan_path.read_text())
    queries = [str(query).strip() for query in plan.get("queries") or []]
    per_query = int(plan.get("per_query") or 0)
    max_calls = int(plan.get("maximum_provider_calls") or 0)
    max_candidates = int(plan.get("maximum_candidates") or 0)
    if (
        str(plan.get("provider") or "").lower() != "openalex"
        or not queries
        or any(not query for query in queries)
        or len(queries) != len(set(queries))
        or per_query < 1
        or max_calls < len(queries)
        or max_candidates < 1
        or plan.get("reference_expansion_authorized") is not False
    ):
        raise ValueError("complexity-gap plan has an invalid provider, boundary, or query set")
    if not execute:
        return {
            "mode": "dry_run",
            "network_calls": 0,
            "queries": queries,
            "per_query": per_query,
            "maximum_candidates": max_candidates,
        }
    if not (plan.get("execution_gate") or {}).get("authorized"):
        raise PermissionError("complexity-gap search is not authorized by the plan")

    retrieved_at = retrieved_at or _now()
    incoming: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    calls = raw_results = 0
    for query in queries:
        try:
            works = client.search(query, per_query)
            calls += 1
            raw_results += len(works)
            incoming.extend(
                normalize_openalex_work(
                    work,
                    retrieved_at=retrieved_at,
                    discovery_depth=0,
                    discovery_query=query,
                )
                for work in works
            )
        except Exception as exc:
            failures.append({"query": query, "error": f"{type(exc).__name__}: {exc}"})
    candidates = _merge_records([], incoming)
    truncated = len(candidates) > max_candidates
    candidates = candidates[:max_candidates]
    _write_jsonl(
        review_dir / "complexity-search-candidates.jsonl",
        candidates,
        key="record_id",
    )
    return _receipt(
        review_dir,
        "complexity-search",
        {
            "mode": "execute",
            "retrieved_at": retrieved_at,
            "network_calls": calls,
            "queries_attempted": len(queries),
            "raw_results": raw_results,
            "unique_candidates": len(candidates),
            "failures": failures,
            "truncated": truncated,
            "active_corpus_modified": False,
            "reference_expansion": 0,
        },
    )


def ingest_exact_seeds(
    review_dir: Path,
    client: ExactSeedClient,
    *,
    design_path: Path,
    execute: bool,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    design = json.loads(design_path.read_text())
    plan = design.get("provider_plan") or {}
    if plan.get("lookup_mode") != "exact_doi_only" or plan.get("reference_depth") != 0:
        raise ValueError("seed design must require exact DOI lookup with reference depth zero")
    seeds = design.get("seeds") or []
    maximum = int(plan.get("maximum_seed_records") or 0)
    raw_dois = [
        _normalize_doi(seed.get("doi"))
        for seed in seeds
        if isinstance(seed, Mapping)
    ]
    if (
        not raw_dois
        or any(doi is None for doi in raw_dois)
        or len(raw_dois) != len(set(raw_dois))
    ):
        raise ValueError("seed design requires unique non-empty DOI values")
    dois = [str(doi) for doi in raw_dois]
    if maximum < 1 or len(dois) > maximum:
        raise ValueError("seed design exceeds maximum_seed_records")
    if not execute:
        return {
            "mode": "dry_run",
            "network_calls": 0,
            "seed_dois": dois,
            "maximum_seed_records": maximum,
        }
    if not (design.get("execution_gate") or {}).get("authorized"):
        raise PermissionError("seed ingestion is not authorized by the design")

    retrieved_at = retrieved_at or _now()
    existing = _read_jsonl(review_dir / "records.jsonl")
    incoming: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    calls = 0
    for doi in dois:
        try:
            work = client.get_doi(doi)
            calls += 1
            record = normalize_openalex_work(
                work, retrieved_at=retrieved_at, discovery_depth=0
            )
            if record.get("doi") != doi:
                raise ValueError(f"provider DOI mismatch: expected {doi}, got {record.get('doi')}")
            record["discovered_by_seed_dois"] = [doi]
            incoming.append(record)
        except Exception as exc:
            failures.append({"doi": doi, "error": f"{type(exc).__name__}: {exc}"})
    merged = _merge_records(existing, incoming)
    _write_jsonl(review_dir / "records.jsonl", merged, key="record_id")
    edges = _sync_edges(review_dir, merged)
    return _receipt(
        review_dir,
        "ingest-seeds",
        {
            "mode": "execute",
            "retrieved_at": retrieved_at,
            "network_calls": calls,
            "seeds_attempted": len(dois),
            "seeds_resolved": len(incoming),
            "records_before": len(existing),
            "records_after": len(merged),
            "reference_edges": len(edges),
            "failures": failures,
        },
    )


def _unresolved_with_depth(records: list[dict[str, Any]], max_depth: int) -> dict[str, int]:
    provider_map = _provider_record_map(records)
    unresolved: dict[str, int] = {}
    for record in records:
        source_depth = int(record.get("discovery_depth", 0))
        if source_depth >= max_depth:
            continue
        for target in record.get("referenced_provider_ids") or []:
            if target not in provider_map:
                target_depth = source_depth + 1
                unresolved[str(target)] = min(unresolved.get(str(target), target_depth), target_depth)
    return unresolved


def expand_references(
    review_dir: Path,
    client: ExpansionClient,
    *,
    execute: bool,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    contract = _load_contract(review_dir)
    records = _read_jsonl(review_dir / "records.jsonl")
    max_depth = int(contract["expansion"]["depth"])
    max_records = int(contract["expansion"]["max_records"])
    initial = _unresolved_with_depth(records, max_depth)
    if not execute:
        return {
            "mode": "dry_run",
            "network_calls": 0,
            "references_pending": len(initial),
            "depth": max_depth,
            "max_records": max_records,
        }
    retrieved_at = retrieved_at or _now()
    requested = 0
    resolved = 0
    failures: list[dict[str, str]] = []
    truncated = False
    while True:
        unresolved = _unresolved_with_depth(records, max_depth)
        if not unresolved:
            break
        capacity = max_records - len(records)
        if capacity <= 0:
            truncated = True
            break
        targets = sorted(unresolved.items())
        if len(targets) > capacity:
            targets = targets[:capacity]
            truncated = True
        incoming: list[dict[str, Any]] = []
        for provider_id, depth in targets:
            if not provider_id.startswith("openalex:"):
                failures.append({"provider_id": provider_id, "error": "unsupported_provider"})
                continue
            requested += 1
            try:
                work = client.get_work(provider_id.split(":", 1)[1])
                incoming.append(
                    normalize_openalex_work(work, retrieved_at=retrieved_at, discovery_depth=depth)
                )
                resolved += 1
            except Exception as exc:
                failures.append(
                    {"provider_id": provider_id, "error": f"{type(exc).__name__}: {exc}"}
                )
        if not incoming:
            break
        before = len(records)
        records = _merge_records(records, incoming)
        if len(records) == before:
            break
        if truncated:
            break
    _write_jsonl(review_dir / "records.jsonl", records, key="record_id")
    edges = _sync_edges(review_dir, records)
    remaining = _unresolved_with_depth(records, max_depth)
    truncated = truncated or bool(remaining and len(records) >= max_records)
    return _receipt(
        review_dir,
        "expand",
        {
            "mode": "execute",
            "retrieved_at": retrieved_at,
            "network_calls": requested,
            "references_requested": requested,
            "references_resolved": resolved,
            "references_remaining_within_depth": len(remaining),
            "records_after": len(records),
            "reference_edges": len(edges),
            "failures": failures,
            "truncated": truncated,
        },
    )


def _artifact_name(record_id: str, suffix: str) -> str:
    label = re.sub(r"[^a-z0-9]+", "-", record_id.lower()).strip("-")[:48]
    digest = hashlib.sha256(record_id.encode()).hexdigest()[:12]
    return f"{label}-{digest}{suffix}"


def download_open_access(
    review_dir: Path,
    fetch: FetchBytes,
    *,
    execute: bool,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    contract = _load_contract(review_dir)
    records = _read_jsonl(review_dir / "records.jsonl")
    _sync_edges(review_dir, records)
    candidates = [record for record in records if record.get("open_access", {}).get("pdf_url")]
    if not execute:
        return {
            "mode": "dry_run",
            "network_calls": 0,
            "open_access_candidates": len(candidates),
            "metadata_only": len(records) - len(candidates),
        }
    retrieved_at = retrieved_at or _now()
    prior = {row["record_id"]: row for row in _read_jsonl(review_dir / "artifacts.jsonl")}
    artifacts: dict[str, dict[str, Any]] = {}
    downloaded = failed = metadata_only = calls = 0
    max_bytes = int(contract["retrieval"]["max_pdf_bytes"])
    for record in records:
        record_id = str(record["record_id"])
        pdf_url = record.get("open_access", {}).get("pdf_url")
        if not pdf_url:
            artifacts[record_id] = {
                "schema_version": ARTIFACT_SCHEMA,
                "record_id": record_id,
                "status": "metadata_only",
                "reason": "no_open_access_pdf",
                "checked_at": retrieved_at,
            }
            metadata_only += 1
            continue
        existing = prior.get(record_id)
        if existing and existing.get("status") in {"downloaded", "extracted"}:
            local = review_dir / str(existing.get("local_path") or "")
            if local.is_file() and _sha256(local) == existing.get("sha256"):
                artifacts[record_id] = existing
                downloaded += 1
                continue
        try:
            payload, content_type, final_url = fetch(str(pdf_url))
            calls += 1
            if len(payload) > max_bytes:
                raise ValueError("pdf_exceeded_size_limit")
            if not payload.startswith(b"%PDF-"):
                raise ValueError("response_was_not_pdf")
            filename = _artifact_name(record_id, ".pdf")
            relative = Path("artifacts/pdfs") / filename
            path = review_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            artifacts[record_id] = {
                "schema_version": ARTIFACT_SCHEMA,
                "record_id": record_id,
                "status": "downloaded",
                "source_url": pdf_url,
                "final_url": final_url,
                "content_type": content_type,
                "license": record.get("open_access", {}).get("license"),
                "local_path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "retrieved_at": retrieved_at,
            }
            downloaded += 1
        except Exception as exc:
            reason = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"
            artifacts[record_id] = {
                "schema_version": ARTIFACT_SCHEMA,
                "record_id": record_id,
                "status": "failed",
                "source_url": pdf_url,
                "reason": reason,
                "checked_at": retrieved_at,
            }
            failed += 1
    _write_jsonl(review_dir / "artifacts.jsonl", artifacts.values(), key="record_id")
    return _receipt(
        review_dir,
        "download",
        {
            "mode": "execute",
            "retrieved_at": retrieved_at,
            "network_calls": calls,
            "records": len(records),
            "downloaded": downloaded,
            "metadata_only": metadata_only,
            "failed": failed,
        },
    )


def attach_local_pdf(
    review_dir: Path,
    *,
    record_id: str,
    source: Path,
    license_name: str,
    attached_at: str | None = None,
) -> dict[str, Any]:
    """Attach a user-authorized local PDF without persisting its source path."""

    contract = _load_contract(review_dir)
    records = _read_jsonl(review_dir / "records.jsonl")
    _sync_edges(review_dir, records)
    if record_id not in {str(record["record_id"]) for record in records}:
        raise ValueError(f"unknown literature record: {record_id}")
    source = source.expanduser().resolve()
    if not source.is_file():
        raise FileNotFoundError(f"local PDF not found: {source}")
    payload = source.read_bytes()
    if len(payload) > int(contract["retrieval"]["max_pdf_bytes"]):
        raise ValueError("pdf_exceeded_size_limit")
    if not payload.startswith(b"%PDF-"):
        raise ValueError("local_file_was_not_pdf")
    if not license_name.strip():
        raise ValueError("a license or local-use authorization label is required")
    attached_at = attached_at or _now()
    relative = Path("artifacts/pdfs") / _artifact_name(record_id, ".pdf")
    target = review_dir / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(payload)
    artifacts = {
        str(row["record_id"]): row for row in _read_jsonl(review_dir / "artifacts.jsonl")
    }
    artifacts[record_id] = {
        "schema_version": ARTIFACT_SCHEMA,
        "record_id": record_id,
        "status": "downloaded",
        "source_kind": "user_supplied",
        "source_name": source.name,
        "license": license_name.strip(),
        "local_path": relative.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "bytes": len(payload),
        "retrieved_at": attached_at,
    }
    _write_jsonl(review_dir / "artifacts.jsonl", artifacts.values(), key="record_id")
    return _receipt(
        review_dir,
        "attach",
        {
            "mode": "local",
            "attached_at": attached_at,
            "network_calls": 0,
            "record_id": record_id,
            "source_name": source.name,
            "local_path": relative.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "bytes": len(payload),
            "license": license_name.strip(),
        },
    )


def download_targets(
    review_dir: Path,
    fetch: FetchBytes,
    *,
    plan_path: Path,
    execute: bool,
    retrieved_at: str | None = None,
) -> dict[str, Any]:
    contract = _load_contract(review_dir)
    records = {
        str(record["record_id"]): record
        for record in _read_jsonl(review_dir / "records.jsonl")
    }
    plan = json.loads(plan_path.read_text())
    targets = plan.get("targets") or []
    maximum = int(plan.get("maximum_targets") or 0)
    record_ids = [
        str(target.get("record_id"))
        for target in targets
        if isinstance(target, Mapping)
    ]
    if (
        not record_ids
        or len(record_ids) != len(targets)
        or len(record_ids) != len(set(record_ids))
        or maximum < 1
        or len(record_ids) > maximum
    ):
        raise ValueError("target plan requires unique records within maximum_targets")
    unknown = sorted(set(record_ids) - set(records))
    if unknown:
        raise ValueError(f"target plan contains unknown records: {', '.join(unknown)}")
    candidates = sum(bool(target.get("source_url")) for target in targets)
    if not execute:
        return {
            "mode": "dry_run",
            "network_calls": 0,
            "targets": len(targets),
            "download_candidates": candidates,
            "unavailable": len(targets) - candidates,
        }
    if not (plan.get("execution_gate") or {}).get("authorized"):
        raise PermissionError("targeted full-text retrieval is not authorized by the plan")

    retrieved_at = retrieved_at or _now()
    artifacts = {
        str(row["record_id"]): row
        for row in _read_jsonl(review_dir / "artifacts.jsonl")
    }
    max_bytes = int(contract["retrieval"]["max_pdf_bytes"])
    downloaded = failed = metadata_only = calls = 0
    for target in targets:
        record_id = str(target["record_id"])
        source_url = target.get("source_url")
        if not source_url:
            artifacts[record_id] = {
                "schema_version": ARTIFACT_SCHEMA,
                "record_id": record_id,
                "status": "metadata_only",
                "source_kind": target.get("source_kind"),
                "reason": "no_authorized_full_text_source",
                "checked_at": retrieved_at,
            }
            metadata_only += 1
            continue
        try:
            payload, content_type, final_url = fetch(str(source_url))
            calls += 1
            if len(payload) > max_bytes:
                raise ValueError("pdf_exceeded_size_limit")
            if not payload.startswith(b"%PDF-"):
                raise ValueError("response_was_not_pdf")
            relative = Path("artifacts/pdfs") / _artifact_name(record_id, ".pdf")
            path = review_dir / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(payload)
            artifacts[record_id] = {
                "schema_version": ARTIFACT_SCHEMA,
                "record_id": record_id,
                "status": "downloaded",
                "source_kind": target.get("source_kind"),
                "source_url": source_url,
                "final_url": final_url,
                "content_type": content_type,
                "local_path": relative.as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "bytes": len(payload),
                "retrieved_at": retrieved_at,
            }
            downloaded += 1
        except Exception as exc:
            reason = str(exc) if isinstance(exc, ValueError) else f"{type(exc).__name__}: {exc}"
            artifacts[record_id] = {
                "schema_version": ARTIFACT_SCHEMA,
                "record_id": record_id,
                "status": "failed",
                "source_kind": target.get("source_kind"),
                "source_url": source_url,
                "reason": reason,
                "checked_at": retrieved_at,
            }
            failed += 1
    _write_jsonl(review_dir / "artifacts.jsonl", artifacts.values(), key="record_id")
    return _receipt(
        review_dir,
        "download-targets",
        {
            "mode": "execute",
            "retrieved_at": retrieved_at,
            "network_calls": calls,
            "targets": len(targets),
            "downloaded": downloaded,
            "metadata_only": metadata_only,
            "failed": failed,
        },
    )


def _pdftotext(source: Path, target: Path) -> None:
    run = subprocess.run(
        ["pdftotext", "-layout", str(source), str(target)],
        text=True,
        capture_output=True,
    )
    if run.returncode:
        raise RuntimeError(run.stderr.strip() or f"pdftotext exited {run.returncode}")


def extract_downloads(
    review_dir: Path,
    *,
    extractor: Extractor = _pdftotext,
    extracted_at: str | None = None,
) -> dict[str, Any]:
    _load_contract(review_dir)
    extracted_at = extracted_at or _now()
    artifacts = _read_jsonl(review_dir / "artifacts.jsonl")
    extracted = failed = 0
    for artifact in artifacts:
        if artifact.get("status") not in {"downloaded", "extracted"}:
            continue
        source = review_dir / str(artifact["local_path"])
        relative = Path("artifacts/text") / _artifact_name(str(artifact["record_id"]), ".txt")
        target = review_dir / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            extractor(source, target)
            if not target.exists():
                raise RuntimeError("extractor did not create target text")
            artifact.update(
                {
                    "status": "extracted",
                    "text_local_path": relative.as_posix(),
                    "text_sha256": _sha256(target),
                    "text_bytes": target.stat().st_size,
                    "extracted_at": extracted_at,
                }
            )
            artifact.pop("extraction_error", None)
            extracted += 1
        except Exception as exc:
            artifact["extraction_error"] = f"{type(exc).__name__}: {exc}"
            failed += 1
    _write_jsonl(review_dir / "artifacts.jsonl", artifacts, key="record_id")
    return _receipt(
        review_dir,
        "extract",
        {
            "mode": "local",
            "extracted_at": extracted_at,
            "network_calls": 0,
            "extracted": extracted,
            "failed": failed,
        },
    )


def _inside(root: Path, relative: Any) -> Path | None:
    if not relative:
        return None
    candidate = (root / str(relative)).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def validate_review(review_dir: Path) -> dict[str, Any]:
    errors: list[str] = []
    try:
        contract = _load_contract(review_dir)
    except Exception as exc:
        return {"valid": False, "hashes_checked": 0, "errors": [str(exc)]}
    try:
        records = _read_jsonl(review_dir / "records.jsonl")
        artifacts = _read_jsonl(review_dir / "artifacts.jsonl")
        links = _read_jsonl(review_dir / "claim_links.jsonl")
    except ValueError as exc:
        return {"valid": False, "hashes_checked": 0, "errors": [str(exc)]}
    record_ids = [str(record.get("record_id") or "") for record in records]
    if len(record_ids) != len(set(record_ids)):
        errors.append("duplicate record_id in records.jsonl")
    known_records = set(record_ids)
    known_claims = {str(claim["claim_id"]) for claim in contract.get("claims") or []}
    hashes_checked = 0
    for artifact in artifacts:
        record_id = str(artifact.get("record_id") or "")
        if record_id not in known_records:
            errors.append(f"artifact references unknown record: {record_id}")
        for path_key, hash_key in (("local_path", "sha256"), ("text_local_path", "text_sha256")):
            if not artifact.get(path_key):
                continue
            path = _inside(review_dir, artifact[path_key])
            if path is None:
                errors.append(f"artifact path escapes review: {artifact[path_key]}")
                continue
            if not path.is_file():
                errors.append(f"artifact missing: {artifact[path_key]}")
                continue
            hashes_checked += 1
            actual = _sha256(path)
            if actual != artifact.get(hash_key):
                errors.append(f"sha256 mismatch: {artifact[path_key]}")
    for link in links:
        relationship = link.get("relationship")
        if relationship not in RELATIONSHIPS:
            errors.append(f"invalid relationship: {relationship}")
        if str(link.get("claim_id") or "") not in known_claims:
            errors.append(f"claim link references unknown claim: {link.get('claim_id')}")
        if str(link.get("record_id") or "") not in known_records:
            errors.append(f"claim link references unknown record: {link.get('record_id')}")
    expected_edges = _edges(records)
    stored_edges = _read_jsonl(review_dir / "edges.jsonl")
    if stored_edges != expected_edges:
        errors.append("edges.jsonl does not match normalized record references; run report or expansion")
    return {
        "valid": not errors,
        "hashes_checked": hashes_checked,
        "records": len(records),
        "artifacts": len(artifacts),
        "claim_links": len(links),
        "errors": errors,
    }


def render_report(review_dir: Path, *, generated_at: str | None = None) -> dict[str, Any]:
    contract = _load_contract(review_dir)
    records = _read_jsonl(review_dir / "records.jsonl")
    edges = _sync_edges(review_dir, records)
    artifacts = _read_jsonl(review_dir / "artifacts.jsonl")
    links = _read_jsonl(review_dir / "claim_links.jsonl")
    provider_map = _provider_record_map(records)
    unresolved = sum(1 for edge in edges if edge["target_provider_id"] not in provider_map)
    extracted = sum(1 for artifact in artifacts if artifact.get("status") == "extracted")
    downloaded = sum(
        1 for artifact in artifacts if artifact.get("status") in {"downloaded", "extracted"}
    )
    metadata_only = sum(1 for artifact in artifacts if artifact.get("status") == "metadata_only")
    claims_linked = len({str(link.get("claim_id")) for link in links if link.get("claim_id")})
    generated_at = generated_at or _now()
    seed_boundary = contract.get("seed_ingestion") or {}
    assessment_path = review_dir / "revision-6-complexity-assessment.json"
    complexity_assessment = (
        json.loads(assessment_path.read_text()) if assessment_path.exists() else None
    )
    decision = (complexity_assessment or {}).get("decision") or {}
    result = {
        "schema_version": "literature-review-report/v0.1",
        "generated_at": generated_at,
        "review": contract["slug"],
        "records": len(records),
        "reference_edges": len(edges),
        "references_unresolved": unresolved,
        "open_access_pdf_available": sum(
            1 for record in records if record.get("open_access", {}).get("pdf_url")
        ),
        "full_text_downloaded": downloaded,
        "full_text_extracted": extracted,
        "metadata_only": metadata_only,
        "claims_total": len(contract.get("claims") or []),
        "claims_linked": claims_linked,
        "claim_links": len(links),
        "expansion_depth": seed_boundary.get(
            "reference_depth", contract["expansion"]["depth"]
        ),
        "max_records": seed_boundary.get(
            "maximum_records", contract["expansion"]["max_records"]
        ),
    }
    if decision:
        result["complexity_assessment"] = decision.get("substantive_novelty_status")
    _write_json(review_dir / "report.json", result)
    claim_text = {str(claim["claim_id"]): str(claim["text"]) for claim in contract["claims"]}
    record_title = {str(record["record_id"]): str(record["title"]) for record in records}
    lines = [
        f"# Literature review: {contract['title']}",
        "",
        f"- Generated: `{generated_at}`",
        f"- Records: **{len(records)}**",
        f"- Citation edges: **{len(edges)}**",
        f"- Coverage gap: **{unresolved} unresolved provider references**",
        f"- Open-access PDFs available: **{result['open_access_pdf_available']}**",
        f"- Full texts extracted locally: **{extracted}**",
        f"- Claims linked: **{claims_linked}/{result['claims_total']}**",
        "",
        "## Problem",
        "",
        str(contract["problem"]),
        "",
        "## Claim connections",
        "",
    ]
    if not links:
        lines.append("No claim links have been reviewed yet.")
    else:
        for link in sorted(links, key=lambda row: (str(row.get("claim_id")), str(row.get("record_id")))):
            claim_id = str(link.get("claim_id"))
            record_id = str(link.get("record_id"))
            lines.extend(
                [
                    f"### {claim_id} — {link.get('relationship')}",
                    "",
                    f"- Claim: {claim_text.get(claim_id, 'UNKNOWN CLAIM')}",
                    f"- Source: `{record_id}` — {record_title.get(record_id, 'UNKNOWN RECORD')}",
                    f"- Locator: {link.get('locator') or 'not recorded'}",
                    f"- Assessment: {link.get('assessment') or 'not recorded'}",
                    "",
                ]
            )
    if decision:
        proof = (complexity_assessment or {}).get("proof_receipt") or {}
        lines.extend(
            [
                f"## Complexity assessment: {(complexity_assessment or {}).get('claim_id')}",
                "",
                f"- BAD-FIBER: **{decision.get('bad_fiber_complexity')}**",
                f"- CIRCUIT-IDENTIFIABLE: **{decision.get('circuit_identifiable_complexity')}**",
                f"- Substantive novelty: **{decision.get('substantive_novelty_status')}**",
                "- Exact named prior publication: "
                f"**{decision.get('exact_named_prior_publication_status')}**",
                f"- Assessment: {decision.get('interpretation')}",
                f"- Proof receipt: {proof.get('conclusion')}",
                "",
            ]
        )
    lines.extend(
        [
            "## Completeness boundary",
            "",
            "“All references” means all provider-reported bibliography edges within the declared",
            "expansion depth and record cap. Metadata can be complete while local full text remains",
            "unavailable because a source is closed, missing, malformed, or not exposed by the provider.",
            "",
        ]
    )
    (review_dir / "REPORT.md").write_text("\n".join(lines))
    return result


class OpenAlexClient:
    """Minimal public OpenAlex adapter with explicit request pacing."""

    def __init__(self, *, email: str | None = None, delay_seconds: float = 0.12) -> None:
        import requests

        self._requests = requests
        self.email = email
        self.delay_seconds = delay_seconds
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "bipu-literature-review/0.1 (https://github.com/Build-In-Public-University)"}
        )

    def _get(self, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.email:
            params = {**(params or {}), "mailto": self.email}
        response = self.session.get(url, params=params, timeout=45)
        response.raise_for_status()
        time.sleep(self.delay_seconds)
        value = response.json()
        if not isinstance(value, dict):
            raise RuntimeError("OpenAlex response was not an object")
        return value

    def search(self, query: str, per_page: int) -> list[dict[str, Any]]:
        value = self._get(
            "https://api.openalex.org/works",
            {"search": query, "per-page": min(per_page, 100), "select": _OPENALEX_FIELDS},
        )
        results = value.get("results") or []
        return [item for item in results if isinstance(item, dict)]

    def get_work(self, openalex_id: str) -> dict[str, Any]:
        return self._get(
            f"https://api.openalex.org/works/{quote(_openalex_id(openalex_id))}",
            {"select": _OPENALEX_FIELDS},
        )

    def get_doi(self, doi: str) -> dict[str, Any]:
        normalized = _normalize_doi(doi)
        if not normalized:
            raise ValueError("DOI is required")
        identifier = quote(f"https://doi.org/{normalized}", safe="")
        return self._get(
            f"https://api.openalex.org/works/{identifier}",
            {"select": _OPENALEX_FIELDS},
        )


_OPENALEX_FIELDS = ",".join(
    (
        "id",
        "doi",
        "ids",
        "title",
        "publication_year",
        "authorships",
        "primary_location",
        "best_oa_location",
        "open_access",
        "referenced_works",
        "abstract_inverted_index",
        "type",
        "language",
    )
)


def _requests_fetch(url: str) -> tuple[bytes, str, str]:
    import requests

    response = requests.get(
        url,
        timeout=60,
        allow_redirects=True,
        headers={"User-Agent": "bipu-literature-review/0.1"},
    )
    response.raise_for_status()
    return response.content, response.headers.get("content-type", ""), response.url


def _parse_claim(value: str) -> dict[str, str]:
    if "=" not in value:
        raise argparse.ArgumentTypeError("claim must be CLAIM_ID=TEXT")
    claim_id, text = value.split("=", 1)
    if not claim_id.strip() or not text.strip():
        raise argparse.ArgumentTypeError("claim must have a non-empty id and text")
    return {"claim_id": claim_id.strip(), "text": text.strip()}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Reproducible literature review workbench")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init = subparsers.add_parser("init", help="create a review contract")
    init.add_argument("--root", type=Path, default=Path("literature"))
    init.add_argument("--slug", required=True)
    init.add_argument("--title", required=True)
    init.add_argument("--problem", required=True)
    init.add_argument("--claim", action="append", type=_parse_claim, required=True)
    init.add_argument("--query", action="append", required=True)
    init.add_argument("--depth", type=int, default=1)
    init.add_argument("--max-records", type=int, default=500)
    init.add_argument("--per-query", type=int, default=25)

    for command in ("discover", "expand", "download"):
        item = subparsers.add_parser(command)
        item.add_argument("--review", type=Path, required=True)
        item.add_argument("--execute", action="store_true")
        item.add_argument("--email")
    seeds = subparsers.add_parser("ingest-seeds", help="ingest exact DOI seeds")
    seeds.add_argument("--review", type=Path, required=True)
    seeds.add_argument("--design", type=Path, required=True)
    seeds.add_argument("--execute", action="store_true")
    seeds.add_argument("--email")
    gap = subparsers.add_parser(
        "complexity-search", help="run an isolated plan-driven complexity-gap search"
    )
    gap.add_argument("--review", type=Path, required=True)
    gap.add_argument("--plan", type=Path, required=True)
    gap.add_argument("--execute", action="store_true")
    gap.add_argument("--email")
    targets = subparsers.add_parser(
        "download-targets", help="retrieve only full texts named in an authorized plan"
    )
    targets.add_argument("--review", type=Path, required=True)
    targets.add_argument("--plan", type=Path, required=True)
    targets.add_argument("--execute", action="store_true")
    for command in ("extract", "validate", "report"):
        item = subparsers.add_parser(command)
        item.add_argument("--review", type=Path, required=True)
    attach = subparsers.add_parser("attach", help="attach a user-authorized local PDF")
    attach.add_argument("--review", type=Path, required=True)
    attach.add_argument("--record-id", required=True)
    attach.add_argument("--pdf", type=Path, required=True)
    attach.add_argument("--license", required=True)

    args = parser.parse_args(argv)
    if args.command == "init":
        contract = build_review_contract(
            slug=args.slug,
            title=args.title,
            problem=args.problem,
            claims=args.claim,
            queries=args.query,
            expansion_depth=args.depth,
            max_records=args.max_records,
            max_results_per_query=args.per_query,
        )
        output = {"review_dir": str(initialize_review(args.root, contract))}
    elif args.command == "discover":
        output = discover(
            args.review, OpenAlexClient(email=args.email), execute=args.execute
        )
    elif args.command == "ingest-seeds":
        output = ingest_exact_seeds(
            args.review,
            OpenAlexClient(email=args.email),
            design_path=args.design,
            execute=args.execute,
        )
    elif args.command == "complexity-search":
        output = search_complexity_gap(
            args.review,
            OpenAlexClient(email=args.email),
            plan_path=args.plan,
            execute=args.execute,
        )
    elif args.command == "expand":
        output = expand_references(
            args.review, OpenAlexClient(email=args.email), execute=args.execute
        )
    elif args.command == "download":
        output = download_open_access(
            args.review, _requests_fetch, execute=args.execute
        )
    elif args.command == "download-targets":
        output = download_targets(
            args.review,
            _requests_fetch,
            plan_path=args.plan,
            execute=args.execute,
        )
    elif args.command == "extract":
        output = extract_downloads(args.review)
    elif args.command == "attach":
        output = attach_local_pdf(
            args.review,
            record_id=args.record_id,
            source=args.pdf,
            license_name=args.license,
        )
    elif args.command == "validate":
        output = validate_review(args.review)
    else:
        output = render_report(args.review)
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0 if output.get("valid", True) else 1


if __name__ == "__main__":
    raise SystemExit(main())
