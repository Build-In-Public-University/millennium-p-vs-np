from __future__ import annotations

import argparse
import hashlib
import json
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer

from .benchmark import (
    PostExample,
    _binary_metrics,
    _cosine_score,
    _error_specimens,
    _fit_classifier,
    build_examples,
    complete_holdout_days,
    evaluate_benchmark,
    parse_time,
    rolling_split,
    tokens,
)
from .evaluability_audit import _fold_type_support
from .experiment import read_jsonl, source_receipt


UTC = timezone.utc
PARTITIONS = ("mutual", "follower_only", "following_only", "outside")


@dataclass(frozen=True)
class TypeEvent:
    post: PostExample
    account: str
    label: int


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc(value: str) -> datetime:
    return parse_time(value)


def _artifact_names(contract: dict[str, Any]) -> dict[str, str]:
    window = contract["collection_window"]
    start = _utc(window["authored_start_inclusive"])
    authored_end = _utc(window["authored_end_exclusive"])
    interaction_end = _utc(window["interaction_end_exclusive"])
    handle = contract["subject"].lstrip("@").lower()
    subject_name = handle.split("_", 1)[0]
    authored_last = (authored_end - timedelta(days=1)).date().isoformat()
    interaction_last = (interaction_end - timedelta(days=1)).date().isoformat()
    start_day = start.date().isoformat()
    return {
        "tweets": f"{handle}_tweets_{start_day}_{authored_last}.jsonl",
        "interactions": f"interactions_with_{subject_name}_{start_day}_{interaction_last}.jsonl",
        "extraction": f"extraction_receipt_{start_day}_{interaction_last}.json",
    }


def _preflight(
    source_root: Path,
    contract: dict[str, Any],
    evaluated_at: datetime,
) -> tuple[dict[str, Any], dict[str, Path]]:
    blockers: list[str] = []
    paths: dict[str, Path] = {}
    if contract.get("schema_version") != "community-archive-next-window/v0.2":
        blockers.append("unsupported_contract_schema")
    if contract.get("adaptive_extension_allowed") is not False:
        blockers.append("adaptive_extension_not_disabled")
    if contract.get("research_lock", {}).get("layer_08_allowed") is not False:
        blockers.append("layer_08_not_locked")

    window = contract["collection_window"]
    start = _utc(window["authored_start_inclusive"])
    authored_end = _utc(window["authored_end_exclusive"])
    interaction_end = _utc(window["interaction_end_exclusive"])
    acquire_not_before = _utc(window["acquire_not_before"])
    if not start < authored_end < interaction_end:
        blockers.append("invalid_collection_window")
    if evaluated_at.astimezone(UTC) < acquire_not_before:
        blockers.append("label_horizon_not_mature")

    snapshot = contract["topology_snapshot"]
    observed_day = date.fromisoformat(snapshot["observed_at"])
    if observed_day >= start.date():
        blockers.append("topology_snapshot_not_pre_window")
    topology_sources = {
        "snapshot": {
            "logical_path": snapshot["logical_path"],
            "sha256": snapshot["sha256"],
        },
        **snapshot.get("feature_sources", {}),
    }
    for name, source in topology_sources.items():
        path = source_root / source["logical_path"]
        paths[f"topology_{name}"] = path
        if not path.exists():
            blockers.append(f"topology_{name}_missing")
        elif _sha(path) != source["sha256"]:
            blockers.append(f"topology_{name}_sha256_mismatch")

    names = _artifact_names(contract)
    for name, filename in names.items():
        path = source_root / "data" / filename
        paths[name] = path
        if not path.exists():
            blockers.append(f"{name}_missing")

    tweets: list[dict[str, Any]] = []
    interactions: list[dict[str, Any]] = []
    if paths["tweets"].exists() and paths["interactions"].exists():
        tweets = read_jsonl(paths["tweets"])
        interactions = read_jsonl(paths["interactions"])
        if any(not (start <= _utc(str(row["created_at"])) < authored_end) for row in tweets):
            blockers.append("authored_post_outside_window")
        if any(not (start <= _utc(str(row["created_at"])) < interaction_end) for row in interactions):
            blockers.append("interaction_outside_window")

    if paths["extraction"].exists():
        extraction = json.loads(paths["extraction"].read_text())
        expected_window = {
            "authored_start_inclusive": start,
            "authored_end_exclusive": authored_end,
            "interaction_end_exclusive": interaction_end,
        }
        received_window = extraction.get("window", {})
        if any(
            key not in received_window or _utc(str(received_window[key])) != value
            for key, value in expected_window.items()
        ):
            blockers.append("extraction_window_mismatch")
        expected_sources = {
            "authored_posts": paths["tweets"],
            "interactions": paths["interactions"],
        }
        for name, path in expected_sources.items():
            source = extraction.get("sources", {}).get(name, {})
            if path.exists() and source.get("sha256") != _sha(path):
                blockers.append(f"extraction_{name}_sha256_mismatch")

    holdout_days = [date.fromisoformat(value) for value in contract["holdout_days"]]
    if tweets:
        try:
            complete = complete_holdout_days(
                tweets,
                interaction_end,
                timedelta(hours=contract["label_horizon_hours"]),
                len(holdout_days),
            )
            if complete != holdout_days:
                blockers.append("holdout_days_do_not_match_contract")
        except ValueError:
            blockers.append("insufficient_complete_holdout_days")

    blockers = list(dict.fromkeys(blockers))
    return {
        "status": "passed" if not blockers else "failed",
        "evaluated_at": evaluated_at.astimezone(UTC).isoformat(),
        "blockers": blockers,
        "checks": {
            "contract_schema": contract.get("schema_version"),
            "adaptive_extension_allowed": contract.get("adaptive_extension_allowed"),
            "topology_observed_day": snapshot["observed_at"],
            "label_horizon_mature": evaluated_at.astimezone(UTC) >= acquire_not_before,
            "holdout_days": contract["holdout_days"],
        },
    }, paths


def _partition_map(nodes: list[dict[str, Any]]) -> dict[str, str]:
    partitions: dict[str, str] = {}
    for row in nodes:
        handle = str(row.get("handle") or "").strip().lower()
        if not handle:
            continue
        sources = set(row.get("sources") or ())
        follower = "follower_snapshot" in sources
        following = "following_snapshot" in sources
        if follower and following:
            partition = "mutual"
        elif follower:
            partition = "follower_only"
        elif following:
            partition = "following_only"
        else:
            partition = "outside"
        partitions[handle] = partition
    return partitions


def _support_pass(
    examples: list[PostExample],
    interactions: list[dict[str, Any]],
    holdout_days: list[date],
    label_horizon: timedelta,
) -> tuple[dict[str, dict[str, int]], list[dict[str, Any]]]:
    totals = {
        "H-CA-01": {"direct_interaction_post": 0, "no_direct_interaction_post": 0},
        "H-CA-02": {"seen_account_events": 0},
        "H-CA-03": {"new_account_post": 0, "no_new_account_post": 0},
        "H-CA-04": {"reply": 0, "quote": 0},
    }
    folds: list[dict[str, Any]] = []
    for holdout_day in holdout_days:
        train, test = rolling_split(examples, holdout_day, label_horizon)
        candidates = {account for row in train for account in row.direct_accounts}
        positive = sum(row.has_direct_interaction for row in test)
        seen_events = sum(len(set(row.direct_accounts) & candidates) for row in test)
        new_posts = sum(bool(set(row.direct_accounts) - candidates) for row in test)
        type_support = _fold_type_support(
            interactions,
            {row.post_id: row.created_at for row in test},
            holdout_day,
            label_horizon,
        )
        fold = {
            "holdout_day": holdout_day.isoformat(),
            "training_posts": len(train),
            "heldout_posts": len(test),
            "support": {
                "H-CA-01": {
                    "direct_interaction_post": positive,
                    "no_direct_interaction_post": len(test) - positive,
                },
                "H-CA-02": {"seen_account_events": seen_events},
                "H-CA-03": {
                    "new_account_post": new_posts,
                    "no_new_account_post": len(test) - new_posts,
                },
                "H-CA-04": {
                    "reply": type_support["linked_reply_events"],
                    "quote": type_support["linked_quote_events"],
                    "excluded_unlinked_mentions": type_support["excluded_unlinked_mentions"],
                    "ambiguous_linked_events": type_support["ambiguous_linked_events"],
                },
            },
        }
        folds.append(fold)
        for target in totals:
            for key in totals[target]:
                totals[target][key] += fold["support"][target][key]
    return totals, folds


def _required_support(contract: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {
        "H-CA-01": dict(contract["targets"]["H-CA-01"]["required_support"]),
        "H-CA-02": dict(contract["targets"]["H-CA-02"]["required_support"]),
        "H-CA-03": dict(contract["targets"]["H-CA-03"]["required_support"]),
        "H-CA-04": dict(contract["targets"]["H-CA-04"]["required_support"]),
    }


def _eligibility(
    support: dict[str, dict[str, int]], required: dict[str, dict[str, int]]
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for target, floors in required.items():
        blockers = [
            f"{name}_below_{floor}"
            for name, floor in floors.items()
            if support[target].get(name, 0) < floor
        ]
        result[target] = {
            "status": "eligible" if not blockers else "not_evaluatable_yet",
            "support": support[target],
            "required_support": floors,
            "blockers": blockers,
        }
    return result


def _content_features(
    train: list[PostExample], test: list[PostExample]
) -> tuple[Any, Any]:
    vectorizer = TfidfVectorizer(min_df=1, max_features=1200, ngram_range=(1, 2), stop_words="english")
    train_features = vectorizer.fit_transform(row.text for row in train)
    return train_features, vectorizer.transform(row.text for row in test)


def _context_features(
    train: list[PostExample], test: list[PostExample], partitions: dict[str, str]
) -> tuple[np.ndarray, np.ndarray]:
    profiles = {name: Counter() for name in PARTITIONS}
    counts: Counter[str] = Counter()

    def features(row: PostExample) -> list[float]:
        query = Counter(tokens(row.text))
        total = max(1, sum(counts.values()))
        return [
            *[_cosine_score(query, profiles[name]) for name in PARTITIONS],
            *[counts[name] / total for name in PARTITIONS],
        ]

    train_rows: list[list[float]] = []
    for row in train:
        train_rows.append(features(row))
        query = Counter(tokens(row.text))
        for event in row.interaction_events:
            partition = partitions.get(event.account.lower(), "outside")
            profiles[partition].update(query)
            counts[partition] += 1
    return np.asarray(train_rows, dtype=float), np.asarray([features(row) for row in test], dtype=float)


def _model_result(
    train_features: Any,
    test_features: Any,
    train_labels: np.ndarray,
    test_labels: np.ndarray,
    test_rows: list[PostExample],
    macro: bool = False,
) -> dict[str, Any]:
    if len(set(train_labels.tolist())) < 2 or not len(test_labels):
        return {"status": "not_evaluatable_yet", "reason": "training_class_balance"}
    model = _fit_classifier(train_features, train_labels)
    probabilities = model.predict_proba(test_features)[:, 1]
    metrics = _binary_metrics(test_labels, probabilities)
    if macro:
        quote_ap = metrics["average_precision"]
        reply_ap = (
            round(float(_binary_metrics(1 - test_labels, 1 - probabilities)["average_precision"]), 6)
            if len(set(test_labels.tolist())) == 2
            else None
        )
        metrics["macro_average_precision"] = (
            round((float(quote_ap) + float(reply_ap)) / 2, 6)
            if quote_ap is not None and reply_ap is not None
            else None
        )
    return {
        "status": "evaluated",
        "metrics": metrics,
        "error_specimens": _error_specimens(test_rows, test_labels, probabilities),
    }


def _global_result(labels: np.ndarray, probability: float, macro: bool = False) -> dict[str, Any]:
    probabilities = np.full(len(labels), probability)
    metrics = _binary_metrics(labels, probabilities)
    if macro:
        quote_ap = metrics["average_precision"]
        reply_ap = _binary_metrics(1 - labels, 1 - probabilities)["average_precision"]
        metrics["macro_average_precision"] = (
            round((float(quote_ap) + float(reply_ap)) / 2, 6)
            if quote_ap is not None and reply_ap is not None
            else None
        )
    return {"status": "evaluated", "metrics": metrics}


def _h3_fold(
    train: list[PostExample], test: list[PostExample], partitions: dict[str, str]
) -> dict[str, Any]:
    seen: set[str] = set()
    train_labels: list[int] = []
    for row in train:
        accounts = set(row.direct_accounts)
        train_labels.append(int(bool(accounts - seen)))
        seen.update(accounts)
    test_labels = np.asarray([int(bool(set(row.direct_accounts) - seen)) for row in test], dtype=int)
    train_array = np.asarray(train_labels, dtype=int)
    prior = float(train_array.mean()) if len(train_array) else 0.0
    content_train, content_test = _content_features(train, test)
    context_train, context_test = _context_features(train, test, partitions)
    models = {
        "global_new_account_rate": _global_result(test_labels, prior),
        "content_only": _model_result(content_train, content_test, train_array, test_labels, test),
        "topology_context_only": _model_result(context_train, context_test, train_array, test_labels, test),
        "combined": _model_result(
            hstack((content_train, csr_matrix(context_train))),
            hstack((content_test, csr_matrix(context_test))),
            train_array,
            test_labels,
            test,
        ),
    }
    return {"models": models}


def _type_events(
    tweets: list[dict[str, Any]], interactions: list[dict[str, Any]], label_horizon: timedelta
) -> list[TypeEvent]:
    examples = {row.post_id: row for row in build_examples(tweets, interactions, label_horizon)}
    events: list[TypeEvent] = []
    for row in interactions:
        event_time = _utc(str(row["created_at"]))
        reply = str(row.get("reply_to_tweet_id") or "")
        quote = str(row.get("quoted_tweet_id") or "")
        valid: list[tuple[str, int]] = []
        for target, label in ((reply, 0), (quote, 1)):
            if target in examples:
                delta = event_time - examples[target].created_at
                if timedelta(0) <= delta <= label_horizon:
                    valid.append((target, label))
        if len(valid) != 1:
            continue
        account = str(row.get("username") or "").strip()
        if account:
            target, label = valid[0]
            events.append(TypeEvent(examples[target], account, label))
    return sorted(events, key=lambda event: (event.post.created_at, event.post.post_id, event.account))


def _type_aux_features(
    train: list[TypeEvent], test: list[TypeEvent], partitions: dict[str, str]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    def topology(event: TypeEvent) -> list[float]:
        partition = partitions.get(event.account.lower(), "outside")
        return [float(partition == name) for name in PARTITIONS]

    def prior(event: TypeEvent, history: list[TypeEvent]) -> list[float]:
        earlier = [row.label for row in history if row.account.lower() == event.account.lower() and row.post.created_at < event.post.created_at]
        total = len(earlier)
        quotes = sum(earlier)
        return [math.log1p(total), quotes / max(1, total), (total - quotes) / max(1, total)]

    return (
        np.asarray([topology(row) for row in train]),
        np.asarray([topology(row) for row in test]),
        np.asarray([prior(row, train) for row in train]),
        np.asarray([prior(row, train) for row in test]),
    )


def _h4_fold(
    train_posts: list[PostExample],
    test_posts: list[PostExample],
    events: list[TypeEvent],
    partitions: dict[str, str],
) -> dict[str, Any]:
    train_ids = {row.post_id for row in train_posts}
    test_ids = {row.post_id for row in test_posts}
    train = [row for row in events if row.post.post_id in train_ids]
    test = [row for row in events if row.post.post_id in test_ids]
    train_labels = np.asarray([row.label for row in train], dtype=int)
    test_labels = np.asarray([row.label for row in test], dtype=int)
    prior = float(train_labels.mean()) if len(train_labels) else 0.0
    train_posts_for_events = [row.post for row in train]
    test_posts_for_events = [row.post for row in test]
    content_train, content_test = _content_features(train_posts_for_events, test_posts_for_events)
    topology_train, topology_test, prior_train, prior_test = _type_aux_features(train, test, partitions)
    models = {
        "global_quote_rate": _global_result(test_labels, prior, macro=True),
        "content_only": _model_result(content_train, content_test, train_labels, test_labels, test_posts_for_events, macro=True),
        "topology_only": _model_result(topology_train, topology_test, train_labels, test_labels, test_posts_for_events, macro=True),
        "prior_type_only": _model_result(prior_train, prior_test, train_labels, test_labels, test_posts_for_events, macro=True),
        "combined": _model_result(
            hstack((content_train, csr_matrix(topology_train), csr_matrix(prior_train))),
            hstack((content_test, csr_matrix(topology_test), csr_matrix(prior_test))),
            train_labels,
            test_labels,
            test_posts_for_events,
            macro=True,
        ),
    }
    return {"models": models}


def _summarize(folds: list[dict[str, Any]], target: str) -> dict[str, Any]:
    names = folds[0][target]["models"] if folds and target in folds[0] else ()
    result: dict[str, Any] = {}
    for name in names:
        rows = [
            fold[target]["models"][name]["metrics"]
            for fold in folds
            if target in fold and fold[target]["models"][name]["status"] == "evaluated"
        ]
        if not rows:
            result[name] = {"status": "not_evaluatable_yet"}
            continue
        metrics: dict[str, Any] = {}
        for metric in rows[0]:
            values = [float(row[metric]) for row in rows if row.get(metric) is not None]
            metrics[metric] = {
                "mean": round(statistics.mean(values), 6) if values else None,
                "population_std": round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0,
                "windows": len(values),
            }
        result[name] = {"status": "evaluated", "metrics": metrics}
    return result


def _resolve(
    summary: dict[str, Any], combined: str, baselines: tuple[str, ...], metric: str
) -> dict[str, Any]:
    challenger = summary.get(combined, {})
    comparators = {name: summary.get(name, {}) for name in baselines}
    if challenger.get("status") != "evaluated" or any(
        row.get("status") != "evaluated" for row in comparators.values()
    ):
        return {"outcome": "not_evaluatable_yet", "reason": "model_training_or_metric_unavailable"}
    challenger_value = challenger["metrics"][metric]["mean"]
    baseline_values = {
        name: row["metrics"][metric]["mean"] for name, row in comparators.items()
    }
    best_name, best_value = max(baseline_values.items(), key=lambda item: item[1])
    delta = challenger_value - best_value
    return {
        "outcome": "provisional_support" if delta > 0 else "not_supported",
        "reason": "combined_beat_all_frozen_baselines" if delta > 0 else "combined_failed_to_beat_best_frozen_baseline",
        "best_baseline": best_name,
        f"mean_{metric}_delta": round(delta, 6),
    }


def _failed_receipt(
    contract_path: Path,
    contract: dict[str, Any],
    preflight: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "community-archive-prediction/v0.2",
        "status": "preflight_failed",
        "contract": {
            "schema_version": contract.get("schema_version"),
            "sha256": _sha(contract_path),
        },
        "preflight": preflight,
        "targets": {
            target: {"status": "not_run", "reason": "preflight_failed"}
            for target in ("H-CA-01", "H-CA-02", "H-CA-03", "H-CA-04")
        },
        "privacy": {
            "raw_text_emitted": False,
            "post_ids_emitted": False,
            "account_identities_emitted": False,
        },
    }


def run_prospective(
    source_root: Path,
    contract_path: Path,
    output: Path,
    evaluated_at: datetime | None = None,
) -> dict[str, Any]:
    source_root = source_root.expanduser().resolve()
    contract_path = contract_path.expanduser().resolve()
    contract = json.loads(contract_path.read_text())
    evaluated_at = evaluated_at or datetime.now(UTC)
    if evaluated_at.tzinfo is None:
        raise ValueError("evaluated_at must be timezone-aware")
    preflight, paths = _preflight(source_root, contract, evaluated_at)
    if preflight["status"] != "passed":
        receipt = _failed_receipt(contract_path, contract, preflight)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
        return receipt

    tweets = read_jsonl(paths["tweets"])
    interactions = read_jsonl(paths["interactions"])
    nodes = read_jsonl(paths["topology_nodes"])
    partitions = _partition_map(nodes)
    label_horizon = timedelta(hours=contract["label_horizon_hours"])
    holdout_days = [date.fromisoformat(value) for value in contract["holdout_days"]]
    source_end = _utc(contract["collection_window"]["interaction_end_exclusive"])
    examples = build_examples(tweets, interactions, label_horizon)
    support, folds = _support_pass(examples, interactions, holdout_days, label_horizon)
    targets = _eligibility(support, _required_support(contract))

    active_v01 = {target for target in ("H-CA-01", "H-CA-02") if targets[target]["status"] == "eligible"}
    legacy: dict[str, Any] | None = None
    if active_v01:
        legacy = evaluate_benchmark(
            tweets,
            interactions,
            source_end,
            holdout_count=len(holdout_days),
            label_horizon=label_horizon,
            minimum_positive_events=int(contract["minimum_class_support"]),
            active_targets=active_v01,
            time_control_mode="all_cyclic_permutations",
        )
        for target, summary_name in (("H-CA-01", "direct_interaction_models"), ("H-CA-02", "account_ranking_models")):
            if target not in active_v01:
                continue
            targets[target] = {
                **targets[target],
                "status": legacy["targets"][target]["status"],
                "outcome": legacy["targets"][target].get("outcome"),
                "reason": legacy["targets"][target].get("reason"),
                "models": legacy["summary"][summary_name],
            }
            if target == "H-CA-01":
                targets[target]["negative_control"] = legacy["negative_controls"][
                    "shuffled_event_times"
                ]
            else:
                targets[target]["negative_control"] = legacy["negative_controls"][
                    "shuffled_account_labels_within_window"
                ]

    type_events = _type_events(tweets, interactions, label_horizon)
    for index, holdout_day in enumerate(holdout_days):
        train, test = rolling_split(examples, holdout_day, label_horizon)
        if targets["H-CA-03"]["status"] == "eligible":
            folds[index]["H-CA-03"] = _h3_fold(train, test, partitions)
        if targets["H-CA-04"]["status"] == "eligible":
            folds[index]["H-CA-04"] = _h4_fold(train, test, type_events, partitions)

    if targets["H-CA-03"]["status"] == "eligible":
        summary = _summarize(folds, "H-CA-03")
        targets["H-CA-03"] = {
            **targets["H-CA-03"],
            "status": "evaluated",
            "models": summary,
            **_resolve(
                summary,
                "combined",
                ("global_new_account_rate", "content_only", "topology_context_only"),
                "average_precision",
            ),
        }
    if targets["H-CA-04"]["status"] == "eligible":
        summary = _summarize(folds, "H-CA-04")
        targets["H-CA-04"] = {
            **targets["H-CA-04"],
            "status": "evaluated",
            "models": summary,
            **_resolve(
                summary,
                "combined",
                ("global_quote_rate", "content_only", "topology_only", "prior_type_only"),
                "macro_average_precision",
            ),
        }

    for target in targets.values():
        if target["status"] == "eligible":
            target["status"] = "not_evaluatable_yet"
            target["outcome"] = "not_evaluatable_yet"
            target["reason"] = "model_not_executed"

    sources = {
        "tweets": source_receipt(paths["tweets"], f"data/{paths['tweets'].name}", rows=len(tweets)),
        "interactions": source_receipt(
            paths["interactions"], f"data/{paths['interactions'].name}", rows=len(interactions)
        ),
        "extraction_receipt": source_receipt(
            paths["extraction"], f"data/{paths['extraction'].name}"
        ),
    }
    for name in ("snapshot", "nodes", "edges"):
        path = paths[f"topology_{name}"]
        sources[f"topology_{name}"] = source_receipt(
            path, str(path.relative_to(source_root))
        )

    receipt = {
        "schema_version": "community-archive-prediction/v0.2",
        "status": "evaluated",
        "contract": {
            "schema_version": contract["schema_version"],
            "sha256": _sha(contract_path),
            "holdout_days": contract["holdout_days"],
            "minimum_class_support": contract["minimum_class_support"],
            "adaptive_extension_allowed": contract["adaptive_extension_allowed"],
            "amendments": contract.get("amendments", []),
        },
        "evaluation_contract": {
            "H-CA-01": {
                "prediction_unit": "authored_post_at_publication",
                "label": "direct_reply_or_quote_within_24_hours",
            },
            "H-CA-02": {
                "prediction_unit": "eligible_seen_account_post_pair_at_publication",
                "label": "account_replies_or_quotes_within_24_hours",
            },
            "H-CA-03": {
                "prediction_unit": contract["targets"]["H-CA-03"]["prediction_unit"],
                "label": "at_least_one_previously_unseen_account_replies_or_quotes_within_24_hours",
            },
            "H-CA-04": {
                "prediction_unit": contract["targets"]["H-CA-04"]["prediction_unit"],
                "label": "reply_versus_quote",
                "limitation": "conditional classification; does not predict whether the account interacts",
            },
        },
        "preflight": preflight,
        "support": support,
        "targets": targets,
        "folds": folds,
        "provenance": {
            "generated_at": evaluated_at.astimezone(UTC).isoformat(),
            "generator": "python3 -m community_archive_prediction.prospective",
            "sources": sources,
        },
        "privacy": {
            "raw_text_emitted": False,
            "post_ids_emitted": False,
            "account_identities_emitted": False,
            "exact_post_timestamps_emitted": False,
        },
        "research_lock": {"layer_08_allowed": False},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the frozen Community Archive v0.2 benchmark")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path.home() / "Projects/leo-twitter-audience-model",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        default=Path("evidence/community-archive-next-window-v0.2.json"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/runs/community-archive-prediction-v0.2.json"),
    )
    args = parser.parse_args()
    receipt = run_prospective(args.source_root, args.contract, args.output)
    print(
        json.dumps(
            {
                "output": str(args.output),
                "status": receipt["status"],
                "preflight": receipt["preflight"],
                "targets": receipt["targets"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
