# Community Archive network substrate — v0.1

**Observed:** 2026-07-29

**Source repository:** sibling local repository `leo-twitter-audience-model`
**Policy:** source data stays in the source repository; this file records aggregate capabilities and gaps.

## Available substrates

### Seven-day public interaction window

Source artifacts:

- `data/leo_guinan_tweets_2026-07-12_2026-07-19.jsonl`
- `data/interactions_with_leo_2026-07-12_2026-07-19.jsonl`
- `data/tweet_feature_table.jsonl`
- `reports/audience_model_results.json`

Verified aggregate receipt:

- authored posts: `870`;
- posts with visible direct interactions: `118`;
- visible reply/quote/mention events: `140`;
- interacting accounts: `68`;
- repeat accounts with at least two events: `30`;
- chronological test posts: `233`;
- chronological test interaction events: `22`;
- held-out events from accounts unseen in training: `8`;
- held-out seen-account events evaluated: `13`.

Existing preliminary baselines:

- text-only direct-interaction ROC AUC: `0.554`;
- text-only average precision: `0.106`;
- held-out positive rate: `0.086`;
- content Recall@5/10 for seen accounts: `0.462 / 0.462`;
- content plus three-day recency Recall@5/10: `0.385 / 0.462`;
- new-account event share: `0.364`.

Interpretation: text signal is weak; the simple recency boost did not improve Recall@10 and reduced Recall@5. These are priors for the frozen benchmark, not promoted results.

### Attention, relationship, and distribution ledgers

Source: `reports/three_ledger_manifest.json`.

- attention rows: `870`; account identities resolved: `0`;
- relationship rows: `129`; account identities resolved: `129`;
- distribution rows: `119`; identities resolved: `12`;
- account rollup rows: `68`.

Usable now:

- visible reply/direct-mention recurrence;
- visible quote identity where present;
- aggregate favorite and retweet counts as post-level outcomes;
- topic and structure features;
- previously seen versus new interacting account.

Not usable now:

- account-level like attention;
- complete retweet-by-user amplification;
- impressions, views, or lurker composition.

### Archive relationship graph

Source artifacts:

- `data/relationship_graph_2026-07-29/relationship_snapshot.json`
- `data/relationship_graph_2026-07-29/relationship_nodes.jsonl`
- `data/relationship_graph_2026-07-29/relationship_edges.jsonl`

Snapshot aggregates:

- followers: `3,052`;
- following: `1,684`;
- mutual: `920`;
- follower-only: `2,132`;
- following-only: `764`;
- graph nodes: `8,218`;
- graph edges: `9,411`;
- authored mentions: `32,492`;
- authored replies to other accounts: `16,457`.

Usable now:

- frozen mutual/follower-only/following-only partitions;
- historical authored interaction frequency;
- topology-versus-interaction discordance.

Not usable now:

- follower gain/loss prediction;
- relationship lifecycle labels;
- current follow state.

Reason: there is one synchronized relationship snapshot, not a sequence.

### Cross-population and propagation artifacts

Source artifacts:

- `data/cross_population_account_metrics.jsonl`
- `data/leo_candidate_bridge_posts.jsonl`
- `data/two_hop_propagation_edges.jsonl`
- `data/claim_outcome_ledger.jsonl`

Aggregates:

- cohort accounts: `76`;
- directed cohort edges: `157`;
- mutual account pairs: `31`;
- bridge posts carrying a source post into a candidate timeline: `36`;
- bridge posts with observed audience response: `0`;
- observed two-hop edges: `0`;
- candidates with bridge posts: `21`;
- claim outcomes scored: `0`.

Second-hop propagation, trust transfer, and claim accuracy are therefore `not_evaluatable_yet`.

## Coverage and leakage boundary

Every benchmark row must carry:

- source table/file;
- observation timestamp or snapshot boundary;
- prediction timestamp;
- label window;
- account candidate-set rule;
- whether identity is resolved;
- whether the row is archive-upload, extension/API incremental, or aggregate-only;
- freshness caveat.

Forbidden features:

- engagement observed after prediction time;
- relationship membership from a snapshot later than prediction time;
- labels inferred from unresolved aggregate counts;
- private messages, private analytics, or unpublished identity joins;
- future topic labels derived from the outcome text.

## Verdict

The substrate is sufficient for a first chronological benchmark of visible direct interaction and seen-account recurrence. It is insufficient for claims about propagation, relationship transitions, trust, truth, or total audience reach.
