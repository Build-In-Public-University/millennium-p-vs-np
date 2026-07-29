from __future__ import annotations

import math
import re
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any, Iterable

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score


TOKEN_RE = re.compile(r"[a-z0-9_]+")
UTC = timezone.utc


@dataclass(frozen=True)
class InteractionEvent:
    created_at: datetime
    account: str
    interaction_types: tuple[str, ...]


@dataclass(frozen=True)
class PostExample:
    post_id: str
    created_at: datetime
    text: str
    direct_accounts: tuple[str, ...]
    interaction_events: tuple[InteractionEvent, ...]

    @property
    def has_direct_interaction(self) -> bool:
        return bool(self.interaction_events)


def parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError(f"timestamp lacks timezone: {value}")
    return parsed.astimezone(UTC)


def complete_holdout_days(
    tweets: list[dict[str, Any]],
    source_end: datetime,
    label_horizon: timedelta,
    count: int,
) -> list[date]:
    if source_end.tzinfo is None:
        raise ValueError("source_end must be timezone-aware")
    days = sorted({parse_time(str(row["created_at"])).date() for row in tweets})
    complete = [
        day
        for day in days
        if datetime.combine(day + timedelta(days=1), time.min, UTC) + label_horizon
        <= source_end.astimezone(UTC)
    ]
    if len(complete) < count:
        raise ValueError(f"need {count} complete holdout days, found {len(complete)}")
    return complete[-count:]


def build_examples(
    tweets: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    label_horizon: timedelta,
) -> list[PostExample]:
    events_by_target: dict[str, list[InteractionEvent]] = defaultdict(list)
    for row in interactions:
        account = str(row.get("username") or "").strip()
        if not account or not row.get("created_at"):
            continue
        event = InteractionEvent(
            created_at=parse_time(str(row["created_at"])),
            account=account,
            interaction_types=tuple(sorted(str(value) for value in row.get("interaction_types") or ())),
        )
        targets = {
            str(target)
            for target in (row.get("reply_to_tweet_id"), row.get("quoted_tweet_id"))
            if target
        }
        for target in targets:
            events_by_target[target].append(event)

    examples: list[PostExample] = []
    for row in tweets:
        post_id = str(row["tweet_id"])
        created_at = parse_time(str(row["created_at"]))
        events = tuple(
            sorted(
                (
                    event
                    for event in events_by_target.get(post_id, ())
                    if timedelta(0) <= event.created_at - created_at <= label_horizon
                ),
                key=lambda event: (event.created_at, event.account),
            )
        )
        examples.append(
            PostExample(
                post_id=post_id,
                created_at=created_at,
                text=str(row.get("full_text") or ""),
                direct_accounts=tuple(sorted({event.account for event in events})),
                interaction_events=events,
            )
        )
    return sorted(examples, key=lambda row: (row.created_at, row.post_id))


def rolling_split(
    examples: list[PostExample],
    holdout_day: date,
    label_horizon: timedelta,
) -> tuple[list[PostExample], list[PostExample]]:
    cutoff = datetime.combine(holdout_day, time.min, UTC)
    end = cutoff + timedelta(days=1)
    train = [row for row in examples if row.created_at + label_horizon <= cutoff]
    test = [row for row in examples if cutoff <= row.created_at < end]
    return train, test


def tokens(text: str) -> list[str]:
    return TOKEN_RE.findall(text.lower())


def _known_events(examples: Iterable[PostExample]) -> list[InteractionEvent]:
    return sorted(
        (event for row in examples for event in row.interaction_events),
        key=lambda event: event.created_at,
    )


def _recurrence_matrix(rows: list[PostExample], history: list[PostExample]) -> np.ndarray:
    events = _known_events(history)
    matrix: list[list[float]] = []
    for row in rows:
        prior = [event for event in events if event.created_at < row.created_at]
        recent = [event for event in prior if row.created_at - event.created_at <= timedelta(hours=72)]
        hours_since = (
            min(168.0, (row.created_at - prior[-1].created_at).total_seconds() / 3600)
            if prior
            else 168.0
        )
        matrix.append(
            [
                math.log1p(len(recent)),
                math.log1p(len({event.account for event in recent})),
                hours_since / 168.0,
            ]
        )
    return np.asarray(matrix, dtype=float)


def _calibration_error(labels: np.ndarray, probabilities: np.ndarray, bins: int = 10) -> float:
    total = len(labels)
    error = 0.0
    for index in range(bins):
        low = index / bins
        high = (index + 1) / bins
        mask = (probabilities >= low) & (
            probabilities <= high if index == bins - 1 else probabilities < high
        )
        if mask.any():
            error += float(mask.mean()) * abs(float(labels[mask].mean()) - float(probabilities[mask].mean()))
    return error if total else 0.0


def _binary_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict[str, Any]:
    metrics: dict[str, Any] = {
        "average_precision": round(float(average_precision_score(labels, probabilities)), 6)
        if labels.sum()
        else None,
        "roc_auc": round(float(roc_auc_score(labels, probabilities)), 6)
        if len(set(labels.tolist())) == 2
        else None,
        "brier_score": round(float(brier_score_loss(labels, probabilities)), 6),
        "calibration_error": round(_calibration_error(labels, probabilities), 6),
    }
    return metrics


def _error_specimens(
    rows: list[PostExample], labels: np.ndarray, probabilities: np.ndarray, limit: int = 3
) -> dict[str, list[dict[str, Any]]]:
    false_positives = sorted(
        (index for index, label in enumerate(labels) if not label),
        key=lambda index: -probabilities[index],
    )[:limit]
    false_negatives = sorted(
        (index for index, label in enumerate(labels) if label),
        key=lambda index: probabilities[index],
    )[:limit]

    def specimen(index: int) -> dict[str, Any]:
        row = rows[index]
        return {
            "row_index": index,
            "created_day": row.created_at.date().isoformat(),
            "label": int(labels[index]),
            "predicted_probability": round(float(probabilities[index]), 6),
            "character_count": len(row.text),
            "token_count": len(tokens(row.text)),
        }

    return {
        "highest_scored_negatives": [specimen(index) for index in false_positives],
        "lowest_scored_positives": [specimen(index) for index in false_negatives],
    }


def _fit_classifier(features: Any, labels: np.ndarray) -> LogisticRegression:
    model = LogisticRegression(
        class_weight="balanced",
        max_iter=1000,
        random_state=0,
        solver="liblinear",
    )
    model.fit(features, labels)
    return model


def _evaluate_binary_fold(
    train: list[PostExample], test: list[PostExample]
) -> tuple[dict[str, Any], np.ndarray]:
    train_labels = np.asarray([row.has_direct_interaction for row in train], dtype=int)
    test_labels = np.asarray([row.has_direct_interaction for row in test], dtype=int)
    global_probability = float(train_labels.mean()) if len(train_labels) else 0.0
    global_probs = np.full(len(test), global_probability)
    models: dict[str, Any] = {
        "global_positive_rate": {
            "status": "evaluated",
            "metrics": _binary_metrics(test_labels, global_probs),
        },
        "topology_only": {
            "status": "not_evaluatable_yet",
            "reason": "relationship_snapshot_postdates_prediction_windows",
        },
    }
    if len(set(train_labels.tolist())) < 2 or not test:
        unavailable = {"status": "not_evaluatable_yet", "reason": "training_class_balance"}
        for name in ("content_only", "recurrence_only", "combined"):
            models[name] = dict(unavailable)
        return models, global_probs

    vectorizer = TfidfVectorizer(
        min_df=2,
        max_features=1200,
        ngram_range=(1, 2),
        stop_words="english",
    )
    train_text = vectorizer.fit_transform(row.text for row in train)
    test_text = vectorizer.transform(row.text for row in test)
    train_recurrence = _recurrence_matrix(train, train)
    test_recurrence = _recurrence_matrix(test, train)

    feature_sets = {
        "content_only": (train_text, test_text),
        "recurrence_only": (train_recurrence, test_recurrence),
        "combined": (
            hstack((train_text, csr_matrix(train_recurrence))),
            hstack((test_text, csr_matrix(test_recurrence))),
        ),
    }
    content_probs = global_probs
    for name, (train_features, test_features) in feature_sets.items():
        model = _fit_classifier(train_features, train_labels)
        probabilities = model.predict_proba(test_features)[:, 1]
        models[name] = {
            "status": "evaluated",
            "metrics": _binary_metrics(test_labels, probabilities),
            "error_specimens": _error_specimens(test, test_labels, probabilities),
        }
        if name == "content_only":
            content_probs = probabilities
    return models, content_probs


def _cosine_score(query: Counter[str], profile: Counter[str]) -> float:
    if not query or not profile:
        return 0.0
    dot = sum(query[token] * profile[token] for token in query)
    query_norm = math.sqrt(sum(value * value for value in query.values()))
    profile_norm = math.sqrt(sum(value * value for value in profile.values()))
    return dot / (query_norm * profile_norm) if query_norm and profile_norm else 0.0


def _ordered(scores: dict[str, float]) -> list[str]:
    return [account for account, _ in sorted(scores.items(), key=lambda item: (-item[1], item[0]))]


def _rank_map(order: list[str]) -> dict[str, int]:
    return {account: index + 1 for index, account in enumerate(order)}


def _evaluate_account_fold(
    train: list[PostExample], test: list[PostExample]
) -> tuple[dict[str, Any], list[tuple[dict[str, int], tuple[str, ...]]]]:
    frequency: Counter[str] = Counter()
    profiles: dict[str, Counter[str]] = defaultdict(Counter)
    last_seen: dict[str, datetime] = {}
    for row in train:
        query = Counter(tokens(row.text))
        for event in row.interaction_events:
            frequency[event.account] += 1
            profiles[event.account].update(query)
            last_seen[event.account] = max(last_seen.get(event.account, event.created_at), event.created_at)
    candidates = sorted(frequency)
    totals = {
        "all_account_events": 0,
        "seen_account_events": 0,
        "new_account_events": 0,
    }
    hits = {name: {5: 0, 10: 0, "rr": 0.0} for name in ("account_frequency", "content_only", "recurrence_only", "combined")}
    control_rows: list[tuple[dict[str, int], tuple[str, ...]]] = []
    specimens: list[dict[str, Any]] = []

    for row_index, row in enumerate(test):
        actual = set(row.direct_accounts)
        if not actual:
            continue
        totals["all_account_events"] += len(actual)
        seen = tuple(sorted(actual.intersection(candidates)))
        totals["seen_account_events"] += len(seen)
        totals["new_account_events"] += len(actual) - len(seen)
        query = Counter(tokens(row.text))
        scores = {
            "account_frequency": {account: float(frequency[account]) for account in candidates},
            "content_only": {account: _cosine_score(query, profiles[account]) for account in candidates},
            "recurrence_only": {
                account: -(row.created_at - last_seen[account]).total_seconds() for account in candidates
            },
        }
        rank_maps = {name: _rank_map(_ordered(values)) for name, values in scores.items()}
        size = max(1, len(candidates))
        combined_scores = {
            account: sum((size - rank_maps[name][account] + 1) / size for name in rank_maps)
            for account in candidates
        }
        rank_maps["combined"] = _rank_map(_ordered(combined_scores))
        for name, ranks in rank_maps.items():
            for account in seen:
                rank = ranks[account]
                hits[name][5] += int(rank <= 5)
                hits[name][10] += int(rank <= 10)
                hits[name]["rr"] += 1 / rank
        control_rows.append((rank_maps["combined"], seen))
        if seen and len(specimens) < 8:
            specimens.append(
                {
                    "row_index": row_index,
                    "created_day": row.created_at.date().isoformat(),
                    "actual_seen_count": len(seen),
                    "best_actual_rank": min(rank_maps["combined"][account] for account in seen),
                    "candidate_count": len(candidates),
                    "query_token_count": len(query),
                }
            )

    denominator = totals["seen_account_events"]
    models: dict[str, Any] = {}
    for name, values in hits.items():
        models[name] = {
            "status": "evaluated" if denominator else "not_evaluatable_yet",
            "recall_at_5": round(values[5] / denominator, 6) if denominator else None,
            "recall_at_10": round(values[10] / denominator, 6) if denominator else None,
            "mrr": round(values["rr"] / denominator, 6) if denominator else None,
        }
    models["topology_only"] = {
        "status": "not_evaluatable_yet",
        "reason": "relationship_snapshot_postdates_prediction_windows",
    }
    return {
        "candidate_accounts": len(candidates),
        **totals,
        "candidate_coverage": round(denominator / max(1, totals["all_account_events"]), 6),
        "new_account_event_share": round(
            totals["new_account_events"] / max(1, totals["all_account_events"]), 6
        ),
        "models": models,
        "error_specimens": specimens,
    }, control_rows


def _rotated(values: np.ndarray) -> np.ndarray:
    return np.roll(values, 1) if len(values) > 1 else values.copy()


def _account_shuffle_recall(control_rows: list[tuple[dict[str, int], tuple[str, ...]]]) -> float | None:
    if len(control_rows) < 2:
        return None
    actual_sets = [actual for _, actual in control_rows]
    shifted = actual_sets[-1:] + actual_sets[:-1]
    hits = total = 0
    for (ranks, _), actual in zip(control_rows, shifted):
        for account in actual:
            if account in ranks:
                total += 1
                hits += int(ranks[account] <= 10)
    return round(hits / total, 6) if total else None


def _summarize_binary_folds(folds: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    model_names = folds[0]["direct_interaction_models"] if folds else ()
    for model_name in model_names:
        metric_rows = [
            fold["direct_interaction_models"][model_name].get("metrics")
            for fold in folds
            if fold["direct_interaction_models"][model_name]["status"] == "evaluated"
        ]
        metric_rows = [row for row in metric_rows if row]
        if not metric_rows:
            summary[model_name] = {"status": "not_evaluatable_yet"}
            continue
        metrics: dict[str, Any] = {}
        for metric in metric_rows[0]:
            values = [row[metric] for row in metric_rows if row[metric] is not None]
            metrics[metric] = {
                "mean": round(statistics.mean(values), 6) if values else None,
                "population_std": round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0,
                "windows": len(values),
            }
        summary[model_name] = {"status": "evaluated", "metrics": metrics}
    return summary


def _summarize_account_folds(folds: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    model_names = folds[0]["account_ranking"]["models"] if folds else ()
    for model_name in model_names:
        rows = []
        for fold in folds:
            ranking = fold["account_ranking"]
            model = ranking["models"][model_name]
            if model["status"] == "evaluated" and ranking["seen_account_events"]:
                rows.append((model, ranking["seen_account_events"]))
        if not rows:
            summary[model_name] = {"status": "not_evaluatable_yet"}
            continue
        total_weight = sum(weight for _, weight in rows)
        metrics: dict[str, Any] = {}
        for metric in ("recall_at_5", "recall_at_10", "mrr"):
            values = [float(row[metric]) for row, _ in rows]
            weighted = sum(float(row[metric]) * weight for row, weight in rows) / total_weight
            metrics[metric] = {
                "weighted_mean": round(weighted, 6),
                "window_mean": round(statistics.mean(values), 6),
                "population_std": round(statistics.pstdev(values), 6) if len(values) > 1 else 0.0,
                "windows": len(values),
            }
        summary[model_name] = {"status": "evaluated", "metrics": metrics}
    return summary


def resolve_direct_interaction_hypothesis(
    folds: list[dict[str, Any]], controls: list[dict[str, Any]]
) -> dict[str, Any]:
    observed = [float(fold["direct_interaction_models"]["content_only"]["metrics"]["average_precision"]) for fold in folds]
    baselines = [float(fold["direct_interaction_models"]["global_positive_rate"]["metrics"]["average_precision"]) for fold in folds]
    shuffled = [float(control["metrics"]["average_precision"]) for control in controls]
    positive_windows = sum(value > baseline for value, baseline in zip(observed, baselines))
    control_windows = sum(value >= signal for value, signal in zip(shuffled, observed))
    mean_delta = statistics.mean(value - baseline for value, baseline in zip(observed, baselines))
    if positive_windows < 2 or mean_delta <= 0:
        outcome = "not_supported"
        reason = "content_failed_to_beat_global_rate_in_two_windows"
    elif control_windows >= 2:
        outcome = "not_supported"
        reason = f"shuffled_time_control_matched_or_exceeded_observed_in_{control_windows}_windows"
    else:
        outcome = "provisional_support"
        reason = "content_beat_global_rate_and_deterministic_time_control"
    return {
        "outcome": outcome,
        "reason": reason,
        "mean_average_precision_delta": round(mean_delta, 6),
        "positive_delta_windows": positive_windows,
        "time_control_at_least_observed_windows": control_windows,
    }


def _resolve_account_hypothesis(summary: dict[str, Any], controls: list[dict[str, Any]]) -> dict[str, Any]:
    combined = summary["combined"]["metrics"]["recall_at_10"]["weighted_mean"]
    best_baseline = max(summary[name]["metrics"]["recall_at_10"]["weighted_mean"] for name in ("account_frequency", "content_only", "recurrence_only"))
    control_values = [row["recall_at_10"] for row in controls if row["recall_at_10"] is not None]
    if combined <= best_baseline:
        outcome = "not_supported"
        reason = "combined_failed_to_beat_best_boring_baseline"
    elif control_values and statistics.mean(control_values) >= combined:
        outcome = "not_supported"
        reason = "shuffled_account_control_matched_or_exceeded_observed"
    else:
        outcome = "provisional_support"
        reason = "combined_beat_boring_baselines_and_shuffled_account_control"
    return {
        "outcome": outcome,
        "reason": reason,
        "combined_recall_at_10": combined,
        "best_baseline_recall_at_10": best_baseline,
    }


def evaluate_benchmark(
    tweets: list[dict[str, Any]],
    interactions: list[dict[str, Any]],
    source_end: datetime,
    holdout_count: int = 3,
    label_horizon: timedelta = timedelta(hours=24),
    minimum_positive_events: int = 30,
) -> dict[str, Any]:
    examples = build_examples(tweets, interactions, label_horizon)
    holdout_days = complete_holdout_days(tweets, source_end, label_horizon, holdout_count)
    folds: list[dict[str, Any]] = []
    time_controls: list[dict[str, Any]] = []
    account_controls: list[dict[str, Any]] = []

    for holdout_day in holdout_days:
        train, test = rolling_split(examples, holdout_day, label_horizon)
        binary_models, content_probs = _evaluate_binary_fold(train, test)
        account_ranking, control_rows = _evaluate_account_fold(train, test)
        test_labels = np.asarray([row.has_direct_interaction for row in test], dtype=int)
        shuffled_labels = _rotated(test_labels)
        time_controls.append(
            {
                "holdout_day": holdout_day.isoformat(),
                "model": "content_only_fixed_predictions",
                "permutation": "rotate_labels_by_one_row",
                "metrics": _binary_metrics(shuffled_labels, content_probs),
            }
        )
        account_controls.append(
            {
                "holdout_day": holdout_day.isoformat(),
                "model": "combined_fixed_rankings",
                "permutation": "rotate_actual_account_sets_by_one_positive_row",
                "recall_at_10": _account_shuffle_recall(control_rows),
            }
        )
        folds.append(
            {
                "holdout_day": holdout_day.isoformat(),
                "train_posts": len(train),
                "test_posts": len(test),
                "positive_test_posts": int(test_labels.sum()),
                "direct_interaction_models": binary_models,
                "account_ranking": account_ranking,
            }
        )

    positive_posts = sum(fold["positive_test_posts"] for fold in folds)
    seen_account_events = sum(fold["account_ranking"]["seen_account_events"] for fold in folds)
    all_account_events = sum(fold["account_ranking"]["all_account_events"] for fold in folds)
    h1_status = "evaluated" if positive_posts >= minimum_positive_events else "not_evaluatable_yet"
    h2_status = "evaluated" if seen_account_events >= minimum_positive_events else "not_evaluatable_yet"

    account_summary = _summarize_account_folds(folds)

    def active_target(status: str, support: int) -> dict[str, Any]:
        result: dict[str, Any] = {"status": status, "positive_support": support}
        if status != "evaluated":
            result["reason"] = f"positive_support_below_{minimum_positive_events}"
            result["outcome"] = "unresolved_underpowered"
        return result

    h1 = active_target(h1_status, positive_posts)
    h2 = active_target(h2_status, seen_account_events)
    if h1_status == "evaluated":
        h1.update(resolve_direct_interaction_hypothesis(folds, time_controls))
    if h2_status == "evaluated":
        h2.update(_resolve_account_hypothesis(account_summary, account_controls))

    return {
        "schema_version": "community-archive-prediction/v0.1",
        "data_contract": {
            "source_end_exclusive": source_end.astimezone(UTC).isoformat(),
            "label_horizon_hours": label_horizon.total_seconds() / 3600,
            "label_scope": "reply_or_quote_targeting_authored_post",
            "excluded_labels": ["mention_without_target_post_linkage"],
            "holdout_selection": "last complete UTC days with full label horizon",
            "candidate_rule": "accounts observed in matured training rows only",
            "within_holdout_updates": False,
            "minimum_positive_events": minimum_positive_events,
        },
        "support": {
            "heldout_posts": sum(fold["test_posts"] for fold in folds),
            "positive_heldout_posts": positive_posts,
            "heldout_account_events": all_account_events,
            "seen_heldout_account_events": seen_account_events,
        },
        "targets": {
            "H-CA-01": h1,
            "H-CA-02": h2,
            "H-CA-03": {"status": "deferred_to_v0.2", "reason": "new_account_model_not_implemented"},
            "H-CA-04": {"status": "deferred_to_v0.2", "reason": "interaction_type_model_not_implemented"},
            "H-CA-05": {"status": "not_evaluatable_yet", "reason": "zero_observed_propagation_positives"},
            "H-CA-06": {"status": "not_evaluatable_yet", "reason": "single_relationship_snapshot"},
            "H-CA-07": {"status": "deferred_to_v0.2", "reason": "observation_partition_not_frozen"},
            "H-CA-08": {"status": "not_evaluatable_yet", "reason": "claim_outcomes_unscored"},
        },
        "folds": folds,
        "summary": {
            "direct_interaction_models": _summarize_binary_folds(folds),
            "account_ranking_models": account_summary,
        },
        "negative_controls": {
            "shuffled_event_times": time_controls,
            "shuffled_account_labels_within_window": account_controls,
        },
        "privacy": {
            "raw_text_emitted": False,
            "post_ids_emitted": False,
            "account_identities_emitted": False,
        },
    }
