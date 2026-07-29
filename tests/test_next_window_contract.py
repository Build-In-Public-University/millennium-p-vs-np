from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "evidence/community-archive-next-window-v0.2.json"


def test_next_window_is_prospective_frozen_and_non_adaptive() -> None:
    contract = json.loads(CONTRACT.read_text())

    assert contract["schema_version"] == "community-archive-next-window/v0.2"
    assert contract["status"] == "frozen_before_acquisition"
    assert contract["topology_snapshot"]["observed_at"] == "2026-07-29"
    assert contract["topology_snapshot"]["sha256"] == (
        "4dc4a6d8d5097c9f27b74cad9dd98bf3a485a3cf91e4ff7a8ab5a7c473f2a2c4"
    )
    assert contract["topology_snapshot"]["feature_sources"] == {
        "nodes": {
            "logical_path": "data/relationship_graph_2026-07-29/relationship_nodes.jsonl",
            "sha256": "30d02e020314064ed86a710829242e76ff87c78eee92b86a1aef6f48b3af3d6d",
        },
        "edges": {
            "logical_path": "data/relationship_graph_2026-07-29/relationship_edges.jsonl",
            "sha256": "75a288468a289564f7fe2e19df9ceb40aaef9d82ed948d04319f57ed70a7264d",
        },
    }
    assert contract["collection_window"] == {
        "authored_start_inclusive": "2026-07-30T00:00:00Z",
        "authored_end_exclusive": "2026-08-14T00:00:00Z",
        "interaction_end_exclusive": "2026-08-15T00:00:00Z",
        "acquire_not_before": "2026-08-15T00:00:00Z",
    }
    assert contract["holdout_days"] == ["2026-08-11", "2026-08-12", "2026-08-13"]
    assert contract["label_horizon_hours"] == 24
    assert contract["minimum_class_support"] == 30
    assert contract["adaptive_extension_allowed"] is False
    assert contract["underpowered_action"] == "publish_not_evaluatable_without_extension"
    assert contract["amendments"] == [
        {
            "amended_at": "2026-07-29T21:27:17Z",
            "reason": "Add omitted hashes for the pre-window account-level topology feature sources.",
            "scope": "provenance_only",
            "unchanged": ["hypotheses", "dates", "holdouts", "labels", "thresholds"],
        },
        {
            "amended_at": "2026-07-29T21:56:38Z",
            "reason": "Make the existing class-support semantics and prediction units machine-readable.",
            "scope": "contract_clarification",
            "unchanged": ["hypotheses", "dates", "holdouts", "labels", "threshold_values"],
        },
    ]
    assert contract["targets"]["H-CA-01"]["required_support"] == {
        "direct_interaction_post": 30,
        "no_direct_interaction_post": 30,
    }
    assert contract["targets"]["H-CA-03"]["prediction_unit"] == "authored_post_at_publication"
    assert contract["targets"]["H-CA-04"]["prediction_unit"] == (
        "linked_account_post_event_conditional_on_interaction"
    )


def test_next_window_requires_approval_and_preserves_research_lock() -> None:
    contract = json.loads(CONTRACT.read_text())

    assert contract["external_acquisition"]["approved"] is False
    assert contract["external_acquisition"]["mechanism"] == "Community Archive REST enriched_tweets"
    assert contract["external_acquisition"]["raw_output_repository"] == "leo-twitter-audience-model"
    assert contract["external_acquisition"]["current_extractor_status"] == "ready_dry_run_verified"
    assert contract["external_acquisition"]["current_extractor_blockers"] == []
    assert contract["external_acquisition"]["default_mode"] == "dry_run_zero_network_calls"
    assert contract["research_lock"]["layer_08_allowed"] is False
    assert contract["research_lock"]["ontology_changes_allowed"] is False
    assert contract["research_lock"]["threshold_changes_allowed"] is False
