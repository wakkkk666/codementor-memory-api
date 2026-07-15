# CodeMentor AI Learning Report Design

## Goal

Add a read-only learning report to the Dify Chatflow. The report must expose
evidence-based learner progress without allowing the report LLM to invent
counts, percentages, topic states, or mastery.

## Scope

The report is triggered by requests such as "generate learning report". It
shows:

- mastered-topic progress out of the current 23-topic Java course;
- counts for started, learning, reviewing, and mastered topics;
- per-topic assessment count, accuracy, and state;
- skill accuracy, confidence, and retained misconceptions;
- review priorities and a next-step recommendation.

The report does not create assessments, record evidence, or modify memory.
Only `mastered` topics count toward course completion. A `learning` topic is
started but not completed.

## Architecture

```text
Dify Chatflow -> Memory API report endpoint -> Supabase
                                      |
                                      v
                          Dify Report Generator LLM -> Answer
```

The Memory API calculates all counts and percentages. Dify only formats the
returned structured report. `COURSE_TOPIC_COUNT` is a backend configuration
value initialized to 23 and must be updated together with future course-map
changes.

## API Contract

`GET /v1/memory/{user_id}/report` returns a read-only JSON object containing:

- `course_total` and `mastered_progress_percent`;
- `summary` counts;
- topic rows with status, assessment totals, accuracy, and last assessment;
- skill rows with status, confidence, accuracy, and misconceptions;
- `review_priorities` selected deterministically from reviewing topics and
  skills with recorded misconceptions.

The endpoint uses the existing `X-Memory-Token` authorization. It returns a
valid zero-progress report for a new learner.

## Dify Flow

```text
Question Classifier (learning report)
  -> Learning Report Read (HTTP)
  -> Learning Report Generator (LLM)
  -> Learning Report Answer
```

The classifier receives a new `Learning Report` class. The generator can only
state facts present in the HTTP result. If the read fails, its answer states
that the learning record is temporarily unavailable and does not produce
statistics.

## Output

The generated answer has five sections:

1. Learning overview;
2. Topic progress;
3. Skill performance;
4. Review priorities;
5. Next-step recommendation.

## Acceptance Tests

1. An existing learner report reproduces stored topic/skill evidence and only
   counts mastered topics as completed.
2. A new learner report has zero counts and no fabricated weaknesses.
3. Report calls do not mutate `learner_memories`.
4. Dify passes a report request through the new classification branch and the
   rendered answer uses only the HTTP report result.
5. A report request made while an assessment is active cancels that assessment
   before entering the report branch, rather than recording a false answer.
