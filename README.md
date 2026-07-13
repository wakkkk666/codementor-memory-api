# CodeMentor Memory API

Backend memory service for the CodeMentor AI Dify Chatflow.

It stores structured learner progress in Supabase instead of retaining raw
chat history. Mastery is evidence-based: a topic becomes `mastered` only
after at least three practice or interview assessments with an accuracy of at
least 60%.

## Service layout

- `memory-service/app`: FastAPI application and deterministic memory rules
- `memory-service/sql`: Supabase table migration
- `memory-service/tests`: unit tests for the learning-state rules

## Deploy on Render

Render reads `render.yaml` and deploys the FastAPI service from
`memory-service`. Configure these environment variables in the Render
dashboard; never commit their values:

- `SUPABASE_URL`
- `SUPABASE_SERVICE_ROLE_KEY`
- `MEMORY_API_TOKEN`

The health endpoint is available at `/health`.
