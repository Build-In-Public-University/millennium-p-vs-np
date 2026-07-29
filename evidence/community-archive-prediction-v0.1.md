# Community Archive prediction benchmark v0.1

**Status:** executed; H-CA-01 not supported, H-CA-02 underpowered
**Executed:** 2026-07-29
**Machine receipt:** `runs/community-archive-prediction-v0.1.json`

## Question

Can content or recent relationship history predict visible future public
interaction better than boring priors when every feature, label, and candidate
set is restricted to information available before prediction time?

## Frozen run contract

- Source window ends `2026-07-20T00:00:00+00:00`.
- A direct interaction is a reply or quote targeting an authored post within
  24 hours after publication.
- Mentions are excluded because the archive cannot link them to a specific
  authored target post.
- Holdouts are the last three UTC days with complete 24-hour label horizons:
  July 16, 17, and 18.
- Training rows must have matured before each daily cutoff.
- Account candidates must occur in matured training rows.
- Models do not update within a holdout.
- Raw text, post IDs, and account identities are excluded from the receipt.

July 19 was not scored because its posts do not have a complete 24-hour label
window before the source boundary.

## Source receipts

| Source | Rows | SHA-256 |
|---|---:|---|
| Authored posts | 870 | `640b85746a6b148591b6dcb03945e342a6e8729e717b077d39cb2574375a97af` |
| Interaction records | 178 | `9455d4cf22cdd641721853ef3af683cf9066a0bb8ff43ac60bdc4749b762a61e` |
| Prior window contract | — | `2845630b691062ed972ec5b35dfbff02aa1c38edac31c66dde2e965b91bc06ee` |

The raw records remain in the sibling source repository.

## Support

| Quantity | Count |
|---|---:|
| Held-out posts | 338 |
| Positive held-out posts | 40 |
| Held-out account events | 46 |
| Seen-account events eligible for ranking | 17 |
| New or otherwise out-of-candidate account events | 29 |

## H-CA-01 outcome: not supported on the reply/quote subset

This run does not resolve the mention portion of H-CA-01. For linked replies
and quotes, content-only AP exceeded the global-rate AP in all three windows. The mean
window AP increased from `0.123435` to `0.158961`, a nominal delta of
`+0.035526`.

That is not sufficient evidence. A deterministic one-row rotation of event
labels produced AP at least as high as the observed content model in all three
windows. The receipt therefore marks H-CA-01 `not_supported`, not supported and
not falsified universally.

| Binary model | Mean AP | Mean ROC AUC | Mean Brier | Mean calibration error |
|---|---:|---:|---:|---:|
| Global positive rate | 0.123435 | 0.500000 | 0.108867 | 0.048307 |
| Content only | 0.158961 | 0.567234 | 0.198632 | 0.290901 |
| Recurrence only | 0.250967 | 0.582045 | 0.321673 | 0.462903 |
| Combined | 0.153574 | 0.570743 | 0.247279 | 0.364316 |

Recurrence-only produced the highest AP, but its Brier score was nearly three
times the global prior and its calibration error was `0.462903`. This is a
ranking curiosity, not a deployable predictor. Combined modeling did not repair
it.

## H-CA-02 outcome: unresolved underpowered

Only 17 seen-account events were rankable, below the frozen floor of 30.
Descriptive metrics reinforce the prior negative result but cannot resolve the
hypothesis.

| Ranking model | Weighted Recall@5 | Weighted Recall@10 | Weighted MRR |
|---|---:|---:|---:|
| Account frequency | 0.352941 | 0.588235 | 0.213445 |
| Content only | 0.117647 | 0.294118 | 0.084972 |
| Recurrence only | 0.352941 | 0.411765 | 0.191322 |
| Combined | 0.294118 | 0.411765 | 0.224056 |

Account frequency beat combined Recall@10 by `0.176470`. Combined improved MRR
slightly, but the support floor was not met and the shuffled-account control was
not cleanly lower.

## Other targets

- H-CA-03: not evaluatable; a subsequent audit found 25 new-account posts and
  a relationship snapshot that postdates prediction.
- H-CA-04: not evaluatable; the audit found 44 linked replies, 3 linked quotes,
  and the same postdated relationship snapshot.
- H-CA-05: not evaluable; zero propagation positives.
- H-CA-06: not evaluable; one relationship snapshot.
- H-CA-07: deferred; observation partition not frozen.
- H-CA-08: not evaluable; claim outcomes remain unscored.
- Topology baseline: not evaluable because the relationship snapshot postdates
  every prediction window.

## Limitations

- Three adjacent daily windows are not three independent populations.
- The time control is one deterministic rotation, not a full permutation
  distribution.
- Account ranking covers only `17/46` held-out account events.
- Visible replies and quotes are not total attention, impressions, endorsement,
  trust, influence, or truth.
- No causal claim follows from any metric in this receipt.

## Consequence

The v0.1 pipeline is executable and leakage-bounded. The empirical program is
not complete. The goal remains locked until a later source window provides at
least 30 seen-account events and H-CA-03/H-CA-04 are evaluated or explicitly
retired under a revised frozen contract.

## Reproduction

```bash
python3 -m community_archive_prediction.experiment \
  --source-root ~/Projects/leo-twitter-audience-model \
  --output evidence/runs/community-archive-prediction-v0.1.json
```

The generated timestamp may change. Source hashes, support, folds, metrics,
controls, and outcomes must not change while the source receipts are unchanged.
