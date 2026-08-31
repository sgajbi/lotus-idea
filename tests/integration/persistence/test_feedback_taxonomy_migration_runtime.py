from __future__ import annotations

from typing import cast

import psycopg
from psycopg.rows import dict_row
import pytest

from app.domain import FEEDBACK_TAXONOMY_VERSION
from app.infrastructure.migrations import (
    MigrationConnection,
    MigrationDirection,
    MigrationExecutionPlan,
    build_migration_plan,
    execute_migration_plan,
)
from tests.integration.postgres_runtime_support import MIGRATIONS_DIR


def test_feedback_taxonomy_migration_maps_and_restores_legacy_feedback(
    postgres_database_url: str,
) -> None:
    apply_plan = build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY)
    migration = next(step for step in apply_plan.steps if step.version == "017")
    rollback_plan = MigrationExecutionPlan(
        direction=MigrationDirection.ROLLBACK,
        steps=(migration,),
    )
    migration_apply_plan = MigrationExecutionPlan(
        direction=MigrationDirection.APPLY,
        steps=(migration,),
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        execute_migration_plan(cast(MigrationConnection, connection), rollback_plan)
        _insert_legacy_feedback(connection)
        execute_migration_plan(cast(MigrationConnection, connection), migration_apply_plan)
        governed = _load_governed_feedback(connection)
        execute_migration_plan(cast(MigrationConnection, connection), rollback_plan)
        restored = _load_restored_feedback(connection)
        execute_migration_plan(cast(MigrationConnection, connection), migration_apply_plan)

    governed_feedback = cast(dict[str, object], governed["feedback"])
    governed_evaluation_context = cast(dict[str, object], governed["evaluation_context"])
    governed_outbox_payload = cast(dict[str, object], governed["outbox_payload"])
    restored_feedback = cast(dict[str, object], restored["feedback"])
    restored_outbox_payload = cast(dict[str, object], restored["outbox_payload"])
    assert governed["feedback_taxonomy_version"] == FEEDBACK_TAXONOMY_VERSION
    assert governed["feedback_outcome"] == "not_useful"
    assert governed["feedback_reason"] == "wrong_timing"
    assert governed_feedback["outcome"] == "not_useful"
    assert governed_feedback["reason"] == "wrong_timing"
    assert governed_evaluation_context == {
        "candidate_family": "high_cash",
        "candidate_identity_policy_version": "idea-opportunity-identity-v2",
        "score_policy_version": "idle-liquidity-v1",
        "score": "82",
        "evidence_supportability": "ready",
        "ranking_policy_version": "idea-deterministic-ranking-v1",
        "queue_priority_bucket": "high",
    }
    assert governed["outbox_event_type"] == "idea.feedback.recorded.v2"
    assert governed_outbox_payload == {
        "feedback_outcome": "not_useful",
        "feedback_reason": "wrong_timing",
        "feedback_taxonomy_version": FEEDBACK_TAXONOMY_VERSION,
        "actor_role": "advisor",
    }
    assert restored_feedback["outcome"] == "too_late"
    assert "taxonomy_version" not in restored_feedback
    assert "reason" not in restored_feedback
    assert restored["has_evaluation_context"] is False
    assert restored["outbox_event_type"] == "idea.feedback.recorded.v1"
    assert restored_outbox_payload == {
        "feedback_outcome": "too_late",
        "actor_role": "advisor",
    }


def test_feedback_taxonomy_rollback_fails_closed_for_new_governed_feedback(
    postgres_database_url: str,
) -> None:
    migration = next(
        step
        for step in build_migration_plan(MIGRATIONS_DIR, MigrationDirection.APPLY).steps
        if step.version == "017"
    )
    rollback_plan = MigrationExecutionPlan(
        direction=MigrationDirection.ROLLBACK,
        steps=(migration,),
    )
    with psycopg.connect(postgres_database_url, row_factory=dict_row) as connection:
        _insert_governed_feedback(connection)

        with pytest.raises(
            psycopg.errors.RaiseException,
            match="cannot roll back governed feedback taxonomy",
        ):
            execute_migration_plan(cast(MigrationConnection, connection), rollback_plan)

        with connection.cursor() as cursor:
            cursor.execute(
                "DELETE FROM idea_feedback_event WHERE feedback_event_id = %s",
                ("governed-feedback-001",),
            )
            cursor.execute(
                "DELETE FROM idea_candidate_record WHERE candidate_id = %s",
                ("governed-feedback-candidate",),
            )
        connection.commit()


def _insert_legacy_feedback(connection: psycopg.Connection[dict[str, object]]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO idea_candidate_record (
                candidate_id, family, lifecycle_status, review_posture,
                evidence_packet_id, evidence_hash, candidate_json,
                generated_at_utc, persisted_at_utc, updated_at_utc,
                business_identity_id, identity_policy_version,
                material_fingerprint, material_version, evidence_version,
                change_reason, supersedes_material_version
            ) VALUES (
                'legacy-feedback-candidate', 'high_cash', 'generated',
                'advisor_review_required', 'legacy-evidence',
                'sha256:1111111111111111111111111111111111111111111111111111111111111111',
                jsonb_build_object(
                    'identity', jsonb_build_object(
                        'policy_version', 'idea-opportunity-identity-v2'
                    ),
                    'score', jsonb_build_object(
                        'policy_version', 'idle-liquidity-v1',
                        'score', '82',
                        'reason_codes', jsonb_build_array('queue_priority'),
                        'contributions', jsonb_build_array(
                            jsonb_build_object(
                                'component', 'legacy_fixed_policy',
                                'input_score', '82',
                                'weight', '1',
                                'contribution', '82'
                            )
                        ),
                        'conflict_penalty_applied', '0'
                    ),
                    'evidence_packet', jsonb_build_object('supportability', 'ready')
                ),
                '2026-06-21T10:00:00Z', '2026-06-21T10:00:00Z',
                '2026-06-21T10:00:00Z',
                'opportunity_legacy_feedback_candidate',
                'idea-opportunity-identity-v2',
                'sha256:2222222222222222222222222222222222222222222222222222222222222222',
                1, 1, 'initial_detection', NULL
            );
            INSERT INTO idea_feedback_event (
                feedback_event_id, candidate_id, actor_subject,
                feedback_json, recorded_at_utc
            ) VALUES (
                'legacy-feedback-001', 'legacy-feedback-candidate', 'advisor-legacy',
                jsonb_build_object(
                    'feedback', jsonb_build_object(
                        'feedback_id', 'legacy-feedback-001',
                        'outcome', 'too_late',
                        'actor_role', 'advisor',
                        'reason_codes', jsonb_build_array('feedback_recorded'),
                        'recorded_at_utc', '2026-06-21T10:05:00+00:00'
                    ),
                    'candidate_id', 'legacy-feedback-candidate',
                    'evidence_packet_id', 'legacy-evidence',
                    'evidence_content_hash',
                        'sha256:3333333333333333333333333333333333333333333333333333333333333333',
                    'source_signal_ids', jsonb_build_array('legacy-signal'),
                    'actor_subject', 'advisor-legacy',
                    'actor_role', 'advisor'
                ),
                '2026-06-21T10:05:00Z'
            );
            INSERT INTO idea_outbox_event (
                outbox_event_id, event_type, aggregate_type, aggregate_id,
                schema_version, payload_json, status, occurred_at_utc,
                idempotency_fingerprint, correlation_id, trace_id, lineage_origin,
                retry_count
            ) VALUES (
                'legacy-feedback-outbox-001', 'idea.feedback.recorded.v1',
                'idea_candidate', 'legacy-feedback-candidate', 'v1',
                jsonb_build_object(
                    'feedback_outcome', 'too_late',
                    'actor_role', 'advisor'
                ),
                'pending', '2026-06-21T10:05:00Z',
                'sha256:4444444444444444444444444444444444444444444444444444444444444444',
                'corr-legacy-feedback', 'trace-legacy-feedback', 'legacy_migrated', 0
            );
            """
        )
    connection.commit()


def _insert_governed_feedback(connection: psycopg.Connection[dict[str, object]]) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO idea_candidate_record (
                candidate_id, family, lifecycle_status, review_posture,
                evidence_packet_id, evidence_hash, candidate_json,
                generated_at_utc, persisted_at_utc, updated_at_utc,
                business_identity_id, identity_policy_version,
                material_fingerprint, material_version, evidence_version,
                change_reason, supersedes_material_version
            ) VALUES (
                'governed-feedback-candidate', 'high_cash', 'generated',
                'advisor_review_required', 'governed-evidence',
                'sha256:5555555555555555555555555555555555555555555555555555555555555555',
                '{}'::JSONB, '2026-06-21T11:00:00Z',
                '2026-06-21T11:00:00Z', '2026-06-21T11:00:00Z',
                'opportunity_governed_feedback_candidate',
                'idea-opportunity-identity-v2',
                'sha256:6666666666666666666666666666666666666666666666666666666666666666',
                1, 1, 'initial_detection', NULL
            );
            INSERT INTO idea_feedback_event (
                feedback_event_id, candidate_id, actor_subject,
                feedback_json, recorded_at_utc,
                feedback_taxonomy_version, feedback_outcome, feedback_reason
            ) VALUES (
                'governed-feedback-001', 'governed-feedback-candidate', 'advisor-governed',
                jsonb_build_object(
                    'feedback', jsonb_build_object(
                        'feedback_id', 'governed-feedback-001',
                        'taxonomy_version', 'idea-feedback-taxonomy-v1',
                        'outcome', 'useful',
                        'reason', 'relevant',
                        'actor_role', 'advisor',
                        'recorded_at_utc', '2026-06-21T11:05:00+00:00'
                    ),
                    'candidate_id', 'governed-feedback-candidate',
                    'evidence_packet_id', 'governed-evidence',
                    'actor_subject', 'advisor-governed',
                    'actor_role', 'advisor'
                ),
                '2026-06-21T11:05:00Z',
                'idea-feedback-taxonomy-v1', 'useful', 'relevant'
            );
            """
        )
    connection.commit()


def _load_governed_feedback(
    connection: psycopg.Connection[dict[str, object]],
) -> dict[str, object]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT feedback_taxonomy_version, feedback_outcome, feedback_reason,
                   feedback_json->'feedback' AS feedback,
                   feedback_json->'evaluation_context' AS evaluation_context,
                   outbox.event_type AS outbox_event_type,
                   outbox.payload_json AS outbox_payload
            FROM idea_feedback_event AS feedback
            JOIN idea_outbox_event AS outbox
              ON outbox.aggregate_id = feedback.candidate_id
             AND outbox.occurred_at_utc = feedback.recorded_at_utc
            WHERE feedback.feedback_event_id = 'legacy-feedback-001'
            """
        )
        row = cursor.fetchone()
    assert row is not None
    return row


def _load_restored_feedback(
    connection: psycopg.Connection[dict[str, object]],
) -> dict[str, object]:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT feedback.feedback_json->'feedback' AS feedback,
                   feedback.feedback_json ? 'evaluation_context' AS has_evaluation_context,
                   outbox.event_type AS outbox_event_type,
                   outbox.payload_json AS outbox_payload
            FROM idea_feedback_event AS feedback
            JOIN idea_outbox_event AS outbox
              ON outbox.aggregate_id = feedback.candidate_id
             AND outbox.occurred_at_utc = feedback.recorded_at_utc
            WHERE feedback.feedback_event_id = 'legacy-feedback-001'
            """
        )
        row = cursor.fetchone()
    assert row is not None
    return row
