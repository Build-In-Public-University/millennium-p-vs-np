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
