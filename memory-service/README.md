# CodeMentor Memory Service

This FastAPI service persists learner state for a Dify Chatflow. It intentionally
stores structured progress and concise feedback rather than raw conversations.

## Local setup

1. Create and activate a virtual environment.
2. Install dependencies with `py -m pip install -r requirements.txt`.
3. Copy `.env.example` to `.env` and set the three values.
4. Run the SQL in `sql/001_create_learner_memories.sql` in the Supabase SQL Editor.
5. Start the service with `py -m uvicorn app.main:app --reload --port 8000`.

## API authentication

All `/v1` endpoints require an `X-Memory-Token` header matching
`MEMORY_API_TOKEN`. Do not put the Supabase service-role key in Dify.

## Tests

Run `py -m pytest` from this directory.
