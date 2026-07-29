# Evidence: finite sampling-versus-prediction instrument v0.1

- Date: 2026-07-29
- Status: implemented synthetic instrument
- Artifact: `runs/network-observation-v0.1.json`
- Method: exhaustive enumeration, not statistical sampling

## Exact claim supported

In the implemented finite model, sensor configuration determines whether a
Boolean task is locally identifiable, only jointly identifiable, or not exactly
identifiable. Communication topology changes the aggregation radius while
holding observations fixed.

## Method of checking

The run enumerates all 16 four-bit worlds. It evaluates OR and PARITY under six
network configurations formed from three sensor layouts and two topologies.
Worlds are partitioned by identical observations; task outputs are then checked
for invariance within every partition.

## Observed results

- Central full-state sensor: local validation, accuracy `1/1`.
- Distributed complete sensing: distributed validation, accuracy `1/1`.
- One missing sensor, OR: predictive regime, best uniform-prior accuracy
  `15/16`.
- One missing sensor, PARITY: predictive regime, best uniform-prior accuracy
  `1/2`.
- Complete distributed sensing: clique aggregation radius `1`; path radius `3`.
- Partial sensing: clique aggregation radius `1`; path radius `2`.

The receipt includes explicit indistinguishable-world witnesses. For partial
PARITY, `[0,0,0,0]` and `[0,0,0,1]` produce the same observation and opposite
answers.

## Limitations

This is a finite information-availability result. It does not measure search
cost, asymptotic complexity, noisy sensors, adversarial nodes, bandwidth,
certificate size, or classical P/NP membership. The uniform-prior accuracy is a
declared synthetic baseline, not a claim about reality.

## Independent replication status

Not independently replicated. Automated tests verify the model invariants and
the artifact schema.

## Consequence for the idea

The observation-equivalence mechanism survives its first executable test. No
novel complexity theorem has been established. The next discriminating test
must compare this representation against standard communication-complexity and
distributed-computing baselines rather than merely adding larger synthetic
worlds.
