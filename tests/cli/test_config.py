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


def test_api_route_config_round_trip_uses_provider_endpoint_and_key(tmp_path, monkeypatch):
    monkeypatch.setenv("API_ROUTE_API_KEY", "route-test")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    cfg_path = tmp_path / "config.toml"
    ConfigManager(cfg_path).set_llm(provider="api-route", model="gpt-6.1-sol")

    config = ConfigManager(cfg_path).get_llm_config()
    assert config.provider == "api-route"
    assert config.model == "gpt-6.1-sol"
    assert config.base_url == "https://global.api-route.com/v1"
    assert config.api_key == "route-test"


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


def _isolate_default_config(tmp_path, monkeypatch):
    """Point ConfigManager() at a temp toml so CLI init never touches ~/.he."""
    cfg_path = tmp_path / "config.toml"
    monkeypatch.setattr("hyperextract.cli.config.DEFAULT_CONFIG_FILE", cfg_path)
    return cfg_path


def _read_init_toml(cfg_path):
    import tomllib

    with open(cfg_path, "rb") as f:
        return tomllib.load(f)


@pytest.mark.parametrize("provider", ["google", "anthropic", "deepseek"])
def test_quick_init_llm_only_provider_does_not_write_same_provider_embedder(
    tmp_path, monkeypatch, provider
):
    """Quick init must not copy an LLM-only provider onto embedder.provider."""
    from typer.testing import CliRunner

    from hyperextract.cli.cli import app
    from hyperextract.utils.client import PROVIDER_PRESETS

    cfg_path = _isolate_default_config(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, ["config", "init", "-p", provider, "-k", _FAKE_API_KEY])

    assert result.exit_code == 0, result.output
    assert "no default embedder" in result.output
    assert "he config embedder" in result.output

    data = _read_init_toml(cfg_path)
    assert data["llm"]["provider"] == provider
    assert data["llm"]["model"] == PROVIDER_PRESETS[provider]["default_llm"]
    assert data["llm"]["api_key"] == _FAKE_API_KEY
    assert data["embedder"].get("provider") != provider
    assert data["embedder"].get("api_key") in ("", None)


def test_quick_init_openai_still_writes_same_provider_embedder(tmp_path, monkeypatch):
    """Providers with a real default_embedder still share the LLM provider."""
    from typer.testing import CliRunner

    from hyperextract.cli.cli import app

    cfg_path = _isolate_default_config(tmp_path, monkeypatch)
    runner = CliRunner()
    result = runner.invoke(app, ["config", "init", "-p", "openai", "-k", _FAKE_API_KEY])

    assert result.exit_code == 0, result.output
    data = _read_init_toml(cfg_path)
    assert data["llm"]["provider"] == "openai"
    assert data["embedder"]["provider"] == "openai"
    assert data["embedder"]["model"] == "text-embedding-3-small"
    assert data["embedder"]["api_key"] == _FAKE_API_KEY


def test_interactive_init_llm_only_prompts_separate_openai_embedder(
    tmp_path, monkeypatch
):
    """Interactive Google init must not keep embedder.provider == google."""
    from hyperextract.cli.commands import config as config_cmd

    cfg_path = _isolate_default_config(tmp_path, monkeypatch)
    answers = iter(
        [
            "6",  # google in the interactive provider list
            "",  # default LLM model
            "",  # default LLM base URL
            _FAKE_API_KEY,
            "",  # default embedder provider (openai)
            "",  # default embedder model
            "",  # default embedder base URL
            "sk-emb",
        ]
    )
    monkeypatch.setattr(config_cmd.console, "input", lambda _prompt="": next(answers))

    config_cmd.init(provider=None, api_key=None, base_url=None)

    data = _read_init_toml(cfg_path)
    assert data["llm"]["provider"] == "google"
    assert data["llm"]["model"] == "gemini-3.8-flash"
    assert data["embedder"]["provider"] == "openai"
    assert data["embedder"]["model"] == "text-embedding-3-small"
    assert data["embedder"]["api_key"] == "sk-emb"


def test_legacy_broken_google_embedder_still_fails_create_embedder():
    """Lock the create_embedder guard so a leftover google embedder still fails."""
    from hyperextract.utils.client import create_embedder

    with pytest.raises(ValueError, match="embed"):
        create_embedder(
            {"provider": "google", "model": "text-embedding-3-small"},
            api_key=_FAKE_API_KEY,
        )


def test_quick_init_warns_when_provider_has_no_default_llm(tmp_path, monkeypatch):
    """`he config init` has no --model flag, so a preset-less provider (vllm)
    must say the written model is a placeholder."""
    from typer.testing import CliRunner

    from hyperextract.cli.cli import app

    cfg_path = _isolate_default_config(tmp_path, monkeypatch)
    result = CliRunner().invoke(
        app,
        [
            "config",
            "init",
            "-p",
            "vllm",
            "-k",
            "dummy",
            "-u",
            "http://localhost:8000/v1",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "no default LLM" in result.output
    assert "he config llm -p vllm -m" in result.output
    # The placeholder is still written (LLMConfig.model has a repo-wide default).
    assert _read_init_toml(cfg_path)["llm"]["provider"] == "vllm"


def test_quick_init_does_not_warn_when_preset_has_default_llm(tmp_path, monkeypatch):
    from typer.testing import CliRunner

    from hyperextract.cli.cli import app

    _isolate_default_config(tmp_path, monkeypatch)
    result = CliRunner().invoke(
        app, ["config", "init", "-p", "deepseek", "-k", _FAKE_API_KEY]
    )

    assert result.exit_code == 0, result.output
    assert "no default LLM" not in result.output
def test_atlascloud_is_a_library_preset_with_its_own_key_env():
    """The CLI reads Atlas Cloud from the library tables, not a copy."""
    from hyperextract.cli import config as cli_config

    assert "atlascloud" in cli_config.PROVIDER_PRESETS
    assert cli_config.PROVIDER_API_KEY_ENV["atlascloud"] == ("ATLASCLOUD_API_KEY",)


def test_get_llm_config_reads_atlascloud_env_key(tmp_path, monkeypatch):
    """Empty toml api_key must resolve ATLASCLOUD_API_KEY, ahead of OPENAI_API_KEY."""
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-must-not-win")
    monkeypatch.setenv("ATLASCLOUD_API_KEY", "apikey-atlas-from-env")

    cm = ConfigManager(tmp_path / "config.toml")
    cm.set_llm(provider="atlascloud", model="deepseek-ai/deepseek-v4-flash", api_key="")
    cfg = cm.get_llm_config()

    assert cfg.api_key == "apikey-atlas-from-env"
    assert cfg.base_url == "https://api.atlascloud.ai/v1"


def test_interactive_init_lists_atlascloud():
    """he config init provider list includes Atlas Cloud."""
    import inspect

    from hyperextract.cli.commands.config import init

    assert '"atlascloud"' in inspect.getsource(init)


def test_get_llm_and_embedder_config_read_runcrate_env_key(tmp_path, monkeypatch):
    """Empty toml api_key must resolve RUNCRATE_API_KEY, ahead of OPENAI_API_KEY."""
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "sk-openai-must-not-win")
    monkeypatch.setenv("RUNCRATE_API_KEY", "rc-from-env")

    cm = ConfigManager(tmp_path / "config.toml")
    cm.set_llm(provider="runcrate", model="deepseek-ai/DeepSeek-V4.1-Flash", api_key="")
    cm.set_embedder(provider="runcrate", model="BAAI/bge-m3", api_key="")

    llm_cfg = cm.get_llm_config()
    assert llm_cfg.api_key == "rc-from-env"
    assert llm_cfg.base_url == "https://api.runcrate.ai/v1"
    emb_cfg = cm.get_embedder_config()
    assert emb_cfg.api_key == "rc-from-env"
    assert emb_cfg.base_url == "https://api.runcrate.ai/v1"



def test_provider_help_lists_every_registered_preset():
    """The --provider help text is derived, so a new preset cannot drift out."""
    from hyperextract.cli.commands.config import _PROVIDER_HELP
    from hyperextract.utils.client import PROVIDER_PRESETS

    for name in ("cheaperinference", "api-route", "atlascloud", "runcrate"):
        assert name in PROVIDER_PRESETS
        assert name in _PROVIDER_HELP
    # Aliases are listed once, under their canonical name.
    assert "claude" not in _PROVIDER_HELP.split(", ")
    assert "gemini" not in _PROVIDER_HELP.split(", ")


def test_interactive_init_offers_every_registered_preset(tmp_path, monkeypatch):
    """Presets missing from the curated menu are appended, not dropped."""
    from hyperextract.cli.commands import config as config_cmd

    _isolate_default_config(tmp_path, monkeypatch)
    printed: list[str] = []
    monkeypatch.setattr(
        config_cmd.console, "print", lambda *a, **k: printed.append(str(a[0]) if a else "")
    )
    # Abort right after the provider menu is rendered.
    monkeypatch.setattr(
        config_cmd.console, "input", lambda *a, **k: (_ for _ in ()).throw(EOFError)
    )

    try:
        config_cmd.init(provider=None, api_key=None, base_url=None)
    except EOFError:
        pass

    menu = "\n".join(printed)
    assert "cheaperinference" in menu
    assert "api-route" in menu


def test_interactive_init_rejects_zero_choice(tmp_path, monkeypatch):
    """`0` must not select the last menu entry via negative indexing."""
    from hyperextract.cli.commands import config as config_cmd

    _isolate_default_config(tmp_path, monkeypatch)
    printed: list[str] = []
    monkeypatch.setattr(
        config_cmd.console,
        "print",
        lambda *a, **k: printed.append(str(a[0]) if a else ""),
    )
    # "0" for the menu, then abort — the prompts after it are not under test.
    answers = iter(["0"])

    def _input(*_args, **_kwargs):
        try:
            return next(answers)
        except StopIteration:
            raise EOFError from None

    monkeypatch.setattr(config_cmd.console, "input", _input)

    with pytest.raises(EOFError):
        config_cmd.init(provider=None, api_key=None, base_url=None)

    # Step 2 echoes the selection; "0" must not land on providers[-1].
    step2 = [line for line in printed if "Step 2" in line]
    assert step2, printed
    assert "Provider: custom" not in step2[0]
    assert "Provider: openai" in step2[0]
