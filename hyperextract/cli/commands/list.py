"""List command for Hyper-Extract CLI."""

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from hyperextract.utils.logging import get_logger
from hyperextract.utils.template_engine import Gallery

logger = get_logger("he.list")
console = Console()

app = typer.Typer(
    name="list",
    help="List available resources",
)


def _get_description(cfg, lang: str = "en") -> str:
    """Get description from template config, handling both str and dict types."""
    desc = cfg.description
    if isinstance(desc, dict):
        return desc.get(lang, desc.get("en", ""))
    return desc or ""


@app.command(name="template")
def template(
    query: str | None = typer.Option(
        None, "--query", "-q", help="Query to search templates"
    ),
    autotype: str | None = typer.Option(
        None, "--autotype", "-a", help="Filter by autotype"
    ),
    language: str | None = typer.Option(
        None, "--lang", "-l", help="Language filter (en/zh/all, default: en)"
    ),
    include_methods: bool = typer.Option(
        True, "--include-methods/--no-methods", help="Include method templates"
    ),
):
    """List all available templates with detailed information."""
    logger.info(
        "command=list-template query=%s autotype=%s lang=%s", query, autotype, language
    )
    target_lang = language if language else "en"

    results = Gallery.list(
        filter_by_query=query,
        filter_by_type=autotype,
        filter_by_language=None if target_lang == "all" else target_lang,
    )

    templates = []
    for path, cfg in results.items():
        languages = cfg.language if cfg.language else ["en"]
        if isinstance(languages, str):
            languages = [languages]

        if target_lang == "all":
            for lang in languages:
                templates.append((path, cfg.type, _get_description(cfg, lang)))
        else:
            lang = (
                target_lang
                if target_lang in languages
                else (languages[0] if languages else "en")
            )
            templates.append((path, cfg.type, _get_description(cfg, lang)))

    if include_methods and target_lang != "zh":
        from hyperextract.methods import list_method_cfgs

        method_templates = list_method_cfgs()
        for name, cfg in method_templates.items():
            templates.append((name, cfg.type, cfg.description))

    if not templates:
        console.print("[yellow]No templates found.[/yellow]")
        return

    table = Table(
        title="Available Templates",
        show_header=True,
        header_style="bold magenta",
        expand=True,
        show_lines=True,
    )
    table.add_column("Template ID", style="cyan", width=26)
    table.add_column("Type", style="yellow", no_wrap=True, width=22)
    table.add_column("Description", style="green")

    for tid, template_type, desc in templates:
        domain, name = tid.split("/", 1)
        table.add_row(Text(f"{domain}/\n{name}", style="cyan"), template_type, desc)

    console.print(table)
    console.print(f"\n[dim]Total: {len(templates)} templates[/dim]")
    console.print()
    console.print("[dim]Type explanations:[/dim]")
    console.print("  [cyan]document[/cyan] - Chunked raw text (no LLM extraction)")
    console.print("  [cyan]graph[/cyan] - Entity-relationship graph (binary relations)")
    console.print("  [cyan]hypergraph[/cyan] - Hypergraph (n-ary relations)")
    console.print("  [cyan]temporal_graph[/cyan] - Graph with time context")
    console.print("  [cyan]spatial_graph[/cyan] - Graph with location context")
    console.print("  [cyan]spatio_temporal_graph[/cyan] - Graph with time and location")
    console.print("  [cyan]list[/cyan] - Key-value list")
    console.print("  [cyan]model[/cyan] - Structured data model")
    console.print("  [cyan]set[/cyan] - Entity collection")
    console.print()
    console.print(
        "[dim]Tip: Use [bold]he parse <input> -t <template_id> -l <lang>[/bold] to extract with a template[/dim]"
    )


@app.command(name="method")
def method(
    query: str | None = typer.Option(
        None, "--query", "-q", help="Query to search methods"
    ),
):
    """List all available extraction methods with detailed information."""
    logger.info("command=list-method query=%s", query)
    from hyperextract.methods import list_methods

    items = list_methods()

    if query:
        query_lower = query.lower()
        items = {
            k: v
            for k, v in items.items()
            if query_lower in k.lower()
            or query_lower in v.get("description", "").lower()
        }

    if not items:
        console.print("[yellow]No methods found.[/yellow]")
        return

    table = Table(
        title="Available Methods",
        show_header=True,
        header_style="bold magenta",
        expand=True,
        show_lines=True,
    )
    table.add_column("Method", style="cyan")
    table.add_column("Type", style="yellow", no_wrap=True, width=12)
    table.add_column("Description", style="green")

    for name, info in items.items():
        method_type = info["type"]
        description = info["description"]
        table.add_row(Text(f"method/\n{name}", style="cyan"), method_type, description)

    console.print(table)
    console.print(f"\n[dim]Total: {len(items)} methods[/dim]")
    console.print()
    console.print("[dim]Method explanations:[/dim]")
    console.print("  [cyan]graph[/cyan] - Binary relation graph (entity-relationship)")
    console.print(
        "  [cyan]hypergraph[/cyan] - N-ary hypergraph (multi-entity relations)"
    )
    console.print()
    console.print(
        "[dim]Tip: Use [bold]he parse <input> -m <method_name>[/bold] to extract with a method[/dim]"
    )
