# Evidence: source-grounded certificates v0.3

- Date: 2026-07-29
- Status: implemented synthetic instrument
- Artifact: `runs/network-observation-v0.3.json`
- Method: exhaustive enumeration of all 16 four-bit worlds
- Verifier: node 0

## Question

Given a verifier's local samples, what is the smallest bundle of remote,
source-grounded attestations that makes the task answer invariant across every
compatible world?

A remote assignment is source-grounded only when its issuer's configured sensor
scope contains that world variable. This validates placement in the model; it
does not establish sensor honesty or cryptographic authenticity.

## Logical payload accounting

A non-empty bundle counts:

- one claimed-answer bit;
- issuer identifier bits per sample;
- variable-index bits per sample;
- one observed-value bit per sample.

For four variables on four nodes, each attested sample costs five logical bits,
plus one claim bit per bundle. Signature bytes, keys, headers, transport,
replay protection, and fault tolerance are excluded.

## Results

| Task | Sensors | Exact worlds | Impossible worlds | Samples | Logical bits |
|---|---|---:|---:|---:|---:|
| OR | central | 16 | 0 | 0 | 0 |
| OR | distributed | 16 | 0 | 0–3 | 0–16 |
| OR | partial | 14 | 2 | 0–2 | 0–11 |
| PARITY | central | 16 | 0 | 0 | 0 |
| PARITY | distributed | 16 | 0 | 3 | 16 |
| PARITY | partial | 0 | 16 | 2 | 11 |

Path and clique profiles are identical here because both are connected and the
certificate metric counts logical payload, not transport cost. Their delivery
rounds and raw transmissions remain different in the v0.2 communication layer.

## Interpretation

- A true OR needs only one grounded `1` unless the verifier already sees one.
- A false OR needs every unobserved variable grounded as `0`.
- PARITY needs every unobserved variable; no sampled bit can be omitted in this
  finite exact model.
- Under partial sensing, x3 has no issuer. Consequently PARITY has no exact
  source-grounded certificate in any world.
- Partial OR fails only in the two worlds where x0=x1=x2=0. The hidden x3 can
  reverse the answer, and no node can attest it.

The failed certificates matter more than the successful ones. They show that a
certificate cannot repair absent sensing without adding an oracle, trusted
advice, or a new sensor.

## Trust boundary

Every non-local successful bundle still assumes:

1. issuer identity is authentic;
2. the issuer reports its sampled value truthfully.

The instrument does not model signatures, compromised sensors, collusion,
Byzantine faults, freshness, or revocation. “Source-grounded” therefore means
structurally attributable under the declared network configuration—not trusted
in the cryptographic or institutional sense.

## Claim boundary

This experiment measures finite observation sufficiency and logical certificate
payload under explicit sensor scopes. It does not measure general NP witness
complexity, cryptographic proof security, or classical computational hardness.
It does not resolve P versus NP.
