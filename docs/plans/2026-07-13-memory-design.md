# CodeMentor AI Long-Term Memory Design

## Goal

Persist learner state across Dify Chatflow conversations so a learner can resume
their curriculum without repeating prior progress. This system stores structured
state, not full conversation transcripts.

## Architecture

```text
Dify Chatflow -> FastAPI Memory API -> Supabase
```

Dify calls the API with `sys.user_id` and an internal token. The FastAPI service
is the only component that has the Supabase service-role key.

## Memory Model

Each learner has one `learner_memories` record. Its `memory` JSON contains:

```json
{
  "schema_version": 1,
  "learning_goal": "",
  "current_plan": [],
  "topic_states": {},
  "recent_topics": [],
  "preferences": {},
  "last_learning_at": null
}
```

`topic_states` is keyed by a canonical course-map topic name. A topic stores
practice and interview counters, calculated accuracy, status, and concise recent
feedback. Raw answers and full conversations are deliberately excluded.

## Assessment Rules

Only practice and interview results update correctness counters. A learner self
reporting completion only marks a topic as `learning` and adds it to recent
topics. A topic becomes `mastered` only when it has at least three valid
assessments and an accuracy of at least 60 percent. Below that threshold it is
`reviewing`.

The assessment LLM returns structured evidence. The API, rather than the LLM,
applies these deterministic rules.

## API

- `GET /v1/memory/{user_id}` returns stored or default state.
- `POST /v1/memory/{user_id}/evidence` records one practice or interview result.
- `PATCH /v1/memory/{user_id}` updates goals, plan, preferences, or recent topic.

All non-health endpoints require `X-Memory-Token`. Memory read failures must not
block a Dify answer; memory write failures must not change the current answer.

## Acceptance Tests

1. A new user receives default state.
2. Three answers with two correct marks a topic as `mastered` at 60 percent.
3. Separate user IDs never share records.
4. A later read returns recent topics and topic states for planning.
