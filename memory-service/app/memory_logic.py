from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


MIN_ASSESSMENTS_FOR_MASTERY = 3
MASTERY_THRESHOLD = 60.0


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def default_memory() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "learning_goal": "",
        "current_plan": [],
        "topic_states": {},
        "recent_topics": [],
        "preferences": {},
        "last_learning_at": None,
    }


def ensure_memory(memory: dict[str, Any] | None) -> dict[str, Any]:
    result = default_memory()
    if memory:
        result.update(deepcopy(memory))
    result.setdefault("topic_states", {})
    result.setdefault("recent_topics", [])
    result.setdefault("preferences", {})
    result.setdefault("current_plan", [])
    return result


def _topic_state(memory: dict[str, Any], topic: str) -> dict[str, Any]:
    states = memory["topic_states"]
    state = states.setdefault(
        topic,
        {
            "status": "learning",
            "practice_total": 0,
            "practice_correct": 0,
            "interview_total": 0,
            "interview_correct": 0,
            "accuracy": 0.0,
            "last_assessed_at": None,
            "last_feedback": "",
        },
    )
    return state


def record_evidence(
    memory: dict[str, Any],
    *,
    topic: str,
    source: str,
    is_correct: bool,
    feedback: str,
    assessed_at: str | None = None,
) -> dict[str, Any]:
    result = ensure_memory(memory)
    state = _topic_state(result, topic)

    total_key = f"{source}_total"
    correct_key = f"{source}_correct"
    state[total_key] += 1
    if is_correct:
        state[correct_key] += 1

    total = state["practice_total"] + state["interview_total"]
    correct = state["practice_correct"] + state["interview_correct"]
    state["accuracy"] = round((correct / total) * 100, 2) if total else 0.0
    state["last_assessed_at"] = assessed_at or utc_now()
    state["last_feedback"] = feedback
    state["status"] = (
        "mastered"
        if total >= MIN_ASSESSMENTS_FOR_MASTERY and state["accuracy"] >= MASTERY_THRESHOLD
        else "reviewing"
        if total >= MIN_ASSESSMENTS_FOR_MASTERY
        else "learning"
    )
    _add_recent_topic(result, topic)
    result["last_learning_at"] = state["last_assessed_at"]
    return result


def record_self_report(memory: dict[str, Any], topic: str) -> dict[str, Any]:
    result = ensure_memory(memory)
    _topic_state(result, topic)
    _add_recent_topic(result, topic)
    result["last_learning_at"] = utc_now()
    return result


def _add_recent_topic(memory: dict[str, Any], topic: str) -> None:
    topics = [item for item in memory["recent_topics"] if item != topic]
    memory["recent_topics"] = ([topic] + topics)[:5]
