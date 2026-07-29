from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from community_archive_prediction.prospective import run_prospective


UTC = timezone.utc


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows))


def _stamp(day: int, hour: int) -> str:
    return datetime(2026, 1, day, hour, tzinfo=UTC).isoformat()


def _fixture(tmp_path: Path, minimum: int = 1) -> tuple[Path, Path]:
    source = tmp_path / "source"
    data = source / "data"
    graph = data / "relationship_graph_2025-12-31"
    graph.mkdir(parents=True)

    nodes = [
        {"handle": "leo_guinan", "sources": ["account"]},
        {"handle": "alice", "sources": ["follower_snapshot", "following_snapshot"]},
        {"handle": "new6", "sources": ["follower_snapshot"]},
        {"handle": "new7", "sources": ["following_snapshot"]},
        {"handle": "new8", "sources": []},
    ]
    _write_jsonl(graph / "relationship_nodes.jsonl", nodes)
    _write_jsonl(graph / "relationship_edges.jsonl", [])
    (graph / "relationship_snapshot.json").write_text(
        json.dumps({"observed_at": "2025-12-31", "handle": "leo_guinan"}) + "\n"
    )

    tweets: list[dict] = []
    interactions: list[dict] = []
    for day in range(1, 9):
        familiar = f"post-{day}-familiar"
        novel = f"post-{day}-novel"
        quiet = f"post-{day}-quiet"
        tweets.extend(
            [
                {"tweet_id": familiar, "created_at": _stamp(day, 9), "full_text": "familiar systems note"},
                {"tweet_id": novel, "created_at": _stamp(day, 11), "full_text": "novel boundary question"},
                {"tweet_id": quiet, "created_at": _stamp(day, 14), "full_text": "quiet status line"},
            ]
        )
        interactions.extend(
            [
                {
                    "tweet_id": f"reply-{day}",
                    "created_at": _stamp(day, 10),
                    "username": "alice",
                    "reply_to_tweet_id": familiar,
                    "quoted_tweet_id": None,
                    "interaction_types": ["reply"],
                },
                {
                    "tweet_id": f"quote-{day}",
                    "created_at": _stamp(day, 12),
                    "username": "alice",
                    "reply_to_tweet_id": None,
                    "quoted_tweet_id": novel,
                    "interaction_types": ["quote", "mention"],
                },
            ]
        )
        if day >= 6:
            interactions.append(
                {
                    "tweet_id": f"new-reply-{day}",
                    "created_at": _stamp(day, 13),
                    "username": f"new{day}",
                    "reply_to_tweet_id": novel,
                    "quoted_tweet_id": None,
                    "interaction_types": ["reply", "mention"],
                }
            )

    tweets_name = "leo_guinan_tweets_2026-01-01_2026-01-08.jsonl"
    interactions_name = "interactions_with_leo_2026-01-01_2026-01-09.jsonl"
    tweets_path = data / tweets_name
    interactions_path = data / interactions_name
    _write_jsonl(tweets_path, tweets)
    _write_jsonl(interactions_path, interactions)

    extraction = {
        "schema_version": "community-archive-acquisition/v0.2",
        "window": {
            "authored_start_inclusive": "2026-01-01T00:00:00+00:00",
            "authored_end_exclusive": "2026-01-09T00:00:00+00:00",
            "interaction_end_exclusive": "2026-01-10T00:00:00+00:00",
        },
        "sources": {
            "authored_posts": {
                "logical_path": f"data/{tweets_name}",
                "sha256": _sha(tweets_path),
                "rows": len(tweets),
            },
            "interactions": {
                "logical_path": f"data/{interactions_name}",
                "sha256": _sha(interactions_path),
                "rows": len(interactions),
            },
        },
    }
    (data / "extraction_receipt_2026-01-01_2026-01-09.json").write_text(
        json.dumps(extraction, indent=2, sort_keys=True) + "\n"
    )

    contract = {
        "schema_version": "community-archive-next-window/v0.2",
        "status": "frozen_before_acquisition",
        "subject": "@leo_guinan",
        "topology_snapshot": {
            "observed_at": "2025-12-31",
            "logical_path": "data/relationship_graph_2025-12-31/relationship_snapshot.json",
            "sha256": _sha(graph / "relationship_snapshot.json"),
            "feature_sources": {
                "nodes": {
                    "logical_path": "data/relationship_graph_2025-12-31/relationship_nodes.jsonl",
                    "sha256": _sha(graph / "relationship_nodes.jsonl"),
                },
                "edges": {
                    "logical_path": "data/relationship_graph_2025-12-31/relationship_edges.jsonl",
                    "sha256": _sha(graph / "relationship_edges.jsonl"),
                },
            },
        },
        "collection_window": {
            "authored_start_inclusive": "2026-01-01T00:00:00Z",
            "authored_end_exclusive": "2026-01-09T00:00:00Z",
            "interaction_end_exclusive": "2026-01-10T00:00:00Z",
            "acquire_not_before": "2026-01-10T00:00:00Z",
        },
        "holdout_days": ["2026-01-06", "2026-01-07", "2026-01-08"],
        "label_horizon_hours": 24,
        "minimum_class_support": minimum,
        "adaptive_extension_allowed": False,
        "underpowered_action": "publish_not_evaluatable_without_extension",
        "targets": {
            "H-CA-01": {
                "role": "replication",
                "control_upgrade": "within_window_permutation_distribution",
                "required_support": {
                    "direct_interaction_post": minimum,
                    "no_direct_interaction_post": minimum,
                },
            },
            "H-CA-02": {"required_support": {"seen_account_events": minimum}},
            "H-CA-03": {
                "prediction_unit": "authored_post_at_publication",
                "required_support": {"new_account_post": minimum, "no_new_account_post": minimum},
                "required_features": ["pre_window_cross_population_partition"],
            },
            "H-CA-04": {
                "prediction_unit": "linked_account_post_event_conditional_on_interaction",
                "required_support": {"reply": minimum, "quote": minimum},
                "required_features": ["pre_window_relationship_partition"],
            },
        },
        "privacy_boundary": {
            "benchmark_repository_excludes": ["raw text", "post IDs", "interacting-account identities"]
        },
        "research_lock": {"layer_08_allowed": False},
    }
    contract_path = tmp_path / "contract.json"
    contract_path.write_text(json.dumps(contract, indent=2, sort_keys=True) + "\n")
    return source, contract_path


def test_prospective_runner_executes_only_eligible_targets_and_is_deterministic(tmp_path: Path) -> None:
    source, contract = _fixture(tmp_path)
    evaluated_at = datetime(2026, 1, 10, 1, tzinfo=UTC)

    first = run_prospective(source, contract, tmp_path / "first.json", evaluated_at=evaluated_at)
    second = run_prospective(source, contract, tmp_path / "second.json", evaluated_at=evaluated_at)

    assert first == second
    assert first["schema_version"] == "community-archive-prediction/v0.2"
    assert first["status"] == "evaluated"
    assert first["preflight"]["status"] == "passed"
    assert first["evaluation_contract"]["H-CA-04"] == {
        "prediction_unit": "linked_account_post_event_conditional_on_interaction",
        "label": "reply_versus_quote",
        "limitation": "conditional classification; does not predict whether the account interacts",
    }
    assert [fold["holdout_day"] for fold in first["folds"]] == [
        "2026-01-06",
        "2026-01-07",
        "2026-01-08",
    ]
    assert all(first["targets"][target]["status"] == "evaluated" for target in first["targets"])
    controls = first["targets"]["H-CA-01"]["negative_control"]
    assert len(controls) == 3
    assert all(row["permutation"] == "all_non_identity_cyclic_label_rotations" for row in controls)
    assert all(row["permutation_count"] == 2 for row in controls)
    assert set(first["targets"]["H-CA-03"]["models"]) == {
        "global_new_account_rate",
        "content_only",
        "topology_context_only",
        "combined",
    }
    assert set(first["targets"]["H-CA-04"]["models"]) == {
        "global_quote_rate",
        "content_only",
        "topology_only",
        "prior_type_only",
        "combined",
    }
    serialized = json.dumps(first)
    for forbidden in ("alice", "new6", "post-", "novel boundary", "username", "full_text"):
        assert forbidden not in serialized


def test_underpowered_targets_emit_no_model_metrics(tmp_path: Path) -> None:
    source, contract = _fixture(tmp_path, minimum=4)

    receipt = run_prospective(
        source,
        contract,
        tmp_path / "underpowered.json",
        evaluated_at=datetime(2026, 1, 10, 1, tzinfo=UTC),
    )

    assert receipt["preflight"]["status"] == "passed"
    assert receipt["targets"]["H-CA-03"]["status"] == "not_evaluatable_yet"
    assert receipt["targets"]["H-CA-04"]["status"] == "not_evaluatable_yet"
    assert "models" not in receipt["targets"]["H-CA-03"]
    assert "models" not in receipt["targets"]["H-CA-04"]


def test_preflight_hash_failure_stops_every_model(tmp_path: Path) -> None:
    source, contract = _fixture(tmp_path)
    nodes = source / "data/relationship_graph_2025-12-31/relationship_nodes.jsonl"
    nodes.write_text(nodes.read_text() + json.dumps({"handle": "late", "sources": []}) + "\n")

    receipt = run_prospective(
        source,
        contract,
        tmp_path / "blocked.json",
        evaluated_at=datetime(2026, 1, 10, 1, tzinfo=UTC),
    )

    assert receipt["status"] == "preflight_failed"
    assert receipt["preflight"]["blockers"] == ["topology_nodes_sha256_mismatch"]
    assert all(target["status"] == "not_run" for target in receipt["targets"].values())
    assert all("models" not in target for target in receipt["targets"].values())
