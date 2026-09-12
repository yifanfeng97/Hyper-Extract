"""Tests for ConfigManager persistence."""

import logging
import os
import subprocess

import pytest

from hyperextract.cli.config import ConfigManager, _icacls, _icacls_text

# Fixture-only dummy; never a real key from the environment.
_FAKE_API_KEY = "sk-test"

_POSIX_ONLY = pytest.mark.skipif(
    os.name == "nt",
    reason="POSIX file modes are not enforced on Windows",
)
_WINDOWS_ONLY = pytest.mark.skipif(
    os.name != "nt",
    reason="Windows ACL checks use icacls",
)


def test_save_creates_custom_parent_dir(tmp_path):
    """_save() must create the parent of a custom config_path, not the default dir."""
    cfg_path = tmp_path / "nested" / "dir" / "config.toml"  # parent doesn't exist yet

    mgr = ConfigManager(cfg_path)
    mgr.set_llm(provider="openai", model="gpt-4o-mini", api_key="sk-x")

    assert cfg_path.exists()

    # Round-trips back through a fresh manager.
    reloaded = ConfigManager(cfg_path)
    assert reloaded.llm.model == "gpt-4o-mini"


@_POSIX_ONLY
def test_save_sets_owner_only_permissions(tmp_path):
    cfg_path = tmp_path / "config.toml"
    mgr = ConfigManager(cfg_path)
    mgr.set_llm(provider="openai", model="gpt-4o-mini", api_key=_FAKE_API_KEY)

    assert cfg_path.stat().st_mode & 0o777 == 0o600


@_POSIX_ONLY
def test_save_tightens_existing_world_readable_file(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[llm]\nprovider = "openai"\nmodel = "gpt-4o-mini"\n'
        f'api_key = "{_FAKE_API_KEY}"\nbase_url = ""\n',
        encoding="utf-8",
    )
    cfg_path.chmod(0o644)
    assert cfg_path.stat().st_mode & 0o777 == 0o644

    mgr = ConfigManager(cfg_path)
    mgr.set_llm(provider="openai", api_key=_FAKE_API_KEY)

    assert cfg_path.stat().st_mode & 0o777 == 0o600


@_POSIX_ONLY
def test_load_warns_when_config_is_group_or_world_readable(tmp_path, caplog):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[llm]\nprovider = "openai"\nmodel = "gpt-4o-mini"\n'
        f'api_key = "{_FAKE_API_KEY}"\nbase_url = ""\n',
        encoding="utf-8",
    )
    cfg_path.chmod(0o644)

    with caplog.at_level(logging.WARNING, logger="hyperextract.cli.config"):
        ConfigManager(cfg_path)

    assert caplog.records
    assert any("0600" in record.getMessage() for record in caplog.records)
    assert _FAKE_API_KEY not in caplog.text


def _acl_text(path) -> str:
    return _icacls_text(_icacls(str(path)))


@_WINDOWS_ONLY
def test_save_sets_owner_only_acl(tmp_path):
    cfg_path = tmp_path / "config.toml"
    mgr = ConfigManager(cfg_path)
    mgr.set_llm(provider="openai", model="gpt-4o-mini", api_key=_FAKE_API_KEY)

    text = _acl_text(cfg_path)
    assert "Everyone:(R)" not in text
    assert "Everyone:" not in text


@_WINDOWS_ONLY
def test_save_removes_everyone_read(tmp_path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[llm]\nprovider = "openai"\nmodel = "gpt-4o-mini"\n'
        f'api_key = "{_FAKE_API_KEY}"\nbase_url = ""\n',
        encoding="utf-8",
    )
    subprocess.run(
        ["icacls", str(cfg_path), "/grant", "Everyone:(R)"],
        check=True,
        capture_output=True,
    )
    assert "Everyone:" in _acl_text(cfg_path)

    mgr = ConfigManager(cfg_path)
    mgr.set_llm(provider="openai", api_key=_FAKE_API_KEY)

    text = _acl_text(cfg_path)
    assert "Everyone:(R)" not in text
    assert "Everyone:" not in text


@_WINDOWS_ONLY
def test_load_warns_when_everyone_can_read(tmp_path, caplog):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[llm]\nprovider = "openai"\nmodel = "gpt-4o-mini"\n'
        f'api_key = "{_FAKE_API_KEY}"\nbase_url = ""\n',
        encoding="utf-8",
    )
    subprocess.run(
        ["icacls", str(cfg_path), "/grant", "Everyone:(R)"],
        check=True,
        capture_output=True,
    )

    with caplog.at_level(logging.WARNING, logger="hyperextract.cli.config"):
        ConfigManager(cfg_path)

    assert caplog.records
    assert any("Everyone" in record.getMessage() for record in caplog.records)
    assert _FAKE_API_KEY not in caplog.text
def test_cli_provider_tables_are_library_presets():
    """CLI must not keep a drifting copy of library provider tables."""
    from hyperextract.cli import config as cli_config
    from hyperextract.utils.client import PROVIDER_API_KEY_ENV, PROVIDER_PRESETS

    assert cli_config.PROVIDER_PRESETS is PROVIDER_PRESETS
    assert cli_config.PROVIDER_API_KEY_ENV is PROVIDER_API_KEY_ENV
    assert "orcarouter" in cli_config.PROVIDER_PRESETS
    assert cli_config.PROVIDER_API_KEY_ENV["orcarouter"] == ("ORCAROUTER_API_KEY",)
    assert "google" in cli_config.PROVIDER_PRESETS
    assert cli_config.PROVIDER_API_KEY_ENV["google"] == (
        "GOOGLE_API_KEY",
        "GEMINI_API_KEY",
    )


def test_get_llm_config_reads_orcarouter_env_key(tmp_path, monkeypatch):
    """Empty toml api_key must resolve ORCAROUTER_API_KEY for orcarouter."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("ORCAROUTER_API_KEY", "sk-orca-from-env")

    cm = ConfigManager(tmp_path / "config.toml")
    cm.set_llm(provider="orcarouter", model="orcarouter/auto", api_key="")
    cfg = cm.get_llm_config()

    assert cfg.api_key == "sk-orca-from-env"
    assert cfg.base_url == "https://api.orcarouter.ai/v1"


def test_get_llm_config_orcarouter_key_beats_openai_key(tmp_path, monkeypatch):
    """ORCAROUTER_API_KEY must win over OPENAI_API_KEY for orcarouter."""
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-must-not-win")
    monkeypatch.setenv("ORCAROUTER_API_KEY", "sk-orca-preferred")

    cm = ConfigManager(tmp_path / "config.toml")
    cm.set_llm(provider="orcarouter", api_key="")
    cfg = cm.get_llm_config()

    assert cfg.api_key == "sk-orca-preferred"


def test_interactive_init_lists_orcarouter_and_anthropic():
    """he config init provider list must match library presets."""
    import inspect

    from hyperextract.cli.commands.config import init

    source = inspect.getsource(init)
    assert '"orcarouter"' in source
    assert '"anthropic"' in source
    assert '"google"' in source


def test_get_llm_config_reads_google_env_key(tmp_path, monkeypatch):
    """Empty toml api_key must resolve GOOGLE_API_KEY for google."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "sk-google-from-env")

    cm = ConfigManager(tmp_path / "config.toml")
    cm.set_llm(provider="google", model="gemini-3.8-flash", api_key="")
    cfg = cm.get_llm_config()

    assert cfg.api_key == "sk-google-from-env"
    assert cfg.base_url == ""
