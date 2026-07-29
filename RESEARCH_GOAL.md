# Active research goal

**Status:** v0.1 executed; goal remains locked
**Set:** 2026-07-29
**Executed:** 2026-07-29

## Goal

Determine which future public interaction and propagation attributes are predictably identifiable from a time-bounded Community Archive network state, and quantify when topology, content, recurrence, and cross-population position add held-out information beyond boring priors.

Community Archive is the empirical testbed for the observation-relative framework. This does not turn social prediction into a proof about P versus NP. It tests whether the framework survives noisy, partial, asynchronous observations outside toy worlds.

## Primary benchmark

Given only information available before prediction time `t`, predict:

1. whether an authored post receives a visible direct reply, quote, or mention;
2. which previously observed account interacts;
3. whether the event comes from a previously unseen account;
4. which visible interaction type occurs;
5. when labels become evaluable, whether a bridge post produces observed second-hop propagation.

The first four are active targets. The fifth remains `not_evaluatable_yet` because the current two-hop ledger contains zero positive audience-response events.

## Success criterion

The goal is unlocked only when a versioned benchmark receipt contains:

- at least three chronological held-out windows;
- global-rate, frequency, content-only, topology-only, and recurrence-only baselines;
- a combined model evaluated on the same rows and candidate set;
- average precision, Brier score, and calibration for binary targets;
- Recall@5, Recall@10, MRR, candidate coverage, and new-account share for account ranking;
- confidence intervals or per-window dispersion;
- false-positive and false-negative specimen receipts;
- explicit `not_evaluatable_yet` states for targets without sufficient positives or synchronized snapshots;
- a machine-readable result at
  `evidence/runs/community-archive-prediction-v0.1.json`.

Success is not “the combined model wins.” A clean null or baseline victory satisfies the research goal if the receipt is complete.

## Research lock

The v0.1 receipts exist, but the goal remains locked: H-CA-02 has only 17
seen-account events against the frozen floor of 30; H-CA-03 has 25 new-account
posts and a postdated relationship snapshot; H-CA-04 has only 3 linked quotes
and the same postdated snapshot.

The prospective v0.2 contract freezes July 30–August 13 authored posts, a
24-hour interaction horizon through August 14, and the July 29 relationship
snapshot. Acquisition requires separate external approval and cannot run before
August 15 UTC.

The v0.2 evaluator is built but has not seen the future window. It performs
hash, maturity, topology, holdout, and support preflight before fitting models;
unsupported targets emit no model metrics. H-CA-01 requires both binary classes,
H-CA-03 uses sequential training-only partition-topic context, and H-CA-04 is a
conditional linked-event reply-versus-quote task. None of this unlocks Layer 08
before the real receipt exists.

While the goal remains locked:

- no Layer 08;
- no new ontology for attention, trust, influence, energy, or intelligence;
- no public claim that archive topology predicts behavior;
- no model promotion from the existing seven-day pilot;
- no use of future engagement, future graph state, or post-outcome labels as features.

Allowed work:

- freeze the source and snapshot contract;
- construct chronological examples;
- implement boring baselines;
- run leakage tests and shuffled-time controls;
- produce calibration, residual, and error receipts;
- acquire a later public-data window with explicit approval and provenance;
- attach outcomes to currently unscored bridge claims.

## Current prior

The existing pilot is weak evidence, not a win:

- direct-interaction text model: ROC AUC `0.554`, average precision `0.106`;
- test positive rate: `0.086`;
- specific-account content Recall@5/10: `0.462 / 0.462`;
- content plus three-day recency Recall@5/10: `0.385 / 0.462`;
- new-account share of held-out interaction events: `0.364`;
- observed second-hop propagation positives: `0`.

The first combined benchmark therefore began with a negative prior: recurrence may add no value, and observed propagation may remain unevaluable.

## v0.1 outcome

The benchmark used the last three complete 24-hour label windows: July 16,
17, and 18. Across 338 held-out posts it observed 40 positive posts and 46
account events.

- H-CA-01: `not_supported` on the evaluable reply/quote subset; mentions lack
  target-post linkage. Content-only average precision exceeded the global rate
  by `0.035526` on average, but the deterministic shuffled-time control
  matched or exceeded observed content AP in all three windows.
- H-CA-02: `unresolved_underpowered`. Only 17 account events came from accounts
  in the matured training candidate sets, below the frozen floor of 30.
- H-CA-03: `not_evaluatable_yet`. There are 25 new-account posts, below the
  class floor of 30, and the cross-population snapshot postdates prediction.
- H-CA-04: `not_evaluatable_yet`. There are 44 linked replies but only 3 linked
  quotes; the relationship snapshot also postdates prediction.
- Account frequency remained the best descriptive Recall@10 baseline at
  `0.588235`; combined ranking reached `0.411765`.
- Topology remained unavailable because the relationship snapshot postdates
  every prediction window.

The machine receipt is `evidence/runs/community-archive-prediction-v0.1.json`;
its interpretation is `evidence/community-archive-prediction-v0.1.md`.

## Boundaries

The program predicts visible public archive events, not:

- impressions or lurkers;
- private analytics;
- like-by-user attention when identity is absent;
- complete retweet identity;
- trust, intent, endorsement, truth, or influence;
- current X state beyond the recorded source window.

Raw social data remains in its source repository. This repository stores aggregate receipts, schemas, hypotheses, and public-safe error specimens only.

## Linked artifacts

- `ideas/2026-07-29-community-archive-network-prediction.md`
- `evidence/community-archive-network-substrate-v0.1.md`
- `evidence/community-archive-hypotheses-v0.1.json`
- `evidence/community-archive-prediction-v0.1.md`
- `evidence/community-archive-evaluability-v0.1.md`
- `evidence/community-archive-next-window-v0.2.json`
- `evidence/runs/community-archive-prediction-v0.1.json`
- `evidence/runs/community-archive-evaluability-v0.1.json`
- `evidence/theorem-ledger-v0.7.md`
