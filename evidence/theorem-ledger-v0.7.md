# Theorem and claim ledger — v0.7

**Status:** consolidation receipt, not a P versus NP result

**Instrument:** `network_relativity/`
**Generated evidence:** `evidence/runs/network-observation-v0.7.json`

## Classification

- **Established:** standard fact used by the instrument.
- **Finite corollary:** follows directly inside the declared finite model.
- **Implementation invariant:** true because the executable contract enforces it.
- **Conjectural bridge:** proposed connection to empirical archive-network prediction; unproved.

## Ledger

| ID | Statement | Class | Receipt or proof burden |
|---|---|---|---|
| T-01 | For finite world set `W`, observation map `O`, and task `f`, an exact validator based only on `O(w)` exists iff `f` is constant on every fiber of `O`. | Established | Necessity: identical observations must receive one output. Sufficiency: map each observation class to its common task value. Executed in `analyze_identifiability`. |
| T-02 | A case is distributed-but-not-local when the joint observation determines `f` and every individual node observation fails to determine `f`. | Finite corollary | Exhaustive finite counterexample search in v0.1 fixtures. This is a classification, not an asymptotic complexity separation. |
| T-03 | Changing network topology while holding sensors and task fixed can change communication rounds without changing observational identifiability. | Finite corollary | v0.2 path/clique fixtures; topology affects routes, not observation fibers. |
| T-04 | A source-grounded certificate is sufficient only when every world compatible with its attested facts has the same task answer. | Implementation invariant | Exhaustive compatible-world enumeration in v0.3. Minimality is by finite enumeration in the instrument, not a general complexity theorem. |
| T-05 | In a static world with lossless retained observations, cumulative observational information cannot decrease as epochs are appended. | Finite corollary | v0.4 rotating-sensor fixture. It does not apply when the world changes, cache entries expire, or provenance is invalidated. |
| T-06 | An inferred private desire without authorization cannot alter the realized action in the v0.5 protocol. | Implementation invariant | Authorization gate is deny-by-default. This is a protocol property, not a claim about human behavior. |
| T-07 | Endpoint equality is insufficient for trajectory compatibility when direction, timing, transition-rate, or acceleration constraints differ. | Finite corollary | v0.6 blind-spot probe: all four cases share endpoint and horizon; two violate acceleration constraints. |
| T-08 | A correction cycle is next-message ready iff the corrected state matches the observation and every register required by the reset contract is cleared. | Implementation invariant | `evaluate_correction_cycle`; blocked correction and uncleared-syndrome fixtures. |
| T-09 | In the declared finite ensemble, corrective-message value is `H(Z|Y) - H(Z|Y,M)`, and the ideal avoided erasure floor is `k_B T ln(2)` times that difference. | Established + finite calculation | v0.7 helpful/constant-message ensembles. No measured device energy. |
| T-10 | Independent reset boundaries permit addition of their declared ideal floors; dependent boundaries require a joint ensemble rather than a guessed sum. | Established modeling rule + invariant | v0.7 emits `null` for dependent aggregate floor. |
| C-01 | Future visible archive interactions may be bounded by observation classes induced by content, topology, recurrence, and source coverage. | Conjectural bridge | Requires chronological archive benchmark and comparison against class-frequency/Bayes-style ceilings. |
| C-02 | Relationship topology may add predictive information beyond content for previously observed interactors. | Conjectural bridge | Existing seven-day pilot is preliminary evidence against a simple three-day recency boost. Must survive at least three held-out windows. |
| C-03 | Cross-population position may predict second-hop propagation. | Conjectural bridge | Currently not evaluatable: 36 bridge posts and zero observed audience-response positives. |

## What this establishes

The seven-layer instrument gives exact finite answers to questions about observational equivalence, communication, certificates, retained evidence, authorization, trajectory envelopes, and declared erasure entropy.

## What this does not establish

It does not establish:

- `P = NP` or `P != NP`;
- an asymptotic lower bound;
- a new complexity class;
- that social behavior is deterministic or generally predictable;
- that topology means trust, influence, or truth;
- that a real device approaches the Landauer floor;
- novelty relative to the full literature.

## Next proof work

Before manuscript language:

1. formalize T-01 through T-10 with definitions independent of Python;
2. identify citations and prior formulations for each established statement;
3. separate exhaustive finite algorithms from general decision problems;
4. state runtime in `|W|`, node count, and candidate-certificate count;
5. test whether any archive-network result survives boring frequency and shuffled-time controls;
6. publish nulls and `not_evaluatable_yet` outcomes with the same prominence as wins.
