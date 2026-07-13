# CodeMentor Skill Evidence Design

## Objective

Replace coarse chapter-only progress with atomic skill evidence while retaining
the existing topic summary for backward compatibility.

## Model

Each assessment can update a topic summary and up to ten `skill_results`. A
skill result has a stable `skill_id`, an outcome, an evidence weight, and an
optional concise misconception label. The service persists aggregates only; it
does not retain raw conversation content or full learner answers.

Examples:

- `control-flow.if.basic-condition`
- `control-flow.if.relational-operators`
- `control-flow.if.else-branch`

## Status Rules

The accepted rule remains unchanged for each skill: at least three effective
assessments and at least 60 percent accuracy produces `mastered`; three or more
assessments below 60 percent produces `reviewing`; otherwise the skill is
`learning`. A new skill is `unknown`.

Question difficulty may later influence evidence weight, but no hard question
is required for mastery. The service also returns a confidence level based on
evidence volume: low below 3, medium from 3 to below 6, and high from 6.

## Evaluation Contract

The Dify evaluator must return structured evidence for each assessed skill. A
single answer can be correct for one skill and incorrect for another. For code
questions, executable checks should be preferred over LLM-only judgment where
they are available.

## Active Assessment

The service temporarily stores one active assessment per learner. It contains a
generated assessment ID, topic, source, question, skill targets, and rubric.
It is not raw chat history and is deleted after matching evidence is written or
when the learner cancels. This lets the next user message be evaluated against
the exact prior task rather than guessed from text alone.
