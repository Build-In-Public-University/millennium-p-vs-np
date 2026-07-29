"""Finite observation model for network-relative validation experiments."""

import math
from collections import defaultdict, deque
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
from itertools import combinations
from typing import Hashable, Iterable, Mapping


BOLTZMANN_CONSTANT_J_PER_K = 1.380649e-23


@dataclass(frozen=True)
class WorldState:
    """A finite world represented by binary state variables."""

    bits: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.bits:
            raise ValueError("a world must contain at least one bit")
        if any(bit not in (0, 1) for bit in self.bits):
            raise ValueError("world bits must be 0 or 1")

    @classmethod
    def from_integer(cls, value: int, bit_count: int) -> "WorldState":
        if bit_count < 1:
            raise ValueError("bit_count must be positive")
        if value < 0 or value >= 2**bit_count:
            raise ValueError("value does not fit in bit_count bits")
        return cls(tuple((value >> index) & 1 for index in range(bit_count)))


class BooleanTask(Enum):
    """Small exact tasks used to expose observation boundaries."""

    OR = "or"
    PARITY = "parity"

    def evaluate(self, world: WorldState) -> bool:
        if self is BooleanTask.OR:
            return any(world.bits)
        return sum(world.bits) % 2 == 1


Observation = tuple[tuple[int, tuple[tuple[int, int], ...]], ...]
NodeObservation = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class IdentifiabilityReport:
    """Exact finite-world identifiability result under a uniform prior."""

    identifiable: bool
    best_possible_accuracy: Fraction
    counterexample: tuple[WorldState, WorldState] | None


@dataclass(frozen=True)
class CommunicationReport:
    """Root-relative communication costs for exact task aggregation."""

    root: int
    task: BooleanTask
    route_edges: tuple[tuple[int, int], ...]
    rounds: int
    message_count: int
    aggregate_bit_transmissions: int
    raw_bit_transmissions: int


@dataclass(frozen=True)
class AttestedSample:
    """A value claim grounded in an issuer's declared sensor scope."""

    issuer: int
    world_index: int
    value: int


@dataclass(frozen=True)
class CertificateReport:
    """Smallest source-grounded bundle that determines a task answer."""

    verifier: int
    task: BooleanTask
    claimed_answer: bool
    samples: tuple[AttestedSample, ...]
    determines_answer: bool
    worlds_remaining: int
    logical_payload_bits: int
    trust_assumptions: tuple[str, ...]
    unattested_indices: tuple[int, ...]


@dataclass(frozen=True)
class ProspectivePoint:
    """One node's timestamped desired world at a declared future horizon."""

    node: int
    formed_at: int
    horizon: int
    desired_world: WorldState

    def __post_init__(self) -> None:
        if self.node < 0:
            raise ValueError("prospective point node must be non-negative")
        if self.formed_at < 0 or self.horizon <= self.formed_at:
            raise ValueError("prospective horizon must follow formation time")


@dataclass(frozen=True)
class TimespaceExchange:
    """Actual communication edge plus its two private prospective endpoints."""

    sender: int
    receiver: int
    sent_at: int
    received_at: int
    sender_point: ProspectivePoint
    receiver_point: ProspectivePoint
    sender_model_of_receiver: WorldState
    receiver_model_of_sender: WorldState
    sender_authorizes_receiver: frozenset[int]
    receiver_authorizes_sender: frozenset[int]
    sender_knowledge: frozenset[Hashable]
    receiver_knowledge: frozenset[Hashable]
    sender_transmits: frozenset[Hashable]
    receiver_transmits: frozenset[Hashable]
    idea_payload_bits: int = 0

    def __post_init__(self) -> None:
        if self.sender == self.receiver:
            raise ValueError("an exchange needs two distinct nodes")
        if self.sent_at < 0 or self.received_at < self.sent_at:
            raise ValueError("exchange timestamps are out of order")
        if self.sender_point.node != self.sender:
            raise ValueError("sender point belongs to the wrong node")
        if self.receiver_point.node != self.receiver:
            raise ValueError("receiver point belongs to the wrong node")
        if self.sender_point.horizon != self.receiver_point.horizon:
            raise ValueError("prospective endpoints need a shared horizon")
        if self.sender_point.horizon < self.received_at:
            raise ValueError("prospective horizon precedes message receipt")

        worlds = (
            self.sender_point.desired_world,
            self.receiver_point.desired_world,
            self.sender_model_of_receiver,
            self.receiver_model_of_sender,
        )
        bit_counts = {len(world.bits) for world in worlds}
        if len(bit_counts) != 1:
            raise ValueError("desires and cross-models need equal dimensions")
        bit_count = len(worlds[0].bits)
        authorizations = self.sender_authorizes_receiver | self.receiver_authorizes_sender
        if any(index < 0 or index >= bit_count for index in authorizations):
            raise ValueError("authorization index exceeds desired world")
        if not self.sender_transmits <= self.sender_knowledge:
            raise ValueError("sender cannot transmit an idea it does not hold")
        if not self.receiver_transmits <= self.receiver_knowledge:
            raise ValueError("receiver cannot transmit an idea it does not hold")
        if self.idea_payload_bits < 0:
            raise ValueError("idea payload cannot be negative")


@dataclass(frozen=True)
class TimespaceReport:
    """Prospective model accuracy and authorized local coordination outcome."""

    desire_distance: int
    sender_model_error: int
    receiver_model_error: int
    self_only_target: WorldState
    modeled_target: WorldState
    oracle_target: WorldState
    self_only_loss: int
    modeled_loss: int
    oracle_loss: int
    predictive_gain: int
    oracle_gap: int
    modeling_efficiency: Fraction
    realized_world: WorldState
    sender_realization_gap: int
    receiver_realization_gap: int
    modeled_target_realization_gap: int
    sender_knowledge_after: frozenset[Hashable]
    receiver_knowledge_after: frozenset[Hashable]
    logical_payload_bits: int
    authorization_violations: tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class ProspectiveTrajectory:
    """One node's intended sequence of worlds from now through completion."""

    node: int
    formed_at: int
    states: tuple[WorldState, ...]

    def __post_init__(self) -> None:
        if self.node < 0 or self.formed_at < 0:
            raise ValueError("trajectory node and formation time must be non-negative")
        if len(self.states) < 2:
            raise ValueError("a trajectory needs a start and at least one transition")
        if len({len(state.bits) for state in self.states}) != 1:
            raise ValueError("trajectory states need equal dimensions")

    @property
    def completion_at(self) -> int:
        return self.formed_at + len(self.states) - 1


@dataclass(frozen=True)
class TransitionEnvelope:
    """A receiver's declared scope, pace, and ramp constraints."""

    receiver: int
    accepted_target: WorldState
    earliest_completion_at: int
    authorized_indices: frozenset[int]
    max_load_per_epoch: int
    max_acceleration_per_epoch: int

    def __post_init__(self) -> None:
        if self.receiver < 0 or self.earliest_completion_at < 0:
            raise ValueError("receiver and completion time must be non-negative")
        if self.max_load_per_epoch < 0 or self.max_acceleration_per_epoch < 0:
            raise ValueError("load and acceleration limits must be non-negative")
        bit_count = len(self.accepted_target.bits)
        if any(index < 0 or index >= bit_count for index in self.authorized_indices):
            raise ValueError("authorized index exceeds accepted target")


@dataclass(frozen=True)
class TrajectoryConflict:
    """One falsifiable reason an intended trajectory exceeds an envelope."""

    kind: str
    epoch: int
    requested: int | WorldState | frozenset[int]
    accepted: int | WorldState | frozenset[int]


@dataclass(frozen=True)
class TrajectoryCompatibilityReport:
    """Exact compatibility result plus the receiver's shortest accepted witness."""

    compatible: bool
    conflicts: tuple[TrajectoryConflict, ...]
    conflict_types: tuple[str, ...]
    first_conflict_epoch: int | None
    transition_loads: tuple[int, ...]
    acceleration_loads: tuple[int, ...]
    excess_load_by_epoch: tuple[int, ...]
    excess_acceleration_by_epoch: tuple[int, ...]
    required_max_load: int
    required_max_acceleration: int
    required_authorization: frozenset[int]
    minimum_feasible_completion_at: int | None
    minimum_delay: int | None
    accepted_witness: ProspectiveTrajectory | None


@dataclass(frozen=True)
class CorrectionCycle:
    """One correction and its explicit logical-register reset contract."""

    prediction: WorldState
    observation: WorldState
    corrected_state: WorldState
    corrective_message_bits: int
    system_boundary: str
    reset_contract: str
    required_cleared_registers: frozenset[str]
    cleared_registers: frozenset[str]
    erased_entropy_by_register: tuple[tuple[str, float], ...]
    temperature_kelvin: float

    def __post_init__(self) -> None:
        dimensions = {
            len(self.prediction.bits),
            len(self.observation.bits),
            len(self.corrected_state.bits),
        }
        if len(dimensions) != 1:
            raise ValueError("prediction, observation, and correction need equal dimensions")
        if self.corrective_message_bits < 0:
            raise ValueError("corrective message length must be non-negative")
        if not self.system_boundary.strip() or not self.reset_contract.strip():
            raise ValueError("system boundary and reset contract are required")
        if not math.isfinite(self.temperature_kelvin) or self.temperature_kelvin <= 0:
            raise ValueError("temperature must be finite and positive")
        register_names = [name for name, _ in self.erased_entropy_by_register]
        if len(register_names) != len(set(register_names)):
            raise ValueError("each cleared register needs one entropy entry")
        if set(register_names) != set(self.cleared_registers):
            raise ValueError("every cleared register needs an explicit entropy entry")
        register_scope = self.required_cleared_registers | self.cleared_registers
        if any(not name.strip() for name in register_scope):
            raise ValueError("register names cannot be empty")
        if any(
            not math.isfinite(entropy_bits) or entropy_bits < 0
            for _, entropy_bits in self.erased_entropy_by_register
        ):
            raise ValueError("erased entropy must be finite and non-negative")


@dataclass(frozen=True)
class CorrectionCycleReport:
    """Logical correction state and its Landauer lower bound."""

    prediction_error_bits: int
    remaining_error_bits: int
    correction_payload_bits: int
    erased_logical_entropy_bits: float
    landauer_floor_joules: float
    uncleared_required_registers: frozenset[str]
    next_message_ready: bool
    system_boundary: str
    reset_contract: str


@dataclass(frozen=True)
class CorrectionEnsembleSample:
    """One equally weighted erasure state with retained and messaged context."""

    erased_state: tuple[int, ...]
    retained_side_information: tuple[int, ...]
    corrective_message: tuple[int, ...]

    def __post_init__(self) -> None:
        if not self.erased_state:
            raise ValueError("erased state cannot be empty")
        values = (
            self.erased_state
            + self.retained_side_information
            + self.corrective_message
        )
        if any(value not in (0, 1) for value in values):
            raise ValueError("ensemble states must be binary")


@dataclass(frozen=True)
class CorrectionEnsembleReport:
    """Conditional erasure entropy before and after corrective side information."""

    sample_count: int
    entropy_without_message_bits: float
    entropy_with_message_bits: float
    message_information_bits: float
    naive_marginal_entropy_bits: float
    correlation_savings_bits: float
    landauer_without_message_joules: float
    landauer_with_message_joules: float
    landauer_avoided_joules: float
    temperature_kelvin: float


@dataclass(frozen=True)
class CorrectionSequenceReport:
    """Correction-cycle aggregation with an explicit additivity boundary."""

    cycle_count: int
    all_next_message_ready: bool
    independent_reset_boundaries: bool
    total_prediction_error_bits: int
    total_erased_entropy_bits: float | None
    landauer_floor_joules: float | None


@dataclass(frozen=True)
class TemporalStepReport:
    """Observation and certificate state at one network epoch."""

    step: int
    reachable_nodes: tuple[int, ...]
    instantaneous_facts: NodeObservation
    cumulative_facts: NodeObservation
    instantaneous_worlds_remaining: int
    cumulative_worlds_remaining: int
    instantaneous_determines_answer: bool
    cumulative_determines_answer: bool
    current_certificate: CertificateReport
    previous_certificate_fresh: bool | None


@dataclass(frozen=True)
class TemporalValidationReport:
    """Validation behavior across a static world's changing network."""

    steps: tuple[TemporalStepReport, ...]
    earliest_instantaneous_step: int | None
    earliest_cumulative_step: int | None


@dataclass(frozen=True)
class TemporalNetworkSequence:
    """Ordered network snapshots over one static hidden world."""

    snapshots: tuple["NetworkConfiguration", ...]

    def __post_init__(self) -> None:
        if not self.snapshots:
            raise ValueError("a temporal sequence needs at least one snapshot")
        node_counts = {snapshot.node_count for snapshot in self.snapshots}
        if len(node_counts) != 1:
            raise ValueError("all temporal snapshots must use the same nodes")

    def analyze(
        self,
        world: WorldState,
        task: BooleanTask,
        verifier: int,
    ) -> TemporalValidationReport:
        bit_count = len(world.bits)
        claimed_answer = task.evaluate(world)
        cumulative_facts: dict[int, int] = {}
        latest_certificate: CertificateReport | None = None
        earliest_instantaneous_step = None
        earliest_cumulative_step = None
        steps = []

        for step, snapshot in enumerate(self.snapshots):
            snapshot._validate_node(verifier)
            distances, _ = snapshot._shortest_path_tree(verifier)
            reachable_nodes = tuple(sorted(distances))
            instantaneous_facts = {
                world_index: value
                for node in reachable_nodes
                for world_index, value in snapshot.observe_at_node(world, node)
            }
            cumulative_facts.update(instantaneous_facts)

            instantaneous_worlds = snapshot._worlds_consistent_with(
                bit_count, instantaneous_facts
            )
            cumulative_worlds = snapshot._worlds_consistent_with(
                bit_count, cumulative_facts
            )
            instantaneous_exact = {
                task.evaluate(candidate) for candidate in instantaneous_worlds
            } == {claimed_answer}
            cumulative_exact = {
                task.evaluate(candidate) for candidate in cumulative_worlds
            } == {claimed_answer}

            current_certificate = snapshot.attested_certificate(
                world, task, verifier
            )
            previous_certificate_fresh = None
            if latest_certificate is not None:
                scopes = dict(snapshot.sensor_scopes)
                if latest_certificate.samples:
                    previous_certificate_fresh = all(
                        sample.issuer in distances
                        and sample.world_index in scopes.get(sample.issuer, ())
                        for sample in latest_certificate.samples
                    )
                else:
                    previous_certificate_fresh = (
                        current_certificate.determines_answer
                        and not current_certificate.samples
                    )

            if current_certificate.determines_answer:
                latest_certificate = current_certificate
            if instantaneous_exact and earliest_instantaneous_step is None:
                earliest_instantaneous_step = step
            if cumulative_exact and earliest_cumulative_step is None:
                earliest_cumulative_step = step

            steps.append(
                TemporalStepReport(
                    step=step,
                    reachable_nodes=reachable_nodes,
                    instantaneous_facts=tuple(sorted(instantaneous_facts.items())),
                    cumulative_facts=tuple(sorted(cumulative_facts.items())),
                    instantaneous_worlds_remaining=len(instantaneous_worlds),
                    cumulative_worlds_remaining=len(cumulative_worlds),
                    instantaneous_determines_answer=instantaneous_exact,
                    cumulative_determines_answer=cumulative_exact,
                    current_certificate=current_certificate,
                    previous_certificate_fresh=previous_certificate_fresh,
                )
            )

        return TemporalValidationReport(
            steps=tuple(steps),
            earliest_instantaneous_step=earliest_instantaneous_step,
            earliest_cumulative_step=earliest_cumulative_step,
        )


@dataclass(frozen=True)
class NetworkConfiguration:
    """Communication graph plus the world variables sampled at each node."""

    node_count: int
    edges: frozenset[tuple[int, int]]
    sensor_scopes: tuple[tuple[int, frozenset[int]], ...]

    def __post_init__(self) -> None:
        if self.node_count < 1:
            raise ValueError("node_count must be positive")
        for left, right in self.edges:
            self._validate_node(left)
            self._validate_node(right)
            if left >= right:
                raise ValueError("edges must be normalized as (lower, higher)")
        sensor_nodes = [node for node, _ in self.sensor_scopes]
        if sensor_nodes != sorted(set(sensor_nodes)):
            raise ValueError("sensor nodes must be unique and sorted")
        for node, scope in self.sensor_scopes:
            self._validate_node(node)
            if any(index < 0 for index in scope):
                raise ValueError("sensor indices must be non-negative")

    @classmethod
    def from_edges(
        cls,
        node_count: int,
        edges: Iterable[tuple[int, int]],
        sensor_scopes: Mapping[int, set[int]],
    ) -> "NetworkConfiguration":
        normalized_edges = frozenset(
            (min(left, right), max(left, right)) for left, right in edges
        )
        return cls._build(node_count, normalized_edges, sensor_scopes)

    @classmethod
    def path(
        cls, node_count: int, sensor_scopes: Mapping[int, set[int]]
    ) -> "NetworkConfiguration":
        edges = frozenset((node, node + 1) for node in range(node_count - 1))
        return cls._build(node_count, edges, sensor_scopes)

    @classmethod
    def clique(
        cls, node_count: int, sensor_scopes: Mapping[int, set[int]]
    ) -> "NetworkConfiguration":
        edges = frozenset(
            (left, right)
            for left in range(node_count)
            for right in range(left + 1, node_count)
        )
        return cls._build(node_count, edges, sensor_scopes)

    @classmethod
    def _build(
        cls,
        node_count: int,
        edges: frozenset[tuple[int, int]],
        sensor_scopes: Mapping[int, set[int]],
    ) -> "NetworkConfiguration":
        normalized_scopes = tuple(
            (node, frozenset(scope))
            for node, scope in sorted(sensor_scopes.items())
        )
        return cls(node_count, edges, normalized_scopes)

    def observe(self, world: WorldState) -> Observation:
        return tuple(
            (node, self.observe_at_node(world, node))
            for node, _ in self.sensor_scopes
        )

    def observe_at_node(self, world: WorldState, node: int) -> NodeObservation:
        self._validate_node(node)
        scopes = dict(self.sensor_scopes)
        scope = scopes.get(node, frozenset())
        if any(index >= len(world.bits) for index in scope):
            raise ValueError("sensor index exceeds world size")
        return tuple((index, world.bits[index]) for index in sorted(scope))

    def participating_sensor_nodes(self) -> set[int]:
        return {node for node, scope in self.sensor_scopes if scope}

    def aggregation_radius(self, root: int, participating_nodes: set[int]) -> int:
        """Minimum synchronous rounds for all participants to reach ``root``."""

        self._validate_node(root)
        for node in participating_nodes:
            self._validate_node(node)
        if not participating_nodes:
            return 0

        distances, _ = self._shortest_path_tree(root)

        unreachable = participating_nodes - distances.keys()
        if unreachable:
            raise ValueError(f"sensor nodes cannot reach root: {sorted(unreachable)}")
        return max(distances[node] for node in participating_nodes)

    def communication_plan(
        self, root: int, task: BooleanTask
    ) -> CommunicationReport:
        """Return the task-specific aggregation plan rooted at ``root``."""

        self._validate_node(root)
        participants = self.participating_sensor_nodes()
        distances, parents = self._shortest_path_tree(root)
        unreachable = participants - distances.keys()
        if unreachable:
            raise ValueError(f"sensor nodes cannot reach root: {sorted(unreachable)}")

        route_edges: set[tuple[int, int]] = set()
        raw_bit_transmissions = 0
        scopes = dict(self.sensor_scopes)
        for participant in participants:
            raw_bit_transmissions += len(scopes[participant]) * distances[participant]
            node = participant
            while node != root:
                parent = parents[node]
                route_edges.add((node, parent))
                node = parent

        ordered_edges = tuple(sorted(route_edges))
        rounds = max((distances[node] for node in participants), default=0)
        return CommunicationReport(
            root=root,
            task=task,
            route_edges=ordered_edges,
            rounds=rounds,
            message_count=len(ordered_edges),
            aggregate_bit_transmissions=len(ordered_edges),
            raw_bit_transmissions=raw_bit_transmissions,
        )

    def attested_certificate(
        self,
        world: WorldState,
        task: BooleanTask,
        verifier: int,
    ) -> CertificateReport:
        """Return the smallest source-grounded certificate available to a verifier."""

        self._validate_node(verifier)
        bit_count = len(world.bits)
        scopes = dict(self.sensor_scopes)
        if any(index >= bit_count for scope in scopes.values() for index in scope):
            raise ValueError("sensor index exceeds world size")

        local_facts = dict(self.observe_at_node(world, verifier))
        distances, _ = self._shortest_path_tree(verifier)
        candidates: list[AttestedSample] = []
        unattested_indices = []
        for world_index in range(bit_count):
            if world_index in local_facts:
                continue
            issuers = [
                node
                for node, scope in self.sensor_scopes
                if world_index in scope and node in distances
            ]
            if not issuers:
                unattested_indices.append(world_index)
                continue
            issuer = min(issuers, key=lambda node: (distances[node], node))
            candidates.append(
                AttestedSample(
                    issuer=issuer,
                    world_index=world_index,
                    value=world.bits[world_index],
                )
            )

        claimed_answer = task.evaluate(world)
        for sample_count in range(len(candidates) + 1):
            for selected in combinations(candidates, sample_count):
                consistent = self._worlds_consistent_with(
                    bit_count=bit_count,
                    facts={
                        **local_facts,
                        **{sample.world_index: sample.value for sample in selected},
                    },
                )
                outcomes = {task.evaluate(candidate) for candidate in consistent}
                if outcomes == {claimed_answer}:
                    return self._certificate_report(
                        verifier=verifier,
                        task=task,
                        claimed_answer=claimed_answer,
                        samples=selected,
                        worlds_remaining=len(consistent),
                        bit_count=bit_count,
                        unattested_indices=unattested_indices,
                        determines_answer=True,
                    )

        consistent = self._worlds_consistent_with(
            bit_count=bit_count,
            facts={
                **local_facts,
                **{sample.world_index: sample.value for sample in candidates},
            },
        )
        return self._certificate_report(
            verifier=verifier,
            task=task,
            claimed_answer=claimed_answer,
            samples=candidates,
            worlds_remaining=len(consistent),
            bit_count=bit_count,
            unattested_indices=unattested_indices,
            determines_answer=False,
        )

    def _certificate_report(
        self,
        *,
        verifier: int,
        task: BooleanTask,
        claimed_answer: bool,
        samples: Iterable[AttestedSample],
        worlds_remaining: int,
        bit_count: int,
        unattested_indices: Iterable[int],
        determines_answer: bool,
    ) -> CertificateReport:
        ordered_samples = tuple(samples)
        node_bits = (self.node_count - 1).bit_length()
        index_bits = (bit_count - 1).bit_length()
        logical_payload_bits = (
            1 + len(ordered_samples) * (node_bits + index_bits + 1)
            if ordered_samples
            else 0
        )
        trust_assumptions = (
            (
                "issuer identity is authentic",
                "issuer reports its sampled value truthfully",
            )
            if ordered_samples
            else ()
        )
        return CertificateReport(
            verifier=verifier,
            task=task,
            claimed_answer=claimed_answer,
            samples=ordered_samples,
            determines_answer=determines_answer,
            worlds_remaining=worlds_remaining,
            logical_payload_bits=logical_payload_bits,
            trust_assumptions=trust_assumptions,
            unattested_indices=tuple(unattested_indices),
        )

    @staticmethod
    def _worlds_consistent_with(
        bit_count: int, facts: Mapping[int, int]
    ) -> tuple[WorldState, ...]:
        worlds = []
        for value in range(2**bit_count):
            world = WorldState.from_integer(value, bit_count)
            if all(world.bits[index] == expected for index, expected in facts.items()):
                worlds.append(world)
        return tuple(worlds)

    def _shortest_path_tree(self, root: int) -> tuple[dict[int, int], dict[int, int]]:
        """Build a deterministic breadth-first routing tree from ``root``."""

        adjacency = {node: set() for node in range(self.node_count)}
        for left, right in self.edges:
            adjacency[left].add(right)
            adjacency[right].add(left)

        distances = {root: 0}
        parents: dict[int, int] = {}
        queue = deque([root])
        while queue:
            node = queue.popleft()
            for neighbor in sorted(adjacency[node]):
                if neighbor not in distances:
                    distances[neighbor] = distances[node] + 1
                    parents[neighbor] = node
                    queue.append(neighbor)
        return distances, parents

    def _validate_node(self, node: int) -> None:
        if node < 0 or node >= self.node_count:
            raise ValueError(f"node {node} is outside the network")


def landauer_floor_joules(
    erased_entropy_bits: float, temperature_kelvin: float
) -> float:
    """Return the ideal Landauer floor for explicitly erased logical entropy."""

    if not math.isfinite(erased_entropy_bits) or erased_entropy_bits < 0:
        raise ValueError("erased entropy must be finite and non-negative")
    if not math.isfinite(temperature_kelvin) or temperature_kelvin <= 0:
        raise ValueError("temperature must be finite and positive")
    return (
        BOLTZMANN_CONSTANT_J_PER_K
        * temperature_kelvin
        * math.log(2)
        * erased_entropy_bits
    )


def evaluate_correction_cycle(cycle: CorrectionCycle) -> CorrectionCycleReport:
    """Evaluate correction, reset completion, and its ideal erasure floor."""

    erased_entropy = sum(
        entropy_bits for _, entropy_bits in cycle.erased_entropy_by_register
    )
    uncleared = cycle.required_cleared_registers - cycle.cleared_registers
    remaining_error = _hamming_distance(cycle.corrected_state, cycle.observation)
    return CorrectionCycleReport(
        prediction_error_bits=_hamming_distance(cycle.prediction, cycle.observation),
        remaining_error_bits=remaining_error,
        correction_payload_bits=cycle.corrective_message_bits,
        erased_logical_entropy_bits=erased_entropy,
        landauer_floor_joules=landauer_floor_joules(
            erased_entropy, cycle.temperature_kelvin
        ),
        uncleared_required_registers=uncleared,
        next_message_ready=remaining_error == 0 and not uncleared,
        system_boundary=cycle.system_boundary,
        reset_contract=cycle.reset_contract,
    )


def analyze_correction_ensemble(
    samples: Iterable[CorrectionEnsembleSample], *, temperature_kelvin: float
) -> CorrectionEnsembleReport:
    """Measure conditional erasure entropy under equally weighted samples."""

    sample_tuple = tuple(samples)
    if not sample_tuple:
        raise ValueError("a correction ensemble needs at least one sample")
    dimensions = (
        {len(sample.erased_state) for sample in sample_tuple},
        {len(sample.retained_side_information) for sample in sample_tuple},
        {len(sample.corrective_message) for sample in sample_tuple},
    )
    if any(len(lengths) != 1 for lengths in dimensions):
        raise ValueError("ensemble registers need consistent dimensions")
    landauer_floor_joules(0, temperature_kelvin)

    without_message = _conditional_erasure_entropy(
        sample_tuple, include_message=False
    )
    with_message = _conditional_erasure_entropy(sample_tuple, include_message=True)
    message_information = max(0.0, without_message - with_message)
    erased_width = len(sample_tuple[0].erased_state)
    naive_marginal = sum(
        _conditional_erasure_entropy(
            sample_tuple, include_message=True, erased_index=index
        )
        for index in range(erased_width)
    )
    correlation_savings = max(0.0, naive_marginal - with_message)
    return CorrectionEnsembleReport(
        sample_count=len(sample_tuple),
        entropy_without_message_bits=without_message,
        entropy_with_message_bits=with_message,
        message_information_bits=message_information,
        naive_marginal_entropy_bits=naive_marginal,
        correlation_savings_bits=correlation_savings,
        landauer_without_message_joules=landauer_floor_joules(
            without_message, temperature_kelvin
        ),
        landauer_with_message_joules=landauer_floor_joules(
            with_message, temperature_kelvin
        ),
        landauer_avoided_joules=landauer_floor_joules(
            message_information, temperature_kelvin
        ),
        temperature_kelvin=temperature_kelvin,
    )


def analyze_correction_sequence(
    cycles: Iterable[CorrectionCycle], *, independent_reset_boundaries: bool
) -> CorrectionSequenceReport:
    """Sum reset floors only when the caller declares independent boundaries."""

    cycle_tuple = tuple(cycles)
    if not cycle_tuple:
        raise ValueError("a correction sequence needs at least one cycle")
    reports = tuple(evaluate_correction_cycle(cycle) for cycle in cycle_tuple)
    if independent_reset_boundaries:
        total_entropy: float | None = sum(
            report.erased_logical_entropy_bits for report in reports
        )
        total_floor: float | None = sum(
            report.landauer_floor_joules for report in reports
        )
    else:
        total_entropy = None
        total_floor = None
    return CorrectionSequenceReport(
        cycle_count=len(reports),
        all_next_message_ready=all(report.next_message_ready for report in reports),
        independent_reset_boundaries=independent_reset_boundaries,
        total_prediction_error_bits=sum(
            report.prediction_error_bits for report in reports
        ),
        total_erased_entropy_bits=total_entropy,
        landauer_floor_joules=total_floor,
    )


def _conditional_erasure_entropy(
    samples: tuple[CorrectionEnsembleSample, ...],
    *,
    include_message: bool,
    erased_index: int | None = None,
) -> float:
    context_counts: dict[
        tuple[tuple[int, ...], tuple[int, ...]], dict[tuple[int, ...], int]
    ] = defaultdict(lambda: defaultdict(int))
    for sample in samples:
        context = (
            sample.retained_side_information,
            sample.corrective_message if include_message else (),
        )
        erased = (
            sample.erased_state
            if erased_index is None
            else (sample.erased_state[erased_index],)
        )
        context_counts[context][erased] += 1

    sample_count = len(samples)
    entropy = 0.0
    for counts in context_counts.values():
        group_count = sum(counts.values())
        group_entropy = -sum(
            (count / group_count) * math.log2(count / group_count)
            for count in counts.values()
        )
        entropy += (group_count / sample_count) * group_entropy
    return entropy


def analyze_trajectory_compatibility(
    trajectory: ProspectiveTrajectory,
    envelope: TransitionEnvelope,
) -> TrajectoryCompatibilityReport:
    """Compare one intended path with a receiver's finite transition envelope."""

    bit_count = len(trajectory.states[0].bits)
    if len(envelope.accepted_target.bits) != bit_count:
        raise ValueError("trajectory and envelope need equal dimensions")

    transition_loads = tuple(
        _hamming_distance(left, right)
        for left, right in zip(trajectory.states, trajectory.states[1:])
    )
    previous_load = 0
    accelerations = []
    for load in transition_loads:
        accelerations.append(load - previous_load)
        previous_load = load
    acceleration_loads = tuple(accelerations)

    changes_by_epoch = []
    for offset, (left, right) in enumerate(
        zip(trajectory.states, trajectory.states[1:]), start=1
    ):
        changed = frozenset(
            index
            for index, (left_bit, right_bit) in enumerate(zip(left.bits, right.bits))
            if left_bit != right_bit
        )
        changes_by_epoch.append((trajectory.formed_at + offset, changed))
    required_authorization = frozenset().union(
        *(changed for _, changed in changes_by_epoch)
    ) - envelope.authorized_indices

    conflicts = []
    if trajectory.states[-1] != envelope.accepted_target:
        conflicts.append(
            TrajectoryConflict(
                "direction",
                trajectory.completion_at,
                trajectory.states[-1],
                envelope.accepted_target,
            )
        )
    if trajectory.completion_at < envelope.earliest_completion_at:
        conflicts.append(
            TrajectoryConflict(
                "horizon",
                trajectory.completion_at,
                trajectory.completion_at,
                envelope.earliest_completion_at,
            )
        )
    if required_authorization:
        first_epoch = min(
            epoch
            for epoch, changed in changes_by_epoch
            if changed - envelope.authorized_indices
        )
        conflicts.append(
            TrajectoryConflict(
                "authorization",
                first_epoch,
                required_authorization,
                envelope.authorized_indices,
            )
        )
    for offset, load in enumerate(transition_loads, start=1):
        if load > envelope.max_load_per_epoch:
            conflicts.append(
                TrajectoryConflict(
                    "rate",
                    trajectory.formed_at + offset,
                    load,
                    envelope.max_load_per_epoch,
                )
            )
    for offset, acceleration in enumerate(acceleration_loads, start=1):
        if acceleration > envelope.max_acceleration_per_epoch:
            conflicts.append(
                TrajectoryConflict(
                    "acceleration",
                    trajectory.formed_at + offset,
                    acceleration,
                    envelope.max_acceleration_per_epoch,
                )
            )

    kind_order = ("direction", "horizon", "authorization", "rate", "acceleration")
    conflict_types = tuple(
        kind for kind in kind_order if any(conflict.kind == kind for conflict in conflicts)
    )
    witness = _accepted_trajectory_witness(
        start=trajectory.states[0],
        node=trajectory.node,
        formed_at=trajectory.formed_at,
        envelope=envelope,
    )
    minimum_completion = witness.completion_at if witness else None
    return TrajectoryCompatibilityReport(
        compatible=not conflicts,
        conflicts=tuple(conflicts),
        conflict_types=conflict_types,
        first_conflict_epoch=(
            min(conflict.epoch for conflict in conflicts) if conflicts else None
        ),
        transition_loads=transition_loads,
        acceleration_loads=acceleration_loads,
        excess_load_by_epoch=tuple(
            max(0, load - envelope.max_load_per_epoch) for load in transition_loads
        ),
        excess_acceleration_by_epoch=tuple(
            max(0, acceleration - envelope.max_acceleration_per_epoch)
            for acceleration in acceleration_loads
        ),
        required_max_load=max(transition_loads, default=0),
        required_max_acceleration=max((0, *acceleration_loads)),
        required_authorization=required_authorization,
        minimum_feasible_completion_at=minimum_completion,
        minimum_delay=(
            max(0, minimum_completion - trajectory.completion_at)
            if minimum_completion is not None
            else None
        ),
        accepted_witness=witness,
    )


def _accepted_trajectory_witness(
    start: WorldState,
    node: int,
    formed_at: int,
    envelope: TransitionEnvelope,
) -> ProspectiveTrajectory | None:
    """Find the shortest accepted path, retaining epoch because waiting matters."""

    bit_count = len(start.bits)
    worlds = tuple(WorldState.from_integer(value, bit_count) for value in range(2**bit_count))
    max_epoch = max(formed_at, envelope.earliest_completion_at) + (
        2**bit_count * (bit_count + 1)
    )
    queue: deque[tuple[WorldState, int, tuple[WorldState, ...]]] = deque(
        [(start, 0, (start,))]
    )
    visited = {(start, 0, formed_at)}
    while queue:
        current, previous_load, path = queue.popleft()
        epoch = formed_at + len(path) - 1
        if current == envelope.accepted_target and epoch >= envelope.earliest_completion_at:
            return ProspectiveTrajectory(node=node, formed_at=formed_at, states=path)
        if epoch >= max_epoch:
            continue

        next_epoch = epoch + 1
        for candidate in worlds:
            changed = frozenset(
                index
                for index, (current_bit, candidate_bit) in enumerate(
                    zip(current.bits, candidate.bits)
                )
                if current_bit != candidate_bit
            )
            load = len(changed)
            if not changed <= envelope.authorized_indices:
                continue
            if load > envelope.max_load_per_epoch:
                continue
            if load - previous_load > envelope.max_acceleration_per_epoch:
                continue
            if candidate == envelope.accepted_target and next_epoch < envelope.earliest_completion_at:
                continue
            key = (candidate, load, next_epoch)
            if key in visited:
                continue
            visited.add(key)
            queue.append((candidate, load, path + (candidate,)))
    return None


def evaluate_timespace_exchange(
    actual_world: WorldState,
    exchange: TimespaceExchange,
    control_scopes: Mapping[int, set[int]],
    coordination_weight: int = 2,
    realized_world: WorldState | None = None,
) -> TimespaceReport:
    """Compare self-only, modeled, and oracle local targets for one exchange."""

    bit_count = len(actual_world.bits)
    realized_world = realized_world or actual_world
    if len(realized_world.bits) != bit_count:
        raise ValueError("actual and realized worlds need equal dimensions")
    endpoint_worlds = (
        exchange.sender_point.desired_world,
        exchange.receiver_point.desired_world,
        exchange.sender_model_of_receiver,
        exchange.receiver_model_of_sender,
    )
    if any(len(world.bits) != bit_count for world in endpoint_worlds):
        raise ValueError("actual world and prospective states need equal dimensions")
    if coordination_weight < 0:
        raise ValueError("coordination_weight must be non-negative")

    nodes = (exchange.sender, exchange.receiver)
    scopes = {node: frozenset(control_scopes.get(node, set())) for node in nodes}
    if any(index < 0 or index >= bit_count for scope in scopes.values() for index in scope):
        raise ValueError("control index exceeds world size")
    if scopes[exchange.sender] & scopes[exchange.receiver]:
        raise ValueError("control scopes must not overlap")

    sender_desire = exchange.sender_point.desired_world
    receiver_desire = exchange.receiver_point.desired_world
    desires = {
        exchange.sender: sender_desire,
        exchange.receiver: receiver_desire,
    }
    cross_models = {
        exchange.sender: exchange.sender_model_of_receiver,
        exchange.receiver: exchange.receiver_model_of_sender,
    }
    authorizations = {
        exchange.sender: exchange.receiver_authorizes_sender,
        exchange.receiver: exchange.sender_authorizes_receiver,
    }
    other_node = {
        exchange.sender: exchange.receiver,
        exchange.receiver: exchange.sender,
    }

    def target_for(policy: str) -> WorldState:
        bits = list(actual_world.bits)
        for node in nodes:
            own_desire = desires[node]
            if policy == "self_only":
                modeled_other = None
            elif policy == "modeled":
                modeled_other = cross_models[node]
            else:
                modeled_other = desires[other_node[node]]

            for index in sorted(scopes[node]):
                candidates = []
                for value in (0, 1):
                    loss = int(value != own_desire.bits[index])
                    if modeled_other is not None and index in authorizations[node]:
                        loss += coordination_weight * int(
                            value != modeled_other.bits[index]
                        )
                    candidates.append(
                        (loss, int(value != actual_world.bits[index]), value)
                    )
                bits[index] = min(candidates)[2]
        return WorldState(tuple(bits))

    def realized_loss(target: WorldState) -> int:
        loss = 0
        for node in nodes:
            own_desire = desires[node]
            actual_other_desire = desires[other_node[node]]
            for index in scopes[node]:
                loss += int(target.bits[index] != own_desire.bits[index])
                if index in authorizations[node]:
                    loss += coordination_weight * int(
                        target.bits[index] != actual_other_desire.bits[index]
                    )
        return loss

    self_only_target = target_for("self_only")
    modeled_target = target_for("modeled")
    oracle_target = target_for("oracle")
    self_only_loss = realized_loss(self_only_target)
    modeled_loss = realized_loss(modeled_target)
    oracle_loss = realized_loss(oracle_target)
    predictive_gain = self_only_loss - modeled_loss

    authorization_violations = []
    for node in nodes:
        for index in scopes[node] - authorizations[node]:
            if modeled_target.bits[index] != self_only_target.bits[index]:
                authorization_violations.append((node, index))

    logical_payload_bits = 6 * bit_count + exchange.idea_payload_bits
    return TimespaceReport(
        desire_distance=_hamming_distance(sender_desire, receiver_desire),
        sender_model_error=_hamming_distance(
            exchange.sender_model_of_receiver, receiver_desire
        ),
        receiver_model_error=_hamming_distance(
            exchange.receiver_model_of_sender, sender_desire
        ),
        self_only_target=self_only_target,
        modeled_target=modeled_target,
        oracle_target=oracle_target,
        self_only_loss=self_only_loss,
        modeled_loss=modeled_loss,
        oracle_loss=oracle_loss,
        predictive_gain=predictive_gain,
        oracle_gap=modeled_loss - oracle_loss,
        modeling_efficiency=(
            Fraction(predictive_gain, logical_payload_bits)
            if logical_payload_bits
            else Fraction(0, 1)
        ),
        realized_world=realized_world,
        sender_realization_gap=_hamming_distance(realized_world, sender_desire),
        receiver_realization_gap=_hamming_distance(realized_world, receiver_desire),
        modeled_target_realization_gap=_hamming_distance(
            realized_world, modeled_target
        ),
        sender_knowledge_after=(
            exchange.sender_knowledge | exchange.receiver_transmits
        ),
        receiver_knowledge_after=(
            exchange.receiver_knowledge | exchange.sender_transmits
        ),
        logical_payload_bits=logical_payload_bits,
        authorization_violations=tuple(authorization_violations),
    )


def _hamming_distance(left: WorldState, right: WorldState) -> int:
    if len(left.bits) != len(right.bits):
        raise ValueError("worlds need equal dimensions")
    return sum(left_bit != right_bit for left_bit, right_bit in zip(left.bits, right.bits))


def analyze_identifiability(
    worlds: Iterable[WorldState],
    network: NetworkConfiguration,
    task: BooleanTask,
) -> IdentifiabilityReport:
    """Partition worlds by observation and test task invariance per partition."""

    world_list = tuple(worlds)
    if not world_list:
        raise ValueError("at least one possible world is required")
    return _analyze_partition(
        world_list,
        key=lambda world: network.observe(world),
        task=task,
    )


def classify_validation_regime(
    worlds: Iterable[WorldState],
    network: NetworkConfiguration,
    task: BooleanTask,
) -> str:
    """Classify exact validation as local, distributed, or predictive."""

    world_list = tuple(worlds)
    global_report = analyze_identifiability(world_list, network, task)
    if not global_report.identifiable:
        return "predictive"

    for node in range(network.node_count):
        local_report = _analyze_partition(
            world_list,
            key=lambda world, node=node: network.observe_at_node(world, node),
            task=task,
        )
        if local_report.identifiable:
            return "local"
    return "distributed"


def _analyze_partition(
    worlds: tuple[WorldState, ...],
    key,
    task: BooleanTask,
) -> IdentifiabilityReport:
    groups: dict[Hashable, list[WorldState]] = defaultdict(list)
    for world in worlds:
        groups[key(world)].append(world)

    correct_under_best_predictor = 0
    counterexample = None
    for group in groups.values():
        outcomes: dict[bool, list[WorldState]] = defaultdict(list)
        for world in group:
            outcomes[task.evaluate(world)].append(world)
        correct_under_best_predictor += max(len(bucket) for bucket in outcomes.values())
        if counterexample is None and len(outcomes) > 1:
            buckets = list(outcomes.values())
            counterexample = (buckets[0][0], buckets[1][0])

    return IdentifiabilityReport(
        identifiable=counterexample is None,
        best_possible_accuracy=Fraction(correct_under_best_predictor, len(worlds)),
        counterexample=counterexample,
    )