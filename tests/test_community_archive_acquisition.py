from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from community_archive_prediction.acquisition import (
    acquire_window,
    assert_horizon_mature,
    build_query_plan,
)


UTC = timezone.utc
START = datetime(2026, 7, 30, tzinfo=UTC)
AUTHORED_END = datetime(2026, 8, 14, tzinfo=UTC)
INTERACTION_END = datetime(2026, 8, 15, tzinfo=UTC)


def test_execution_refuses_an_immature_interaction_horizon() -> None:
    with pytest.raises(RuntimeError, match="refusing immature acquisition"):
        assert_horizon_mature(
            interaction_end=INTERACTION_END,
            now=datetime(2026, 8, 14, 23, 59, tzinfo=UTC),
        )

    assert_horizon_mature(
        interaction_end=INTERACTION_END,
        now=datetime(2026, 8, 15, tzinfo=UTC),
    )


def test_query_plan_is_parameterized_dry_run_safe_and_horizon_complete() -> None:
    plan = build_query_plan(
        handle="leo_guinan",
        authored_start=START,
        authored_end=AUTHORED_END,
        interaction_end=INTERACTION_END,
    )

    assert plan["mode"] == "dry_run"
    assert plan["network_calls"] == 0
    assert plan["authored_output"] == "leo_guinan_tweets_2026-07-30_2026-08-13.jsonl"
    assert plan["interactions_output"] == "interactions_with_leo_2026-07-30_2026-08-14.jsonl"
    assert plan["queries"]["authored"]["created_at"] == "gte.2026-07-30T00:00:00Z"
    assert plan["queries"]["authored"]["and"] == "(created_at.lt.2026-08-14T00:00:00Z)"
    assert plan["queries"]["replies"]["and"] == "(created_at.lt.2026-08-15T00:00:00Z)"
    assert plan["queries"]["mentions"]["and"] == "(created_at.lt.2026-08-15T00:00:00Z)"
    assert "apikey" not in json.dumps(plan).lower()
    assert "authorization" not in json.dumps(plan).lower()


def test_acquisition_deduplicates_interactions_and_writes_hashed_source_receipt(
    tmp_path: Path,
) -> None:
    calls: list[tuple[str, dict[str, str]]] = []
    authored = [
        {
            "tweet_id": "post-1",
            "username": "leo_guinan",
            "created_at": "2026-08-13T10:00:00Z",
            "full_text": "authored",
        }
    ]
    reply = {
        "tweet_id": "interaction-1",
        "username": "account-a",
        "created_at": "2026-08-14T09:00:00Z",
        "full_text": "@leo_guinan reply",
        "reply_to_tweet_id": "post-1",
        "reply_to_username": "leo_guinan",
        "quoted_tweet_id": None,
    }
    quote = {
        "tweet_id": "interaction-2",
        "username": "account-b",
        "created_at": "2026-08-14T08:00:00Z",
        "full_text": "quote",
        "reply_to_tweet_id": None,
        "reply_to_username": None,
        "quoted_tweet_id": "post-1",
    }
    self_reply = {
        **reply,
        "tweet_id": "self-1",
        "username": "leo_guinan",
    }

    def fake_fetch(kind: str, params: dict[str, str]) -> list[dict[str, Any]]:
        calls.append((kind, params))
        return {
            "authored": authored,
            "replies": [reply, self_reply],
            "mentions": [reply],
            "quotes": [quote],
        }[kind]

    receipt = acquire_window(
        source_root=tmp_path,
        handle="leo_guinan",
        authored_start=START,
        authored_end=AUTHORED_END,
        interaction_end=INTERACTION_END,
        fetch_pages=fake_fetch,
    )

    tweets_path = tmp_path / "data/leo_guinan_tweets_2026-07-30_2026-08-13.jsonl"
    interactions_path = tmp_path / "data/interactions_with_leo_2026-07-30_2026-08-14.jsonl"
    receipt_path = tmp_path / "data/extraction_receipt_2026-07-30_2026-08-14.json"
    assert tweets_path.exists()
    assert interactions_path.exists()
    assert receipt_path.exists()

    interactions = [json.loads(line) for line in interactions_path.read_text().splitlines()]
    assert [row["tweet_id"] for row in interactions] == ["interaction-2", "interaction-1"]
    assert interactions[0]["interaction_types"] == ["quote"]
    assert interactions[1]["interaction_types"] == ["mention", "reply"]
    assert {kind for kind, _ in calls} == {"authored", "replies", "mentions", "quotes"}

    assert receipt["window"]["interaction_end_exclusive"] == "2026-08-15T00:00:00Z"
    assert receipt["rows"] == {"authored": 1, "interactions": 2}
    assert receipt["sources"]["authored"]["sha256"] == hashlib.sha256(
        tweets_path.read_bytes()
    ).hexdigest()
    assert receipt["sources"]["interactions"]["sha256"] == hashlib.sha256(
        interactions_path.read_bytes()
    ).hexdigest()
    serialized = json.dumps(receipt).lower()
    assert "apikey" not in serialized
    assert "authorization" not in serialized
