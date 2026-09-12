"""Tests for log level configuration via HYPER_EXTRACT_LOG_LEVEL env var."""

import logging
import os
from unittest.mock import patch

from typer.testing import CliRunner

from hyperextract.cli.cli import app
from hyperextract.utils.logging import ENV_LOG_LEVEL, configure_logging

runner = CliRunner()


class TestLogLevelEnvVar:
    """Test that log level is controlled by HYPER_EXTRACT_LOG_LEVEL env var."""

    def test_env_var_default_warning(self):
        """Without env var, default log level is WARNING."""
        with patch.dict(os.environ, {}, clear=False):
            # Remove the env var if present
            os.environ.pop(ENV_LOG_LEVEL, None)
            configure_logging()
            assert logging.getLogger().level == logging.WARNING

    def test_env_var_sets_debug(self):
        """HYPER_EXTRACT_LOG_LEVEL=DEBUG sets root logger to DEBUG."""
        with patch.dict(os.environ, {ENV_LOG_LEVEL: "DEBUG"}):
            configure_logging()
            assert logging.getLogger().level == logging.DEBUG

    def test_env_var_sets_info(self):
        """HYPER_EXTRACT_LOG_LEVEL=INFO sets root logger to INFO."""
        with patch.dict(os.environ, {ENV_LOG_LEVEL: "INFO"}):
            configure_logging()
            assert logging.getLogger().level == logging.INFO

    def test_env_var_sets_error(self):
        """HYPER_EXTRACT_LOG_LEVEL=ERROR sets root logger to ERROR."""
        with patch.dict(os.environ, {ENV_LOG_LEVEL: "ERROR"}):
            configure_logging()
            assert logging.getLogger().level == logging.ERROR

    def test_env_var_case_insensitive(self):
        """HYPER_EXTRACT_LOG_LEVEL=debug (lowercase) should work."""
        with patch.dict(os.environ, {ENV_LOG_LEVEL: "debug"}):
            configure_logging()
            assert logging.getLogger().level == logging.DEBUG

    def test_env_var_invalid_falls_back_to_warning(self):
        """Invalid log level falls back to WARNING."""
        with patch.dict(os.environ, {ENV_LOG_LEVEL: "INVALID"}):
            configure_logging()
            assert logging.getLogger().level == logging.WARNING


class TestCLINoVerboseFlag:
    """Test that --verbose flag is no longer supported."""

    def test_verbose_flag_not_in_help(self):
        """--verbose should NOT appear in help output."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "--verbose" not in result.output

    def test_verbose_flag_causes_error(self):
        """Using --verbose should cause an error (unrecognized option)."""
        result = runner.invoke(app, ["--verbose", "--version"])
        assert result.exit_code != 0

    def test_version_works_without_verbose(self):
        """--version works without --verbose."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert "Hyper-Extract CLI" in result.output

    def test_subcommand_help_works(self):
        """Subcommand help works without --verbose."""
        result = runner.invoke(app, ["info", "--help"])
        assert result.exit_code == 0

    def test_parse_help_works(self):
        """he parse --help exits cleanly."""
        result = runner.invoke(app, ["parse", "--help"])
        assert result.exit_code == 0

    def test_search_help_works(self):
        """he search --help exits cleanly."""
        result = runner.invoke(app, ["search", "--help"])
        assert result.exit_code == 0

    def test_talk_help_works(self):
        """he talk --help exits cleanly."""
        result = runner.invoke(app, ["talk", "--help"])
        assert result.exit_code == 0

    def test_feed_help_works(self):
        """he feed --help exits cleanly."""
        result = runner.invoke(app, ["feed", "--help"])
        assert result.exit_code == 0

    def test_build_index_help_works(self):
        """he build-index --help exits cleanly."""
        result = runner.invoke(app, ["build-index", "--help"])
        assert result.exit_code == 0

    def test_show_help_works(self):
        """he show --help exits cleanly."""
        result = runner.invoke(app, ["show", "--help"])
        assert result.exit_code == 0

    def test_list_template_help_works(self):
        """he list template --help exits cleanly."""
        result = runner.invoke(app, ["list", "template", "--help"])
        assert result.exit_code == 0

    def test_list_template_legend_includes_document(self):
        """Type explanations mention AutoDocument's YAML type."""
        result = runner.invoke(app, ["list", "template"])
        assert result.exit_code == 0, result.output
        assert "document" in result.output
        assert "temporal_graph" in result.output
        assert "spatial_graph" in result.output
        assert "spatio_temporal_graph" in result.output

    def test_config_help_works(self):
        """he config --help exits cleanly."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0

    def test_bare_he_banner_lists_manage_commands(self):
        """No-arg `he` banner includes tag, remove, and clean."""
        result = runner.invoke(app, [])
        assert result.exit_code == 0
        assert "he tag" in result.output
        assert "he remove" in result.output
        assert "he clean" in result.output

    def test_info_missing_ka_exits_with_error(self):
        """he info <nonexistent> exits with error."""
        result = runner.invoke(app, ["info", "/nonexistent/path"])
        assert result.exit_code != 0
