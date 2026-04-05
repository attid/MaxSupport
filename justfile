test:
	PYTHONPATH=. uv run pytest tests

lint:
	uv run ruff check src

fmt:
	uv run ruff format src

fmt-check:
	uv run ruff format --check src

check: fmt lint test
