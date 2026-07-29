# Evidence: trajectory compatibility v0.6

- Date: 2026-07-29
- Status: implemented finite instrument
- Artifact: `runs/network-observation-v0.6.json`
- Substrate: two-bit prospective trajectories with a declared receiver envelope
- Physical-energy status: not measured

## Frozen predictions

These predictions were written into tests before the Layer 06 implementation.

1. `00 → 10 → 11` is compatible with a one-bit-per-epoch, one-bit-per-epoch² ramp envelope.
2. `00 → 00 → 11` has the same endpoint and horizon but violates a one-bit positive-ramp envelope.
3. A receiver whose earliest accepted completion is `t+4` rejects completion at `t+2`; delay repairs it.
4. `00 → 11` exceeds a one-bit-per-epoch rate envelope; one additional epoch repairs it.
5. A transition touching an unauthorized variable has no accepted witness under that envelope.
6. An intended endpoint different from the accepted endpoint is a direction conflict.
7. Among all four `00 → middle → 11` paths, endpoint-only comparison misses two acceleration conflicts.

## Executed outcomes

| Profile | Compatible | Conflict | Minimum completion | Minimum repair |
|---|---:|---|---:|---|
| `smooth_compatible` | yes | none | `t+2` | none |
| `burst_acceleration` | no | acceleration | `t+2` | smooth ramp |
| `early_horizon` | no | horizon | `t+4` | delay two epochs |
| `burst_rate` | no | rate | `t+2` | delay one epoch |
| `unauthorized_scope` | no | authorization | unreachable | expand authorized scope |
| `direction_mismatch` | no | direction | `t+1` | align endpoint |

Frozen prediction misses: **0**.

## Endpoint blind-spot probe

The probe fixes:

- start: `00`;
- endpoint: `11`;
- completion: `t+2`;
- authorization: both bits;
- maximum transition load: two bits per epoch;
- maximum positive acceleration: one bit per epoch².

It enumerates all four intermediate worlds.

| Result | Count |
|---|---:|
| Cases with same endpoint and horizon | 4 |
| Compatible paths | 2 |
| Acceleration conflicts | 2 |
| False-compatible under endpoint-only comparison | 2 |

Endpoint equality therefore hides an incompatibility in `2/4` paths under this envelope.

The mechanism is not endpoint disagreement. It is path shape:

- smooth paths distribute the transition load;
- burst paths increase load by two bits in one epoch;
- the receiver permits a positive ramp of only one bit per epoch².

## Definitions

For trajectory states `γ(0), …, γ(h)`, transition load is Hamming distance:

`ℓ(t) = d_H(γ(t-1), γ(t))`.

Positive acceleration load is:

`a(t) = ℓ(t) - ℓ(t-1)`, with `ℓ(-1) = 0`.

The present envelope constrains positive ramp-up. Deceleration is not bounded.

A trajectory is compatible only when all conditions hold:

1. intended endpoint equals accepted endpoint;
2. completion is not earlier than the receiver's declared minimum;
3. every changed variable is authorized;
4. every transition load is within the per-epoch limit;
5. every positive acceleration is within the ramp limit.

The accepted witness is found by finite breadth-first search over `(world, previous load, epoch)`. Epoch remains in the state because waiting can restore compatibility.

## What changed conceptually

Layer 05 compared desired endpoints. Layer 06 compares an intended path with a receiver's accepted set of paths.

Two nodes can now agree on `11 at t+2` while disagreeing on whether `00 → 00 → 11` is admissible. The prior endpoint representation could not express that disagreement.

Compatibility is directional. This instrument evaluates one sender's intended trajectory against one receiver's declared envelope. It does not infer private readiness.

## Authorization boundary

A path that is physically reachable but outside the declared authorization scope remains incompatible. The witness search does not silently widen consent to make a path exist.

## Energy boundary

This layer records logical transition load and positive ramp. It does **not** convert them to energy.

It does not identify:

- prediction residual entropy;
- correction-code length;
- overwritten prediction bits;
- syndrome or scratch bits reset;
- temperature;
- measured communication or computation energy;
- a Landauer lower bound.

Logical transition load is not erased logical entropy. Treating the two as interchangeable would price an analogy rather than a physical operation.

## Claim boundary

Established only for the finite model:

- endpoint equality does not guarantee trajectory compatibility;
- rate and acceleration constraints can distinguish paths with identical endpoints and horizons;
- exact finite search can produce a shortest accepted witness;
- delay can repair some pace conflicts;
- authorization can make an otherwise reachable target inadmissible.

Not established:

- human readiness or private acceptance;
- continuous-time acceleration;
- optimal planning in large state spaces;
- noisy or strategic declarations;
- physical energy expenditure;
- Landauer dissipation;
- persuasion or preference formation;
- classical P versus NP.

## Next falsifiable layer

Layer 07 should attach a correction lifecycle to incompatible predictions:

`predict → receive correction → compute residual → update → reset`.

Only bits irreversibly erased under an explicit system boundary and reset contract may enter a Landauer ledger.
