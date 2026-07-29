from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable


UTC = timezone.utc
API_URL = "https://fabxmporizzqflnftavs.supabase.co/rest/v1/enriched_tweets"
DOCS_URL = "https://www.community-archive.org/llms.txt"
FIELDS = (
    "tweet_id,username,account_display_name,created_at,full_text,retweet_count,"
    "favorite_count,reply_to_tweet_id,reply_to_username,quoted_tweet_id,conversation_id"
)
FetchPages = Callable[[str, dict[str, str]], list[dict[str, Any]]]


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("window timestamps must be timezone-aware")
    return value.astimezone(UTC)


def _iso(value: datetime) -> str:
    return _utc(value).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validate_handle(handle: str) -> str:
    normalized = handle.removeprefix("@").lower()
    if not re.fullmatch(r"[a-z0-9_]{1,15}", normalized):
        raise ValueError("handle must contain 1-15 letters, digits, or underscores")
    return normalized


def _output_names(
    handle: str,
    authored_start: datetime,
    authored_end: datetime,
    interaction_end: datetime,
) -> tuple[str, str, str]:
    authored_last = (_utc(authored_end) - timedelta(days=1)).date().isoformat()
    interaction_last = (_utc(interaction_end) - timedelta(days=1)).date().isoformat()
    first = _utc(authored_start).date().isoformat()
    subject_name = handle.split("_", 1)[0]
    return (
        f"{handle}_tweets_{first}_{authored_last}.jsonl",
        f"interactions_with_{subject_name}_{first}_{interaction_last}.jsonl",
        f"extraction_receipt_{first}_{interaction_last}.json",
    )


def build_query_plan(
    *,
    handle: str,
    authored_start: datetime,
    authored_end: datetime,
    interaction_end: datetime,
) -> dict[str, Any]:
    handle = _validate_handle(handle)
    authored_start = _utc(authored_start)
    authored_end = _utc(authored_end)
    interaction_end = _utc(interaction_end)
    if not authored_start < authored_end < interaction_end:
        raise ValueError("expected authored_start < authored_end < interaction_end")

    authored_name, interactions_name, receipt_name = _output_names(
        handle, authored_start, authored_end, interaction_end
    )
    authored_start_filter = f"gte.{_iso(authored_start)}"
    authored_end_filter = f"(created_at.lt.{_iso(authored_end)})"
    interaction_end_filter = f"(created_at.lt.{_iso(interaction_end)})"
    common = {"select": FIELDS, "created_at": authored_start_filter, "order": "created_at.asc"}

    return {
        "mode": "dry_run",
        "network_calls": 0,
        "handle": handle,
        "authored_output": authored_name,
        "interactions_output": interactions_name,
        "receipt_output": receipt_name,
        "queries": {
            "authored": {
                **common,
                "username": f"ilike.{handle}",
                "and": authored_end_filter,
            },
            "replies": {
                **common,
                "reply_to_username": f"ilike.{handle}",
                "and": interaction_end_filter,
            },
            "mentions": {
                **common,
                "full_text": f"ilike.*@{handle}*",
                "and": interaction_end_filter,
            },
            "quotes": {
                **common,
                "quoted_tweet_id": "in.(<authored_ids_chunk>)",
                "and": interaction_end_filter,
            },
        },
    }


def _dedupe(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {str(row["tweet_id"]): dict(row) for row in rows}
    return sorted(by_id.values(), key=lambda row: (str(row.get("created_at") or ""), str(row["tweet_id"])))


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    body = "\n".join(json.dumps(row, ensure_ascii=False, sort_keys=True) for row in rows)
    path.write_text(body + ("\n" if body else ""))


def _source_receipt(path: Path, rows: int) -> dict[str, Any]:
    return {
        "logical_path": f"data/{path.name}",
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "bytes": path.stat().st_size,
        "rows": rows,
    }


def acquire_window(
    *,
    source_root: Path,
    handle: str,
    authored_start: datetime,
    authored_end: datetime,
    interaction_end: datetime,
    fetch_pages: FetchPages,
) -> dict[str, Any]:
    plan = build_query_plan(
        handle=handle,
        authored_start=authored_start,
        authored_end=authored_end,
        interaction_end=interaction_end,
    )
    handle = plan["handle"]
    queries = plan["queries"]
    authored = _dedupe(fetch_pages("authored", queries["authored"]))
    authored_ids = {str(row["tweet_id"]) for row in authored}
    replies = fetch_pages("replies", queries["replies"])
    mentions = fetch_pages("mentions", queries["mentions"])
    quotes: list[dict[str, Any]] = []
    ordered_ids = sorted(authored_ids)
    for offset in range(0, len(ordered_ids), 80):
        chunk = ordered_ids[offset : offset + 80]
        params = {
            **queries["quotes"],
            "quoted_tweet_id": "in.(" + ",".join(chunk) + ")",
        }
        quotes.extend(fetch_pages("quotes", params))

    interactions: list[dict[str, Any]] = []
    for row in _dedupe(replies + mentions + quotes):
        if str(row.get("username") or "").lower() == handle:
            continue
        types: list[str] = []
        if (
            str(row.get("reply_to_tweet_id") or "") in authored_ids
            or str(row.get("reply_to_username") or "").lower() == handle
        ):
            types.append("reply")
        if str(row.get("quoted_tweet_id") or "") in authored_ids:
            types.append("quote")
        if f"@{handle}" in str(row.get("full_text") or "").lower():
            types.append("mention")
        row["interaction_types"] = sorted(set(types)) or ["interaction"]
        interactions.append(row)

    data_dir = source_root.expanduser().resolve() / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    tweets_path = data_dir / plan["authored_output"]
    interactions_path = data_dir / plan["interactions_output"]
    receipt_path = data_dir / plan["receipt_output"]
    _write_jsonl(tweets_path, authored)
    _write_jsonl(interactions_path, interactions)

    receipt = {
        "schema_version": "community-archive-extraction/v0.2",
        "source": "Community Archive REST enriched_tweets",
        "handle": f"@{handle}",
        "extracted_at": datetime.now(UTC).isoformat(),
        "window": {
            "authored_start_inclusive": _iso(authored_start),
            "authored_end_exclusive": _iso(authored_end),
            "interaction_end_exclusive": _iso(interaction_end),
        },
        "rows": {"authored": len(authored), "interactions": len(interactions)},
        "sources": {
            "authored": _source_receipt(tweets_path, len(authored)),
            "interactions": _source_receipt(interactions_path, len(interactions)),
        },
        "privacy": {
            "credentials_persisted": False,
            "raw_rows_remain_in_source_repository": True,
        },
    }
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def _network_fetcher() -> FetchPages:
    import requests

    docs = requests.get(DOCS_URL, timeout=30)
    docs.raise_for_status()
    match = re.search(r"eyJ[A-Za-z0-9_\-.]{100,}", docs.text)
    if not match:
        raise RuntimeError("Community Archive anonymous key was not found in its documentation")
    key = match.group(0)
    headers = {"apikey": key, "Authorization": f"Bearer {key}"}

    def fetch(kind: str, params: dict[str, str]) -> list[dict[str, Any]]:
        del kind
        rows: list[dict[str, Any]] = []
        offset = 0
        while True:
            page_params = {**params, "limit": "1000", "offset": str(offset)}
            response = requests.get(API_URL, headers=headers, params=page_params, timeout=60)
            response.raise_for_status()
            page = response.json()
            if not isinstance(page, list):
                raise RuntimeError("Community Archive returned a non-list response")
            rows.extend(page)
            if len(page) < 1000:
                return rows
            offset += 1000

    return fetch


def _parse_time(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise argparse.ArgumentTypeError("timestamps must include a timezone")
    return parsed.astimezone(UTC)


def assert_horizon_mature(*, interaction_end: datetime, now: datetime) -> None:
    if _utc(now) < _utc(interaction_end):
        raise RuntimeError(
            f"refusing immature acquisition: interaction horizon ends {_iso(interaction_end)}, "
            f"now {_iso(now)}"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Plan or execute Community Archive window acquisition")
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--handle", default="leo_guinan")
    parser.add_argument("--authored-start", type=_parse_time, required=True)
    parser.add_argument("--authored-end", type=_parse_time, required=True)
    parser.add_argument("--interaction-end", type=_parse_time, required=True)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="make external requests and write raw rows; default is a network-free query plan",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    plan = build_query_plan(
        handle=args.handle,
        authored_start=args.authored_start,
        authored_end=args.authored_end,
        interaction_end=args.interaction_end,
    )
    if not args.execute:
        print(json.dumps(plan, indent=2, sort_keys=True))
        return
    try:
        assert_horizon_mature(interaction_end=args.interaction_end, now=datetime.now(UTC))
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc
    receipt = acquire_window(
        source_root=args.source_root,
        handle=args.handle,
        authored_start=args.authored_start,
        authored_end=args.authored_end,
        interaction_end=args.interaction_end,
        fetch_pages=_network_fetcher(),
    )
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
