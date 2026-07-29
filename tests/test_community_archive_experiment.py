from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from community_archive_prediction.experiment import run_benchmark


UTC = timezone.utc


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))


def test_runner_writes_hashed_identity_free_receipt(tmp_path: Path) -> None:
    source = tmp_path / "source"
    data = source / "data"
    reports = source / "reports"
    reports.mkdir(parents=True)
    tweets: list[dict[str, object]] = []
    interactions: list[dict[str, object]] = []
    for day in range(1, 9):
        for index in range(4):
            post_id = f"post-{day}-{index}"
            positive = index % 2 == 0
            tweets.append(
                {
                    "tweet_id": post_id,
                    "created_at": datetime(2026, 1, day, 12, tzinfo=UTC).isoformat(),
                    "full_text": "signal question" if positive else "quiet note",
                }
            )
            if positive:
                interactions.append(
                    {
                        "tweet_id": f"event-{day}-{index}",
                        "created_at": datetime(2026, 1, day, 13, tzinfo=UTC).isoformat(),
                        "reply_to_tweet_id": post_id,
                        "quoted_tweet_id": None,
                        "username": "private-test-account",
                        "interaction_types": ["reply"],
                    }
                )
    write_jsonl(data / "leo_guinan_tweets_2026-07-12_2026-07-19.jsonl", tweets)
    write_jsonl(data / "interactions_with_leo_2026-07-12_2026-07-19.jsonl", interactions)
    (reports / "audience_model_results.json").write_text(
        json.dumps({"window": {"end_exclusive": "2026-01-10"}})
    )
    output = tmp_path / "receipt.json"

    receipt = run_benchmark(
        source_root=source,
        output=output,
        minimum_positive_events=1,
    )

    assert json.loads(output.read_text()) == receipt
    assert receipt["provenance"]["generated_at"].endswith("+00:00")
    assert set(receipt["provenance"]["sources"]) == {"tweets", "interactions", "window_contract"}
    assert all(len(source_row["sha256"]) == 64 for source_row in receipt["provenance"]["sources"].values())
    serialized = json.dumps(receipt)
    assert str(tmp_path) not in serialized
    assert "private-test-account" not in serialized
    assert "post-" not in serialized
