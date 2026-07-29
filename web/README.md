# Observation Lab UI

A self-contained browser workbench for the finite Network Relativity observation
model. It makes no network requests and has no build step.

## Run locally

From the repository root:

```bash
python3 -m http.server 8900 --directory web
```

Then open <http://localhost:8900>.

## Interactive surface

- Flip the current world's binary variables.
- Change the task between OR and PARITY.
- Compare path and clique communication topologies.
- Choose the validation root and inspect the exact evidence route.
- Apply central, distributed, and partial sensor presets.
- Select any network node and edit the exact world variables it samples.
- Inspect the resulting local, distributed, or predictive regime.
- Compare synchronous rounds, route messages, task-aggregate bit-transmissions,
  and raw bit-transmissions.
- Inspect the minimal source-grounded certificate at the selected validation
  root, including issuers, logical payload, worlds remaining, and unavailable
  certificates.
- Move through rotating-sensor, root-link-failure, and connectivity-recovery
  epochs; compare current facts, cached facts, and prior-certificate freshness.
- Edit two private desired futures and a separately realized future; compare
  self-only, cross-modeled, and oracle local targets.
- Switch between accurate, inverted, and unauthorized cross-models; inspect
  predictive gain, realization gap, idea accumulation, and authorization state.
- Compare intended trajectories with receiver-declared endpoint, horizon,
  authorization, transition-load, and positive-acceleration constraints.
- Inspect the first incompatibility, shortest accepted witness, minimum
  completion epoch, and smallest displayed repair.
- Switch among retained-prediction, overwrite, syndrome-reset, incomplete,
  message-assisted, correlated-batch, and repeated-reset correction profiles.
- Inspect next-message readiness, erased logical entropy, the ideal Landauer
  floor at a declared temperature, corrective-message information, correlation
  savings, and whether repeated reset boundaries are legally additive.
- Inspect exact observational-equivalence classes and counterexample worlds.
- Export the current configuration and computed boundary as a JSON receipt.

State persists locally in the browser under
`network-relativity-observation-lab-v1`.

## Claim boundary

The UI exhaustively enumerates finite binary worlds and calculates
observational identifiability, best possible accuracy under a uniform prior,
deterministic shortest-path communication costs, and minimal source-grounded
certificate bundles. Aggregate transmission uses one-bit associative summaries
specific to OR and PARITY. Certificate payload excludes signatures and assumes
authentic issuer identity plus truthful sensor reports. The UI does not model
packet overhead, congestion, Byzantine faults, or asymptotic computational
complexity. Temporal scenarios hold the hidden world static, assume connected
sensors deliver within each epoch, and retain cached observations. The
timespace plane separately represents `W(0)`, desired endpoints, proposed
targets, and `W(2)`; it does not infer human preferences, model persuasion, or
authorize action from inferred desire. The trajectory layer uses discrete
Hamming transition load and positive ramp constraints; it does not infer energy
from those values. The correction layer uses an explicit finite-register reset
contract and equally weighted finite ensembles to compute conditional erased
entropy and an ideal `k_B T ln(2)` lower bound at the selected temperature. It
does not measure device work, communication or computation energy, dissipated
heat, finite-time overhead, or human metabolic energy. Neither plane resolves
classical P versus NP.
