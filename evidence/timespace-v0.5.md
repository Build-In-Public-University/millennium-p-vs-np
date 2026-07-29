# Evidence: timespace v0.5

- Date: 2026-07-29
- Status: implemented finite instrument
- Artifact: `runs/network-observation-v0.5.json`
- Coordination substrate: two nodes, two world bits, three epochs
- Control: N0 controls x0; N1 controls x1
- Coordination weight: 2
- Exchange payload: 14 logical bits

## Frozen model

A spacetime exchange connects `(N0,t=0)` to `(N1,t=1)`. Each endpoint has a private prospective point at the shared horizon `t=2`:

- `D0(2)`: N0's desired world;
- `D1(2)`: N1's desired world.

Each node holds a cross-model of the other's desired point. Cross-models may affect an action only on a scope explicitly authorized by the other endpoint. Ideas accumulate through bidirectional transmission without merging the private desire states.

The evaluator keeps four objects separate:

1. actual `W(0)`;
2. desired `D0(2)` and `D1(2)`;
3. self-only, modeled, and oracle proposed targets;
4. realized `W(2)`.

## Predictions frozen before execution

For each coordination profile, enumerate four actual worlds, four sender desires, and four receiver desires: 64 cases.

| Profile | Predicted wins | Predicted ties | Predicted losses |
|---|---:|---:|---:|
| Accurate + authorized | 48 | 16 | 0 |
| Inverted + authorized | 0 | 16 | 48 |
| Accurate + unauthorized | 0 | 64 | 0 |

A win means the modeled policy has lower realized authorized coordination loss than the self-only policy. A loss means it is worse.

## Executed coordination results

| Profile | Wins | Ties | Losses | Total predictive gain | Mean cross-model error | Oracle matches |
|---|---:|---:|---:|---:|---:|---:|
| Accurate + authorized | 48 | 16 | 0 | +64 | 0 | 64 |
| Inverted + authorized | 0 | 16 | 48 | -192 | 2 bits | 0 |
| Accurate + unauthorized | 0 | 64 | 0 | 0 | 0 | 64 |

Authorization violations: `0` in all 192 coordination cases.

The negative control matters more than the positive result. An inverted model loses in 48/64 cases and accumulates three units of excess loss for each controlled-bit mistake. Predictive coordination is not monotonically beneficial.

No frozen combinatorial prediction missed in this run.

## Executed realization probe

A second probe independently enumerates:

- four `W(0)` states;
- four realized `W(2)` states;
- four sender desires;
- four receiver desires.

Total: 256 cases, including 192 where the world drifts.

| Modeled-target realization gap | Cases |
|---|---:|
| 0 bits | 64 |
| 1 bit | 128 |
| 2 bits | 64 |

Mean modeled-target realization gap: `1` bit.

Even with exact cross-models, the proposed target equals independently realized reality in only 64/256 cases. Knowing what connected nodes want is not knowing what the world will become.

## Idea accumulation

Every exchange begins with one private idea at each node and transmits one idea in each direction. Both nodes end with `{sender-idea, receiver-idea}`. Their desired endpoints remain distinct objects.

This demonstrates accumulation by communication. It does not model semantic compatibility, compression, forgetting, deception, or whether an idea is true.

## Claim boundary

This instrument measures:

- prospective cross-model error;
- authorized local coordination loss;
- predictive gain per logical payload bit;
- bidirectional idea accumulation;
- distance between proposed, desired, and realized futures.

It does not measure:

- real human preferences;
- persuasion or preference formation;
- strategic or deceptive messages;
- causal control of the realized world;
- classical computational complexity;
- a proof concerning P versus NP.

`inferred_preference`, `declared_preference`, and `authorized_objective` remain separate. Desire is not permission.
