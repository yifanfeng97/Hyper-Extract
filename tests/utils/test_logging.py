"""Tests for runtime log-level changes (hyperextract.utils.logging)."""

import io
import logging

from hyperextract.utils.logging import configure_logging, get_logger, set_log_level


def _capture_root_output() -> io.StringIO:
    """Point every root handler at one in-memory stream."""
    buffer = io.StringIO()
    for handler in logging.getLogger().handlers:
        if isinstance(handler, logging.StreamHandler):
            handler.stream = buffer
    return buffer


class TestSetLogLevel:
    def test_raising_verbosity_emits_lower_level_records(self):
        """configure_logging() levels the handlers, so set_log_level must too."""
        configure_logging(level="WARNING")
        buffer = _capture_root_output()

        set_log_level("DEBUG")
        get_logger("he.test").info("visible-after-raise")

        assert "visible-after-raise" in buffer.getvalue()

    def test_handlers_follow_the_new_level(self):
        configure_logging(level="WARNING")

        set_log_level("DEBUG")

        assert logging.getLogger().level == logging.DEBUG
        assert all(
            handler.level == logging.DEBUG
            for handler in logging.getLogger().handlers
        )

    def test_lowering_verbosity_still_filters(self):
        configure_logging(level="DEBUG")
        buffer = _capture_root_output()

        set_log_level("ERROR")
        get_logger("he.test").info("should-be-filtered")

        assert "should-be-filtered" not in buffer.getvalue()
