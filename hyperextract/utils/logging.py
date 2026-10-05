"""Unified logging configuration using structlog."""

import logging
import sys

import structlog

ENV_LOG_LEVEL = "HYPER_EXTRACT_LOG_LEVEL"
ENV_LOG_FILE = "HYPER_EXTRACT_LOG_FILE"


def configure_logging(
    level: str = "WARNING",
    json_output: bool = False,
    output_file: str | None = None,
) -> None:
    """Configure structlog for hyper-extract.

    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR").
        json_output: If True, output JSON format (for production).
        output_file: Optional file path to write logs.
    """
    import os

    level = os.getenv(ENV_LOG_LEVEL, level).upper()
    level_value = getattr(logging, level, logging.WARNING)

    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=True)
            if not json_output
            else structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handlers = []

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(level_value)
    handlers.append(console_handler)

    env_log_file = os.getenv(ENV_LOG_FILE)
    final_output_file = output_file if output_file else env_log_file

    if final_output_file:
        from pathlib import Path

        log_path = Path(final_output_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(level_value)
        handlers.append(file_handler)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    for handler in handlers:
        root_logger.addHandler(handler)
    root_logger.setLevel(level_value)


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Get a configured structlog logger.

    Args:
        name: Logger name (typically __name__).

    Returns:
        A structlog bound logger instance.
    """
    return structlog.get_logger(name)


def set_log_level(level: str) -> None:
    """Dynamically set log level at runtime.

    Args:
        level: Log level ("DEBUG", "INFO", "WARNING", "ERROR").
    """
    level_value = getattr(logging, level.upper(), logging.WARNING)
    root_logger = logging.getLogger()
    root_logger.setLevel(level_value)
    # configure_logging() levels each handler too, so raising verbosity needs
    # both — otherwise the handler keeps filtering at the configured level.
    for handler in root_logger.handlers:
        handler.setLevel(level_value)


__all__ = ["configure_logging", "get_logger", "set_log_level"]
