from app.memory_logic import default_memory, record_evidence, record_self_report


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
