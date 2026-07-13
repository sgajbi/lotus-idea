from app.domain import InMemoryIdeaRepository


def test_in_memory_review_workflow_repository_behavior_has_one_owner() -> None:
    methods = (
        "record_review_action",
        "precheck_review_mutation",
        "record_feedback_event",
        "_review_identity_result",
        "_review_identity_record",
    )

    assert {getattr(InMemoryIdeaRepository, method_name).__module__ for method_name in methods} == {
        "app.domain.persistence_review_workflow"
    }
