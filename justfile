run:
	PYTHONPATH=. uv run python -m src.main

test:
	PYTHONPATH=. uv run pytest tests

test-fast:
	PYTHONPATH=. uv run pytest tests -q

lint:
	uv run ruff check src tests .linters
	uv run pyright

fmt:
	uv run ruff check --fix src tests .linters
	uv run ruff format src tests .linters

fmt-check:
	uv run ruff format --check src tests .linters

arch-test:
	uv run python .linters/check_architecture.py

metrics:
	uv run python .linters/code_metrics.py

check: fmt-check lint arch-test test
