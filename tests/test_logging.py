import structlog


def test_json_logging_uses_structured_renderer():
    from src.infrastructure.logging import build_log_processors

    processors = build_log_processors("json")

    assert isinstance(processors[-1], structlog.processors.JSONRenderer)


def test_console_logging_uses_development_renderer():
    from src.infrastructure.logging import build_log_processors

    processors = build_log_processors("console")

    assert isinstance(processors[-1], structlog.dev.ConsoleRenderer)
