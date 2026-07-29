# Theory note: observation factorization before complexity

- **Version:** v0.1
- **Status:** formalization draft; elementary theorem, no novelty claim
- **Authors:** Leo Guinan, Marvin
- **Date:** 2026-07-29
- **Scope:** exact finite observation, distributed locality, and finite Bayes risk

## Claim boundary

An algorithm cannot compute a task exactly from an observation when two worlds
with the same observation require different task outputs. This is an
identifiability obstruction, not a computational lower bound.

The elementary mathematical core is a factorization criterion. Its value here
is disciplinary: test whether the answer is present in the declared input
before discussing communication rounds, running time, certificates, or
prediction.

## 1. Observation model

Let:

- \(W\) be a nonempty set of possible worlds;
- \(X\) be an observation space;
- \(Y\) be a nonempty task-output space;
- \(O:W\to X\) be an observation map;
- \(f:W\to Y\) be a task.

The observation fiber containing \(w\in W\) is

\[
[w]_O = O^{-1}(O(w)).
\]

Define the equivalence kernel of a map \(a\) by

\[
R_a = \{(u,v)\in W^2 : a(u)=a(v)\}.
\]

The word "kernel" here means an equivalence relation induced by a map, not an
algebraic kernel.

### Definition 1 — exact observational identifiability

The task \(f\) is **exactly identifiable from** \(O\) when there is a decision
map

\[
g:O(W)\to Y
\]

such that

\[
f = g\circ O.
\]

Only values on the realized image \(O(W)\) matter. An extension of \(g\) to all
of \(X\) is arbitrary outside that image.

## 2. Factorization theorem

### Theorem 1 — fiber constancy

The following statements are equivalent:

1. \(f\) is exactly identifiable from \(O\);
2. \(f\) is constant on every fiber of \(O\);
3. \(R_O\subseteq R_f\).

When these conditions hold, the decision map on \(O(W)\) is unique.

#### Proof

Assume 1. If \(O(u)=O(v)\), then

\[
f(u)=g(O(u))=g(O(v))=f(v),
\]

so 2 holds. Statement 2 is exactly the relation inclusion in 3.

Now assume 2. For each \(x\in O(W)\), choose any \(w\) with \(O(w)=x\) and
define

\[
g(x)=f(w).
\]

This is well-defined because all worlds in the fiber \(O^{-1}(x)\) have the
same task value. Hence \(g(O(w))=f(w)\) for every \(w\), proving 1.

If \(g_1\circ O=f=g_2\circ O\), then for every \(x\in O(W)\), selecting a
world \(w\) with \(O(w)=x\) gives \(g_1(x)=f(w)=g_2(x)\). Thus the factor on
the realized image is unique. ∎

### Counterexample witness

Failure has a two-world witness:

\[
O(u)=O(v) \quad\text{and}\quad f(u)\ne f(v).
\]

No amount of computation over \(O(w)\) removes this obstruction. An exact
solver must receive a refined observation, add an assumption excluding one
world, or weaken the guarantee.

## 3. Comparing observation systems

### Definition 2 — refinement preorder

Say \(O_1\) **refines** \(O_2\), written \(O_1\succeq O_2\), when some map
\(h\) satisfies

\[
O_2 = h\circ O_1.
\]

Equivalently, \(R_{O_1}\subseteq R_{O_2}\): the finer observation never merges
worlds that the coarser observation separates.

### Proposition 1 — exact-task monotonicity

If \(O_1\succeq O_2\), every task exactly identifiable from \(O_2\) is exactly
identifiable from \(O_1\).

#### Proof

If \(f=g\circ O_2\) and \(O_2=h\circ O_1\), then

\[
f=(g\circ h)\circ O_1.
\]

∎

### Proposition 2 — task-class characterization

The following are equivalent:

1. \(O_1\succeq O_2\);
2. every task, with arbitrary codomain, identifiable from \(O_2\) is
   identifiable from \(O_1\).

#### Proof

Proposition 1 gives 1 implies 2. For the converse, take the task \(f=O_2\).
It is identifiable from \(O_2\) by the identity map. By 2, it factors through
\(O_1\), so \(O_2=h\circ O_1\) for some \(h\). ∎

Allowing the task codomain to vary is required for the converse because its
proof uses \(O_2\) itself as the task.

This comparison concerns deterministic informativeness. It does not yet assign
an acquisition cost, communication cost, or computational cost to either map.

## 4. Local and joint observation

Let a network have node set \(V=\{1,\ldots,n\}\), with local observations
\(O_i:W\to X_i\). Define the joint observation

\[
O_V(w)=(O_1(w),\ldots,O_n(w)).
\]

### Definition 3 — validation regimes

For a task \(f\):

- **local at node \(i\):** \(f=g_i\circ O_i\) for some \(g_i\);
- **jointly identifiable:** \(f=g\circ O_V\) for some \(g\);
- **distributed but not local:** jointly identifiable, while no node-local
  factorization exists;
- **non-identifiable:** no joint factorization exists.

### Corollary 1 — distributed-but-not-local criterion

A task is distributed but not local exactly when

\[
R_{O_V}\subseteq R_f
\]

and, for every node \(i\),

\[
R_{O_i}\nsubseteq R_f.
\]

This is a statement about information placement. It is not yet a statement
about whether the nodes can communicate that information under a given
protocol.

## 5. Identifiability, communication, and computation

The current framework separates three burdens.

### Burden A — identifiability

Does a factor \(g\) exist for the observation actually available at the
decision point?

A failed fiber test ends the exact problem before runtime analysis begins.

### Burden B — communication

If observations are distributed, can the decision point obtain enough of them
under a graph, bandwidth, message, fault, and timing model?

If all local observations can reach the decision point losslessly, changing a
connected path to a connected clique can change communication cost without
changing \(O_V\) or its fibers. If topology disconnects an informative node,
drops messages, or changes which observations arrive before the deadline, the
effective observation map changes and identifiability may change with it.

Thus the calibrated topology statement is:

> Holding the effective joint observation fixed, topology can change
> communication cost without changing observational identifiability.

Topology does not enjoy this separation when it changes the effective
observation.

### Burden C — computation

When \(g\) exists and its required observation reaches the decision point, what
resources are needed to evaluate \(g\)? This requires an encoded family of
instances and a machine model. Existence of \(g\) supplies no useful polynomial
runtime bound by itself.

For an ordinary decision problem with the full encoded input available,
\(O\) is the identity map. The factorization test is then trivial; classical
computational complexity remains untouched. Conversely, a computationally
easy task can become non-identifiable after a lossy observation map.

### Accounting identity, not a complexity theorem

A system may incur distinct costs for:

1. acquiring \(O(w)\);
2. communicating distributed components of \(O(w)\);
3. computing \(g(O(w))\).

These costs should not be added until units and composition rules are declared.
The separation is conceptual bookkeeping, not a new complexity class.

## 6. Distribution-relative prediction

Exact identifiability treats every declared world as possible. Prediction adds
a distribution and a loss.

Assume finite \(W\) and \(Y\), a probability mass function \(\mu\) on \(W\),
and zero-one loss. For any predictor \(a:O(W)\to Y\), define

\[
R_\mu(a;O,f)
=
\Pr_{w\sim\mu}[a(O(w))\ne f(w)].
\]

### Theorem 2 — finite Bayes risk on observation fibers

The minimum achievable risk from \(O\) is

\[
R_\mu^*(O,f)
=
1-
\sum_{x\in O(W)}
\max_{y\in Y}
\sum_{\substack{w\in W:\\O(w)=x,\\f(w)=y}}
\mu(w).
\]

#### Proof

A predictor selects one output independently for each observation value
\(x\). On fiber \(O^{-1}(x)\), the best choice is any label with maximum
probability mass. Summing those independent maxima gives optimal accuracy; its
complement is optimal risk. ∎

### Corollary 2 — exact versus almost-sure identifiability

\(R_\mu^*(O,f)=0\) exactly when \(f\) is constant \(\mu\)-almost surely on
every positive-mass observation fiber.

This is weaker than Theorem 1 when \(\mu\) gives zero mass to declared worlds.
A predictor can be perfect under \(\mu\) while failing the all-world exact
criterion.

### Corollary 3 — Bayes-risk monotonicity

If \(O_1\succeq O_2\), then

\[
R_\mu^*(O_1,f)\le R_\mu^*(O_2,f).
\]

A predictor using \(O_1\) can always discard information by applying the map
from \(O_1\) to \(O_2\), then imitate the optimal \(O_2\)-predictor.

For non-zero-one loss, replace the majority label in each fiber with a
conditional Bayes action. Infinite spaces require measurable maps and regular
conditional distributions; this note makes no theorem beyond the finite case.

## 7. Executed finite specimens

The existing four-bit instrument exhaustively checks these cases under the
uniform distribution.

### Complete distributed sensing

When the four local observations jointly expose all four bits, the joint map is
injective. Every Boolean task on those worlds factors through it. PARITY is
jointly identifiable although no one-bit node can determine it alone.

A path and clique preserve the same joint map. In the declared routing model,
the path requires three rounds and the clique one; identifiability remains
unchanged.

### One missing bit: PARITY

Worlds differing only in the missing bit share an observation and have opposite
PARITY labels. Every fiber is balanced, so

\[
R_\mu^*=\frac{1}{2}.
\]

### One missing bit: OR

Only the observation with three visible zeros is ambiguous. The two worlds in
that fiber have opposite labels and equal mass. All other worlds are certainly
positive. Therefore

\[
R_\mu^*=\frac{1}{16},
\qquad
\text{optimal accuracy}=\frac{15}{16}.
\]

These examples instantiate the theorems. They do not strengthen them.

## 8. Finite audit complexity

For an explicitly enumerated finite world table with hashable observations and
task outputs, Theorem 1 can be audited in one pass:

1. compute \(O(w)\) and \(f(w)\) for each world;
2. store the first task output and witness world for each observation;
3. fail when a later world in the same fiber has a different output.

Ignoring the cost of evaluating and encoding \(O\) and \(f\), this takes
expected \(O(|W|)\) dictionary operations and \(O(|O(W)|)\) storage. A naive
pairwise witness search takes \(O(|W|^2)\) comparisons and is unnecessary.
Checking all \(n\) local maps independently takes \(O(n|W|)\) such operations.

This is the complexity of auditing a fully enumerated finite table. It says
nothing about succinct world descriptions, implicit observation maps, or
asymptotic decision families.

## 9. Succinct circuit identifiability

The fiber obstruction becomes a decision problem once observations and tasks
are represented succinctly.

### Definition 4 — BAD-FIBER

An instance consists of Boolean circuits

\[
O:\{0,1\}^n\to\{0,1\}^m
\quad\text{and}\quad
f:\{0,1\}^n\to\{0,1\}.
\]

`BAD-FIBER` asks whether there exist \(u,v\in\{0,1\}^n\) such that

\[
O(u)=O(v)
\quad\text{and}\quad
f(u)\ne f(v).
\]

Its complement, `CIRCUIT-IDENTIFIABLE`, asks whether \(f\) factors through
\(O\) on the entire Boolean domain.

### Theorem 3 — succinct bad-fiber complexity

`BAD-FIBER` is NP-complete. Consequently, `CIRCUIT-IDENTIFIABLE` is
coNP-complete.

#### Proof

`BAD-FIBER` is in NP: guess \(u,v\), evaluate both circuits on both worlds,
and verify observation equality and task inequality in polynomial time.

For NP-hardness, reduce an arbitrary SAT instance \(\varphi(x)\), where
\(x\in\{0,1\}^k\). Construct worlds \((b,x)\in\{0,1\}^{k+1}\) and circuits

\[
O(b,x)=x,
\qquad
f(b,x)=b\land\varphi(x).
\]

If \(\varphi\) is satisfiable at \(x^*\), then \((0,x^*)\) and \((1,x^*)\)
have the same observation, while their task values are 0 and 1. Thus the
constructed instance has a bad fiber.

Conversely, if the constructed instance has a bad fiber, observation equality
forces the two worlds to share the same \(x\). Task inequality is possible only
when their \(b\)-bits differ and \(\varphi(x)=1\). Hence \(\varphi\) is
satisfiable. The construction is polynomial, proving NP-hardness.

`CIRCUIT-IDENTIFIABLE` is exactly the complement of `BAD-FIBER`, so it is
coNP-complete. ∎

The hardness already holds when the observation map merely drops one designated
input bit. All instance-specific difficulty can reside in the Boolean task
circuit.

This theorem classifies the audit problem for one explicit representation. It
does not show that evaluating an identifiable factor is hard, define a new
complexity class, or separate P from NP. If P = NP, the completeness statements
remain valid while their usual tractability interpretation changes.

## 10. Novelty boundary and prior-work burden

No novelty is claimed for Theorem 1 or Theorem 2. The factorization statement
is elementary and sits near established ideas including:

- functions constant on equivalence classes and quotient factorization;
- sufficient statistics and decision rules;
- comparison of statistical experiments and information orderings;
- distributed function computation and communication complexity;
- indistinguishability arguments in distributed computing;
- partial observability in control and decision processes.

Theorem 3 is a nontrivial complexity classification inside the declared
representation, but its proof is an immediate SAT reduction and its novelty is
unassessed. It must be compared against circuit functional dependence,
information-flow verification, noninterference, and related dependency-testing
problems before being presented as a contribution.

Candidate value, in increasing order of burden, is:

1. an audit instrument that catches impossible exact-inference requests;
2. a clean accounting framework separating acquisition, communication, and
   computation;
3. a useful theorem for succinctly represented observation families;
4. a genuinely new asymptotic model with nontrivial upper or lower bounds.

The first is implemented. The second is formalized but may be familiar
synthesis. The third now has one elementary NP/coNP classification, with no
novelty claim.

## 11. Falsifiers and next proof obligations

Downgrade the theory to instrumentation-only if any of the following survives
close comparison:

1. the three-burden decomposition is already standard in equivalent form;
2. observation factorization adds no discriminating result beyond choosing the
   correct classical input encoding;
3. every proposed topology result is already captured without residue by a
   standard communication model;
4. Theorem 3 is only a standard circuit-dependence or noninterference problem
   under renamed variables, with no residual theorem or method.

Before introducing a named complexity class, the program must provide:

- an asymptotic family of worlds, observations, and tasks;
- an explicit encoding and machine/communication model;
- closure properties or reductions;
- at least one nontrivial complete problem, separation, or simulation theorem;
- a literature comparison showing the object is not a renamed existing class.

The smallest next theoretical step is not another layer. It is a prior-work map
for Theorems 1–3, followed by variants whose answers are not immediate from the
same SAT reduction: restricted circuit classes, noisy channels, bounded-risk
thresholds, and distributed protocols that cannot centralize the full joint
observation.

The frozen prior-work contract is
`literature/observation-factorization/review.json`. Its acquisition status and
scope are documented in `literature/observation-factorization/README.md`.

## 12. Verification receipt

An OS-temporary, dependency-free verifier exhaustively checked:

- all 1,296 pairs of four-world observation maps into three labels and Boolean
  tasks, confirming factor existence exactly matches fiber constancy;
- all 278 Boolean truth tables through three variables under the Theorem 3 SAT
  reduction, confirming bad-fiber existence exactly matches satisfiability;
- the uniform-prior missing-bit risks \(1/2\) for PARITY and \(1/16\) for OR;
- required artifact links and the explicit empirical Layer 08 lock.

Receipt:

`AD_HOC_OBSERVATION_FACTORIZATION_OK factor_cases=1296
reduction_truth_tables=278 parity_risk=1/2 or_risk=1/16
layer08_locked=true links_present=true`

The temporary verifier was removed after a zero exit. The repository test suite
then returned `60 passed`. These checks validate the finite calculations and
reduction implementation; they do not establish literature novelty.
