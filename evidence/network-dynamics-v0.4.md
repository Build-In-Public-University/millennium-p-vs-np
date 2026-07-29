# Evidence: dynamic networks v0.4

- Date: 2026-07-29
- Status: implemented synthetic instrument
- Artifact: `runs/network-observation-v0.4.json`
- Method: exhaustive enumeration of all 16 four-bit worlds for OR and PARITY

## Frozen temporal contract

A run holds the hidden world fixed while network snapshots change.

At every epoch:

1. sensor scopes and edges are fixed for that epoch;
2. every sensor connected to verifier N0 delivers its current observation within the epoch;
3. the verifier retains observations from prior epochs;
4. instantaneous identifiability uses only current-epoch facts;
5. cumulative identifiability uses every retained fact;
6. prior-certificate freshness requires each attesting issuer to remain reachable and to retain the attested variable in its scope.

This is an epoch model, not a packet-level dynamic-network simulator.

## Scenarios

### Rotating sensor

The path stays connected. At epoch `t`, only Nt samples xt.

| Task | Eventual cumulative exact worlds | Never instantaneous exact | Earliest cumulative epoch |
|---|---:|---:|---|
| OR | 16/16 | 1/16 | t0: 8, t1: 4, t2: 2, t3: 2 |
| PARITY | 16/16 | 16/16 | t3: 16 |

PARITY supplies the clean temporal separation: no individual epoch contains enough information, but the static-world cache does after all four variables have appeared.

OR is asymmetric. Any sampled `1` proves TRUE immediately. The all-zero world requires all four sampled zeros and becomes exact only at t3.

### Root-link failure

Epoch 0 is a connected distributed path. At epoch 1, edge N0—N1 disappears and isolates the verifier from N1–N3.

| Task | Cached exact after failure | Stale prior-certificate events |
|---|---:|---:|
| OR | 16/16 | 8 |
| PARITY | 16/16 | 16 |

Cached facts remain sufficient because the world is assumed static. Freshness does not: every PARITY certificate used remote issuers, so all 16 become unrefreshable after the cut.

For OR, the eight worlds with x0=1 validate locally and need no remote bundle. The other eight prior certificates become stale.

### Connectivity recovery

Epoch 0 isolates N0. Epoch 1 restores edge N0—N1.

| Task | Eventual cumulative exact worlds | Earliest cumulative epoch |
|---|---:|---|
| OR | 16/16 | t0: 8, t1: 8 |
| PARITY | 16/16 | t1: 16 |

Again OR can validate locally at t0 whenever x0=1. PARITY waits for reconnection in every world.

## What this establishes

Within the frozen finite model:

- instantaneous and cumulative identifiability are distinct;
- a sequence of individually insufficient views can become sufficient when the hidden world is static and observations persist;
- cached semantic sufficiency can survive a network failure after certificate freshness is lost;
- network recovery can restore current-epoch validation.

## What this does not establish

The artifact does not model:

- a world that changes during the sequence;
- stale-value detection or cache invalidation;
- packet-level delay, loss, contention, or adversarial scheduling;
- node compromise, Byzantine testimony, signatures, or revocation;
- asymptotic dynamic-graph complexity;
- a result about classical P versus NP.

If the world changes between epochs, cumulative facts may combine values that were never jointly true. v0.4 deliberately refuses that case rather than quietly calling stale data knowledge.
