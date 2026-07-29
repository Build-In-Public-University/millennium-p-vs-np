"""Reproducible finite-world experiment for sampling versus prediction."""

import argparse
import json
from fractions import Fraction
from pathlib import Path
from typing import Any

from network_relativity.model import (
    BooleanTask,
    CorrectionCycle,
    CorrectionEnsembleReport,
    CorrectionEnsembleSample,
    NetworkConfiguration,
    ProspectivePoint,
    ProspectiveTrajectory,
    TemporalNetworkSequence,
    TimespaceExchange,
    TransitionEnvelope,
    WorldState,
    analyze_correction_ensemble,
    analyze_correction_sequence,
    analyze_identifiability,
    analyze_trajectory_compatibility,
    classify_validation_regime,
    evaluate_timespace_exchange,
    evaluate_correction_cycle,
)


def run_experiment(bit_count: int = 4) -> dict[str, Any]:
    if bit_count < 2:
        raise ValueError("bit_count must be at least 2")

    worlds = tuple(
        WorldState.from_integer(value, bit_count)
        for value in range(2**bit_count)
    )
    sensor_configurations = {
        "central": {0: set(range(bit_count))},
        "distributed": {index: {index} for index in range(bit_count)},
        "partial": {index: {index} for index in range(bit_count - 1)},
    }
    topology_builders = {
        "clique": NetworkConfiguration.clique,
        "path": NetworkConfiguration.path,
    }

    conditions = []
    for task in BooleanTask:
        for sensor_name, scopes in sensor_configurations.items():
            for topology_name, builder in topology_builders.items():
                network = builder(node_count=bit_count, sensor_scopes=scopes)
                report = analyze_identifiability(worlds, network, task)
                communication = network.communication_plan(root=0, task=task)
                certificates = tuple(
                    network.attested_certificate(world, task, verifier=0)
                    for world in worlds
                )
                exact_certificates = tuple(
                    certificate
                    for certificate in certificates
                    if certificate.determines_answer
                )
                trust_assumptions = next(
                    (
                        certificate.trust_assumptions
                        for certificate in certificates
                        if certificate.trust_assumptions
                    ),
                    (),
                )
                accuracy = report.best_possible_accuracy
                counterexample = None
                if report.counterexample is not None:
                    left, right = report.counterexample
                    counterexample = {
                        "left_world": list(left.bits),
                        "right_world": list(right.bits),
                        "shared_observation": _observation_to_json(network.observe(left)),
                        "left_answer": task.evaluate(left),
                        "right_answer": task.evaluate(right),
                    }
                conditions.append(
                    {
                        "task": task.value,
                        "topology": topology_name,
                        "sensor_configuration": sensor_name,
                        "regime": classify_validation_regime(worlds, network, task),
                        "identifiable": report.identifiable,
                        "best_possible_accuracy": {
                            "numerator": accuracy.numerator,
                            "denominator": accuracy.denominator,
                        },
                        "aggregation_radius": network.aggregation_radius(
                            root=0,
                            participating_nodes=network.participating_sensor_nodes(),
                        ),
                        "communication": {
                            "root": communication.root,
                            "rounds": communication.rounds,
                            "message_count": communication.message_count,
                            "aggregate_bit_transmissions": (
                                communication.aggregate_bit_transmissions
                            ),
                            "raw_bit_transmissions": communication.raw_bit_transmissions,
                            "route_edges": [list(edge) for edge in communication.route_edges],
                        },
                        "certificate_profile": {
                            "verifier": 0,
                            "source_grounded_exact_worlds": len(exact_certificates),
                            "impossible_worlds": len(certificates)
                            - len(exact_certificates),
                            "sample_count": {
                                "minimum": min(
                                    len(certificate.samples)
                                    for certificate in certificates
                                ),
                                "maximum": max(
                                    len(certificate.samples)
                                    for certificate in certificates
                                ),
                            },
                            "logical_payload_bits": {
                                "minimum": min(
                                    certificate.logical_payload_bits
                                    for certificate in certificates
                                ),
                                "maximum": max(
                                    certificate.logical_payload_bits
                                    for certificate in certificates
                                ),
                            },
                            "trust_assumptions": list(trust_assumptions),
                        },
                        "counterexample": counterexample,
                    }
                )

    return {
        "schema_version": "network-observation-experiment/v0.7",
        "world": {
            "bit_count": bit_count,
            "possible_worlds": len(worlds),
            "prior": "uniform",
        },
        "conditions": conditions,
        "temporal_scenarios": _temporal_scenarios(bit_count, worlds),
        "timespace_scenarios": _timespace_scenarios(),
        "timespace_realization_probe": _timespace_realization_probe(),
        "trajectory_scenarios": _trajectory_scenarios(),
        "trajectory_endpoint_blind_spot_probe": _trajectory_endpoint_blind_spot_probe(),
        "correction_scenarios": _correction_scenarios(),
        "correction_message_probe": _correction_message_probe(),
        "correction_batching_probe": _correction_batching_probe(),
        "correction_reset_sequence_probe": _correction_reset_sequence_probe(),
        "claim_boundary": {
            "classical_p_vs_np_resolved": False,
            "measures": [
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
            ],
            "does_not_measure": [
                "classical_time_complexity",
                "computational_search_cost",
                "real_sensor_noise",
                "packet_headers_or_protocol_overhead",
                "contention_or_congestion",
                "cryptographic_signature_size_or_security",
                "sensor_honesty_or_byzantine_faults",
                "world_state_changes_during_a_sequence",
                "within_epoch_message_delay_or_loss",
                "human_preference_inference",
                "persuasion_or_preference_formation",
                "strategic_or_deceptive_messages",
                "measured_physical_energy",
                "communication_or_computation_energy",
                "human_metabolic_energy",
            ],
        },
    }


def _temporal_scenarios(
    bit_count: int, worlds: tuple[WorldState, ...]
) -> list[dict[str, Any]]:
    path_edges = {(node, node + 1) for node in range(bit_count - 1)}
    distributed_scopes = {index: {index} for index in range(bit_count)}
    scenario_sequences = {
        "rotating_sensor": TemporalNetworkSequence(
            snapshots=tuple(
                NetworkConfiguration.from_edges(
                    node_count=bit_count,
                    edges=path_edges,
                    sensor_scopes={step: {step}},
                )
                for step in range(bit_count)
            )
        ),
        "root_link_failure": TemporalNetworkSequence(
            snapshots=(
                NetworkConfiguration.from_edges(
                    node_count=bit_count,
                    edges=path_edges,
                    sensor_scopes=distributed_scopes,
                ),
                NetworkConfiguration.from_edges(
                    node_count=bit_count,
                    edges=path_edges - {(0, 1)},
                    sensor_scopes=distributed_scopes,
                ),
            )
        ),
        "connectivity_recovery": TemporalNetworkSequence(
            snapshots=(
                NetworkConfiguration.from_edges(
                    node_count=bit_count,
                    edges=path_edges - {(0, 1)},
                    sensor_scopes=distributed_scopes,
                ),
                NetworkConfiguration.from_edges(
                    node_count=bit_count,
                    edges=path_edges,
                    sensor_scopes=distributed_scopes,
                ),
            )
        ),
    }

    scenarios = []
    for name, sequence in scenario_sequences.items():
        task_profiles = []
        for task in BooleanTask:
            reports = tuple(
                sequence.analyze(world=world, task=task, verifier=0)
                for world in worlds
            )
            earliest_histogram: dict[str, int] = {}
            for report in reports:
                key = (
                    str(report.earliest_cumulative_step)
                    if report.earliest_cumulative_step is not None
                    else "never"
                )
                earliest_histogram[key] = earliest_histogram.get(key, 0) + 1
            task_profiles.append(
                {
                    "task": task.value,
                    "worlds": len(worlds),
                    "eventual_cumulative_exact_worlds": sum(
                        report.earliest_cumulative_step is not None
                        for report in reports
                    ),
                    "never_instantaneous_exact_worlds": sum(
                        report.earliest_instantaneous_step is None
                        for report in reports
                    ),
                    "earliest_cumulative_step_histogram": earliest_histogram,
                    "stale_previous_certificate_events": sum(
                        step.previous_certificate_fresh is False
                        for report in reports
                        for step in report.steps
                    ),
                }
            )
        scenarios.append(
            {
                "name": name,
                "epochs": len(sequence.snapshots),
                "world_assumption": "static_across_epochs",
                "delivery_assumption": (
                    "all sensors connected to verifier deliver within each epoch"
                ),
                "cache_assumption": "verifier_retains_prior_observations",
                "task_profiles": task_profiles,
            }
        )
    return scenarios


def _correction_scenarios() -> list[dict[str, Any]]:
    profiles = (
        (
            "retained_prediction",
            _correction_cycle(required=frozenset(), cleared=frozenset(), entropy=()),
        ),
        (
            "overwrite_prediction",
            _correction_cycle(
                required=frozenset({"prediction"}),
                cleared=frozenset({"prediction"}),
                entropy=(("prediction", 1.0),),
            ),
        ),
        (
            "uncleared_syndrome",
            _correction_cycle(required=frozenset({"syndrome"})),
        ),
        (
            "cleared_syndrome",
            _correction_cycle(
                required=frozenset({"syndrome"}),
                cleared=frozenset({"syndrome"}),
                entropy=(("syndrome", 1.0),),
            ),
        ),
        (
            "incomplete_correction",
            _correction_cycle(
                corrected=(0, 0),
                required=frozenset({"syndrome"}),
                cleared=frozenset({"syndrome"}),
                entropy=(("syndrome", 1.0),),
            ),
        ),
    )
    rows = []
    for name, cycle in profiles:
        report = evaluate_correction_cycle(cycle)
        rows.append(
            {
                "name": name,
                "prediction": list(cycle.prediction.bits),
                "observation": list(cycle.observation.bits),
                "corrected_state": list(cycle.corrected_state.bits),
                "correction_payload_bits": report.correction_payload_bits,
                "prediction_error_bits": report.prediction_error_bits,
                "remaining_error_bits": report.remaining_error_bits,
                "required_cleared_registers": sorted(
                    cycle.required_cleared_registers
                ),
                "cleared_registers": sorted(cycle.cleared_registers),
                "uncleared_required_registers": sorted(
                    report.uncleared_required_registers
                ),
                "erased_logical_entropy_bits": report.erased_logical_entropy_bits,
                "temperature_kelvin": cycle.temperature_kelvin,
                "ideal_landauer_floor_joules": report.landauer_floor_joules,
                "next_message_ready": report.next_message_ready,
                "system_boundary": report.system_boundary,
                "reset_contract": report.reset_contract,
                "measured_physical_energy_joules": None,
            }
        )
    return rows


def _correction_cycle(
    *,
    corrected: tuple[int, int] = (1, 0),
    required: frozenset[str] = frozenset(),
    cleared: frozenset[str] = frozenset(),
    entropy: tuple[tuple[str, float], ...] = (),
) -> CorrectionCycle:
    return CorrectionCycle(
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


def _correction_message_probe() -> dict[str, dict[str, float | int]]:
    helpful = tuple(
        CorrectionEnsembleSample(
            erased_state=(left, right),
            retained_side_information=(),
            corrective_message=(left,),
        )
        for left in (0, 1)
        for right in (0, 1)
    )
    constant = tuple(
        CorrectionEnsembleSample(
            erased_state=sample.erased_state,
            retained_side_information=(),
            corrective_message=(0,),
        )
        for sample in helpful
    )
    return {
        "helpful_message": _ensemble_receipt(
            analyze_correction_ensemble(helpful, temperature_kelvin=300.0)
        ),
        "constant_message": _ensemble_receipt(
            analyze_correction_ensemble(constant, temperature_kelvin=300.0)
        ),
    }


def _ensemble_receipt(
    report: CorrectionEnsembleReport,
) -> dict[str, float | int]:
    return {
        "sample_count": report.sample_count,
        "entropy_without_message_bits": report.entropy_without_message_bits,
        "entropy_with_message_bits": report.entropy_with_message_bits,
        "message_information_bits": report.message_information_bits,
        "ideal_landauer_without_message_joules": report.landauer_without_message_joules,
        "ideal_landauer_with_message_joules": report.landauer_with_message_joules,
        "ideal_landauer_avoided_joules": report.landauer_avoided_joules,
        "temperature_kelvin": report.temperature_kelvin,
    }


def _correction_batching_probe() -> dict[str, float]:
    samples = tuple(
        CorrectionEnsembleSample(
            erased_state=state,
            retained_side_information=(),
            corrective_message=(),
        )
        for state in ((0, 0, 0), (1, 1, 1))
    )
    report = analyze_correction_ensemble(samples, temperature_kelvin=300.0)
    return {
        "joint_entropy_bits": report.entropy_with_message_bits,
        "naive_marginal_entropy_bits": report.naive_marginal_entropy_bits,
        "correlation_savings_bits": report.correlation_savings_bits,
    }


def _correction_reset_sequence_probe() -> dict[str, float | int | None]:
    cycle = _correction_cycle(
        required=frozenset({"prediction"}),
        cleared=frozenset({"prediction"}),
        entropy=(("prediction", 1.0),),
    )
    one = analyze_correction_sequence(
        (cycle,), independent_reset_boundaries=True
    )
    three = analyze_correction_sequence(
        (cycle, cycle, cycle), independent_reset_boundaries=True
    )
    dependent = analyze_correction_sequence(
        (cycle, cycle, cycle), independent_reset_boundaries=False
    )
    assert one.landauer_floor_joules is not None
    assert three.landauer_floor_joules is not None
    return {
        "one_cycle_erased_entropy_bits": one.total_erased_entropy_bits,
        "three_cycle_erased_entropy_bits": three.total_erased_entropy_bits,
        "one_cycle_floor_joules": one.landauer_floor_joules,
        "three_cycle_floor_joules": three.landauer_floor_joules,
        "three_to_one_floor_ratio": (
            three.landauer_floor_joules / one.landauer_floor_joules
        ),
        "dependent_boundaries_floor_joules": dependent.landauer_floor_joules,
    }


def _trajectory_scenarios() -> list[dict[str, Any]]:
    """Evaluate the six frozen endpoint, pace, ramp, and consent cases."""

    world = lambda bits: WorldState(tuple(bits))
    cases = (
        (
            "smooth_compatible",
            ((0, 0), (1, 0), (1, 1)),
            (1, 1),
            2,
            frozenset({0, 1}),
            1,
            1,
        ),
        (
            "burst_acceleration",
            ((0, 0), (0, 0), (1, 1)),
            (1, 1),
            2,
            frozenset({0, 1}),
            2,
            1,
        ),
        (
            "early_horizon",
            ((0, 0), (1, 0), (1, 1)),
            (1, 1),
            4,
            frozenset({0, 1}),
            1,
            1,
        ),
        (
            "burst_rate",
            ((0, 0), (1, 1)),
            (1, 1),
            1,
            frozenset({0, 1}),
            1,
            2,
        ),
        (
            "unauthorized_scope",
            ((0, 0), (1, 0)),
            (1, 0),
            1,
            frozenset({1}),
            2,
            2,
        ),
        (
            "direction_mismatch",
            ((0, 0), (1, 0)),
            (0, 1),
            1,
            frozenset({0, 1}),
            2,
            2,
        ),
    )
    profiles = []
    for name, state_bits, target_bits, earliest, authorization, max_load, max_accel in cases:
        trajectory = ProspectiveTrajectory(
            node=0,
            formed_at=0,
            states=tuple(world(bits) for bits in state_bits),
        )
        envelope = TransitionEnvelope(
            receiver=1,
            accepted_target=world(target_bits),
            earliest_completion_at=earliest,
            authorized_indices=authorization,
            max_load_per_epoch=max_load,
            max_acceleration_per_epoch=max_accel,
        )
        report = analyze_trajectory_compatibility(trajectory, envelope)
        profiles.append(_trajectory_profile(name, trajectory, envelope, report))
    return profiles


def _trajectory_endpoint_blind_spot_probe() -> dict[str, int]:
    """Hold endpoint and horizon fixed while varying the path between them."""

    worlds = tuple(WorldState.from_integer(value, 2) for value in range(4))
    start = WorldState((0, 0))
    target = WorldState((1, 1))
    envelope = TransitionEnvelope(
        receiver=1,
        accepted_target=target,
        earliest_completion_at=2,
        authorized_indices=frozenset({0, 1}),
        max_load_per_epoch=2,
        max_acceleration_per_epoch=1,
    )
    reports = tuple(
        analyze_trajectory_compatibility(
            ProspectiveTrajectory(0, 0, (start, middle, target)), envelope
        )
        for middle in worlds
    )
    acceleration_conflicts = sum(
        "acceleration" in report.conflict_types for report in reports
    )
    return {
        "cases": len(reports),
        "same_endpoint_and_horizon": len(reports),
        "compatible": sum(report.compatible for report in reports),
        "acceleration_conflicts": acceleration_conflicts,
        "endpoint_only_false_compatible": acceleration_conflicts,
    }


def _trajectory_profile(
    name: str,
    trajectory: ProspectiveTrajectory,
    envelope: TransitionEnvelope,
    report,
) -> dict[str, Any]:
    state_json = lambda state: "".join(str(bit) for bit in state.bits)
    return {
        "name": name,
        "intended_states": [state_json(state) for state in trajectory.states],
        "completion_at": trajectory.completion_at,
        "accepted_target": state_json(envelope.accepted_target),
        "envelope": {
            "earliest_completion_at": envelope.earliest_completion_at,
            "authorized_indices": sorted(envelope.authorized_indices),
            "max_load_per_epoch": envelope.max_load_per_epoch,
            "max_acceleration_per_epoch": envelope.max_acceleration_per_epoch,
        },
        "compatible": report.compatible,
        "conflict_types": list(report.conflict_types),
        "first_conflict_epoch": report.first_conflict_epoch,
        "transition_loads": list(report.transition_loads),
        "acceleration_loads": list(report.acceleration_loads),
        "minimum_feasible_completion_at": report.minimum_feasible_completion_at,
        "minimum_delay": report.minimum_delay,
        "required_max_load": report.required_max_load,
        "required_max_acceleration": report.required_max_acceleration,
        "required_authorization": sorted(report.required_authorization),
        "accepted_witness": (
            [state_json(state) for state in report.accepted_witness.states]
            if report.accepted_witness
            else None
        ),
    }


def _timespace_scenarios() -> list[dict[str, Any]]:
    """Exhaust two-node worlds, desires, and cross-model quality."""

    worlds = tuple(WorldState.from_integer(value, 2) for value in range(4))
    scenario_settings = (
        ("accurate_authorized", "accurate", True),
        ("inverted_model", "inverted", True),
        ("accurate_unauthorized", "accurate", False),
    )
    scenarios = []

    for name, model_quality, authorized in scenario_settings:
        reports = []
        for actual_world in worlds:
            for sender_desire in worlds:
                for receiver_desire in worlds:
                    if model_quality == "accurate":
                        sender_model = receiver_desire
                        receiver_model = sender_desire
                    else:
                        sender_model = WorldState(
                            tuple(1 - bit for bit in receiver_desire.bits)
                        )
                        receiver_model = WorldState(
                            tuple(1 - bit for bit in sender_desire.bits)
                        )

                    exchange = TimespaceExchange(
                        sender=0,
                        receiver=1,
                        sent_at=0,
                        received_at=1,
                        sender_point=ProspectivePoint(
                            node=0,
                            formed_at=0,
                            horizon=2,
                            desired_world=sender_desire,
                        ),
                        receiver_point=ProspectivePoint(
                            node=1,
                            formed_at=1,
                            horizon=2,
                            desired_world=receiver_desire,
                        ),
                        sender_model_of_receiver=sender_model,
                        receiver_model_of_sender=receiver_model,
                        sender_authorizes_receiver=(
                            frozenset({1}) if authorized else frozenset()
                        ),
                        receiver_authorizes_sender=(
                            frozenset({0}) if authorized else frozenset()
                        ),
                        sender_knowledge=frozenset({"sender-idea"}),
                        receiver_knowledge=frozenset({"receiver-idea"}),
                        sender_transmits=frozenset({"sender-idea"}),
                        receiver_transmits=frozenset({"receiver-idea"}),
                        idea_payload_bits=2,
                    )
                    reports.append(
                        evaluate_timespace_exchange(
                            actual_world=actual_world,
                            exchange=exchange,
                            control_scopes={0: {0}, 1: {1}},
                        )
                    )

        case_count = len(reports)
        total_gain = sum(report.predictive_gain for report in reports)
        total_model_error = sum(
            report.sender_model_error + report.receiver_model_error
            for report in reports
        )
        mean_gain = _fraction_json(total_gain, case_count)
        mean_model_error = _fraction_json(total_model_error, 2 * case_count)
        scenarios.append(
            {
                "name": name,
                "cases": case_count,
                "substrate": {
                    "nodes": 2,
                    "world_bits": 2,
                    "epochs": 3,
                    "control_scopes": {"0": [0], "1": [1]},
                    "coordination_weight": 2,
                },
                "model_quality": model_quality,
                "authorization": "mutual_control_scope" if authorized else "none",
                "predictive_outcomes": {
                    "wins": sum(report.predictive_gain > 0 for report in reports),
                    "ties": sum(report.predictive_gain == 0 for report in reports),
                    "losses": sum(report.predictive_gain < 0 for report in reports),
                },
                "total_predictive_gain": total_gain,
                "mean_predictive_gain": mean_gain,
                "mean_cross_model_error": mean_model_error,
                "oracle_matches": sum(
                    report.modeled_target == report.oracle_target for report in reports
                ),
                "authorization_violations": sum(
                    len(report.authorization_violations) for report in reports
                ),
                "knowledge_growth_events": sum(
                    len(report.sender_knowledge_after) > 1
                    for report in reports
                )
                + sum(
                    len(report.receiver_knowledge_after) > 1
                    for report in reports
                ),
                "logical_payload_bits_per_exchange": reports[0].logical_payload_bits,
            }
        )
    return scenarios


def _timespace_realization_probe() -> dict[str, Any]:
    worlds = tuple(WorldState.from_integer(value, 2) for value in range(4))
    reports = []
    drift_cases = 0
    for actual_world in worlds:
        for realized_world in worlds:
            drift_cases += int(actual_world != realized_world) * len(worlds) ** 2
            for sender_desire in worlds:
                for receiver_desire in worlds:
                    exchange = TimespaceExchange(
                        sender=0,
                        receiver=1,
                        sent_at=0,
                        received_at=1,
                        sender_point=ProspectivePoint(
                            node=0,
                            formed_at=0,
                            horizon=2,
                            desired_world=sender_desire,
                        ),
                        receiver_point=ProspectivePoint(
                            node=1,
                            formed_at=1,
                            horizon=2,
                            desired_world=receiver_desire,
                        ),
                        sender_model_of_receiver=receiver_desire,
                        receiver_model_of_sender=sender_desire,
                        sender_authorizes_receiver=frozenset({1}),
                        receiver_authorizes_sender=frozenset({0}),
                        sender_knowledge=frozenset({"sender-idea"}),
                        receiver_knowledge=frozenset({"receiver-idea"}),
                        sender_transmits=frozenset({"sender-idea"}),
                        receiver_transmits=frozenset({"receiver-idea"}),
                        idea_payload_bits=2,
                    )
                    reports.append(
                        evaluate_timespace_exchange(
                            actual_world=actual_world,
                            realized_world=realized_world,
                            exchange=exchange,
                            control_scopes={0: {0}, 1: {1}},
                        )
                    )

    gap_histogram = {
        str(gap): sum(report.modeled_target_realization_gap == gap for report in reports)
        for gap in range(3)
    }
    return {
        "cases": len(reports),
        "world_drift_cases": drift_cases,
        "modeled_target_realization_exact": gap_histogram["0"],
        "modeled_target_realization_gap_histogram": gap_histogram,
        "mean_modeled_target_realization_gap": _fraction_json(
            sum(report.modeled_target_realization_gap for report in reports),
            len(reports),
        ),
        "mean_sender_desire_realization_gap": _fraction_json(
            sum(report.sender_realization_gap for report in reports), len(reports)
        ),
        "mean_receiver_desire_realization_gap": _fraction_json(
            sum(report.receiver_realization_gap for report in reports), len(reports)
        ),
        "assumption": "realization is enumerated independently of proposal and desire",
    }


def _fraction_json(numerator: int, denominator: int) -> dict[str, int]:
    value = Fraction(numerator, denominator)
    return {"numerator": value.numerator, "denominator": value.denominator}


def _observation_to_json(observation) -> list[dict[str, Any]]:
    return [
        {
            "node": node,
            "samples": [
                {"world_index": index, "value": value}
                for index, value in samples
            ],
        }
        for node, samples in observation
    ]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the finite sampling-versus-prediction experiment."
    )
    parser.add_argument("--bit-count", type=int, default=4)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    artifact = run_experiment(bit_count=args.bit_count)
    rendered = json.dumps(artifact, indent=2, sort_keys=True) + "\n"
    if args.output is None:
        print(rendered, end="")
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")


if __name__ == "__main__":
    main()