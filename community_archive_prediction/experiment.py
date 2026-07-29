from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy
import scipy
import sklearn

from .benchmark import evaluate_benchmark


TWEETS_NAME = "leo_guinan_tweets_2026-07-12_2026-07-19.jsonl"
INTERACTIONS_NAME = "interactions_with_leo_2026-07-12_2026-07-19.jsonl"
WINDOW_CONTRACT_NAME = "audience_model_results.json"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def source_receipt(path: Path, logical_path: str, rows: int | None = None) -> dict[str, Any]:
    receipt: dict[str, Any] = {
        "logical_path": logical_path,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
    }
    if rows is not None:
        receipt["rows"] = rows
    return receipt


def run_benchmark(
    source_root: Path,
    output: Path,
    minimum_positive_events: int = 30,
) -> dict[str, Any]:
    tweets_path = source_root / "data" / TWEETS_NAME
    interactions_path = source_root / "data" / INTERACTIONS_NAME
    contract_path = source_root / "reports" / WINDOW_CONTRACT_NAME
    tweets = read_jsonl(tweets_path)
    interactions = read_jsonl(interactions_path)
    contract = json.loads(contract_path.read_text())
    source_end = datetime.fromisoformat(contract["window"]["end_exclusive"]).replace(
        tzinfo=timezone.utc
    )
    receipt = evaluate_benchmark(
        tweets=tweets,
        interactions=interactions,
        source_end=source_end,
        minimum_positive_events=minimum_positive_events,
    )
    receipt["provenance"] = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator": "python3 -m community_archive_prediction.experiment",
        "sources": {
            "tweets": source_receipt(
                tweets_path,
                f"data/{TWEETS_NAME}",
                rows=len(tweets),
            ),
            "interactions": source_receipt(
                interactions_path,
                f"data/{INTERACTIONS_NAME}",
                rows=len(interactions),
            ),
            "window_contract": source_receipt(
                contract_path,
                f"reports/{WINDOW_CONTRACT_NAME}",
            ),
        },
        "dependencies": {
            "numpy": numpy.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2, sort_keys=True, allow_nan=False) + "\n")
    return receipt


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Community Archive prediction benchmark v0.1")
    parser.add_argument(
        "--source-root",
        type=Path,
        default=Path.home() / "Projects" / "leo-twitter-audience-model",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("evidence/runs/community-archive-prediction-v0.1.json"),
    )
    parser.add_argument("--minimum-positive-events", type=int, default=30)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    receipt = run_benchmark(
        source_root=args.source_root,
        output=args.output,
        minimum_positive_events=args.minimum_positive_events,
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "support": receipt["support"],
                "targets": receipt["targets"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
