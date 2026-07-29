# P versus NP

**Status:** Open problem

> Build In Public University research goal: pursue the hardest questions while making every step auditable, falsifiable, and useful to adjacent problems.

## Mandate

Determine whether every problem whose solution can be verified quickly can also be solved quickly.

This repository is a research laboratory, not a claim that the problem is solved or that an idea is correct. Contributions must separate established results, conjectures, analogies, computations, and speculation.

## Active empirical goal

Use Community Archive as a noisy, partial-observation testbed to determine
which future public interaction and propagation attributes are predictably
identifiable from a time-bounded network state. Compare content, topology,
recurrence, and cross-population position against boring priors on at least
three chronological holdouts.

The frozen contract is in `RESEARCH_GOAL.md`. Benchmark v0.1 exists, but the
goal remains locked: H-CA-01 was not supported, H-CA-02 was underpowered, and
the evaluability audit found H-CA-03/H-CA-04 below their class floors with
postdated topology. The project therefore adds no Layer 08 and makes no public
claim that archive topology predicts behavior.

The next prospective window is frozen in
`evidence/community-archive-next-window-v0.2.json`. Its acquisition CLI defaults
to a zero-network dry run and requires both explicit `--execute` and a mature
interaction horizon.

The contract-driven evaluator is implemented in
`community_archive_prediction/prospective.py`. It verifies source and topology
hashes, maturity, exact holdouts, and support before fitting any eligible target.
H-CA-04 is explicitly conditional reply-versus-quote classification; it does not
claim to predict whether an account interacts. The real v0.2 receipt does not
exist yet and is scheduled only after the August 15 label boundary.

This is an empirical stress test of the observation-relative framework. It is
not evidence for either side of P versus NP.

## Research lanes

- `ideas/` — one hypothesis or question per file.
- `connections/` — explicit bridges between concepts, fields, methods, or datasets.
- `evidence/` — sources, calculations, counterexamples, failed attempts, and replication notes.
- `papers/` — paper generators: proposed question, contribution, method, result needed, and falsifier.

## First instrument: sampling versus prediction

`network_relativity/` contains a finite-world instrument for the first bounded
Network Relativity claim: a network can validate a task exactly only when the
task answer is invariant across all worlds that produce the same sensor
observations.

The instrument distinguishes three regimes:

- `local` — one node's samples determine the answer;
- `distributed` — the combined samples determine the answer, but no node can
  validate it alone;
- `predictive` — observationally identical worlds require different answers,
  so exact validation is impossible without another sensor or an assumption.

Run it with no third-party dependencies:

```bash
python3 -m pytest -q
python3 -m network_relativity.experiment \
  --output evidence/runs/network-observation-v0.7.json
```

The generated receipt measures finite observational identifiability, the best
accuracy under a uniform prior, and a topology-dependent aggregation radius.
It does not measure classical time complexity and does not resolve P versus NP.

### Interactive Observation Lab

The progressive browser workbench in `web/` exposes the same first model as a
playable instrument. Configure world bits, task, topology, and each node's
sensor scope; the UI recomputes the validation regime, prediction ceiling,
aggregation radius, observational classes, and exact counterexample worlds.
Its second layer adds a selectable validation root, explicit evidence routes,
and separate round, message, raw-forwarding, and task-aggregation costs.
Its third layer finds the smallest source-grounded attestation bundle that
determines the current answer at the selected root. It reports issuer placement,
logical payload, compatible worlds, unavailable certificates, and the remaining
sensor-honesty and identity assumptions.
Its fourth layer holds the world static while sensor scopes and connectivity
change across epochs. It separates current-epoch identifiability, cumulative
cached identifiability, and whether the prior certificate remains fresh.
Its fifth layer separates spacetime events from private desired futures. It
compares self-only, cross-modeled, and oracle local targets under explicit
authorization, tracks idea accumulation, and keeps desired, proposed, and
realized worlds distinct.
Its sixth layer replaces endpoint-only comparison with finite prospective
trajectories and receiver-declared transition envelopes. It detects direction,
horizon, authorization, rate, and positive-acceleration conflicts, then finds
the shortest accepted witness when one exists. Logical transition load is not
reported as physical energy or Landauer dissipation.
Its seventh layer separates prediction correction from irreversible reset. It
enforces a before-next-message register contract, computes conditional erasure
entropy with retained side information and corrective messages, and reports the
ideal `k_B T ln(2)` floor only for explicitly declared erased entropy. Repeated
floors are summed only across declared independent reset boundaries; actual
device, communication, computation, and human energy remain unmeasured.

```bash
python3 -m http.server 8900 --directory web
```

Open `http://localhost:8900`. The page is self-contained, persists local state,
and exports configurations as JSON receipts.

## Minimum viable idea

Every idea should state:

1. the exact question;
2. what is already known;
3. the proposed mechanism;
4. why the connection may be nontrivial;
5. the smallest calculation, proof attempt, experiment, or close reading;
6. what would falsify or downgrade it;
7. which adjacent problem might benefit even if the main conjecture fails.

## Ambition

The trajectory is deliberately extreme: produce work that could change the boundary of the field. The operating rule is deliberately unromantic: no breakthrough language without a chain of inspectable intermediate artifacts.

## Research integrity

Do not present an analogy as a theorem, a correlation as a mechanism, an AI-generated suggestion as an idea with provenance, or an unreviewed preprint as established science. Preserve failed paths. Name collaborators and sources. Respect human-subjects, biosafety, dual-use, and intellectual-property constraints.
