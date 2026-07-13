from __future__ import annotations

import hmac
import os
import re
from functools import lru_cache
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field
from supabase import Client, create_client

from .memory_logic import default_memory, ensure_memory, record_evidence, record_self_report


USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_.:@-]{1,128}$")
app = FastAPI(title="CodeMentor Memory API", version="0.1.0")


class EvidenceRequest(BaseModel):
    topic: str = Field(min_length=1, max_length=120)
    source: Literal["practice", "interview"]
    is_correct: bool
    score: float = Field(ge=0, le=100)
    feedback: str = Field(default="", max_length=500)


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
    return {"memory": memory, "version": version}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/memory/{user_id}")
def get_memory(user_id: str, _: None = Depends(require_memory_token)) -> dict[str, Any]:
    memory, version = load_record(validate_user_id(user_id))
    return response_body(memory, version)


@app.post("/v1/memory/{user_id}/evidence")
def add_evidence(
    user_id: str,
    evidence: EvidenceRequest,
    _: None = Depends(require_memory_token),
) -> dict[str, Any]:
    user_id = validate_user_id(user_id)
    memory, version = load_record(user_id)
    updated = record_evidence(
        memory,
        topic=evidence.topic,
        source=evidence.source,
        is_correct=evidence.is_correct,
        feedback=evidence.feedback,
    )
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
