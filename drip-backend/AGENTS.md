# drip-backend

FastAPI + SQLAlchemy 2.0 (async, asyncpg/Postgres) + Alembic + Pydantic v2.
Background jobs: arq worker on Redis.
Shell is Windows PowerShell: use PowerShell syntax (Select-Object -First N,
Select-String), not grep/head/tail. Use the raw commands below, don't assume `make` exists.

## Layout
- main.py : app entry (uvicorn main:app)
- app/ : routes, models, services. app/tasks/worker.py has the arq WorkerSettings
- alembic/ : migrations (alembic.ini at root)
- tests/unit, tests/integration : pytest (markers: unit, integration)
- scripts/, docs/ : helpers and documentation

## Commands
- Start DB + Redis: docker compose up -d postgres redis
- Run API: uvicorn main:app --reload --port 8000
- Run worker: python -m arq app.tasks.worker.WorkerSettings
- Migrate: alembic upgrade head
- New migration: alembic revision --autogenerate -m "description"
- One test file: pytest tests/unit/<file>.py -q -x
- Unit tests: pytest tests/unit -m unit -q
- Lint: ruff check app/ tests/
- Types: mypy app/

## Rules
- Only read files I name, or files they directly import. If you need another file, ask first.
- Don't read README.md, SETUP.md, PROGRESS.md, KNOWN_LIMITS.md, UPDATE_NOTES.md, docs/, or Makefile unless I name them.
- Don't read alembic/versions unless the task is about migrations. Never edit an existing migration, create a new one.
- Never read .env, *.pem, .venv, htmlcov, or __pycache__. Use .env.example for config names.
- Ignore fix_migration.py and seed_users.py unless I mention them.
- After a change, run only the relevant test file and ruff on the changed files, not the full suite, unless I ask.
- Show only diffs or changed functions, never whole files.
- No explanations unless I ask. Keep replies short.
- Don't add extra files, tests, docs, or refactors I didn't ask for.
- If the request is ambiguous, ask one question instead of guessing.
- Keep command output small. Never dump full logs.
- If a change touches more than 2 files, give a 3-5 bullet plan and wait for my OK.