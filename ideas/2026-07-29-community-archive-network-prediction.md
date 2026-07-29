# Community Archive network prediction

**Status:** active empirical research program

**Hypotheses frozen:** 2026-07-29
**Machine ledger:** `evidence/community-archive-hypotheses-v0.1.json`

## Question

Which future visible public interaction and propagation attributes are identifiable or predictably compressible from a time-bounded Community Archive network state?

## Why this belongs here

The seven-layer finite instrument asks what a network can know from partial observations, what must move between nodes, which certificates determine an answer, how cached evidence changes over time, which trajectories are admissible, and which corrections require reset.

Community Archive provides a noisy empirical testbed for the same discipline:

- observations are incomplete;
- graph snapshots have boundaries;
- interaction identities are sometimes unresolved;
- future events can disagree inside the same observed profile;
- recurrence can look predictive while leaking time;
- propagation can be absent rather than merely small.

The bridge is methodological. No social classifier result is evidence for `P = NP` or `P != NP`.

## Active targets

1. visible direct interaction on an authored post;
2. specific previously observed interacting account;
3. previously unseen interacting account;
4. visible interaction type: reply, quote, or mention.

Deferred until evaluable:

5. second-hop bridge propagation;
6. follow-relationship transitions;
7. claim outcome accuracy.

## Frozen benchmark

Unit of prediction:

- an authored post or eligible account-post pair at prediction time `t`;
- features strictly available before `t`;
- a declared future label window;
- a candidate set constructed from training data only.

Chronology:

- rolling-origin evaluation;
- at least three held-out windows;
- no random train/test split for the primary result;
- source and graph snapshots must predate each prediction.

Boring baselines:

- global positive rate;
- account frequency;
- content-only;
- topology-only;
- recurrence-only.

Challenger:

- content + topology + recurrence, with the same rows and candidate set.

Controls:

- shuffled event times;
- shuffled account labels within each window;
- feature ablations;
- duplicate and future-state leakage audit.

Metrics:

- binary targets: average precision primary, then ROC AUC, Brier score, and calibration error;
- account ranking: Recall@5, Recall@10, MRR, candidate coverage, and new-account share;
- per-window metrics and dispersion, not one pooled number wearing a lab coat.

## Hypotheses

### H-CA-01 — Content predicts visible direct interaction

Prediction: content-only average precision exceeds the global-rate baseline across held-out windows.

Current prior: weak positive. One slice produced AP `0.106` against positive rate `0.086`, with ROC AUC `0.554`.

Falsifier: no positive AP delta in at least two held-out windows.

### H-CA-02 — Recurrence adds specific-account information

Prediction: combined content, frequency, and recurrence improves Recall@10 over the best single-family baseline.

Current prior: preliminary negative. The existing three-day boost reduced Recall@5 from `0.462` to `0.385` and left Recall@10 at `0.462`.

Falsifier: no improvement over the best boring baseline, or apparent improvement survives only in unshuffled time.

### H-CA-03 — Cross-population context predicts new-account events

Prediction: content and cross-population topic position predict whether an interaction comes from an unseen account better than the global new-account rate.

Current prior: untested; new accounts formed `0.364` of held-out events.

Falsifier: account activity volume or global rate explains the result.

### H-CA-04 — Relationship state predicts interaction type

Prediction: frozen relationship partition and prior event type improve macro average precision for reply/quote/mention classification over content alone.

Falsifier: insufficient class support or no held-out improvement.

### H-CA-05 — Cross-population position predicts propagation

Prediction: topology plus bridge-post content beats candidate activity after sufficient positive events accrue.

Status: `not_evaluatable_yet`. Current ledger contains `36` bridge posts and `0` observed audience-response positives.

### H-CA-06 — Interaction predicts relationship transition

Prediction: repeated public interaction predicts one-sided-to-mutual follow transition beyond the base transition rate.

Status: `not_evaluatable_yet`. Only one synchronized relationship snapshot exists.

### H-CA-07 — Observation classes bound exact prediction

Prediction: a model using a declared feature partition cannot exceed the empirical class-conditional ceiling computed from that partition.

Falsifier: a leakage-free model exceeds the ceiling, which would expose an error in the partition or ceiling calculation.

### H-CA-08 — Network position predicts claim accuracy

Status: `not_evaluatable_yet`. The claim ledger exists, but all outcomes are unscored and no independent rubric is frozen.

No accuracy hypothesis will be promoted until labels exist. Attention is not truth with better typography.

## Data and privacy boundary

Raw records remain in `../leo-twitter-audience-model`. This repository receives:

- aggregate source receipts;
- schemas;
- feature definitions;
- model configurations;
- public-safe error specimens;
- metrics and confidence intervals.

It does not receive private messages, private analytics, unresolved identity guesses, or raw archives merely because git can technically hold them.

## First executable milestone

Build `community_archive_prediction/` only after preserving the current checkpoint. The first run should implement H-CA-01 and H-CA-02, reuse the source repository read-only, and emit:

- `evidence/runs/community-archive-prediction-v0.1.json`;
- per-window baseline and challenger metrics;
- FP/FN specimens;
- leakage checks;
- explicit evaluability states for H-CA-03 through H-CA-08.

The outcome may be null. The artifact may not be absent.
