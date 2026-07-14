from app.memory_logic import (
    clear_active_assessment,
    default_memory,
    record_evidence,
    record_self_report,
    start_assessment,
)
from app.main import AssessmentStartRequest, EvidenceRequest, parse_request, unwrap_single_request


def test_two_correct_answers_out_of_three_marks_topic_mastered() -> None:
    memory = default_memory()
    memory = record_evidence(memory, topic="for", source="practice", is_correct=True, feedback="ok")
    memory = record_evidence(memory, topic="for", source="practice", is_correct=False, feedback="retry")
    memory = record_evidence(memory, topic="for", source="interview", is_correct=True, feedback="ok")

    state = memory["topic_states"]["for"]
    assert state["accuracy"] == 66.67
    assert state["status"] == "mastered"


def test_self_report_never_marks_topic_mastered() -> None:
    memory = record_self_report(default_memory(), "for")
    state = memory["topic_states"]["for"]
    assert state["status"] == "learning"
    assert state["practice_total"] == 0
    assert state["interview_total"] == 0


def test_skill_evidence_tracks_subskills_independently() -> None:
    memory = default_memory()
    for correct in (True, True, True):
        memory = record_evidence(
            memory,
            topic="if",
            source="practice",
            is_correct=correct,
            feedback="ok",
            skill_results=[
                {"skill_id": "control-flow.if.basic-condition", "is_correct": correct, "weight": 1.0},
            ],
        )
    memory = record_evidence(
        memory,
        topic="if",
        source="practice",
        is_correct=False,
        feedback="used assignment instead of comparison",
        skill_results=[
            {
                "skill_id": "control-flow.if.relational-operators",
                "is_correct": False,
                "weight": 1.0,
                "misconception": "confuses-assignment-and-comparison",
            },
        ],
    )

    basic = memory["skill_states"]["control-flow.if.basic-condition"]
    operators = memory["skill_states"]["control-flow.if.relational-operators"]
    assert basic["status"] == "mastered"
    assert basic["accuracy"] == 100.0
    assert basic["confidence"] == "medium"
    assert operators["status"] == "learning"
    assert operators["misconceptions"] == ["confuses-assignment-and-comparison"]


def test_active_assessment_is_temporary_and_can_be_cleared() -> None:
    assessment = {
        "id": "assessment-001",
        "topic": "if",
        "source": "practice",
        "question": "What does this condition do?",
        "skill_targets": [{"skill_id": "control-flow.if.basic-syntax", "weight": 1.0}],
        "rubric": ["Recognizes a boolean condition"],
        "created_at": "2026-07-13T00:00:00+00:00",
    }
    memory = start_assessment(default_memory(), assessment)
    assert memory["active_assessment"]["id"] == "assessment-001"

    cleared = clear_active_assessment(memory)
    assert cleared["active_assessment"] is None


def test_request_unwrapper_accepts_dify_single_item_array() -> None:
    evidence = EvidenceRequest(topic="if", source="practice", is_correct=True, score=100)
    assert unwrap_single_request([evidence]) is evidence


def test_request_parser_accepts_dify_input_wrapper() -> None:
    request = parse_request(
        {
            "input": [
                {
                    "topic": "if",
                    "source": "practice",
                    "question": "Write an if statement.",
                    "skill_targets": [{"skill_id": "control-flow.if.basic-syntax", "weight": 1.0}],
                    "rubric": ["Uses a boolean condition"],
                }
            ]
        },
        AssessmentStartRequest,
    )

    assert request.topic == "if"
    assert request.skill_targets[0].skill_id == "control-flow.if.basic-syntax"
