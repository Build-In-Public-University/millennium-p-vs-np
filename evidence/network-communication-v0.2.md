# Evidence: root-relative communication costs v0.2

- Date: 2026-07-29
- Status: implemented synthetic instrument
- Artifact: `runs/network-observation-v0.2.json`
- Method: deterministic shortest-path routing over finite path and clique graphs

## Cost contract

For a chosen validation root, every node with a non-empty sensor scope is a
participant. The instrument constructs a deterministic breadth-first routing
tree and reports:

- `rounds`: maximum participant-to-root distance;
- `message_count`: number of distinct routing edges carrying one aggregated
  message;
- `aggregate_bit_transmissions`: one OR/PARITY summary bit per used edge;
- `raw_bit_transmissions`: each sampled bit multiplied by its distance to the
  root;
- `route_edges`: oriented child-to-parent evidence routes.

OR and PARITY both admit an exact associative one-bit summary. This is a
property of these two tasks, not a universal compression claim.

## Observed comparison

For four distributed one-bit sensors and root node 0:

| Topology | Rounds | Route messages | Aggregate bit-transmissions | Raw bit-transmissions |
| --- | ---: | ---: | ---: | ---: |
| Path | 3 | 3 | 3 | 6 |
| Clique | 1 | 3 | 3 | 3 |

The path and clique expose the same complete observation and therefore have the
same exact answer. The clique lowers latency and raw forwarding cost. It does
not lower the count of remote sensor contributions: three non-root sensors
still send three task summaries.

For a central full-state sensor located at the validation root, all four costs
are zero because validation requires no network movement.

## Supported claim

Under this explicit routing and message model, network topology and root
placement can change communication cost without changing observational
identifiability. Task-specific aggregation can reduce transmitted payload
relative to forwarding raw observations.

## Not measured

- packet headers, acknowledgements, retries, or protocol overhead;
- contention, congestion, asynchronous scheduling, or link capacity;
- compression computation or local evaluation time;
- adversarial, faulty, or noisy nodes;
- certificate size or verification complexity;
- classical P/NP membership.

## Falsifier

The implementation fails this slice if the reported routes are not valid graph
edges ending at the selected root, if rounds differ from the farthest routed
participant, or if aggregate transmission cost exceeds raw forwarding for the
frozen OR/PARITY conditions.

## Verification

`python3 -m pytest -q` returned `8 passed`. The v0.2 run emitted 12 conditions
and the path/clique values shown above.
