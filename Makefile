.PHONY: setup up down logs backend-dev frontend-dev validate validate-backend validate-frontend validate-database test lint typecheck db-upgrade db-check

setup:
	cp -n backend/.env.example backend/.env || true
	cp -n frontend/.env.example frontend/.env || true

up: setup
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

backend-dev:
	cd backend && uvicorn app.main:app --reload --port 8000

frontend-dev:
	cd frontend && npm run dev

validate: validate-backend validate-frontend
	docker compose config --quiet

validate-backend:
	cd backend && python -m compileall -q app
	cd backend && python scripts/check_architecture.py
	cd backend && python -m pytest -q

validate-frontend:
	cd frontend && npm run typecheck
	cd frontend && npm run lint
	cd frontend && npm test -- --run
	cd frontend && npm run build

validate-database:
	cd backend && alembic heads
	cd backend && alembic history
	cd backend && alembic current
	cd backend && alembic check

test:
	cd backend && python -m pytest -q
	cd frontend && npm test -- --run

lint:
	cd backend && python scripts/check_architecture.py
	cd frontend && npm run lint

typecheck:
	cd frontend && npm run typecheck

db-upgrade:
	cd backend && alembic upgrade head

db-check:
	cd backend && alembic check
