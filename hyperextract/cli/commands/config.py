"""Config command for Hyper-Extract CLI."""

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from hyperextract.utils.logging import get_logger

from ..config import ConfigManager

logger = get_logger("he.config")
console = Console()

app = typer.Typer(
    name="config",
    help="Manage LLM and Embedder configuration",
    invoke_without_command=True,
)


@app.callback()
def config_callback(
    ctx: typer.Context,
):
    """Show configuration help when running 'he config' without subcommand."""
    if ctx.invoked_subcommand is not None:
        return

    from ..utils import LOGO

    console.print()
    console.print(Text(LOGO, style="bold cyan"))

    from rich.rule import Rule

    console.print(Rule(style="cyan dim"))
    console.print()

    title_text = Text("CONFIGURATION", style="bold cyan")
    desc_text = Text("Manage LLM and Embedder settings", style="dim")

    header = Table(box=None, show_header=False, pad_edge=False)
    header.add_column(no_wrap=True)
    header.add_column(style="dim white", no_wrap=True)
    header.add_row(title_text, desc_text)

    console.print(header)
    console.print()
    console.print(Rule(style="cyan dim"))
    console.print()

    console.print("[bold cyan]Available Commands:[/bold cyan]")
    console.print()

    commands_info = [
        (
            "he config init",
            "Interactive configuration setup (recommended for first-time users)",
        ),
        ("he config show", "Display current configuration"),
        ("he config llm", "Configure LLM settings"),
        ("he config embedder", "Configure Embedder settings"),
    ]

    for cmd, desc in commands_info:
        console.print(f"  [green]{cmd:<30}[/green] {desc}")

    console.print()
    console.print(Rule(style="cyan dim"))
    console.print()

    console.print("[bold cyan]Quick Start:[/bold cyan]")
    console.print()
    console.print(
        "  [yellow]1.[/yellow] Run [green]he config init[/green] for interactive setup"
    )
    console.print("  [yellow]2.[/yellow] Or configure individually:")
    console.print("     [green]he config llm --api-key YOUR_KEY[/green]")
    console.print("     [green]he config embedder --api-key YOUR_KEY[/green]")
    console.print()

    console.print("[bold cyan]Environment Variables (alternative):[/bold cyan]")
    console.print()
    console.print(
        "  [green]OPENAI_API_KEY[/green] - OpenAI API key (used if not set in config)"
    )
    console.print(
        "  [green]ANTHROPIC_API_KEY[/green] - Anthropic/Claude API key (or CLAUDE_API_KEY)"
    )
    console.print("  [green]OPENAI_BASE_URL[/green] - Custom API base URL (optional)")
    console.print()

    console.print(Rule(style="cyan dim"))
    console.print()

    hint_text = Text("💡 Tip: Run ", style="dim")
    hint_text.append("he config <command> --help", style="bold cyan")
    hint_text.append(" for detailed command usage", style="dim")
    console.print(hint_text)
    console.print()

    raise typer.Exit()


def _show_config():
    """Show current configuration."""
    config = ConfigManager()
    cfg = config.show()

    table = Table(title="Hyper-Extract Configuration")
    table.add_column("Service", style="cyan", width=12)
    table.add_column("Provider", style="blue", width=12)
    table.add_column("Model", style="yellow", width=28)
    table.add_column("API Key", style="magenta", width=20)
    table.add_column("Base URL", style="green", width=30)

    llm_cfg = cfg["llm"]
    emb_cfg = cfg["embedder"]

    table.add_row(
        "LLM",
        llm_cfg.get("provider", "-") or "-",
        llm_cfg["model"],
        llm_cfg["api_key"][:10] + "..." if llm_cfg["api_key"] else "(not set)",
        llm_cfg["base_url"] or "(default)",
    )
    table.add_row(
        "Embedder",
        emb_cfg.get("provider", "-") or "-",
        emb_cfg["model"],
        emb_cfg["api_key"][:10] + "..." if emb_cfg["api_key"] else "(not set)",
        emb_cfg["base_url"] or "(default)",
    )

    console.print(table)


@app.command(name="show")
def show(
    show_all: bool = typer.Option(False, "--show", help="Show all configuration"),
):
    """Show current configuration."""
    logger.info("command=config-show")
    _show_config()


@app.command(name="llm")
def llm(
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Provider preset: openai, anthropic, google, deepseek, bailian, orcarouter, vllm",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="LLM API key",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="LLM model name",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        "-u",
        help="Custom API base URL",
    ),
    show: bool = typer.Option(False, "--show", help="Show current LLM configuration"),
    unset: bool = typer.Option(False, "--unset", help="Unset LLM configuration"),
):
    """Configure LLM settings."""
    logger.info("command=config-llm show=%s unset=%s", show, unset)
    config = ConfigManager()

    if show:
        cfg = config.get_llm_config()
        table = Table(title="LLM Configuration", show_header=False)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Provider", cfg.provider or "(not set)")
        table.add_row("Model", cfg.model)
        table.add_row(
            "API Key", cfg.api_key[:10] + "..." if cfg.api_key else "(not set)"
        )
        table.add_row("Base URL", cfg.base_url or "(default)")
        console.print(table)
        return

    if unset:
        config.unset_llm()
        console.print("[green]LLM configuration cleared[/green]")
        return

    config.set_llm(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
    console.print("[green]LLM configuration updated[/green]")


@app.command(name="embedder")
def embedder(
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Provider preset: openai, anthropic, google, deepseek, bailian, orcarouter, vllm",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="Embedder API key",
    ),
    model: str | None = typer.Option(
        None,
        "--model",
        "-m",
        help="Embedder model name",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        "-u",
        help="Custom API base URL",
    ),
    show: bool = typer.Option(
        False, "--show", help="Show current Embedder configuration"
    ),
    unset: bool = typer.Option(False, "--unset", help="Unset Embedder configuration"),
):
    """Configure Embedder settings."""
    logger.info("command=config-embedder show=%s unset=%s", show, unset)
    config = ConfigManager()

    if show:
        cfg = config.get_embedder_config()
        table = Table(title="Embedder Configuration", show_header=False)
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_row("Provider", cfg.provider or "(not set)")
        table.add_row("Model", cfg.model)
        table.add_row(
            "API Key", cfg.api_key[:10] + "..." if cfg.api_key else "(not set)"
        )
        table.add_row("Base URL", cfg.base_url or "(default)")
        console.print(table)
        return

    if unset:
        config.unset_embedder()
        console.print("[green]Embedder configuration cleared[/green]")
        return

    config.set_embedder(
        provider=provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
    )
    console.print("[green]Embedder configuration updated[/green]")


@app.command(name="init")
def init(
    provider: str | None = typer.Option(
        None,
        "--provider",
        "-p",
        help="Provider preset: openai, anthropic, google, deepseek, bailian, orcarouter, vllm",
    ),
    api_key: str | None = typer.Option(
        None,
        "--api-key",
        "-k",
        help="API key for both LLM and Embedder",
    ),
    base_url: str | None = typer.Option(
        None,
        "--base-url",
        "-u",
        help="Custom API base URL",
    ),
):
    """Initialize configuration interactively."""
    logger.info(
        "command=config-init provider=%s api_key_provided=%s",
        provider,
        api_key is not None,
    )
    config = ConfigManager()

    # Quick mode: provider + api_key provided
    if provider and api_key:
        from hyperextract.utils.client import PROVIDER_PRESETS

        preset = PROVIDER_PRESETS.get(provider, {})
        llm_model = preset.get("default_llm") or "gpt-4o-mini"
        emb_model = preset.get("default_embedder") or "text-embedding-3-small"
        preset_url = preset.get("base_url") or ""
        resolved_base = base_url or preset_url

        config.set_llm(
            provider=provider,
            model=llm_model,
            api_key=api_key,
            base_url=resolved_base,
        )
        if emb_model:
            config.set_embedder(
                provider=provider,
                model=emb_model,
                api_key=api_key,
                base_url=resolved_base,
            )
        else:
            console.print(
                f"[yellow]Warning: Provider '{provider}' has no default embedder. Please configure embedder separately.[/yellow]"
            )

        console.print("[bold green]Configuration saved successfully![/bold green]")
        console.print()
        console.print("[bold]Current settings:[/bold]")
        console.print(f"  [cyan]Provider:[/cyan] {provider}")
        console.print(f"  [cyan]LLM Model:[/cyan] {llm_model}")
        if emb_model:
            console.print(f"  [cyan]Embedder Model:[/cyan] {emb_model}")
        console.print(f"  [cyan]Base URL:[/cyan] {resolved_base or '(default)'}")
        return

    # Legacy quick mode: only api_key provided (OpenAI defaults)
    if api_key and not provider:
        config.set_llm(
            provider="openai",
            model="gpt-4o-mini",
            api_key=api_key,
            base_url=base_url,
        )
        config.set_embedder(
            provider="openai",
            model="text-embedding-3-small",
            api_key=api_key,
            base_url=base_url,
        )
        console.print("[bold green]Configuration saved successfully![/bold green]")
        console.print()
        console.print("[bold]Current settings:[/bold]")
        console.print("  [cyan]Provider:[/cyan] openai")
        console.print("  [cyan]LLM Model:[/cyan] gpt-4o-mini")
        console.print("  [cyan]Embedder Model:[/cyan] text-embedding-3-small")
        console.print("  [cyan]API Key:[/cyan] " + api_key[:10] + "...")
        if base_url:
            console.print(f"  [cyan]Base URL:[/cyan] {base_url}")
        return

    # Interactive mode
    console.print("[bold blue]Hyper-Extract Configuration Setup[/bold blue]")
    console.print()

    from hyperextract.utils.client import PROVIDER_PRESETS

    console.print("[bold]Step 1: Choose Provider[/bold]")
    providers = [
        ("openai", "OpenAI", "https://api.openai.com/v1"),
        ("bailian", "阿里云百炼", "https://dashscope.aliyuncs.com/compatible-mode/v1"),
        ("deepseek", "DeepSeek", "https://api.deepseek.com"),
        ("orcarouter", "OrcaRouter", "https://api.orcarouter.ai/v1"),
        ("anthropic", "Anthropic (Claude)", "native SDK"),
        ("google", "Google Gemini", "native SDK"),
        ("vllm", "本地 vLLM", "自定义地址"),
        ("custom", "其他 OpenAI 兼容接口", "自定义地址"),
    ]
    for i, (key, name, url) in enumerate(providers, 1):
        console.print(f"  [{i}] {name:<20} ({url})")

    choice = console.input(f"\n请选择 [1-{len(providers)}]: ").strip()
    try:
        selected = providers[int(choice) - 1][0] if choice.isdigit() else "openai"
    except (IndexError, ValueError):
        selected = "openai"

    preset = PROVIDER_PRESETS.get(selected, {})
    preset_url = preset.get("base_url") or ""
    default_llm = preset.get("default_llm") or "gpt-4o-mini"
    default_emb = preset.get("default_embedder") or "text-embedding-3-small"

    console.print()
    console.print(f"[bold]Step 2: LLM Configuration (Provider: {selected})[/bold]")

    if selected == "vllm":
        llm_model = console.input("  LLM Model: ").strip()
        llm_base_url = console.input(
            "  LLM Base URL (e.g. http://localhost:8000/v1): "
        ).strip()
    else:
        llm_model = (
            console.input(f"  Model (default: {default_llm}): ").strip() or default_llm
        )
        llm_base_url = (
            console.input(
                f"  Base URL (default: {preset_url}, press Enter to skip): "
            ).strip()
            or preset_url
        )

    llm_api_key = None
    while not llm_api_key:
        llm_api_key = console.input("  API Key: ").strip()
        if not llm_api_key:
            if selected == "vllm":
                llm_api_key = "dummy"
                console.print("  [dim]Using 'dummy' for vLLM[/dim]")
                break
            console.print(
                "  [red]API Key is required. Please enter your API key.[/red]"
            )

    config.set_llm(
        provider=selected,
        model=llm_model,
        api_key=llm_api_key,
        base_url=llm_base_url or None,
    )

    console.print()

    console.print("[bold]Step 3: Embedder Configuration[/bold]")

    if selected == "vllm":
        emb_model = console.input("  Embedder Model (e.g. bge-m3): ").strip()
        emb_base_url = console.input(
            "  Embedder Base URL (e.g. http://localhost:8001/v1): "
        ).strip()
    else:
        emb_model = (
            console.input(f"  Model (default: {default_emb}): ").strip() or default_emb
        )
        emb_base_url = (
            console.input(
                f"  Base URL (default: {preset_url}, press Enter to skip): "
            ).strip()
            or preset_url
        )

    emb_api_key = None
    while not emb_api_key:
        emb_api_key = console.input("  API Key: ").strip()
        if not emb_api_key:
            if selected == "vllm":
                emb_api_key = "dummy"
                console.print("  [dim]Using 'dummy' for vLLM[/dim]")
                break
            console.print(
                "  [red]API Key is required. Please enter your API key.[/red]"
            )

    config.set_embedder(
        provider=selected,
        model=emb_model,
        api_key=emb_api_key,
        base_url=emb_base_url or None,
    )

    console.print()
    console.print("[bold green]Configuration saved successfully![/bold green]")
