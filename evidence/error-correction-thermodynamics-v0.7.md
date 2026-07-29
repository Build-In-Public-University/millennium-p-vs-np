# Evidence: error-correction thermodynamics v0.7

- Date: 2026-07-29
- Status: implemented finite instrument
- Artifact: `runs/network-observation-v0.7.json`
- System boundary: finite logical registers
- Reset contract: before the next message
- Reservoir temperature in frozen profiles: `300 K`

## Claim under test

A prediction error does not itself incur a Landauer cost. An ideal Landauer lower bound appears only when a declared correction protocol irreversibly erases logical entropy inside a stated system boundary.

Reaching the next-send boundary requires both:

1. the corrected state matches the observation; and
2. every register required by the reset contract has been cleared.

Corrective side information can reduce the conditional entropy that must be erased. Reset floors from multiple correction cycles are additive only when their reset boundaries are explicitly independent.

## Operational definitions

For correction cycle `c`:

- `prediction_error_bits(c) = d_H(prediction, observation)`;
- `remaining_error_bits(c) = d_H(corrected_state, observation)`;
- `uncleared(c) = required_cleared_registers - cleared_registers`;
- `next_message_ready(c)` iff `remaining_error_bits(c) = 0` and `uncleared(c) = ∅`;
- `H_erase(c)` is the sum of explicitly declared entropy values for cleared registers;
- `E_L(c) = k_B T ln(2) H_erase(c)`.

The instrument rejects a cleared register without an explicit entropy entry. A deterministic register may declare `0` bits; silence is not accepted as zero.

For equally weighted correction-ensemble samples with erased state `Z`, retained side information `Y`, and corrective message `M`:

- erasure entropy before the message: `H(Z|Y)`;
- erasure entropy after the message: `H(Z|Y,M)`;
- corrective-message value: `I(Z;M|Y) = H(Z|Y) - H(Z|Y,M)`;
- ideal avoided floor: `k_B T ln(2) I(Z;M|Y)`.

## Frozen predictions

Recorded before implementation:

1. A wrong prediction that is corrected but retained has zero immediate erasure floor.
2. Erasing one bit of declared logical entropy at `300 K` yields one Landauer unit.
3. Correct state plus an uncleared required syndrome is not next-message ready.
4. Cleared reset state plus an uncorrected belief is not next-message ready.
5. A one-bit corrective message that partitions four equiprobable two-bit residuals reduces conditional erasure entropy from two bits to one.
6. A constant corrective message reduces no entropy.
7. Three independent one-bit reset boundaries sum to three Landauer units.
8. The correlated batch `{000,111}` has one bit of joint entropy rather than the naïve three-bit marginal sum.

## Executed outcomes

All eight predictions matched.

### Correction lifecycle profiles

| Profile | Prediction error | Remaining error | Erased entropy | Next send |
|---|---:|---:|---:|---|
| retained prediction | 1 bit | 0 bits | 0 bits | ready |
| overwrite prediction | 1 bit | 0 bits | 1 bit | ready |
| uncleared syndrome | 1 bit | 0 bits | 0 bits | blocked |
| cleared syndrome | 1 bit | 0 bits | 1 bit | ready |
| incomplete correction | 1 bit | 1 bit | 1 bit | blocked |

At `300 K`:

- one-bit ideal floor: `2.870978885078724e-21 J`;
- two-bit ideal floor: `5.741957770157448e-21 J`;
- three independent one-bit resets: `8.612936655236172e-21 J`.

### Corrective-message probe

Four equiprobable erased states: `{00, 01, 10, 11}`.

Helpful message `M = first bit of Z`:

- `H(Z|Y) = 2 bits`;
- `H(Z|Y,M) = 1 bit`;
- `I(Z;M|Y) = 1 bit`;
- ideal avoided floor at `300 K`: `2.870978885078724e-21 J`.

Constant message `M = 0`:

- `H(Z|Y) = 2 bits`;
- `H(Z|Y,M) = 2 bits`;
- `I(Z;M|Y) = 0 bits`;
- ideal avoided floor: `0 J`.

### Correlated batching probe

Equally likely erased batches: `{000,111}`.

- joint entropy: `1 bit`;
- naïve sum of marginal entropies: `3 bits`;
- compression attributable to correlation: `2 bits`.

Batching is not intrinsically cheaper. The saving exists because the three registers are perfectly correlated and can be compressed jointly.

### Repeated-reset probe

Under explicitly independent before-next-message reset boundaries:

- one cycle: `1 bit`, one Landauer unit;
- three cycles: `3 bits`, three Landauer units;
- floor ratio: `3.0`.

When boundaries are marked dependent, the aggregate floor is `null`, not a guessed sum. A joint ensemble is required.

## Miss log

- Prediction misses: `0 / 8`.
- Implementation correction: the first UI draft assigned one erased bit to the constant-message profile while displaying `H(Z|Y,M)=2`. Review caught the contradiction before verification; the profile now declares two erased bits.
- Transport/tooling misses are not scientific outcomes and are excluded from the prediction score.

## What would falsify this artifact

- A cleared register can enter a receipt without an explicit entropy value.
- A cycle is marked send-ready while corrected state differs from observation.
- A cycle is marked send-ready while a required register remains uncleared.
- The helpful message fails to reduce the frozen ensemble from two bits to one.
- The constant message reduces conditional entropy.
- The `{000,111}` joint entropy differs from one bit.
- Dependent reset boundaries receive an additive floor without a joint model.
- A fresh v0.7 run differs from the stored machine receipt.

## Claim boundary

This layer measures:

- correction and reset completion;
- declared erased logical entropy;
- an ideal Landauer lower bound at a declared temperature;
- conditional information supplied by a corrective message;
- correlation savings under joint erasure;
- additive floors under declared independent reset boundaries.

This layer does **not** measure:

- actual device work;
- communication or computation energy;
- heat dissipated by hardware;
- finite-time or finite-error thermodynamic overhead;
- memory-controller behavior;
- network transport energy;
- human metabolic or action energy;
- whether a physical implementation approaches the ideal bound.

`measured_physical_energy_joules` remains `null` in every frozen profile.

## Next falsifiable step

Calibrate one concrete computational substrate: name the memory operation, device, temperature assumption, timing window, and wall-power measurement method. Compare measured correction/reset work against the ideal floor without pretending the ratio transfers to another substrate.
