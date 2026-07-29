from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from community_archive_prediction import benchmark
from community_archive_prediction.benchmark import (
    build_examples,
    complete_holdout_days,
    evaluate_benchmark,
    rolling_split,
)


UTC = timezone.utc


def stamp(day: int, hour: int = 12) -> str:
    return datetime(2026, 1, day, hour, tzinfo=UTC).isoformat()


def tweet(tweet_id: str, day: int, text: str, hour: int = 12) -> dict[str, object]:
    return {
        "tweet_id": tweet_id,
        "created_at": stamp(day, hour),
        "full_text": text,
    }


def interaction(
    interaction_id: str,
    target_id: str,
    day: int,
    hour: int,
    account: str,
) -> dict[str, object]:
    return {
        "tweet_id": interaction_id,
        "created_at": stamp(day, hour),
        "reply_to_tweet_id": target_id,
        "quoted_tweet_id": None,
        "username": account,
        "interaction_types": ["reply"],
    }


def synthetic_archive() -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    tweets: list[dict[str, object]] = []
    interactions: list[dict[str, object]] = []
    for day in range(1, 9):
        for index in range(4):
            is_positive = index % 2 == 0
            post_id = f"post-{day}-{index}"
            text = "specific signal question" if is_positive else "quiet routine note"
            tweets.append(tweet(post_id, day, text))
            if is_positive:
                account = "alice" if index == 0 else "bob"
                interactions.append(interaction(f"event-{day}-{index}", post_id, day, 13, account))
    return tweets, interactions


def test_complete_holdouts_require_a_full_label_horizon() -> None:
    tweets = [tweet(f"post-{day}", day, "note") for day in range(1, 9)]

    days = complete_holdout_days(
        tweets,
        source_end=datetime(2026, 1, 10, tzinfo=UTC),
        label_horizon=timedelta(hours=24),
        count=3,
    )

    assert [day.isoformat() for day in days] == ["2026-01-06", "2026-01-07", "2026-01-08"]


def test_build_examples_ignores_prepublication_and_late_events() -> None:
    tweets = [tweet("target", 3, "question")]
    interactions = [
        interaction("early", "target", 3, 11, "early-account"),
        interaction("valid", "target", 3, 13, "valid-account"),
        interaction("late", "target", 4, 13, "late-account"),
    ]

    examples = build_examples(tweets, interactions, timedelta(hours=24))

    assert len(examples) == 1
    assert examples[0].has_direct_interaction is True
    assert examples[0].direct_accounts == ("valid-account",)
    assert len(examples[0].interaction_events) == 1


def test_rolling_split_excludes_training_rows_with_unmatured_labels() -> None:
    tweets = [
        tweet("mature", 2, "old", hour=0),
        tweet("unmatured", 3, "recent", hour=12),
        tweet("test", 4, "held out", hour=1),
    ]
    examples = build_examples(tweets, [], timedelta(hours=24))

    train, test = rolling_split(
        examples,
        holdout_day=datetime(2026, 1, 4, tzinfo=UTC).date(),
        label_horizon=timedelta(hours=24),
    )

    assert [row.post_id for row in train] == ["mature"]
    assert [row.post_id for row in test] == ["test"]


def test_benchmark_emits_three_identity_free_chronological_folds() -> None:
    tweets, interactions = synthetic_archive()

    receipt = evaluate_benchmark(
        tweets=tweets,
        interactions=interactions,
        source_end=datetime(2026, 1, 10, tzinfo=UTC),
        holdout_count=3,
        label_horizon=timedelta(hours=24),
        minimum_positive_events=1,
    )

    assert receipt["schema_version"] == "community-archive-prediction/v0.1"
    assert receipt["data_contract"]["label_scope"] == "reply_or_quote_targeting_authored_post"
    assert receipt["data_contract"]["excluded_labels"] == ["mention_without_target_post_linkage"]
    assert [fold["holdout_day"] for fold in receipt["folds"]] == [
        "2026-01-06",
        "2026-01-07",
        "2026-01-08",
    ]
    assert receipt["targets"]["H-CA-01"]["status"] == "evaluated"
    assert receipt["targets"]["H-CA-02"]["status"] == "evaluated"
    assert receipt["targets"]["H-CA-01"]["outcome"] in {"provisional_support", "not_supported"}
    assert receipt["targets"]["H-CA-02"]["outcome"] in {"provisional_support", "not_supported"}
    assert set(receipt["summary"]["account_ranking_models"]) == {
        "account_frequency",
        "content_only",
        "recurrence_only",
        "combined",
        "topology_only",
    }
    assert set(receipt["folds"][0]["direct_interaction_models"]) == {
        "global_positive_rate",
        "content_only",
        "recurrence_only",
        "combined",
        "topology_only",
    }
    assert receipt["folds"][0]["direct_interaction_models"]["topology_only"]["status"] == "not_evaluatable_yet"
    assert set(receipt["negative_controls"]) == {
        "shuffled_event_times",
        "shuffled_account_labels_within_window",
    }
    serialized = json.dumps(receipt)
    assert "alice" not in serialized
    assert "bob" not in serialized
    assert "post-" not in serialized
    assert "T12:00" not in serialized
    assert "specific signal question" not in serialized


def test_benchmark_marks_underpowered_targets_not_evaluatable() -> None:
    tweets, interactions = synthetic_archive()

    receipt = evaluate_benchmark(
        tweets=tweets,
        interactions=interactions,
        source_end=datetime(2026, 1, 10, tzinfo=UTC),
        holdout_count=3,
        label_horizon=timedelta(hours=24),
        minimum_positive_events=100,
    )

    assert receipt["targets"]["H-CA-01"]["status"] == "not_evaluatable_yet"
    assert receipt["targets"]["H-CA-02"]["status"] == "not_evaluatable_yet"
    assert receipt["targets"]["H-CA-01"]["reason"] == "positive_support_below_100"


def test_benchmark_skips_inactive_target_models_and_can_emit_permutation_distribution() -> None:
    tweets, interactions = synthetic_archive()

    receipt = evaluate_benchmark(
        tweets=tweets,
        interactions=interactions,
        source_end=datetime(2026, 1, 10, tzinfo=UTC),
        holdout_count=3,
        label_horizon=timedelta(hours=24),
        minimum_positive_events=1,
        active_targets={"H-CA-01"},
        time_control_mode="all_cyclic_permutations",
    )

    assert receipt["targets"]["H-CA-01"]["status"] == "evaluated"
    assert receipt["targets"]["H-CA-02"]["status"] == "not_evaluatable_yet"
    assert receipt["summary"]["account_ranking_models"] == {}
    assert receipt["negative_controls"]["shuffled_account_labels_within_window"] == []
    assert all(fold["account_ranking"]["models"] == {} for fold in receipt["folds"])
    controls = receipt["negative_controls"]["shuffled_event_times"]
    assert all(row["permutation"] == "all_non_identity_cyclic_label_rotations" for row in controls)
    assert all(row["permutation_count"] == 3 for row in controls)


def test_h1_resolution_rejects_signal_when_time_control_is_as_good() -> None:
    folds = []
    controls = []
    for observed, baseline, shuffled in ((0.20, 0.10, 0.30), (0.18, 0.12, 0.22), (0.15, 0.10, 0.19)):
        folds.append(
            {
                "direct_interaction_models": {
                    "content_only": {"metrics": {"average_precision": observed}},
                    "global_positive_rate": {"metrics": {"average_precision": baseline}},
                }
            }
        )
        controls.append({"metrics": {"average_precision": shuffled}})

    resolution = benchmark.resolve_direct_interaction_hypothesis(folds, controls)

    assert resolution["outcome"] == "not_supported"
    assert resolution["positive_delta_windows"] == 3
    assert resolution["time_control_at_least_observed_windows"] == 3
    assert resolution["reason"] == "shuffled_time_control_matched_or_exceeded_observed_in_3_windows"
