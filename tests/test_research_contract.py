from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
HYPOTHESES_PATH = ROOT / "evidence" / "community-archive-hypotheses-v0.1.json"


def load_hypotheses() -> dict[str, Any]:
    return json.loads(HYPOTHESES_PATH.read_text())


def test_community_archive_hypotheses_are_frozen_and_falsifiable() -> None:
    ledger = load_hypotheses()
    hypotheses = ledger["hypotheses"]

    assert ledger["schema_version"] == "community-archive-network-hypotheses/v0.1"
    assert [row["id"] for row in hypotheses] == [f"H-CA-{index:02d}" for index in range(1, 9)]
    assert len({row["id"] for row in hypotheses}) == len(hypotheses)
    assert all(row["target"] and row["claim"] and row["falsifier"] for row in hypotheses)
    assert {row["prior_status"] for row in hypotheses} == {
        "weak_positive",
        "preliminary_negative",
        "untested",
        "not_evaluatable_yet",
    }


def test_community_archive_benchmark_is_chronological_and_baselined() -> None:
    contract = load_hypotheses()["benchmark_contract"]

    assert contract["split"] == "rolling chronological origin with at least three held-out windows"
    assert contract["feature_cutoff"] == "strictly before prediction timestamp"
    assert contract["binary_primary_metric"] == "average_precision"
    assert contract["required_baselines"] == [
        "global_positive_rate",
        "account_frequency",
        "content_only",
        "topology_only",
        "recurrence_only",
        "combined",
    ]
    assert contract["negative_controls"] == [
        "shuffled_event_times",
        "shuffled_account_labels_within_window",
    ]
    assert contract["insufficient_status"] == "not_evaluatable_yet"


def test_research_goal_blocks_layer_eight_until_receipt_exists() -> None:
    goal = (ROOT / "RESEARCH_GOAL.md").read_text()

    assert "no Layer 08" in goal
    assert "at least three chronological held-out windows" in goal
    assert "A clean null or baseline victory satisfies the research goal" in goal
    assert "Raw social data remains in its source repository" in goal
    assert "evidence/runs/community-archive-prediction-v0.1.json" in goal
    assert "v0.1 executed" in goal
    assert "goal remains locked" in goal

    ledger = load_hypotheses()
    assert ledger["executed_receipt"] == "evidence/runs/community-archive-prediction-v0.1.json"
    assert ledger["evaluability_audit_receipt"] == "evidence/runs/community-archive-evaluability-v0.1.json"
    assert ledger["hypotheses"][0]["v0_1_outcome"] == "not_supported"
    assert ledger["hypotheses"][1]["v0_1_outcome"] == "unresolved_underpowered"
    assert ledger["hypotheses"][2]["v0_1_outcome"] == "not_evaluatable_yet"
    assert ledger["hypotheses"][3]["v0_1_outcome"] == "not_evaluatable_yet"
    assert "25 new-account posts" in goal
    assert "3 linked quotes" in goal


def test_theorem_ledger_separates_claim_classes_and_denies_pnp_result() -> None:
    ledger = (ROOT / "evidence" / "theorem-ledger-v0.7.md").read_text()

    for claim_class in (
        "Established",
        "Finite corollary",
        "Implementation invariant",
        "Conjectural bridge",
    ):
        assert claim_class in ledger
    assert "It does not establish:" in ledger
    assert "`P = NP` or `P != NP`" in ledger
