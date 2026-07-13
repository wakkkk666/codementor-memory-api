from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from typing import Any


MIN_ASSESSMENTS_FOR_MASTERY = 3
MASTERY_THRESHOLD = 60.0
MAX_RECENT_ITEMS = 5
MAX_MISCONCEPTIONS = 5


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


def default_memory() -> dict[str, Any]:
    return {
        "schema_version": 2,
        "learning_goal": "",
        "current_plan": [],
        "topic_states": {},
        "recent_topics": [],
        "skill_states": {},
        "recent_skills": [],
        "active_assessment": None,
        "preferences": {},
        "last_learning_at": None,
    }


def ensure_memory(memory: dict[str, Any] | None) -> dict[str, Any]:
    result = default_memory()
    if memory:
        result.update(deepcopy(memory))
    result.setdefault("topic_states", {})
    result.setdefault("recent_topics", [])
    result.setdefault("skill_states", {})
    result.setdefault("recent_skills", [])
    result.setdefault("active_assessment", None)
    result.setdefault("preferences", {})
    result.setdefault("current_plan", [])
    result["schema_version"] = max(result.get("schema_version", 1), 2)
    return result


def _topic_state(memory: dict[str, Any], topic: str) -> dict[str, Any]:
    return memory["topic_states"].setdefault(
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


def _skill_state(memory: dict[str, Any], skill_id: str) -> dict[str, Any]:
    return memory["skill_states"].setdefault(
        skill_id,
        {
            "status": "unknown",
            "confidence": "low",
            "effective_assessments": 0.0,
            "effective_correct": 0.0,
            "assessment_count": 0,
            "accuracy": 0.0,
            "practice_count": 0,
            "interview_count": 0,
            "last_assessed_at": None,
            "last_feedback": "",
            "misconceptions": [],
        },
    )


def record_evidence(
    memory: dict[str, Any],
    *,
    topic: str,
    source: str,
    is_correct: bool,
    feedback: str,
    skill_results: list[dict[str, Any]] | None = None,
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
    recorded_at = assessed_at or utc_now()
    state["accuracy"] = round((correct / total) * 100, 2) if total else 0.0
    state["last_assessed_at"] = recorded_at
    state["last_feedback"] = feedback
    state["status"] = _status(total, state["accuracy"], unknown=False)

    for skill_result in skill_results or []:
        _record_skill_evidence(
            result,
            source=source,
            feedback=feedback,
            assessed_at=recorded_at,
            **skill_result,
        )

    _add_recent_item(result, "recent_topics", topic)
    result["last_learning_at"] = recorded_at
    return result


def _record_skill_evidence(
    memory: dict[str, Any],
    *,
    skill_id: str,
    source: str,
    is_correct: bool,
    weight: float,
    feedback: str,
    assessed_at: str,
    misconception: str = "",
) -> None:
    state = _skill_state(memory, skill_id)
    state["effective_assessments"] = round(state["effective_assessments"] + weight, 2)
    if is_correct:
        state["effective_correct"] = round(state["effective_correct"] + weight, 2)
    state["assessment_count"] += 1
    state[f"{source}_count"] += 1
    total = state["effective_assessments"]
    state["accuracy"] = round((state["effective_correct"] / total) * 100, 2) if total else 0.0
    state["last_assessed_at"] = assessed_at
    state["last_feedback"] = feedback
    if misconception and misconception not in state["misconceptions"]:
        state["misconceptions"] = ([misconception] + state["misconceptions"])[:MAX_MISCONCEPTIONS]
    state["status"] = _status(total, state["accuracy"], unknown=False)
    state["confidence"] = "high" if total >= 6 else "medium" if total >= 3 else "low"
    _add_recent_item(memory, "recent_skills", skill_id)


def _status(total: float, accuracy: float, *, unknown: bool) -> str:
    if unknown:
        return "unknown"
    if total < MIN_ASSESSMENTS_FOR_MASTERY:
        return "learning"
    return "mastered" if accuracy >= MASTERY_THRESHOLD else "reviewing"


def record_self_report(memory: dict[str, Any], topic: str) -> dict[str, Any]:
    result = ensure_memory(memory)
    _topic_state(result, topic)
    _add_recent_item(result, "recent_topics", topic)
    result["last_learning_at"] = utc_now()
    return result


def start_assessment(memory: dict[str, Any], assessment: dict[str, Any]) -> dict[str, Any]:
    result = ensure_memory(memory)
    result["active_assessment"] = deepcopy(assessment)
    return result


def clear_active_assessment(memory: dict[str, Any]) -> dict[str, Any]:
    result = ensure_memory(memory)
    result["active_assessment"] = None
    return result


def _add_recent_item(memory: dict[str, Any], key: str, value: str) -> None:
    values = [item for item in memory[key] if item != value]
    memory[key] = ([value] + values)[:MAX_RECENT_ITEMS]
