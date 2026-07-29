import math
from fractions import Fraction
from pathlib import Path

import network_relativity.model as observation_model
from network_relativity.experiment import run_experiment
from network_relativity.model import (
    BooleanTask,
    NetworkConfiguration,
    ProspectivePoint,
    TemporalNetworkSequence,
    TimespaceExchange,
    WorldState,
    analyze_identifiability,
    classify_validation_regime,
    evaluate_timespace_exchange,
)


def all_worlds(bit_count: int) -> tuple[WorldState, ...]:
    return tuple(
        WorldState.from_integer(value, bit_count)
        for value in range(2**bit_count)
    )


def test_one_node_that_samples_every_relevant_bit_makes_validation_local() -> None:
    worlds = all_worlds(3)
    network = NetworkConfiguration.clique(
        node_count=3,
        sensor_scopes={0: {0, 1, 2}},
    )

    report = analyze_identifiability(worlds, network, BooleanTask.PARITY)

    assert report.identifiable is True
    assert report.best_possible_accuracy == Fraction(1, 1)
    assert classify_validation_regime(worlds, network, BooleanTask.PARITY) == "local"


def test_distributed_sensors_make_validation_identifiable_but_not_local() -> None:
    worlds = all_worlds(3)
    network = NetworkConfiguration.path(
        node_count=3,
        sensor_scopes={0: {0}, 1: {1}, 2: {2}},
    )

    report = analyze_identifiability(worlds, network, BooleanTask.PARITY)

    assert report.identifiable is True
    assert report.best_possible_accuracy == Fraction(1, 1)
    assert classify_validation_regime(worlds, network, BooleanTask.PARITY) == "distributed"
    assert network.aggregation_radius(root=0, participating_nodes={0, 1, 2}) == 2


def test_missing_parity_sensor_creates_an_observational_counterexample() -> None:
    worlds = all_worlds(3)
    network = NetworkConfiguration.path(
        node_count=3,
        sensor_scopes={0: {0}, 1: {1}},
    )

    report = analyze_identifiability(worlds, network, BooleanTask.PARITY)

    assert report.identifiable is False
    assert report.best_possible_accuracy == Fraction(1, 2)
    assert report.counterexample is not None
    left, right = report.counterexample
    assert network.observe(left) == network.observe(right)
    assert BooleanTask.PARITY.evaluate(left) != BooleanTask.PARITY.evaluate(right)
    assert classify_validation_regime(worlds, network, BooleanTask.PARITY) == "predictive"


def test_topology_changes_aggregation_cost_without_changing_observations() -> None:
    scopes = {index: {index} for index in range(5)}
    path = NetworkConfiguration.path(node_count=5, sensor_scopes=scopes)
    clique = NetworkConfiguration.clique(node_count=5, sensor_scopes=scopes)

    world = WorldState((1, 0, 1, 0, 1))

    assert path.observe(world) == clique.observe(world)
    assert path.aggregation_radius(root=0, participating_nodes=set(scopes)) == 4
    assert clique.aggregation_radius(root=0, participating_nodes=set(scopes)) == 1


def test_path_communication_plan_separates_raw_forwarding_from_aggregation() -> None:
    scopes = {index: {index} for index in range(5)}
    network = NetworkConfiguration.path(node_count=5, sensor_scopes=scopes)

    report = network.communication_plan(root=2, task=BooleanTask.PARITY)

    assert report.rounds == 2
    assert report.route_edges == ((0, 1), (1, 2), (3, 2), (4, 3))
    assert report.message_count == 4
    assert report.aggregate_bit_transmissions == 4
    assert report.raw_bit_transmissions == 6


def test_clique_reduces_rounds_but_not_one_message_per_remote_sensor() -> None:
    scopes = {index: {index} for index in range(5)}
    network = NetworkConfiguration.clique(node_count=5, sensor_scopes=scopes)

    report = network.communication_plan(root=2, task=BooleanTask.OR)

    assert report.rounds == 1
    assert report.message_count == 4
    assert report.aggregate_bit_transmissions == 4
    assert report.raw_bit_transmissions == 4


def test_central_sensor_at_validation_root_needs_no_communication() -> None:
    network = NetworkConfiguration.path(
        node_count=5,
        sensor_scopes={2: {0, 1, 2, 3, 4}},
    )

    report = network.communication_plan(root=2, task=BooleanTask.PARITY)

    assert report.rounds == 0
    assert report.route_edges == ()
    assert report.message_count == 0
    assert report.aggregate_bit_transmissions == 0
    assert report.raw_bit_transmissions == 0


def test_parity_certificate_reveals_every_fact_missing_at_verifier() -> None:
    network = NetworkConfiguration.path(
        node_count=4,
        sensor_scopes={index: {index} for index in range(4)},
    )

    report = network.attested_certificate(
        world=WorldState((1, 0, 1, 1)),
        task=BooleanTask.PARITY,
        verifier=0,
    )

    assert report.determines_answer is True
    assert report.claimed_answer is True
    assert tuple(
        (sample.issuer, sample.world_index, sample.value)
        for sample in report.samples
    ) == ((1, 1, 0), (2, 2, 1), (3, 3, 1))
    assert report.worlds_remaining == 1
    assert report.logical_payload_bits == 16
    assert report.trust_assumptions == (
        "issuer identity is authentic",
        "issuer reports its sampled value truthfully",
    )


def test_true_or_needs_only_one_remote_attested_one() -> None:
    network = NetworkConfiguration.path(
        node_count=4,
        sensor_scopes={index: {index} for index in range(4)},
    )

    report = network.attested_certificate(
        world=WorldState((0, 0, 1, 0)),
        task=BooleanTask.OR,
        verifier=0,
    )

    assert report.determines_answer is True
    assert tuple(
        (sample.issuer, sample.world_index, sample.value)
        for sample in report.samples
    ) == ((2, 2, 1),)
    assert report.worlds_remaining == 4
    assert report.logical_payload_bits == 6


def test_false_or_requires_every_unobserved_zero() -> None:
    network = NetworkConfiguration.path(
        node_count=4,
        sensor_scopes={index: {index} for index in range(4)},
    )

    report = network.attested_certificate(
        world=WorldState((0, 0, 0, 0)),
        task=BooleanTask.OR,
        verifier=0,
    )

    assert report.determines_answer is True
    assert len(report.samples) == 3
    assert report.worlds_remaining == 1
    assert report.logical_payload_bits == 16


def test_missing_sensor_prevents_source_grounded_parity_certificate() -> None:
    network = NetworkConfiguration.path(
        node_count=4,
        sensor_scopes={0: {0}, 1: {1}, 2: {2}},
    )

    report = network.attested_certificate(
        world=WorldState((0, 0, 0, 1)),
        task=BooleanTask.PARITY,
        verifier=0,
    )

    assert report.determines_answer is False
    assert len(report.samples) == 2
    assert report.worlds_remaining == 2


def test_local_verifier_needs_no_certificate_or_trust_assumption() -> None:
    network = NetworkConfiguration.path(
        node_count=4,
        sensor_scopes={0: {0, 1, 2, 3}},
    )

    report = network.attested_certificate(
        world=WorldState((1, 0, 1, 1)),
        task=BooleanTask.PARITY,
        verifier=0,
    )

    assert report.determines_answer is True
    assert report.samples == ()
    assert report.logical_payload_bits == 0
    assert report.trust_assumptions == ()


def test_rotating_sensors_become_exact_only_after_observations_accumulate() -> None:
    sequence = TemporalNetworkSequence(
        snapshots=(
            NetworkConfiguration.from_edges(
                node_count=2,
                edges={(0, 1)},
                sensor_scopes={0: {0}},
            ),
            NetworkConfiguration.from_edges(
                node_count=2,
                edges={(0, 1)},
                sensor_scopes={1: {1}},
            ),
        )
    )

    report = sequence.analyze(
        world=WorldState((1, 0)),
        task=BooleanTask.PARITY,
        verifier=0,
    )

    assert report.earliest_instantaneous_step is None
    assert report.earliest_cumulative_step == 1
    assert report.steps[0].instantaneous_determines_answer is False
    assert report.steps[0].cumulative_worlds_remaining == 2
    assert report.steps[1].instantaneous_determines_answer is False
    assert report.steps[1].cumulative_determines_answer is True
    assert report.steps[1].cumulative_facts == ((0, 1), (1, 0))


def test_link_failure_expires_certificate_but_not_cached_static_world_facts() -> None:
    sequence = TemporalNetworkSequence(
        snapshots=(
            NetworkConfiguration.from_edges(
                node_count=2,
                edges={(0, 1)},
                sensor_scopes={0: {0}, 1: {1}},
            ),
            NetworkConfiguration.from_edges(
                node_count=2,
                edges=set(),
                sensor_scopes={0: {0}, 1: {1}},
            ),
        )
    )

    report = sequence.analyze(
        world=WorldState((1, 1)),
        task=BooleanTask.PARITY,
        verifier=0,
    )

    assert report.steps[0].current_certificate.determines_answer is True
    assert report.steps[0].previous_certificate_fresh is None
    assert report.steps[1].previous_certificate_fresh is False
    assert report.steps[1].current_certificate.determines_answer is False
    assert report.steps[1].instantaneous_determines_answer is False
    assert report.steps[1].cumulative_determines_answer is True


def test_recovery_restores_instantaneous_validation() -> None:
    sequence = TemporalNetworkSequence(
        snapshots=(
            NetworkConfiguration.from_edges(
                node_count=2,
                edges=set(),
                sensor_scopes={0: {0}, 1: {1}},
            ),
            NetworkConfiguration.from_edges(
                node_count=2,
                edges={(0, 1)},
                sensor_scopes={0: {0}, 1: {1}},
            ),
        )
    )

    report = sequence.analyze(
        world=WorldState((0, 1)),
        task=BooleanTask.PARITY,
        verifier=0,
    )

    assert report.earliest_instantaneous_step == 1
    assert report.earliest_cumulative_step == 1
    assert report.steps[0].reachable_nodes == (0,)
    assert report.steps[1].reachable_nodes == (0, 1)


def test_ui_exposes_the_dynamic_network_timeline_contract() -> None:
    html = (Path(__file__).parents[1] / "web" / "index.html").read_text()

    for marker in (
        'id="dynamicScenario"',
        'id="epochSlider"',
        'id="instantaneousStatus"',
        'id="cumulativeStatus"',
        'id="freshnessStatus"',
        "function temporalAnalysis()",
        "World held static across epochs",
        "network-relativity-ui-state/v0.7",
        'id="timespaceScenario"',
        'id="senderDesireBits"',
        'id="realizedWorldBits"',
        'id="predictiveGain"',
        "function timespaceAnalysis()",
        "Desire is not permission",
        'id="trajectoryPreset"',
        'id="trajectoryMaxAcceleration"',
        'id="trajectoryCompatibility"',
        'id="acceptedTrajectory"',
        'id="trajectoryRepair"',
        "function trajectoryAnalysis()",
        "function acceptedTrajectoryWitness(",
        "Physical energy remains unpriced",
        'id="correctionPreset"',
        'id="correctionEntropyBits"',
        'id="correctionTemperature"',
        'id="correctionIndependent"',
        'id="correctionSendState"',
        'id="correctionConditionalEntropy"',
        'id="correctionSequenceFloor"',
        "function correctionAnalysis()",
        "function applyCorrectionPreset(",
        "measured_physical_energy_joules",
        "Displayed joules are an ideal Landauer lower bound",
    ):
        assert marker in html


def timespace_exchange(
    *,
    receiver_desire: WorldState,
    sender_model: WorldState,
    receiver_authorizes_sender: frozenset[int] = frozenset({0}),
) -> TimespaceExchange:
    return TimespaceExchange(
        sender=0,
        receiver=1,
        sent_at=0,
        received_at=1,
        sender_point=ProspectivePoint(
            node=0,
            formed_at=0,
            horizon=2,
            desired_world=WorldState((0, 0)),
        ),
        receiver_point=ProspectivePoint(
            node=1,
            formed_at=1,
            horizon=2,
            desired_world=receiver_desire,
        ),
        sender_model_of_receiver=sender_model,
        receiver_model_of_sender=WorldState((0, 0)),
        sender_authorizes_receiver=frozenset(),
        receiver_authorizes_sender=receiver_authorizes_sender,
        sender_knowledge=frozenset({"observation:x0=0"}),
        receiver_knowledge=frozenset({"constraint:preserve-x1"}),
        sender_transmits=frozenset({"observation:x0=0"}),
        receiver_transmits=frozenset({"constraint:preserve-x1"}),
        idea_payload_bits=2,
    )


def test_accurate_timespace_model_improves_authorized_local_coordination() -> None:
    report = evaluate_timespace_exchange(
        actual_world=WorldState((0, 0)),
        exchange=timespace_exchange(
            receiver_desire=WorldState((1, 0)),
            sender_model=WorldState((1, 0)),
        ),
        control_scopes={0: {0}, 1: {1}},
    )

    assert report.sender_model_error == 0
    assert report.self_only_target == WorldState((0, 0))
    assert report.modeled_target == WorldState((1, 0))
    assert report.oracle_target == report.modeled_target
    assert report.modeled_loss < report.self_only_loss
    assert report.predictive_gain == 1


def test_wrong_timespace_model_can_be_worse_than_ignoring_the_neighbor() -> None:
    report = evaluate_timespace_exchange(
        actual_world=WorldState((0, 0)),
        exchange=timespace_exchange(
            receiver_desire=WorldState((0, 0)),
            sender_model=WorldState((1, 0)),
        ),
        control_scopes={0: {0}, 1: {1}},
    )

    assert report.sender_model_error == 1
    assert report.self_only_loss == 0
    assert report.modeled_loss == 3
    assert report.predictive_gain == -3


def test_inferred_desire_without_authorization_cannot_change_an_action() -> None:
    report = evaluate_timespace_exchange(
        actual_world=WorldState((0, 0)),
        exchange=timespace_exchange(
            receiver_desire=WorldState((1, 0)),
            sender_model=WorldState((1, 0)),
            receiver_authorizes_sender=frozenset(),
        ),
        control_scopes={0: {0}, 1: {1}},
    )

    assert report.modeled_target == report.self_only_target
    assert report.predictive_gain == 0
    assert report.authorization_violations == ()


def test_ideas_accumulate_bidirectionally_without_merging_private_desires() -> None:
    exchange = timespace_exchange(
        receiver_desire=WorldState((1, 0)),
        sender_model=WorldState((1, 0)),
    )
    report = evaluate_timespace_exchange(
        actual_world=WorldState((0, 0)),
        exchange=exchange,
        control_scopes={0: {0}, 1: {1}},
    )

    assert report.sender_knowledge_after == frozenset(
        {"observation:x0=0", "constraint:preserve-x1"}
    )
    assert report.receiver_knowledge_after == frozenset(
        {"observation:x0=0", "constraint:preserve-x1"}
    )
    assert exchange.sender_point.desired_world != exchange.receiver_point.desired_world
    assert report.logical_payload_bits == 14


def test_realized_world_remains_distinct_from_desire_and_proposed_target() -> None:
    report = evaluate_timespace_exchange(
        actual_world=WorldState((0, 0)),
        realized_world=WorldState((1, 1)),
        exchange=timespace_exchange(
            receiver_desire=WorldState((1, 0)),
            sender_model=WorldState((1, 0)),
        ),
        control_scopes={0: {0}, 1: {1}},
    )

    assert report.realized_world == WorldState((1, 1))
    assert report.sender_realization_gap == 2
    assert report.receiver_realization_gap == 1
    assert report.modeled_target_realization_gap == 1


def test_trajectory_compatibility_api_exists() -> None:
    assert all(
        hasattr(observation_model, name)
        for name in (
            "ProspectiveTrajectory",
            "TransitionEnvelope",
            "TrajectoryCompatibilityReport",
            "analyze_trajectory_compatibility",
        )
    )


def prospective_trajectory(*states: tuple[int, int]):
    return observation_model.ProspectiveTrajectory(
        node=0,
        formed_at=0,
        states=tuple(WorldState(state) for state in states),
    )


def transition_envelope(
    target: tuple[int, int] = (1, 1),
    earliest: int = 2,
    authorization: frozenset[int] = frozenset({0, 1}),
    max_load: int = 1,
    max_acceleration: int = 1,
):
    return observation_model.TransitionEnvelope(
        receiver=1,
        accepted_target=WorldState(target),
        earliest_completion_at=earliest,
        authorized_indices=authorization,
        max_load_per_epoch=max_load,
        max_acceleration_per_epoch=max_acceleration,
    )


def test_smooth_trajectory_is_compatible_with_acceptance_envelope() -> None:
    report = observation_model.analyze_trajectory_compatibility(
        prospective_trajectory((0, 0), (1, 0), (1, 1)),
        transition_envelope(),
    )

    assert report.compatible
    assert report.conflict_types == ()
    assert report.transition_loads == (1, 1)
    assert report.acceleration_loads == (1, 0)
    assert report.minimum_feasible_completion_at == 2
    assert report.minimum_delay == 0


def test_same_endpoint_and_horizon_can_have_acceleration_conflict() -> None:
    report = observation_model.analyze_trajectory_compatibility(
        prospective_trajectory((0, 0), (0, 0), (1, 1)),
        transition_envelope(max_load=2, max_acceleration=1),
    )

    assert not report.compatible
    assert report.conflict_types == ("acceleration",)
    assert report.first_conflict_epoch == 2
    assert report.required_max_acceleration == 2
    assert report.minimum_feasible_completion_at == 2
    assert report.accepted_witness is not None
    assert report.accepted_witness.states[-1] == WorldState((1, 1))


def test_early_completion_is_repaired_by_receiver_delay() -> None:
    report = observation_model.analyze_trajectory_compatibility(
        prospective_trajectory((0, 0), (1, 0), (1, 1)),
        transition_envelope(earliest=4),
    )

    assert report.conflict_types == ("horizon",)
    assert report.first_conflict_epoch == 2
    assert report.minimum_feasible_completion_at == 4
    assert report.minimum_delay == 2
    assert report.accepted_witness is not None
    assert report.accepted_witness.completion_at == 4


def test_rate_conflict_is_repaired_by_one_extra_epoch() -> None:
    report = observation_model.analyze_trajectory_compatibility(
        prospective_trajectory((0, 0), (1, 1)),
        transition_envelope(earliest=1, max_load=1, max_acceleration=2),
    )

    assert report.conflict_types == ("rate",)
    assert report.first_conflict_epoch == 1
    assert report.required_max_load == 2
    assert report.minimum_feasible_completion_at == 2
    assert report.minimum_delay == 1


def test_unauthorized_transition_has_no_accepted_witness() -> None:
    report = observation_model.analyze_trajectory_compatibility(
        prospective_trajectory((0, 0), (1, 0)),
        transition_envelope(
            target=(1, 0),
            earliest=1,
            authorization=frozenset({1}),
            max_load=2,
            max_acceleration=2,
        ),
    )

    assert report.conflict_types == ("authorization",)
    assert report.required_authorization == frozenset({0})
    assert report.minimum_feasible_completion_at is None
    assert report.accepted_witness is None


def test_different_accepted_endpoint_is_direction_conflict() -> None:
    report = observation_model.analyze_trajectory_compatibility(
        prospective_trajectory((0, 0), (1, 0)),
        transition_envelope(
            target=(0, 1),
            earliest=1,
            max_load=2,
            max_acceleration=2,
        ),
    )

    assert report.conflict_types == ("direction",)
    assert report.first_conflict_epoch == 1
    assert report.minimum_feasible_completion_at == 1


def test_correction_thermodynamics_api_exists() -> None:
    assert all(
        hasattr(observation_model, name)
        for name in (
            "CorrectionCycle",
            "CorrectionCycleReport",
            "CorrectionEnsembleSample",
            "CorrectionEnsembleReport",
            "CorrectionSequenceReport",
            "evaluate_correction_cycle",
            "analyze_correction_ensemble",
            "analyze_correction_sequence",
            "landauer_floor_joules",
        )
    )


def correction_cycle(
    *,
    corrected: tuple[int, int] = (1, 0),
    required: frozenset[str] = frozenset(),
    cleared: frozenset[str] = frozenset(),
    entropy: tuple[tuple[str, float], ...] = (),
):
    return observation_model.CorrectionCycle(
        prediction=WorldState((0, 0)),
        observation=WorldState((1, 0)),
        corrected_state=WorldState(corrected),
        corrective_message_bits=1,
        system_boundary="finite-logical-registers",
        reset_contract="before-next-message",
        required_cleared_registers=required,
        cleared_registers=cleared,
        erased_entropy_by_register=entropy,
        temperature_kelvin=300.0,
    )


def test_retained_wrong_prediction_has_no_immediate_erasure_floor() -> None:
    report = observation_model.evaluate_correction_cycle(correction_cycle())

    assert report.prediction_error_bits == 1
    assert report.remaining_error_bits == 0
    assert report.erased_logical_entropy_bits == 0
    assert report.landauer_floor_joules == 0
    assert report.next_message_ready


def test_one_erased_entropy_bit_costs_one_landauer_unit() -> None:
    report = observation_model.evaluate_correction_cycle(
        correction_cycle(
            required=frozenset({"prediction"}),
            cleared=frozenset({"prediction"}),
            entropy=(("prediction", 1.0),),
        )
    )
    expected = 1.380649e-23 * 300.0 * math.log(2)

    assert report.erased_logical_entropy_bits == 1
    assert math.isclose(report.landauer_floor_joules, expected, rel_tol=1e-15)
    assert report.next_message_ready


def test_cleared_register_requires_an_explicit_entropy_receipt() -> None:
    try:
        correction_cycle(
            required=frozenset({"prediction"}),
            cleared=frozenset({"prediction"}),
        )
    except ValueError as error:
        assert "entropy entry" in str(error)
    else:
        raise AssertionError("cleared register accepted without entropy receipt")


def test_next_message_waits_for_correction_and_required_reset() -> None:
    uncorrected = observation_model.evaluate_correction_cycle(
        correction_cycle(
            corrected=(0, 0),
            required=frozenset({"syndrome"}),
            cleared=frozenset({"syndrome"}),
            entropy=(("syndrome", 1.0),),
        )
    )
    uncleared = observation_model.evaluate_correction_cycle(
        correction_cycle(required=frozenset({"syndrome"}))
    )

    assert uncorrected.remaining_error_bits == 1
    assert not uncorrected.next_message_ready
    assert uncleared.remaining_error_bits == 0
    assert uncleared.uncleared_required_registers == frozenset({"syndrome"})
    assert not uncleared.next_message_ready


def correction_ensemble(message_first_bit: bool):
    return tuple(
        observation_model.CorrectionEnsembleSample(
            erased_state=(left, right),
            retained_side_information=(),
            corrective_message=(left,) if message_first_bit else (0,),
        )
        for left in (0, 1)
        for right in (0, 1)
    )


def test_corrective_message_reduces_conditional_erasure_entropy() -> None:
    report = observation_model.analyze_correction_ensemble(
        correction_ensemble(message_first_bit=True), temperature_kelvin=300.0
    )

    assert report.entropy_without_message_bits == 2
    assert report.entropy_with_message_bits == 1
    assert report.message_information_bits == 1
    assert math.isclose(
        report.landauer_avoided_joules,
        observation_model.landauer_floor_joules(1, 300.0),
        rel_tol=1e-15,
    )


def test_constant_message_reduces_no_erasure_entropy() -> None:
    report = observation_model.analyze_correction_ensemble(
        correction_ensemble(message_first_bit=False), temperature_kelvin=300.0
    )

    assert report.entropy_without_message_bits == 2
    assert report.entropy_with_message_bits == 2
    assert report.message_information_bits == 0
    assert report.landauer_avoided_joules == 0


def test_correlated_batch_compresses_below_naive_marginal_resets() -> None:
    samples = tuple(
        observation_model.CorrectionEnsembleSample(
            erased_state=state,
            retained_side_information=(),
            corrective_message=(),
        )
        for state in ((0, 0, 0), (1, 1, 1))
    )
    report = observation_model.analyze_correction_ensemble(
        samples, temperature_kelvin=300.0
    )

    assert report.entropy_with_message_bits == 1
    assert report.naive_marginal_entropy_bits == 3
    assert report.correlation_savings_bits == 2


def test_independent_reset_boundaries_have_additive_landauer_floor() -> None:
    cycle = correction_cycle(
        required=frozenset({"prediction"}),
        cleared=frozenset({"prediction"}),
        entropy=(("prediction", 1.0),),
    )
    additive = observation_model.analyze_correction_sequence(
        (cycle, cycle, cycle), independent_reset_boundaries=True
    )
    dependent = observation_model.analyze_correction_sequence(
        (cycle, cycle, cycle), independent_reset_boundaries=False
    )

    assert additive.all_next_message_ready
    assert additive.total_erased_entropy_bits == 3
    assert math.isclose(
        additive.landauer_floor_joules,
        3 * observation_model.landauer_floor_joules(1, 300.0),
        rel_tol=1e-15,
    )
    assert dependent.total_erased_entropy_bits is None
    assert dependent.landauer_floor_joules is None


def test_experiment_reports_all_three_regimes_and_honest_claim_boundary() -> None:
    artifact = run_experiment(bit_count=4)

    assert artifact["schema_version"] == "network-observation-experiment/v0.7"
    corrections = {row["name"]: row for row in artifact["correction_scenarios"]}
    assert {
        name: (
            row["next_message_ready"],
            row["remaining_error_bits"],
            row["erased_logical_entropy_bits"],
        )
        for name, row in corrections.items()
    } == {
        "retained_prediction": (True, 0, 0),
        "overwrite_prediction": (True, 0, 1),
        "uncleared_syndrome": (False, 0, 0),
        "cleared_syndrome": (True, 0, 1),
        "incomplete_correction": (False, 1, 1),
    }
    message_probe = artifact["correction_message_probe"]
    assert message_probe["helpful_message"]["entropy_without_message_bits"] == 2
    assert message_probe["helpful_message"]["entropy_with_message_bits"] == 1
    assert message_probe["helpful_message"]["message_information_bits"] == 1
    assert message_probe["constant_message"]["message_information_bits"] == 0
    assert artifact["correction_batching_probe"] == {
        "joint_entropy_bits": 1.0,
        "naive_marginal_entropy_bits": 3.0,
        "correlation_savings_bits": 2.0,
    }
    reset_probe = artifact["correction_reset_sequence_probe"]
    assert reset_probe["one_cycle_erased_entropy_bits"] == 1
    assert reset_probe["three_cycle_erased_entropy_bits"] == 3
    assert reset_probe["three_to_one_floor_ratio"] == 3
    assert reset_probe["dependent_boundaries_floor_joules"] is None
    trajectories = {row["name"]: row for row in artifact["trajectory_scenarios"]}
    assert {
        name: (row["compatible"], row["conflict_types"], row["minimum_delay"])
        for name, row in trajectories.items()
    } == {
        "smooth_compatible": (True, [], 0),
        "burst_acceleration": (False, ["acceleration"], 0),
        "early_horizon": (False, ["horizon"], 2),
        "burst_rate": (False, ["rate"], 1),
        "unauthorized_scope": (False, ["authorization"], None),
        "direction_mismatch": (False, ["direction"], 0),
    }
    endpoint_probe = artifact["trajectory_endpoint_blind_spot_probe"]
    assert endpoint_probe == {
        "cases": 4,
        "same_endpoint_and_horizon": 4,
        "compatible": 2,
        "acceleration_conflicts": 2,
        "endpoint_only_false_compatible": 2,
    }
    timespace = {row["name"]: row for row in artifact["timespace_scenarios"]}
    assert set(timespace) == {
        "accurate_authorized",
        "inverted_model",
        "accurate_unauthorized",
    }
    assert timespace["accurate_authorized"]["predictive_outcomes"] == {
        "wins": 48,
        "ties": 16,
        "losses": 0,
    }
    assert timespace["inverted_model"]["predictive_outcomes"] == {
        "wins": 0,
        "ties": 16,
        "losses": 48,
    }
    assert timespace["accurate_unauthorized"]["predictive_outcomes"] == {
        "wins": 0,
        "ties": 64,
        "losses": 0,
    }
    assert all(row["authorization_violations"] == 0 for row in timespace.values())
    realization = artifact["timespace_realization_probe"]
    assert realization["cases"] == 256
    assert realization["world_drift_cases"] == 192
    assert realization["modeled_target_realization_gap_histogram"] == {
        "0": 64,
        "1": 128,
        "2": 64,
    }

    rows = artifact["conditions"]
    assert {row["regime"] for row in rows} == {"local", "distributed", "predictive"}
    assert any(
        row["task"] == "parity"
        and row["sensor_configuration"] == "partial"
        and row["best_possible_accuracy"] == {"numerator": 1, "denominator": 2}
        for row in rows
    )
    path_row = next(
        row
        for row in rows
        if row["task"] == "parity"
        and row["sensor_configuration"] == "distributed"
        and row["topology"] == "path"
    )
    assert path_row["communication"] == {
        "root": 0,
        "rounds": 3,
        "message_count": 3,
        "aggregate_bit_transmissions": 3,
        "raw_bit_transmissions": 6,
        "route_edges": [[1, 0], [2, 1], [3, 2]],
    }
    assert path_row["certificate_profile"] == {
        "verifier": 0,
        "source_grounded_exact_worlds": 16,
        "impossible_worlds": 0,
        "sample_count": {"minimum": 3, "maximum": 3},
        "logical_payload_bits": {"minimum": 16, "maximum": 16},
        "trust_assumptions": [
            "issuer identity is authentic",
            "issuer reports its sampled value truthfully",
        ],
    }
    partial_parity = next(
        row
        for row in rows
        if row["task"] == "parity"
        and row["sensor_configuration"] == "partial"
        and row["topology"] == "path"
    )
    assert partial_parity["certificate_profile"]["source_grounded_exact_worlds"] == 0
    assert partial_parity["certificate_profile"]["impossible_worlds"] == 16
    rotating_parity = next(
        profile
        for scenario in artifact["temporal_scenarios"]
        if scenario["name"] == "rotating_sensor"
        for profile in scenario["task_profiles"]
        if profile["task"] == "parity"
    )
    assert rotating_parity["eventual_cumulative_exact_worlds"] == 16
    assert rotating_parity["never_instantaneous_exact_worlds"] == 16
    assert rotating_parity["earliest_cumulative_step_histogram"] == {"3": 16}
    link_failure_parity = next(
        profile
        for scenario in artifact["temporal_scenarios"]
        if scenario["name"] == "root_link_failure"
        for profile in scenario["task_profiles"]
        if profile["task"] == "parity"
    )
    assert link_failure_parity["stale_previous_certificate_events"] == 16
    assert artifact["claim_boundary"]["classical_p_vs_np_resolved"] is False
    assert artifact["claim_boundary"]["measures"] == [
        "observational_identifiability",
        "best_possible_uniform-prior_accuracy",
        "aggregation_radius",
        "route_message_count",
        "aggregate_bit_transmissions",
        "raw_bit_transmissions",
        "minimal_source_grounded_certificate",
        "logical_certificate_payload_bits",
        "temporal_instantaneous_identifiability",
        "temporal_cumulative_identifiability",
        "certificate_freshness_under_network_change",
        "prospective_cross-model_error",
        "authorized_local_coordination_loss",
        "predictive_gain_per_logical_payload_bit",
        "bidirectional_idea_accumulation",
        "prospective_trajectory_compatibility",
        "transition_rate_and_acceleration_conflicts",
        "minimum_feasible_completion_epoch",
        "next-message_correction_readiness",
        "erased_logical_entropy_bits",
        "ideal_landauer_lower_bound",
        "corrective_message_conditional_information",
        "correlated_batch_erasure_compression",
    ]
    assert artifact["claim_boundary"]["does_not_measure"][-3:] == [
        "measured_physical_energy",
        "communication_or_computation_energy",
        "human_metabolic_energy",
    ]
