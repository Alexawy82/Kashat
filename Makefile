.PHONY: dev-backend run-backend lint format test smoke dev dev-down dev-logs dev-health

export PYTHONPATH := apps/backend/src

dev-backend:
	uvicorn kashat.api.main:app --reload

run-backend:
	uvicorn kashat.api.main:app --host 0.0.0.0 --port 8000

test:
	pytest -q

smoke:
	python scripts/smoke_test.py

dev:
	bash scripts/dev_up.sh

dev-down:
	bash scripts/dev_down.sh

dev-logs:
	bash scripts/dev_up.sh --logs

dev-health:
	bash scripts/dev_up.sh --health

determinism-check:
	PYTHONPATH=apps/backend/src python3 scripts/determinism_check.py
