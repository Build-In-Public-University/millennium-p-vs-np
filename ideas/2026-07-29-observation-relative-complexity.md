# Idea: Observation-relative validation complexity

- Status: finite mechanism executed; mathematical core formalized; novelty unassessed
- Author(s): Leo Guinan, Marvin
- Date: 2026-07-29
- Domain(s): distributed complexity, information theory, sensing
- Main problem connection: separates certificate verification from acquiring the state being verified

## Question

For a task over a world state, which network sensor configurations make the
answer locally calculable, only distributedly calculable, or non-identifiable
without prediction?

## Known starting points

Classical P and NP assume an encoded input is available to the machine.
Distributed models separately measure communication rounds and bandwidth. This
idea adds an explicit observation operator before computation: the network may
not receive every task-relevant state variable.

## Proposed mechanism

Let `S_N(W)` be the observations made by network `N` in world `W`, and let
`f(W)` be the correct task answer. Define observational equivalence by:

`W1 ~N W2` exactly when `S_N(W1) = S_N(W2)`.

Exact validation from the observations is possible only when `f` is constant
on every equivalence class induced by `~N`. If two observationally equivalent
worlds require different answers, no zero-error algorithm restricted to those
observations can distinguish them.

## Executed finite test

Enumerate finite binary worlds and compare OR and PARITY under:

1. one central sensor that samples every bit;
2. one local sensor per bit;
3. one unobserved bit;
4. clique and path communication topologies.

Record the validation regime, exact counterexample pair, uniform-prior optimal
accuracy, and aggregation radius.

This test is implemented in `network_relativity/` and reported in
`evidence/network-observation-v0.1.md`.

## Formalization

`papers/observation-factorization-v0.1.md` proves the exact factorization
criterion, separates identifiability from communication and computation,
derives finite Bayes risk, and proves NP-completeness of succinct Boolean-circuit
bad-fiber detection. The classification has not yet survived a prior-work
novelty audit.

## Smallest next theory test

Compare the circuit result against functional-dependence, noninterference,
information-flow verification, communication-complexity, and statistical
experiment-ordering formulations. Preserve the result as a standard reduction
if no residual novelty remains.

## Falsifier

Downgrade the broader Network Relativity claim if the instrument adds no useful
prediction beyond established observation, communication-complexity, and
distributed-computing models. In particular, a renamed graph diameter is not a
new theory.

## Adjacent value if wrong

The observation-equivalence checker remains a useful preflight for identifying
when a distributed or sensor-based system has been asked to infer information
that its inputs do not contain.

## Sources

- Stephen Cook, “The P versus NP Problem,” Clay Mathematics Institute.
- Existing LOCAL and CONGEST literature provides the baseline for
  topology-dependent distributed complexity.
