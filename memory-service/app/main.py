from __future__ import annotations

import hmac
import json
import os
import re
from datetime import UTC, datetime
from functools import lru_cache
from typing import Annotated, Any, Literal, TypeVar
from uuid import uuid4

from fastapi import Body, Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field, ValidationError
from supabase import Client, create_client

from .memory_logic import (
    build_learning_report,
    clear_active_assessment,
    default_memory,
    ensure_memory,
    record_evidence,
    record_self_report,
    start_assessment,
)


USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")
DEFAULT_COURSE_TOPIC_COUNT = 23
app = FastAPI(title="CodeMentor Memory API", version="0.1.0")


class SkillEvidence(BaseModel):
    skill_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{1,100}$")
    is_correct: bool
    weight: float = Field(default=1.0, gt=0, le=1)
    misconception: str = Field(default="", max_length=200)


class SkillTarget(BaseModel):
    skill_id: str = Field(pattern=r"^[a-z][a-z0-9._-]{1,100}$")
    weight: float = Field(default=1.0, gt=0, le=1)


class EvidenceRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    source: Literal["practice", "interview"]
    is_correct: bool
    score: float = Field(ge=0, le=100)
    feedback: str = Field(default="", max_length=500)
    skill_results: list[SkillEvidence] = Field(default_factory=list, max_length=10)
    assessment_id: str | None = Field(default=None, min_length=1, max_length=64)


class AssessmentStartRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    source: Literal["practice", "interview"]
    question: str = Field(min_length=1, max_length=2000)
    skill_targets: list[SkillTarget] = Field(min_length=1, max_length=3)
    rubric: list[str] = Field(min_length=1, max_length=6)


RequestModel = TypeVar("RequestModel", bound=BaseModel)


def unwrap_single_request(request: Any) -> Any:
    """Normalize the JSON shapes emitted by Dify HTTP nodes."""
    if isinstance(request, str):
        try:
            request = json.loads(request)
        except json.JSONDecodeError as error:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Request body must contain JSON",
            ) from error

    # Some Dify versions wrap an HTTP JSON body in {"input": [...]} and
    # attach transport metadata alongside it.
    if isinstance(request, dict) and "input" in request and "topic" not in request:
        request = request["input"]

    if not isinstance(request, list):
        return request
    if len(request) != 1:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Expected one request object")
    return request[0]


def normalize_nested_json(request: Any) -> Any:
    if not isinstance(request, dict):
        return request

    normalized = request.copy()
    for field in ("skill_targets", "rubric", "skill_results"):
        value = normalized.get(field)
        if not isinstance(value, str):
            continue
        try:
            decoded = json.loads(value)
        except json.JSONDecodeError:
            continue
        if isinstance(decoded, list):
            normalized[field] = decoded
    return normalized


def parse_request(request: Any, model: type[RequestModel]) -> RequestModel:
    try:
        return model.model_validate(normalize_nested_json(unwrap_single_request(request)))
    except ValidationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=error.errors(include_url=False),
        ) from error


class MemoryPatchRequest(BaseModel):
    learning_goal: str | None = Field(default=None, max_length=500)
    current_plan: list[dict[str, Any]] | None = None
    preferences: dict[str, Any] | None = None
    completed_topic: str | None = Field(default=None, max_length=120)


def validate_user_id(user_id: str) -> str:
    if not USER_ID_PATTERN.fullmatch(user_id):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid user_id")
    return user_id


def require_memory_token(
    x_memory_token: Annotated[str | None, Header()] = None,
) -> None:
    expected = os.getenv("MEMORY_API_TOKEN", "")
    if not expected or not x_memory_token or not hmac.compare_digest(x_memory_token, expected):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid memory token")


@lru_cache
def supabase_client() -> Client:
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be configured")
    return create_client(url, key)


def load_record(user_id: str) -> tuple[dict[str, Any], int]:
    response = supabase_client().table("learner_memories").select("memory,version").eq("user_id", user_id).execute()
    if not response.data:
        return default_memory(), 0
    row = response.data[0]
    return ensure_memory(row["memory"]), row["version"]


def save_record(user_id: str, memory: dict[str, Any], version: int) -> None:
    supabase_client().table("learner_memories").upsert(
        {"user_id": user_id, "memory": memory, "version": version + 1},
        on_conflict="user_id",
    ).execute()


def response_body(memory: dict[str, Any], version: int) -> dict[str, Any]:
    active_assessment = memory.get("active_assessment")
    return {
        "memory": memory,
        "version": version,
        "has_active_assessment": active_assessment is not None,
        "active_assessment": active_assessment,
    }


def course_topic_count() -> int:
    raw_value = os.getenv("COURSE_TOPIC_COUNT", str(DEFAULT_COURSE_TOPIC_COUNT))
    try:
        value = int(raw_value)
    except ValueError:
        return DEFAULT_COURSE_TOPIC_COUNT
    return value if value > 0 else DEFAULT_COURSE_TOPIC_COUNT


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/memory/{user_id}")
def get_memory(user_id: str, _: None = Depends(require_memory_token)) -> dict[str, Any]:
    memory, version = load_record(validate_user_id(user_id))
    return response_body(memory, version)


@app.get("/v1/memory/{user_id}/report")
def get_learning_report(user_id: str, _: None = Depends(require_memory_token)) -> dict[str, Any]:
    memory, _version = load_record(validate_user_id(user_id))
    return build_learning_report(memory, course_total=course_topic_count())


@app.post("/v1/memory/{user_id}/evidence")
def add_evidence(
    user_id: str,
    evidence: Annotated[Any, Body()],
    _: None = Depends(require_memory_token),
) -> dict[str, Any]:
    user_id = validate_user_id(user_id)
    evidence = parse_request(evidence, EvidenceRequest)
    memory, version = load_record(user_id)
    active_assessment = memory.get("active_assessment")
    if evidence.assessment_id:
        if not active_assessment or active_assessment["id"] != evidence.assessment_id:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Assessment is no longer active")
        if evidence.topic != active_assessment["topic"] or evidence.source != active_assessment["source"]:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Evidence does not match active assessment")
    updated = record_evidence(
        memory,
        topic=evidence.topic,
        source=evidence.source,
        is_correct=evidence.is_correct,
        feedback=evidence.feedback,
        skill_results=[item.model_dump() for item in evidence.skill_results],
    )
    if evidence.assessment_id:
        updated = clear_active_assessment(updated)
    save_record(user_id, updated, version)
    return response_body(updated, version + 1)


@app.put("/v1/memory/{user_id}/active-assessment")
def begin_assessment(
    user_id: str,
    request: Annotated[Any, Body()],
    _: None = Depends(require_memory_token),
) -> dict[str, Any]:
    user_id = validate_user_id(user_id)
    request = parse_request(request, AssessmentStartRequest)
    memory, version = load_record(user_id)
    assessment = {
        "id": str(uuid4()),
        "topic": request.topic,
        "source": request.source,
        "question": request.question,
        "skill_targets": [item.model_dump() for item in request.skill_targets],
        "rubric": request.rubric,
        "created_at": datetime.now(UTC).isoformat(),
    }
    updated = start_assessment(memory, assessment)
    save_record(user_id, updated, version)
    return response_body(updated, version + 1)


@app.delete("/v1/memory/{user_id}/active-assessment")
def cancel_assessment(user_id: str, _: None = Depends(require_memory_token)) -> dict[str, Any]:
    user_id = validate_user_id(user_id)
    memory, version = load_record(user_id)
    updated = clear_active_assessment(memory)
    save_record(user_id, updated, version)
    return response_body(updated, version + 1)


@app.patch("/v1/memory/{user_id}")
def patch_memory(
    user_id: str,
    patch: MemoryPatchRequest,
    _: None = Depends(require_memory_token),
) -> dict[str, Any]:
    user_id = validate_user_id(user_id)
    memory, version = load_record(user_id)
    updated = ensure_memory(memory)
    if patch.learning_goal is not None:
        updated["learning_goal"] = patch.learning_goal
    if patch.current_plan is not None:
        updated["current_plan"] = patch.current_plan
    if patch.preferences is not None:
        updated["preferences"] = patch.preferences
    if patch.completed_topic is not None:
        updated = record_self_report(updated, patch.completed_topic)
    save_record(user_id, updated, version)
    return response_body(updated, version + 1)
