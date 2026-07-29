# Community Archive H-CA-03/H-CA-04 evaluability audit v0.1

**Status:** executed; both targets `not_evaluatable_yet`
**Executed:** 2026-07-29
**Machine receipt:** `runs/community-archive-evaluability-v0.1.json`

## Purpose

Resolve whether H-CA-03 and H-CA-04 were merely unimplemented or lacked the
label and feature support required by the frozen benchmark contract.

This is an evaluability audit, not a predictive model.

## Contract

- Reuse the benchmark's July 16–18 complete 24-hour holdouts.
- Build candidates only from matured training rows.
- H-CA-03 positive label: a held-out post receives at least one interaction
  from an account absent from the fold's training candidate set.
- H-CA-04 classes: target-specific reply and quote edges derived from
  `reply_to_tweet_id` and `quoted_tweet_id`.
- Do not infer event type from the mixed `interaction_types` list.
- Exclude mentions without target-post linkage.
- Require at least 30 observations in every modeled class.
- Relationship or cross-population features must predate every prediction.

## Source receipts

| Source | Rows | SHA-256 |
|---|---:|---|
| Authored posts | 870 | `640b85746a6b148591b6dcb03945e342a6e8729e717b077d39cb2574375a97af` |
| Interaction records | 178 | `9455d4cf22cdd641721853ef3af683cf9066a0bb8ff43ac60bdc4749b762a61e` |
| Window contract | — | `2845630b691062ed972ec5b35dfbff02aa1c38edac31c66dde2e965b91bc06ee` |
| July 29 relationship snapshot | — | `4dc4a6d8d5097c9f27b74cad9dd98bf3a485a3cf91e4ff7a8ab5a7c473f2a2c4` |

The relationship snapshot records only `observed_at: 2026-07-29`. The runner
uses UTC midnight as the earliest possible instant. It still postdates all
July 16–18 predictions, so the conclusion is invariant to the missing clock
time.

## H-CA-03: not evaluatable yet

| Class or support quantity | Count |
|---|---:|
| Posts with a new-account interaction | 25 |
| Posts without a new-account interaction | 313 |
| New-account events | 29 |
| Seen-account events | 17 |
| All account events | 46 |

Blockers:

1. Positive post support is `25`, below the frozen floor of `30`.
2. The July 29 cross-population/relationship snapshot postdates prediction.

The label is nearly supported. The claimed feature family is not temporally
valid. Running a content-only substitute would test a different hypothesis.

## H-CA-04: not evaluatable yet

| Target-specific class | Count |
|---|---:|
| Linked replies | 44 |
| Linked quotes | 3 |
| Ambiguous linked events | 0 |
| Excluded unlinked mentions | 8 |

Blockers:

1. Quote support is `3`, below the frozen floor of `30`.
2. The July 29 relationship snapshot postdates prediction.
3. Mentions cannot be assigned to authored target posts and therefore cannot
   repair class support.

The old descriptive table copied every row's complete `interaction_types` list
to each reply/quote target. This audit uses target fields instead. Otherwise a
reply that also mentions someone can masquerade as evidence for a mention-type
post outcome. The data had enough ambiguities already.

## Privacy boundary

The receipt contains aggregate fold counts, source hashes, and day-level
boundaries only. Source logical paths identify the subject account. It emits no
text, post IDs, interacting-account identities, raw rows, or exact post
timestamps.

## Decision

H-CA-03 and H-CA-04 move from `deferred_to_v0.2` to
`not_evaluatable_yet`. No model should run on the current window.

A future run requires:

- enough non-overlapping future data to meet every class floor; and
- a relationship or cross-population snapshot observed before the prediction
  window, or a formally revised hypothesis that excludes those features.

The research goal remains locked. No Layer 08.

## Reproduction

```bash
python3 -m community_archive_prediction.evaluability_audit \
  --source-root ~/Projects/leo-twitter-audience-model \
  --output evidence/runs/community-archive-evaluability-v0.1.json \
  --relationship-snapshot-at 2026-07-29T00:00:00+00:00 \
  --minimum-class-support 30
```
