from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from community_archive_prediction.evaluability_audit import evaluate_evaluability, run_audit
from community_archive_prediction.experiment import (
    INTERACTIONS_NAME,
    TWEETS_NAME,
    WINDOW_CONTRACT_NAME,
)


UTC = timezone.utc


def iso(day: int, hour: int) -> str:
    return datetime(2026, 1, day, hour, tzinfo=UTC).isoformat()


def synthetic_archive() -> tuple[list[dict], list[dict]]:
    tweets: list[dict] = []
    interactions: list[dict] = []

    for day in range(1, 6):
        tweet_id = f"train-{day}"
        tweets.append({"tweet_id": tweet_id, "created_at": iso(day, 10), "full_text": "training post"})
        interactions.append(
            {
                "created_at": iso(day, 11),
                "username": "alice",
                "reply_to_tweet_id": tweet_id,
                "quoted_tweet_id": None,
                "interaction_types": ["reply"],
            }
        )

    for day in range(6, 9):
        reply_id = f"reply-{day}"
        quote_id = f"quote-{day}"
        tweets.extend(
            [
                {"tweet_id": reply_id, "created_at": iso(day, 10), "full_text": "reply candidate"},
                {"tweet_id": quote_id, "created_at": iso(day, 12), "full_text": "quote candidate"},
            ]
        )
        interactions.extend(
            [
                {
                    "created_at": iso(day, 11),
                    "username": "alice",
                    "reply_to_tweet_id": reply_id,
                    "quoted_tweet_id": None,
                    "interaction_types": ["reply", "mention"],
                },
                {
                    "created_at": iso(day, 13),
                    "username": f"new-{day}",
                    "reply_to_tweet_id": None,
                    "quoted_tweet_id": quote_id,
                    "interaction_types": ["quote", "mention"],
                },
                {
                    "created_at": iso(day, 14),
                    "username": f"mention-{day}",
                    "reply_to_tweet_id": None,
                    "quoted_tweet_id": None,
                    "interaction_types": ["mention"],
                },
            ]
        )
    return tweets, interactions


def test_audit_separates_label_support_from_feature_availability() -> None:
    tweets, interactions = synthetic_archive()
    receipt = evaluate_evaluability(
        tweets=tweets,
        interactions=interactions,
        source_end=datetime(2026, 1, 10, tzinfo=UTC),
        relationship_snapshot_at=datetime(2026, 1, 11, tzinfo=UTC),
        holdout_count=3,
        label_horizon=timedelta(hours=24),
        minimum_class_support=2,
    )

    assert receipt["schema_version"] == "community-archive-evaluability/v0.1"
    assert [fold["holdout_day"] for fold in receipt["folds"]] == [
        "2026-01-06",
        "2026-01-07",
        "2026-01-08",
    ]
    assert receipt["support"]["H-CA-03"] == {
        "new_account_events": 3,
        "posts_with_new_account_event": 3,
        "seen_account_events": 3,
        "all_account_events": 6,
    }
    assert receipt["support"]["H-CA-04"] == {
        "linked_reply_events": 3,
        "linked_quote_events": 3,
        "ambiguous_linked_events": 0,
        "excluded_unlinked_mentions": 3,
    }
    assert receipt["targets"]["H-CA-03"]["label_status"] == "evaluated"
    assert receipt["targets"]["H-CA-03"]["feature_status"] == "not_evaluatable_yet"
    assert receipt["targets"]["H-CA-03"]["class_support"] == {
        "new_account_post": 3,
        "no_new_account_post": 3,
    }
    assert receipt["targets"]["H-CA-03"]["blockers"] == [
        "relationship_snapshot_postdates_predictions"
    ]
    assert receipt["targets"]["H-CA-04"]["label_status"] == "evaluated"
    assert receipt["targets"]["H-CA-04"]["feature_status"] == "not_evaluatable_yet"
    assert receipt["targets"]["H-CA-04"]["class_support"] == {"reply": 3, "quote": 3}
    assert receipt["data_contract"]["excluded_labels"] == ["mention_without_target_post_linkage"]
    assert receipt["privacy"]["subject_handle_in_source_logical_path"] is True
    assert receipt["privacy"]["interaction_account_identities_emitted"] is False

    serialized = json.dumps(receipt)
    for forbidden in ("alice", "new-", "mention-", "reply-", "quote-", "T10:", "full_text", "username"):
        assert forbidden not in serialized


def test_audit_runner_hashes_sources_and_writes_receipt(tmp_path: Path) -> None:
    tweets, interactions = synthetic_archive()
    source = tmp_path / "source"
    data = source / "data"
    reports = source / "reports"
    data.mkdir(parents=True)
    reports.mkdir(parents=True)

    (data / TWEETS_NAME).write_text(
        "".join(json.dumps(row) + "\n" for row in tweets)
    )
    (data / INTERACTIONS_NAME).write_text(
        "".join(json.dumps(row) + "\n" for row in interactions)
    )
    (reports / WINDOW_CONTRACT_NAME).write_text(
        json.dumps({"window": {"end_exclusive": "2026-01-10"}})
    )
    snapshot = source / "data/relationship_graph_2026-01-11/relationship_snapshot.json"
    snapshot.parent.mkdir(parents=True)
    snapshot.write_text(json.dumps({"observed_at": "2026-01-11T00:00:00+00:00"}))

    output = tmp_path / "audit.json"
    receipt = run_audit(
        source_root=source,
        output=output,
        relationship_snapshot_at=datetime(2026, 1, 11, tzinfo=UTC),
        minimum_class_support=2,
    )

    assert output.exists()
    assert json.loads(output.read_text()) == receipt
    assert receipt["provenance"]["sources"]["tweets"]["rows"] == len(tweets)
    assert len(receipt["provenance"]["sources"]["tweets"]["sha256"]) == 64
    assert str(tmp_path) not in json.dumps(receipt)
