# DRIP Backend — Developer Makefile

.PHONY: help install dev worker db-up db-down db-tools migrate migrate-new migrate-down \
        migrate-history migrate-current db-reset test test-unit test-integration test-security \
        test-coverage lint format typecheck audit clean generate-keys

help:
	@echo ""
	@echo "DRIP Backend — Available commands"
	@echo "make install          Install Python dependencies"
	@echo "make dev              Start API server with hot-reload"
	@echo "make worker           Start ARQ worker"
	@echo "make db-up            Start Postgres + Redis"
	@echo "make db-down          Stop Docker services"
	@echo "make migrate          Apply pending migrations"
	@echo "make migrate-new m=  Create migration"
	@echo "make migrate-down     Rollback last migration"
	@echo "make test             Run full test suite"
	@echo "make test-unit        Run unit tests"
	@echo "make test-integration Run integration tests"
	@echo "make test-security    Run security tests"
	@echo "make lint             Run Ruff"
	@echo "make format           Format with Ruff"
	@echo "make typecheck        Run mypy"
	@echo "make audit            Run pip-audit"
	@echo ""

install:
	python -m pip install --upgrade pip
	python -m pip install -r requirements.txt

dev:
	uvicorn main:app --reload --host 0.0.0.0 --port 8000 --log-level debug

worker:
	python -m arq app.tasks.worker.WorkerSettings

db-up:
	docker compose up -d postgres redis

db-down:
	docker compose down

db-tools:
	docker compose --profile tools up -d

migrate:
	alembic upgrade head

migrate-new:
	@test -n "$(m)" || (echo "Usage: make migrate-new m='description'" && exit 1)
	alembic revision --autogenerate -m "$(m)"

migrate-down:
	alembic downgrade -1

migrate-history:
	alembic history --verbose

migrate-current:
	alembic current

db-reset:
	docker compose down -v
	docker compose up -d postgres redis
	alembic upgrade head

test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v -m unit

test-integration:
	pytest tests/integration/ -v -m integration

test-security:
	pytest tests/unit/test_security.py -v -m unit

test-coverage:
	pytest tests/ --cov=app --cov-report=html

lint:
	ruff check app/ tests/

format:
	ruff check app/ tests/ --fix
	ruff format app/ tests/

typecheck:
	mypy app/

audit:
	pip-audit

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	rm -f coverage.xml .coverage

generate-keys:
	openssl genrsa -out private.pem 2048
	openssl rsa -in private.pem -pubout -out public.pem
	@echo "Keys generated. Put their PEM contents into .env."
