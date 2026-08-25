.PHONY: help install dev test lint scan serve demo docker clean

help:
	@echo "  make install   Install dependencies (add browser support separately)"
	@echo "  make dev       Install with dev + browser extras"
	@echo "  make test      Run the test suite"
	@echo "  make lint      Ruff check"
	@echo "  make demo      Seed demo deals and start the server"
	@echo "  make scan      Run one scan now"
	@echo "  make serve     Start the API, phone app, and hourly scanner"
	@echo "  make docker    Build and start the container"

install:
	pip install -e .

dev:
	pip install -e ".[dev,browser,push]"
	playwright install chromium

test:
	PYTHONPATH=server python -m pytest tests/ -q

lint:
	ruff check server/ tests/

scan:
	PYTHONPATH=server python -m flipscan.cli scan

demo:
	PYTHONPATH=server python -m flipscan.cli scan --demo --no-notify
	PYTHONPATH=server python -m flipscan.cli serve

serve:
	PYTHONPATH=server python -m flipscan.cli serve

docker:
	docker compose up -d --build
	@echo "Running at http://localhost:8000/app/"

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache
