# BeosaBasi monorepo Makefile (TK-000 scaffold).
# Recipes delegate to stdlib-only python scripts so the same targets work
# with GNU make on Windows (cmd), Linux, and macOS.
# Targets with real implementations arrive in later tickets (TK-002, TK-004,
# TK-025, TK-001); dev-*/gen-client stubs print TODO and exit 0.

.PHONY: setup lint test dev-api dev-web dev-worker gen-client

setup:
	python scripts/setup.py

lint:
	python scripts/lint.py

test:
	python scripts/test.py

dev-api:
	@echo TODO(TK-002/TK-025): run FastAPI locally (uvicorn api.main:app --reload).

dev-web:
	@echo TODO(TK-002/TK-040): run Vite dev server against mock API.

dev-worker:
	@echo TODO(TK-002/TK-030): run worker loop (incl. --fake mode).

gen-client:
	@echo TODO(TK-001): generate TS types + Pydantic models from contracts/openapi.yaml.
