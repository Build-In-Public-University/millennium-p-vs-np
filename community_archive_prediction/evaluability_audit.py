from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .benchmark import build_examples, complete_holdout_days, parse_time, rolling_split
from .experiment import (
    INTERACTIONS_NAME,
    TWEETS_NAME,
    WINDOW_CONTRACT_NAME,
    read_jsonl,
    source_receipt,
)


UTC = timezone.utc
def _fold_type_support(
    interactions: list[dict[str, Any]],
    test_posts: dict[str, datetime],
    holdout_day: date,
    label_horizon: timedelta,
) -> dict[str, int]:
    reply_events = 0
    quote_events = 0
    ambiguous_events = 0
    unlinked_mentions = 0

    for row in interactions:
        event_time = parse_time(row["created_at"])
        reply_target = str(row.get("reply_to_tweet_id") or "")
        quote_target = str(row.get("quoted_tweet_id") or "")
        reply_linked = reply_target in test_posts
        quote_linked = quote_target in test_posts

        def valid(target: str) -> bool:
            delta = event_time - test_posts[target]
            return timedelta(0) <= delta <= label_horizon

        reply_valid = reply_linked and valid(reply_target)
        quote_valid = quote_linked and valid(quote_target)
        same_target = reply_valid and quote_valid and reply_target == quote_target

        if same_target:
            ambiguous_events += 1
        else:
            reply_events += int(reply_valid)
            quote_events += int(quote_valid)

        types = set(row.get("interaction_types") or [])
        has_no_target_link = not reply_target and not quote_target
        if "mention" in types and has_no_target_link and event_time.date() == holdout_day:
            unlinked_mentions += 1

    return {
        "linked_reply_events": reply_events,
        "linked_quote_events": quote_events,
        "ambiguous_linked_events": ambiguous_events,
        "excluded_unlinked_mentions": unlinked_mentions,
    }


def _target_state(
    class_support: dict[str, int],
    minimum_class_support: int,
    feature_available: bool,
) -> dict[str, Any]:
    observed_minimum = min(class_support.values())
    label_available = observed_minimum >= minimum_class_support
    label_status = "evaluated" if label_available else "not_evaluatable_yet"
    feature_status = "evaluated" if feature_available else "not_evaluatable_yet"
    blockers: list[str] = []
    if not label_available:
        blockers.append(f"class_support_below_{minimum_class_support}")
    if not feature_available:
        blockers.append("relationship_snapshot_postdates_predictions")

    return {
        "status": "not_evaluatable_yet" if blockers else "evaluable",
        "label_status": label_status,
        "feature_status": feature_status,
        "class_support": class_support,
        "minimum_observed_class_support": observed_minimum,
        "minimum_class_support": minimum_class_support,
        "blockers": blockers,
    }


def evaluate_evaluability(
    tweets: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    source_end: datetime,
    relationship_snapshot_at: datetime,
    holdout_count: int = 3,
    label_horizon: timedelta = timedelta(hours=24),
    minimum_class_support: int = 30,
) -> dict[str, Any]:
    examples = build_examples(tweets, interactions, label_horizon)
    holdout_days = complete_holdout_days(tweets, source_end, label_horizon, holdout_count)
    folds: list[dict[str, Any]] = []

    for holdout_day in holdout_days:
        train, test = rolling_split(examples, holdout_day, label_horizon)
        candidates = {account for row in train for account in row.direct_accounts}
        all_events = 0
        seen_events = 0
        new_events = 0
        posts_with_new = 0

        for row in test:
            accounts = set(row.direct_accounts)
            seen = accounts & candidates
            unseen = accounts - candidates
            all_events += len(accounts)
            seen_events += len(seen)
            new_events += len(unseen)
            posts_with_new += int(bool(unseen))

        test_posts = {row.post_id: row.created_at for row in test}
        type_support = _fold_type_support(interactions, test_posts, holdout_day, label_horizon)
        folds.append(
            {
                "holdout_day": holdout_day.isoformat(),
                "training_posts": len(train),
                "heldout_posts": len(test),
                "H-CA-03": {
                    "new_account_events": new_events,
                    "posts_with_new_account_event": posts_with_new,
                    "seen_account_events": seen_events,
                    "all_account_events": all_events,
                },
                "H-CA-04": type_support,
            }
        )

    h3_support = {
        key: sum(fold["H-CA-03"][key] for fold in folds)
        for key in (
            "new_account_events",
            "posts_with_new_account_event",
            "seen_account_events",
            "all_account_events",
        )
    }
    h4_support = {
        key: sum(fold["H-CA-04"][key] for fold in folds)
        for key in (
            "linked_reply_events",
            "linked_quote_events",
            "ambiguous_linked_events",
            "excluded_unlinked_mentions",
        )
    }
    heldout_posts = sum(fold["heldout_posts"] for fold in folds)
    first_prediction = datetime.combine(holdout_days[0], datetime.min.time(), tzinfo=UTC)
    feature_available = relationship_snapshot_at < first_prediction

    h3_state = _target_state(
        {
            "new_account_post": h3_support["posts_with_new_account_event"],
            "no_new_account_post": heldout_posts - h3_support["posts_with_new_account_event"],
        },
        minimum_class_support,
        feature_available,
    )
    h3_state["label"] = "post_receives_interaction_from_account_absent_from_matured_training_candidates"

    h4_state = _target_state(
        {
            "reply": h4_support["linked_reply_events"],
            "quote": h4_support["linked_quote_events"],
        },
        minimum_class_support,
        feature_available,
    )
    h4_state["label"] = "target_specific_reply_vs_quote"

    return {
        "schema_version": "community-archive-evaluability/v0.1",
        "data_contract": {
            "source_end": source_end.isoformat(),
            "label_horizon_hours": label_horizon.total_seconds() / 3600,
            "holdout_selection": "last complete UTC days with full label horizon",
            "candidate_rule": "accounts in matured training rows only",
            "interaction_type_rule": "reply_to_tweet_id and quoted_tweet_id fields, not mixed interaction_types",
            "excluded_labels": ["mention_without_target_post_linkage"],
            "relationship_snapshot_day": relationship_snapshot_at.date().isoformat(),
            "feature_availability_rule": "relationship snapshot must predate every holdout prediction",
        },
        "folds": folds,
        "support": {"H-CA-03": h3_support, "H-CA-04": h4_support},
        "targets": {"H-CA-03": h3_state, "H-CA-04": h4_state},
        "privacy": {
            "raw_rows_emitted": False,
            "subject_handle_in_source_logical_path": True,
            "interaction_account_identities_emitted": False,
            "post_identifiers_emitted": False,
            "exact_post_timestamps_emitted": False,
        },
    }


def _parse_source_end(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed.astimezone(UTC)


def run_audit(
    source_root: Path,
    output: Path,
    relationship_snapshot_at: datetime,
    minimum_class_support: int = 30,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    tweets_path = source_root / "data" / TWEETS_NAME
    interactions_path = source_root / "data" / INTERACTIONS_NAME
    window_path = source_root / "reports" / WINDOW_CONTRACT_NAME
    snapshot_relative = (
        f"data/relationship_graph_{relationship_snapshot_at.date().isoformat()}"
        "/relationship_snapshot.json"
    )
    snapshot_path = source_root / snapshot_relative

    tweets = read_jsonl(tweets_path)
    interactions = read_jsonl(interactions_path)
    source_window = json.loads(window_path.read_text())
    source_end = _parse_source_end(source_window["window"]["end_exclusive"])
    receipt = evaluate_evaluability(
        tweets=tweets,
        interactions=interactions,
        source_end=source_end,
        relationship_snapshot_at=relationship_snapshot_at,
        minimum_class_support=minimum_class_support,
    )

    sources: dict[str, dict[str, Any]] = {
        "tweets": source_receipt(tweets_path, f"data/{TWEETS_NAME}", rows=len(tweets)),
        "interactions": source_receipt(
            interactions_path,
            f"data/{INTERACTIONS_NAME}",
            rows=len(interactions),
        ),
        "window_contract": source_receipt(
            window_path,
            f"reports/{WINDOW_CONTRACT_NAME}",
        ),
    }
    if snapshot_path.exists():
        sources["relationship_snapshot"] = source_receipt(snapshot_path, snapshot_relative)

    receipt["provenance"] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "sources": sources,
        "command": "python3 -m community_archive_prediction.evaluability_audit --source-root <source> --output <output> --relationship-snapshot-at <timestamp>",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit H-CA-03/H-CA-04 label and feature evaluability")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("evidence/runs/community-archive-evaluability-v0.1.json"))
    parser.add_argument("--relationship-snapshot-at", required=True)
    parser.add_argument("--minimum-class-support", type=int, default=30)
    args = parser.parse_args()
    receipt = run_audit(
        source_root=args.source_root,
        output=args.output,
        relationship_snapshot_at=parse_time(args.relationship_snapshot_at),
        minimum_class_support=args.minimum_class_support,
    )
    print(json.dumps({"output": str(args.output), "support": receipt["support"], "targets": receipt["targets"]}, indent=2))


if __name__ == "__main__":
    main()
