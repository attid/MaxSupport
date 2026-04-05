test:
	PYTHONPATH=. uv run pytest tests

lint:
	uv run ruff check src

fmt:
	uv run ruff format src

check: fmt lint test
