"""CLI entry point for Hyper-Extract."""

import hashlib
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt
from rich.table import Table
from rich.text import Text

from hyperextract.utils.logging import configure_logging, get_logger
from hyperextract.utils.template_engine import Gallery, Template

from .commands import config_app, list_app, template_app
from .config import (
    load_ka_metadata,
)
from .utils import (
    LOGO,
    collect_directory_text_inputs,
    get_template_from_ka,
    read_input,
    require_supported_text_input,
    validate_config,
    validate_ka_path,
    validate_ka_with_data,
    validate_ka_with_index,
)

console = Console()
logger = get_logger("he")

app = typer.Typer(
    name="he",
    help="Hyper-Extract CLI - A command-line tool for knowledge extraction",
    add_completion=False,
    invoke_without_command=True,
)

app.add_typer(list_app, name="list")
app.add_typer(config_app, name="config")
app.add_typer(template_app, name="template")


@app.callback()
def main(
    ctx: typer.Context,
    version: bool = typer.Option(
        False,
        "--version",
        "-v",
        help="Show version information",
        is_eager=True,
    ),
):
    # Configure logging after all imports complete so dependency loggers
    # (e.g. ontosight) don't override our level settings.
    # Log level is controlled solely by the HYPER_EXTRACT_LOG_LEVEL env var.
    configure_logging()
    if version:
        from . import __version__

        console.print(f"[bold]Hyper-Extract CLI[/bold] version {__version__}")
        raise typer.Exit()

    if ctx.invoked_subcommand is None:
        from . import __version__

        console.print()
        console.print(Text(LOGO, style="bold cyan"))

        title_text = Text("HYPER-EXTRACT", style="bold cyan")
        version_text = Text(f"v{__version__}", style="dim white")
        desc_text = Text(
            "Transform document into knowledge-abstract", style="dim", no_wrap=True
        )

        header = Table(box=None, show_header=False, pad_edge=False)
        header.add_column(no_wrap=True)
        header.add_column(style="dim white", no_wrap=True)
        header.add_row(title_text, version_text)

        console.print(header)
        console.print(desc_text)
        console.print()

        from rich.rule import Rule

        console.print(Rule(style="cyan dim"))
        console.print()

        from rich.panel import Panel

        def make_section(title: str, commands: list[tuple[str, str]]) -> Panel:
            table = Table(box=None, show_header=False, pad_edge=False)
            table.add_column(style="green bold", no_wrap=True)
            table.add_column(style="white", no_wrap=True)
            for cmd, desc in commands:
                table.add_row(f"  {cmd}", desc)
            return Panel(
                table,
                title=f"[bold cyan]{title}[/]",
                border_style="cyan dim",
                padding=(0, 1),
                title_align="center",
                width=80,
            )

        sections = [
            make_section(
                "🚀 Getting Started",
                [
                    ("he list template", "List available templates"),
                    ("he list method", "List extraction methods"),
                    ("he template validate <yaml>", "Validate a template YAML file"),
                    ("he config --help", "Manage LLM/Embedder config"),
                ],
            ),
            make_section(
                "✨ Create Knowledge Abstract (KA)",
                [
                    (
                        "he parse <input_document> -o <ka_path>",
                        "Extract KA from document",
                    ),
                    (
                        "he feed <ka_path> <input_document>",
                        "Add document to existing KA",
                    ),
                    ("he build-index <ka_path>", "Build semantic search index"),
                ],
            ),
            make_section(
                "🔍 Explore Knowledge Abstract (KA)",
                [
                    ("he info <ka_path>", "View KA info & stats"),
                    ("he talk <ka_path> [-i]", "Chat with KA"),
                    ("he search <ka_path> <query>", "Semantic search"),
                    ("he show <ka_path>", "Visualize KA"),
                    (
                        "he export obsidian <ka_path> -o <vault>",
                        "Export to Obsidian vault",
                    ),
                    (
                        "he export graphml <ka_path> -o <file>",
                        "Export pairwise graph to GraphML",
                    ),
                    (
                        "he export csv <ka_path> -o <dir>",
                        "Export nodes/edges as CSV tables",
                    ),
                ],
            ),
            make_section(
                "🛠️ Manage Knowledge Abstract (KA)",
                [
                    (
                        "he tag <ka_path> --source ...",
                        "Tag a source document",
                    ),
                    (
                        "he remove <ka_path> ...",
                        "Delete nodes, edges, facts, or documents",
                    ),
                    ("he clean <ka_path>", "Remove index or the whole KA"),
                ],
            ),
        ]

        for section in sections:
            console.print(section)
        console.print()
        console.print(Rule(style="cyan dim"))
        console.print()

        hint_text = Text("💡 Tip: Run ", style="dim")
        hint_text.append("he --help", style="bold cyan")
        hint_text.append(" for detailed documentation", style="dim")
        console.print(hint_text)
        console.print()
        raise typer.Exit()


def select_template_interactive() -> str | None:
    """Interactive template selection when user doesn't specify one."""
    templates = Gallery.list()

    if not templates:
        console.print("[yellow]No templates available.[/yellow]")
        return None

    template_list = list(templates.items())

    console.print()
    console.print("[bold cyan]Select a template:[/bold cyan]")
    console.print()

    for i, (path, cfg) in enumerate(template_list, 1):
        desc = cfg.description if cfg.description else ""
        if isinstance(desc, dict):
            desc = desc.get("zh", desc.get("en", ""))
        console.print(f"  [{i}] {path}")
        if desc:
            console.print(f"      {desc}")

    console.print()

    while True:
        choice = Prompt.ask(
            "Enter number or search keyword",
            default="1",
            show_default=True,
        )

        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(template_list):
                return template_list[idx][0]
            else:
                console.print(
                    f"[red]Invalid number. Please choose 1-{len(template_list)}[/red]"
                )
        else:
            query_lower = choice.lower()
            matches = [
                (i, p, c)
                for i, (p, c) in enumerate(template_list)
                if query_lower in p.lower()
                or (c.description and query_lower in str(c.description).lower())
            ]

            if len(matches) == 1:
                return matches[0][1]
            elif len(matches) > 1:
                console.print(f"[yellow]Found {len(matches)} matches:[/yellow]")
                for i, path, cfg in matches:
                    console.print(f"  [{i + 1}] {path}")
                continue
            else:
                console.print("[yellow]No matches found. Try another keyword.[/yellow]")


@app.command(name="parse")
def parse(
    input: str = typer.Argument(
        ..., help="Input file path, directory, or '-' for stdin"
    ),
    output: str = typer.Option(..., "--output", "-o", help="Output directory"),
    template: str | None = typer.Option(
        None, "--template", "-t", help="Template (omit for interactive selection)"
    ),
    method: str | None = typer.Option(
        None, "--method", "-m", help="Method template (e.g., light_rag, hyper_rag)"
    ),
    lang: str | None = typer.Option(
        None,
        "--lang",
        "-l",
        help="Language (zh/en). Required for knowledge templates, optional for methods (default: en)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force overwrite"),
    no_index: bool = typer.Option(
        False, "--no-index", help="Skip building search index"
    ),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Source attribution (document id) for per-document rollback later (he remove --document)",
    ),
):
    """Extract knowledge from text to a new directory."""
    logger.info(
        "command=parse input=%s output=%s template=%s lang=%s",
        input,
        output,
        template or "auto",
        lang or "auto",
    )
    validate_config()
    logger.info("stage=config_validated")

    if method:
        template = f"method/{method}"
    elif template is None:
        template = select_template_interactive()
        if template is None:
            console.print("[red]No template selected. Exiting.[/red]")
            raise typer.Exit(1)

    is_method_template = template.startswith("method/")

    if is_method_template:
        if lang is not None:
            console.print(
                "[dim]Note: Method templates use English prompts. --lang parameter is ignored.[/dim]"
            )
        lang = "en"
    elif lang is None:
        console.print(
            "[red]Error:[/red] --lang is required for knowledge templates. Use --lang en or --lang zh."
        )
        raise typer.Exit(1)

    output_path = Path(output)

    if output_path.exists() and not force:
        if any(output_path.iterdir()):
            console.print(
                "[red]Error:[/red] Output directory already exists and is not empty. Use --force to overwrite."
            )
            raise typer.Exit(1)

    output_path.mkdir(parents=True, exist_ok=True)

    console.print(f"[blue]Input:[/blue] {input}")
    console.print(f"[blue]Output:[/blue] {output}")
    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Language:[/blue] {lang}")
    console.print(f"[blue]Build Index:[/blue] {'No' if no_index else 'Yes'}")
    console.print()

    try:
        template_config = Template.get(template)
        if template_config is None:
            raise ValueError(f"Template '{template}' not found")
        console.print(f"[green]Template resolved:[/green] {template_config.name}")
        logger.info("stage=template_resolved template=%s", template_config.name)
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    input_path = Path(input)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Creating template instance...", total=None)

        ka = Template.create(template, lang)
        logger.info("stage=template_created")

        if input_path.is_dir():
            progress.update(task, description="Processing directory...")
            text_files = collect_directory_text_inputs(input_path)

            # Per-file provenance: each file is attributed by its stem
            # unless a single --source id was given explicitly.
            file_sources = [source or file_path.stem for file_path in text_files]

            all_text = []
            for file_path, file_source in zip(text_files, file_sources):
                text = read_input(str(file_path))
                all_text.append(text)
                console.print(
                    f"[dim]Loaded {file_path.name}: {len(text)} chars "
                    f"(source: {file_source})[/dim]"
                )

            progress.update(task, description="Extracting knowledge...")
            logger.debug("stage=feed_text_invoked")
            for file_path, file_source, text in zip(text_files, file_sources, all_text):
                ka.feed_text(text, source_id=file_source)
            logger.info("stage=knowledge_extracted files=%d", len(text_files))
        else:
            progress.update(task, description="Reading input...")
            require_supported_text_input(input)
            text = read_input(input)
            console.print(f"[dim]Input text: {len(text)} characters[/dim]")

            progress.update(task, description="Extracting knowledge...")
            logger.debug("stage=feed_text_invoked")
            if source:
                from hyperextract.utils.document_store import SourceDocumentStore

                SourceDocumentStore(output_path).store_file(source, input)
            ka.feed_text(text, source_id=source)
            logger.info("stage=knowledge_extracted chars=%d", len(text))

        progress.update(task, description="Saving data...")

        template_config = Template.get(template)
        if template_config is None and template.endswith(".yaml"):
            import shutil

            filename = Path(template).name
            shutil.copy(template, output_path / filename)
            console.print(
                f"[dim]Custom template '{filename}' saved to KA directory[/dim]"
            )

        ka.dump(output_path)
        logger.info("stage=data_saved output=%s", output_path)

        if not no_index:
            progress.update(task, description="Building search index...")
            ka.build_index()
            console.print("[dim]Index built successfully[/dim]")
            logger.info("stage=index_built")
            progress.update(task, description="Saving index...")
            ka.dump(output_path)
            logger.info("stage=index_saved")

    console.print()
    console.print(
        f"[bold green]Success![/bold green] Knowledge extracted to {output_path}"
    )
    console.print()
    if no_index:
        console.print("[dim]Note: Index was not built.[/dim]")
        console.print(
            f"[dim]  he build-index {output}       # Build index to enable search/talk[/dim]"
        )
        console.print(
            f"[dim]  he feed {output} <new_document>  # Append more documents[/dim]"
        )
    else:
        console.print("[dim]What's next?[/dim]")
        console.print(
            f"[dim]  he show {output}                    # Visualize knowledge graph[/dim]"
        )
        console.print(
            f"[dim]  he feed {output} <new_document>     # Append more documents[/dim]"
        )
        console.print(
            f'[dim]  he search {output} "keyword"        # Semantic search[/dim]'
        )
        console.print(
            f"[dim]  he talk {output} -i                 # Interactive chat[/dim]"
        )
        console.print(
            f'[dim]  he talk {output} -q "your question" # Single query[/dim]'
        )


@app.command(name="show")
def show(ka_path: str = typer.Argument(..., help="Knowledge Abstract directory")):
    """Visualize Knowledge Abstract using OntoSight."""
    logger.info("command=show ka_path=%s", ka_path)
    path = validate_ka_with_data(ka_path)

    template, lang = get_template_from_ka(path)

    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Language:[/blue] {lang}")
    console.print()

    validate_config()

    with console.status("[bold blue]Loading Knowledge Abstract..."):
        try:
            ka = Template.create(template, lang)
            ka.load(path)

        except Exception as e:
            console.print(f"[red]Error loading Knowledge Abstract:[/red] {e}")
            raise typer.Exit(1)

    console.print("[bold blue]Visualizing with OntoSight...[/bold blue]")
    logger.info("stage=visualizing")

    try:
        ka.show()
        logger.info("stage=visualization_complete")
    except Exception as e:
        console.print(f"[red]Error during visualization:[/red] {e}")
        raise typer.Exit(1)

    console.print()
    console.print("[dim]Continue exploring:[/dim]")
    console.print(
        f'[dim]  he search {ka_path} "keyword"  # Search specific content[/dim]'
    )
    console.print(f"[dim]  he talk {ka_path} -i           # Interactive chat[/dim]")


export_app = typer.Typer(
    name="export",
    help="Export a Knowledge Abstract to other formats",
    no_args_is_help=True,
)


@export_app.command(name="obsidian")
def export_obsidian_cmd(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    output: str = typer.Option(..., "--output", "-o", help="Output vault directory"),
    name: str | None = typer.Option(
        None, "--name", help="Vault name used for the index note"
    ),
    no_index: bool = typer.Option(
        False, "--no-index", help="Skip writing the index/map-of-content note"
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Write into an existing, non-empty directory"
    ),
):
    """Export a Knowledge Abstract to an Obsidian vault (Markdown + wikilinks)."""
    logger.info("command=export-obsidian ka_path=%s output=%s", ka_path, output)

    path = validate_ka_with_data(ka_path)
    template, lang = get_template_from_ka(path)

    output_path = Path(output)
    if output_path.exists() and any(output_path.iterdir()) and not force:
        console.print(
            "[red]Error:[/red] Output directory already exists and is not empty. "
            "Use --force to write into it."
        )
        raise typer.Exit(1)

    console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Output vault:[/blue] {output}")
    console.print()

    validate_config()

    vault_name = name or output_path.name or "Knowledge Vault"

    with console.status("[bold blue]Loading Knowledge Abstract..."):
        try:
            ka = Template.create(template, lang)
            ka.load(path)
        except Exception as e:
            console.print(f"[red]Error loading Knowledge Abstract:[/red] {e}")
            raise typer.Exit(1)

    if not hasattr(ka, "export_obsidian"):
        console.print(
            "[red]Error:[/red] Obsidian export is only supported for graph-type "
            "Knowledge Abstracts (graph, hypergraph, temporal/spatial graphs)."
        )
        raise typer.Exit(1)

    with console.status("[bold blue]Exporting to Obsidian vault..."):
        try:
            ka.export_obsidian(
                output_path,
                vault_name=vault_name,
                include_index=not no_index,
                overwrite=force,
            )
        except Exception as e:
            console.print(f"[red]Error during export:[/red] {e}")
            raise typer.Exit(1)

    note_count = len(list(output_path.glob("*.md")))
    console.print()
    console.print(
        f"[bold green]Success![/bold green] Exported {note_count} notes to {output_path}"
    )
    console.print()
    console.print("[dim]Open the folder as a vault in Obsidian to explore it.[/dim]")


def _load_graph_ka_for_export(ka_path: str):
    """Load a graph-family KA for GraphML / CSV export."""
    path = validate_ka_with_data(ka_path)
    template, lang = get_template_from_ka(path)

    validate_config()

    with console.status("[bold blue]Loading Knowledge Abstract..."):
        try:
            ka = Template.create(template, lang)
            ka.load(path)
        except Exception as e:
            console.print(f"[red]Error loading Knowledge Abstract:[/red] {e}")
            raise typer.Exit(1)

    if not hasattr(ka, "export_obsidian"):
        console.print(
            "[red]Error:[/red] GraphML/CSV/Cypher export is only supported for "
            "graph-type Knowledge Abstracts (graph, hypergraph, temporal/spatial graphs)."
        )
        raise typer.Exit(1)

    return ka, path, template


def _is_hypergraph_ka(ka) -> bool:
    """True for AutoHypergraph; temporal/spatial graphs are pairwise."""
    if type(ka).__name__ == "AutoHypergraph":
        return True
    meta = getattr(ka, "metadata", None)
    return isinstance(meta, dict) and meta.get("type") == "hypergraph"


@export_app.command(name="graphml")
def export_graphml_cmd(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    output: str = typer.Option(..., "--output", "-o", help="Output GraphML file"),
):
    """Export a knowledge graph to GraphML.

    Binary edges are written as `<edge source target>`. Edges with three
    or more endpoints are written as GraphML 1.0 `<hyperedge>` elements.
    """
    from hyperextract.utils.exporters import GraphMLHypergraphError, export_to_graphml

    logger.info("command=export-graphml ka_path=%s output=%s", ka_path, output)

    ka, _path, template = _load_graph_ka_for_export(ka_path)

    output_path = Path(output)
    console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Output file:[/blue] {output}")
    console.print()

    with console.status("[bold blue]Exporting to GraphML..."):
        try:
            export_to_graphml(
                ka.nodes,
                ka.edges,
                node_id_extractor=ka.node_key_extractor,
                incident_nodes_extractor=ka.nodes_in_edge_extractor,
                file_path=output_path,
                edge_id_extractor=getattr(ka, "edge_key_extractor", None),
            )
        except GraphMLHypergraphError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error during export:[/red] {e}")
            raise typer.Exit(1)

    console.print()
    console.print(f"[bold green]Success![/bold green] Wrote GraphML to {output_path}")
    console.print()
    console.print("[dim]Open the file in Gephi, yEd, or another GraphML tool.[/dim]")


@export_app.command(name="cypher")
def export_cypher_cmd(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    output: str = typer.Option(..., "--output", "-o", help="Output Cypher file"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite an existing Cypher file"
    ),
):
    """Export a knowledge graph to a Neo4j-compatible Cypher MERGE script.

    Binary edges become relationships. N-ary edges become Hyperedge nodes
    with IN membership (not a pairwise clique).
    """
    from hyperextract.utils.exporters import export_to_cypher

    logger.info("command=export-cypher ka_path=%s output=%s", ka_path, output)

    output_path = Path(output)
    existing_nonempty = (
        output_path.exists()
        and output_path.is_file()
        and output_path.stat().st_size > 0
    )
    if existing_nonempty and not force:
        console.print(
            "[red]Error:[/red] Output file already exists. "
            "Use --force / -f to overwrite it."
        )
        raise typer.Exit(1)

    ka, _path, template = _load_graph_ka_for_export(ka_path)
    console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Output file:[/blue] {output}")
    console.print()

    with console.status("[bold blue]Exporting to Cypher..."):
        try:
            export_to_cypher(
                ka.nodes,
                ka.edges,
                node_id_extractor=ka.node_key_extractor,
                incident_nodes_extractor=ka.nodes_in_edge_extractor,
                file_path=output_path,
                edge_id_extractor=getattr(ka, "edge_key_extractor", None),
            )
        except Exception as e:
            console.print(f"[red]Error during export:[/red] {e}")
            raise typer.Exit(1)

    console.print()
    console.print(f"[bold green]Success![/bold green] Wrote Cypher to {output_path}")
    console.print()
    console.print("[dim]Load with cypher-shell < file.cypher (Neo4j / Memgraph).[/dim]")


@export_app.command(name="csv")
def export_csv_cmd(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    output: str = typer.Option(..., "--output", "-o", help="Output directory"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Write into an existing, non-empty directory"
    ),
):
    """Export a Knowledge Abstract to node and edge CSV tables."""
    from hyperextract.utils.exporters import export_to_csv

    logger.info("command=export-csv ka_path=%s output=%s", ka_path, output)

    output_path = Path(output)
    nonempty = (
        output_path.exists() and output_path.is_dir() and any(output_path.iterdir())
    )
    if nonempty and not force:
        console.print(
            "[red]Error:[/red] Output directory already exists and is not empty. "
            "Use --force to write into it."
        )
        raise typer.Exit(1)

    ka, _path, template = _load_graph_ka_for_export(ka_path)
    hypergraph = _is_hypergraph_ka(ka)

    console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Output directory:[/blue] {output}")
    console.print()

    with console.status("[bold blue]Exporting to CSV..."):
        try:
            export_to_csv(
                ka.nodes,
                ka.edges,
                node_id_extractor=ka.node_key_extractor,
                incident_nodes_extractor=ka.nodes_in_edge_extractor,
                folder_path=output_path,
                edge_id_extractor=getattr(ka, "edge_key_extractor", None),
                hypergraph=hypergraph,
                overwrite=force,
            )
        except FileExistsError:
            console.print(
                "[red]Error:[/red] Output directory already exists and is not empty. "
                "Use --force to write into it."
            )
            raise typer.Exit(1)
        except Exception as e:
            console.print(f"[red]Error during export:[/red] {e}")
            raise typer.Exit(1)

    if hypergraph:
        written = "nodes.csv + hyperedges.csv"
    else:
        written = "nodes.csv + edges.csv"

    console.print()
    console.print(f"[bold green]Success![/bold green] Wrote {written} to {output_path}")


app.add_typer(export_app, name="export")


@app.command(name="info")
def info(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    sources: bool = typer.Option(
        False,
        "--sources",
        help="Show the source ledger (documents that contributed to this KA)",
    ),
):
    """View Knowledge Abstract information and statistics."""
    logger.info("command=info ka_path=%s sources=%s", ka_path, sources)
    import json

    path = validate_ka_with_data(ka_path)

    metadata = load_ka_metadata(path)

    data_file = path / "data.json"
    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, dict):
        node_count = len(data.get("nodes", data.get("entities", [])))
        edge_count = len(data.get("edges", data.get("relations", [])))
        chunk_count = len(data.get("chunks", []))
    elif isinstance(data, list):
        node_count = len(data)
        edge_count = 0
        chunk_count = 0
    else:
        node_count = 0
        edge_count = 0
        chunk_count = 0

    index_exists = (path / "index").exists() and any((path / "index").iterdir())

    table = Table(title="Knowledge Abstract Info", show_header=False, box=None)
    table.add_column("Key", style="cyan", width=15)
    table.add_column("Value", style="green")

    table.add_row("Path", str(path))

    if metadata:
        table.add_row("Template", metadata.get("template", "unknown"))
        table.add_row("Language", metadata.get("lang", "unknown"))
        table.add_row("Created", metadata.get("created_at", "unknown"))
        table.add_row("Updated", metadata.get("updated_at", "unknown"))
    else:
        table.add_row("Template", "[yellow]unknown[/yellow]")
        table.add_row("Language", "[yellow]unknown[/yellow]")

    table.add_row("Nodes", str(node_count))
    table.add_row("Edges", str(edge_count))
    if chunk_count:
        table.add_row("Chunks", str(chunk_count))
    table.add_row(
        "Index", "[green]Built[/green]" if index_exists else "[red]Not Built[/red]"
    )

    console.print(table)

    if sources:
        sources_table = Table(title="Source Ledger", show_header=True)
        sources_table.add_column("Source ID", style="cyan")
        sources_table.add_column("Raw Items", justify="right")
        sources_table.add_column("Content Hash")
        sources_table.add_column("Archived Document")

        ledger_files = [
            (path / "sources_nodes.json", "nodes"),
            (path / "sources_edges.json", "edges"),
            (path / "sources_chunks.json", "chunks"),
            (path / "sources_items.json", "items"),
        ]
        combined: dict = {}
        for ledger_path, _kind in ledger_files:
            if not ledger_path.exists():
                continue
            try:
                entries = json.loads(ledger_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(
                    "sources_ledger_read_failed path=%s error=%s", ledger_path, e
                )
                continue
            from hyperextract.utils.document_store import SourceDocumentStore

            doc_store = SourceDocumentStore(path)
            for entry in entries:
                sid = entry.get("source_id")
                if sid is None:
                    continue
                record = combined.setdefault(
                    sid, {"raw_items": 0, "content_hash": entry.get("content_hash")}
                )
                record["raw_items"] += len(entry.get("raw_items", []))

        if combined:
            for sid, info_row in sorted(combined.items()):
                archived = doc_store.find(sid)
                archived_name = archived[0].name if archived else "—"
                sources_table.add_row(
                    sid,
                    str(info_row["raw_items"]),
                    info_row["content_hash"] or "—",
                    archived_name,
                )
            console.print(sources_table)
        else:
            console.print(
                "[yellow]No source ledger found.[/yellow] "
                "Feed documents with --source to enable per-document rollback."
            )


@app.command(name="search")
def search(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    query: str = typer.Argument(..., help="Search query"),
    top_k: int = typer.Option(3, "--top-k", "-n", help="Number of results"),
    source: list[str] | None = typer.Option(
        None, "--source", help="Scope: only knowledge from these source documents"
    ),
    tag: list[str] | None = typer.Option(
        None, "--tag", help="Scope: only knowledge from sources carrying these tags"
    ),
):
    """Semantic search in Knowledge Abstract."""
    logger.info("command=search ka_path=%s query=%s top_k=%d", ka_path, query, top_k)
    import json

    validate_config()

    path = validate_ka_with_index(ka_path)
    template, lang = get_template_from_ka(path)

    console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
    console.print(f"[blue]Query:[/blue] {query}")
    console.print(f"[blue]Top K:[/blue] {top_k}")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Searching...", total=None)

        try:
            ka = Template.create(template, lang)

            progress.update(task, description="Loading Knowledge Abstract...")
            ka.load(path)

            progress.update(task, description="Searching...")
            scope_kwargs = {}
            if source:
                scope_kwargs["source_ids"] = list(source)
            if tag:
                scope_kwargs["tags"] = list(tag)
            if scope_kwargs:
                # Fail with a clear message when the KA type has no ledger
                # (e.g. AutoList/AutoModel) instead of a raw TypeError.
                import inspect

                search_params = inspect.signature(type(ka).search).parameters
                for flag, key in (("--source", "source_ids"), ("--tag", "tags")):
                    if key in scope_kwargs and key not in search_params:
                        console.print(
                            f"[red]Error:[/red] Scoped search ({flag}) is not "
                            f"supported by {type(ka).__name__} knowledge "
                            "abstracts (no source ledger)."
                        )
                        raise typer.Exit(1)
            results = ka.search(query, top_k=top_k, **scope_kwargs)
            logger.info("stage=search_complete results=%d", len(results))

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    console.print()
    if not results:
        console.print("[yellow]No results found.[/yellow]")
    else:
        console.print(f"[bold green]Found {len(results)} result(s):[/bold green]")
        console.print()

        for i, result in enumerate(results, 1):
            console.print(f"[bold cyan]Result {i}:[/bold cyan]")
            if hasattr(result, "model_dump"):
                console.print_json(
                    json.dumps(result.model_dump(), indent=2, ensure_ascii=False)
                )
            elif hasattr(result, "dict"):
                console.print_json(
                    json.dumps(result.dict(), indent=2, ensure_ascii=False)
                )
            else:
                console.print(str(result))
            console.print()

    console.print("[dim]Continue:[/dim]")
    console.print(
        f'[dim]  he talk {ka_path} -q "question about results"  # Deep dive[/dim]'
    )
    console.print(
        f"[dim]  he talk {ka_path} -i                           # Interactive mode[/dim]"
    )
    console.print(
        f"[dim]  he show {ka_path}                              # Visualize[/dim]"
    )


def chat_loop(ka, ka_path: str, top_k: int = 3):
    """Interactive chat loop."""
    console.print(
        "\n[bold green]Entering interactive mode. Type 'exit' or 'quit' to stop.[/bold green]\n"
    )
    while True:
        try:
            query = console.input("[bold cyan]>[/bold cyan] ")
            if query.lower() in ["exit", "quit", "q"]:
                console.print("\n[dim]Goodbye![/dim]")
                console.print()
                console.print("[dim]Other useful commands:[/dim]")
                console.print(
                    f"[dim]  he show {ka_path}              # Visualize[/dim]"
                )
                console.print(f'[dim]  he search {ka_path} "keyword"  # Search[/dim]')
                console.print(
                    f"[dim]  he info {ka_path}              # View info[/dim]"
                )
                break
            if not query.strip():
                continue
            response = ka.chat(query, top_k=top_k)
            console.print()
            console.print(response.content)
            console.print()
        except KeyboardInterrupt:
            console.print("\n[dim]Goodbye![/dim]")
            console.print()
            console.print("[dim]Other useful commands:[/dim]")
            console.print(f"[dim]  he show {ka_path}              # Visualize[/dim]")
            console.print(f'[dim]  he search {ka_path} "keyword"  # Search[/dim]')
            console.print(f"[dim]  he info {ka_path}              # View info[/dim]")
            break
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")


@app.command(name="tag")
def tag(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    source: str = typer.Option(..., "--source", help="Source document id to tag"),
    add: list[str] | None = typer.Option(
        None, "--add", help="Tag(s) to add (repeatable)"
    ),
    remove: list[str] | None = typer.Option(
        None, "--remove", help="Tag(s) to remove (repeatable)"
    ),
    list_sources: bool = typer.Option(
        False, "--list", "-l", help="List all sources with their tags"
    ),
):
    """Manage tags on source documents (for scoped search and rollback)."""
    logger.info("command=tag ka_path=%s source=%s", ka_path, source)

    path = validate_ka_with_data(ka_path)
    template, lang = get_template_from_ka(path)
    ka = Template.create(template, lang)
    ka.load(path)

    if list_sources:
        table = Table(title="Source Ledger")
        table.add_column("Source ID", style="cyan")
        table.add_column("Raw Items", justify="right")
        table.add_column("Tags", style="green")
        combined = ka.sources()
        for sid, info_row in sorted(combined.items()):
            tags = ka.source_tags(sid)
            table.add_row(
                sid, str(info_row.get("raw_items", "—")), ", ".join(tags) or "—"
            )
        console.print(table)
        return

    if not add and not remove:
        current = ka.source_tags(source)
        console.print(
            f"[cyan]{source}[/cyan] tags: "
            + (", ".join(current) if current else "[yellow]none[/yellow]")
        )
        console.print("[dim]Use --add/--remove to modify, --list to show all.[/dim]")
        return

    tags = ka.tag_source(source, add=list(add or []), remove=list(remove or []))
    console.print(
        f"[bold green]Tagged![/bold green] {source}: {', '.join(tags) if tags else '(no tags)'}"
    )

    # Persist the ledger change (tags live in the source ledger files).
    ka.dump(path)
    console.print(f"[dim]Saved to {path}[/dim]")


@app.command(name="talk")
def talk(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    query: str | None = typer.Option(None, "--query", "-q", help="Question to ask"),
    top_k: int = typer.Option(3, "--top-k", "-n", help="Number of context items"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="Interactive mode"
    ),
):
    """Chat with Knowledge Abstract."""
    logger.info(
        "command=talk ka_path=%s query=%s interactive=%s",
        ka_path,
        query or "loop",
        interactive,
    )
    validate_config()

    path = validate_ka_with_index(ka_path)
    template, lang = get_template_from_ka(path)

    if interactive:
        console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
        console.print(f"[blue]Template:[/blue] {template}")
        console.print(f"[blue]Top K:[/blue] {top_k}")
        console.print()
    elif query is None:
        console.print(
            "[red]Error:[/red] Please provide a query or use --interactive mode"
        )
        raise typer.Exit(1)
    else:
        console.print(f"[blue]Query:[/blue] {query}")
        console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
        console.print(f"[blue]Top K:[/blue] {top_k}")
        console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading...", total=None)

        try:
            ka = Template.create(template, lang)

            progress.update(task, description="Loading Knowledge Abstract...")
            ka.load(path)

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    if interactive:
        chat_loop(ka, ka_path, top_k=top_k)
    else:
        with console.status("[bold blue]Thinking..."):
            try:
                response = ka.chat(query, top_k=top_k)
                console.print(response.content)

                if response.additional_kwargs.get("retrieved_items"):
                    console.print()
                    console.print("[dim]Retrieved context:[/dim]")
                    items = response.additional_kwargs["retrieved_items"]
                    for i, item in enumerate(items, 1):
                        console.print(f"[dim]{i}. {str(item)[:100]}...[/dim]")
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")
                raise typer.Exit(1)

        console.print()
        console.print("[dim]Continue:[/dim]")
        console.print(
            f"[dim]  he talk {ka_path} -i           # Enter interactive mode[/dim]"
        )
        console.print(f'[dim]  he search {ka_path} "keyword"  # Search more[/dim]')
        console.print(f"[dim]  he show {ka_path}              # Visualize[/dim]")


@app.command(name="feed")
def feed(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    input: str = typer.Argument(..., help="Input file path or '-' for stdin"),
    template: str | None = typer.Option(None, "--template", "-t", help="Template"),
    lang: str | None = typer.Option(None, "--lang", "-l", help="Language"),
    source: str | None = typer.Option(
        None,
        "--source",
        help="Source attribution (document id) for per-document rollback later (he remove --document)",
    ),
    refeed: bool = typer.Option(
        False,
        "--refeed",
        help="Re-ingest even if this source's content hash is unchanged",
    ),
    store_doc: bool = typer.Option(
        True,
        "--store-doc/--no-store-doc",
        help="Archive the source document under documents/ (requires --source)",
    ),
):
    """Append knowledge to an existing Knowledge Abstract."""
    logger.info("command=feed ka_path=%s input=%s", ka_path, input)
    validate_config()

    output_path = validate_ka_path(ka_path)

    metadata = load_ka_metadata(output_path)
    if not metadata:
        console.print(
            f"[red]Error:[/red] Not a valid Knowledge Abstract directory: {ka_path}"
        )
        raise typer.Exit(1)

    if template is None:
        template = metadata.get("template", "general/graph")
    if lang is None:
        lang = metadata.get("lang", "zh")

    console.print(f"[blue]Knowledge Abstract:[/blue] {ka_path}")
    console.print(f"[blue]Input:[/blue] {input}")
    console.print(f"[blue]Template:[/blue] {template} (from metadata)")
    console.print(f"[blue]Language:[/blue] {lang} (from metadata)")
    console.print()

    try:
        ka = Template.create(template, lang)
        console.print(f"[green]Template loaded:[/green] {template}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Loading existing knowledge...", total=None)

        ka.load(output_path)

        progress.update(task, description="Reading input...")
        require_supported_text_input(input)
        text = read_input(input)
        console.print(f"[dim]Input text: {len(text)} characters[/dim]")

        # Change detection: skip unchanged sources without any LLM calls.
        text_hash_to_record = None
        if source:
            text_hash_to_record = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if not refeed:
                recorded = ka.source_content_hash(source)
                if recorded == text_hash_to_record:
                    logger.info("stage=source_unchanged source=%s", source)
                    console.print(
                        f"[yellow]Source '{source}' is unchanged (content hash "
                        "matches) — nothing to do.[/yellow] "
                        "Use --refeed to re-ingest anyway."
                    )
                    raise typer.Exit(0)

        # Archive the source document (provenance evidence, kept across
        # rollbacks; purge with he remove --document ... --purge-documents).
        stored_doc = None
        if store_doc and source:
            from hyperextract.utils.document_store import SourceDocumentStore

            original_name = "stdin.txt" if input == "-" else Path(input).name
            store = SourceDocumentStore(output_path)
            if input == "-":
                stored_doc = store.store_text(source, text, original_name)
            else:
                stored_doc = store.store_file(source, input)
            console.print(f"[dim]Document archived: {stored_doc}[/dim]")

        progress.update(task, description="Appending knowledge...")
        logger.debug("stage=feed_text_invoked")
        ka.feed_text(text, source_id=source, content_hash=text_hash_to_record)
        logger.info("stage=knowledge_appended chars=%d", len(text))

        progress.update(task, description="Saving data...")
        ka.dump(output_path)
        logger.info("stage=data_saved")

    console.print()
    console.print(
        f"[bold green]Success![/bold green] Knowledge appended to {output_path}"
    )
    console.print()
    console.print("[dim]Next steps:[/dim]")
    console.print(f"[dim]  he show {ka_path}              # Visualize[/dim]")
    console.print(
        f"[dim]  he build-index {ka_path}       # Rebuild index (if needed)[/dim]"
    )


@app.command(name="build-index")
def build_index(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    force: bool = typer.Option(False, "--force", "-f", help="Force rebuild"),
):
    """Build vector index for Knowledge Abstract."""
    logger.info("command=build-index ka_path=%s force=%s", ka_path, force)
    validate_config()

    path = validate_ka_with_data(ka_path)

    index_dir = path / "index"
    if index_dir.exists() and any(index_dir.iterdir()) and not force:
        console.print(
            "[yellow]Warning:[/yellow] Index already exists. Use --force to rebuild."
        )
        console.print(f"[dim]Index location: {index_dir}[/dim]")
        raise typer.Exit(0)

    template, lang = get_template_from_ka(path)

    console.print(f"[blue]Template:[/blue] {template}")
    console.print(f"[blue]Language:[/blue] {lang}")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Initializing...", total=None)

        try:
            ka = Template.create(template, lang)

            progress.update(task, description="Loading Knowledge Abstract...")
            ka.load(path)

            if force:
                console.print("[dim]Force rebuild: clearing existing index...[/dim]")
                ka.clear_index()

            progress.update(task, description="Building index...")
            ka.build_index()
            logger.info("stage=index_built")

            progress.update(task, description="Saving index...")
            ka.dump(path)
            logger.info("stage=index_saved")

        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

    console.print()
    console.print(f"[bold green]Success![/bold green] Index built for {ka_path}")
    console.print()
    console.print("[dim]Now you can:[/dim]")
    console.print(f'[dim]  he search {ka_path} "keyword"  # Semantic search[/dim]')
    console.print(f"[dim]  he talk {ka_path} -i           # Interactive chat[/dim]")


@app.command(name="clean")
def clean(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    all_: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Remove the ENTIRE Knowledge Abstract (data, metadata, and index)",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
):
    """Clean a Knowledge Abstract: remove its search index, or the whole KA with --all."""
    import shutil

    logger.info("command=clean ka_path=%s all=%s", ka_path, all_)

    # validate_ka_with_data ensures the target really is a KA (has data.json),
    # so --all never rmtree's an arbitrary mistyped directory.
    path = validate_ka_with_data(ka_path)

    if all_:
        target = path
        what = f"the ENTIRE Knowledge Abstract '{path}' (data, metadata, index)"
    else:
        target = path / "index"
        if not target.exists() or not any(target.iterdir()):
            console.print("[yellow]Nothing to clean:[/yellow] no index found.")
            console.print(
                f"[dim]Tip: use --all to remove the whole KA at {path}.[/dim]"
            )
            raise typer.Exit(0)
        what = f"the search index of '{path}'"

    console.print(f"[yellow]This will permanently delete[/yellow] {what}.")
    if not yes and not typer.confirm("Are you sure?"):
        console.print("[dim]Aborted. Nothing was deleted.[/dim]")
        raise typer.Exit(0)

    try:
        shutil.rmtree(target)
    except Exception as e:
        console.print(f"[red]Error:[/red] Failed to delete {target}: {e}")
        raise typer.Exit(1)

    console.print(f"[bold green]Cleaned![/bold green] Removed {target}")
    if not all_:
        console.print(f"[dim]Rebuild it with: he build-index {ka_path}[/dim]")


@app.command(name="remove")
def remove_items(
    ka_path: str = typer.Argument(..., help="Knowledge Abstract directory"),
    node: list[str] = typer.Option(
        None, "--node", help="Node key(s) to delete (hard delete, removes orphan edges)"
    ),
    edge: list[str] = typer.Option(
        None, "--edge", help="Edge key(s) to delete (hard delete)"
    ),
    edit_node_key: str = typer.Option(
        None, "--edit-node", help="Node key to soft-edit (LLM rewrites it minus --fact)"
    ),
    edit_edge_key: str = typer.Option(
        None, "--edit-edge", help="Edge key to soft-edit (LLM rewrites it minus --fact)"
    ),
    fact: str = typer.Option(
        None, "--fact", help="Fact to remove from the --edit-node/--edit-edge item"
    ),
    instruction: str = typer.Option(
        None, "--instruction", help="Free-form edit instruction (instead of --fact)"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Preview changes without persisting them"
    ),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Back up data.json before writing"
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip the confirmation prompt"),
    document: str | None = typer.Option(
        None,
        "--document",
        help="Remove all knowledge contributed by this source document "
        "(requires the KA to have been fed with --source)",
    ),
    strategy: str = typer.Option(
        "exact",
        "--strategy",
        help="Rollback strategy for --document: exact (re-merge surviving "
        "sources) or touched (delete all affected keys)",
    ),
    purge_documents: bool = typer.Option(
        False,
        "--purge-documents",
        help="With --document: also delete the archived source document file",
    ),
):
    """Delete nodes/edges by key, remove a fact (LLM-assisted), or roll back a whole document.

    Hard delete:     he remove ./ka --node Apple --edge "Apple-partner-Google"
    Soft delete:     he remove ./ka --edit-node Apple --fact "founded by Steve Jobs"
    Document rollback: he remove ./ka --document ./docs/old-paper.md
    """
    import shutil
    from datetime import datetime

    logger.info(
        "command=remove ka_path=%s dry_run=%s document=%s",
        ka_path,
        dry_run,
        document,
    )

    hard_targets = list(node or []) + list(edge or [])
    soft_target = edit_node_key or edit_edge_key
    if (hard_targets or soft_target or document) and sum(
        bool(x) for x in (hard_targets, soft_target, document)
    ) > 1:
        console.print(
            "[red]Error:[/red] Choose ONE of: --node/--edge (hard delete), "
            "--edit-node/--edit-edge (soft delete), or --document "
            "(whole-document rollback)."
        )
        raise typer.Exit(1)
    if soft_target and not fact and not instruction:
        console.print("[red]Error:[/red] Soft delete needs --fact or --instruction.")
        raise typer.Exit(1)
    if document and not (Path(document).name or document):
        pass  # unreachable; keeps option semantics explicit
    if not hard_targets and not soft_target and not document:
        console.print(
            "[yellow]Nothing to do.[/yellow] "
            "Use --node/--edge to delete items, --edit-node/--edit-edge "
            "with --fact to remove a single fact, or --document to roll back "
            "a whole source document."
        )
        raise typer.Exit(0)

    path = validate_ka_with_data(ka_path)
    template, lang = get_template_from_ka(path)
    ka = Template.create(template, lang)
    ka.load(path)

    if document and not hasattr(ka, "remove_source"):
        console.print(
            f"[red]Error:[/red] Document rollback requires a source-tracked "
            f"knowledge abstract (graph-family or chunk-based). "
            f"'{template}' produced a {type(ka).__name__}, which does not "
            "support it."
        )
        raise typer.Exit(1)
    if not document and not hasattr(ka, "remove_nodes"):
        console.print(
            f"[red]Error:[/red] `he remove` keyed deletion supports graph-family "
            f"knowledge abstracts (graph / hypergraph / temporal / spatial). "
            f"'{template}' produced a {type(ka).__name__}, which does not "
            "support keyed deletion. For lists/sets, use the Python API "
            "`ka.remove(item)`; or rebuild the KA with `he clean --all`."
        )
        raise typer.Exit(1)

    try:
        if document:
            if strategy not in ("exact", "touched"):
                console.print(
                    f"[red]Error:[/red] Unknown strategy: {strategy!r} "
                    "(use exact or touched)."
                )
                raise typer.Exit(1)
            try:
                report = ka.remove_source(document, strategy=strategy)
            except KeyError:
                console.print(
                    f"[yellow]Nothing matched — no recorded contributions "
                    f"for source '{document}'. Was the KA fed with "
                    f"--source?[/yellow]"
                )
                raise typer.Exit(0)
        elif hard_targets:
            report = {}
            if node:
                report.update(ka.remove_nodes(*node))
            if edge:
                report.update(ka.remove_edges(*edge))
        else:
            if not yes and not dry_run:
                console.print(
                    "[yellow]Soft delete rewrites the item with an LLM.[/yellow] "
                    "Use --dry-run to preview, -y to skip this prompt."
                )
                if not typer.confirm("Apply the edit?"):
                    console.print("[dim]Aborted. Nothing was changed.[/dim]")
                    raise typer.Exit(0)
            if edit_node_key:
                report = ka.edit_node(
                    edit_node_key,
                    remove_fact=fact,
                    instruction=instruction,
                    dry_run=dry_run,
                )
            else:
                report = ka.edit_edge(
                    edit_edge_key,
                    remove_fact=fact,
                    instruction=instruction,
                    dry_run=dry_run,
                )
    except KeyError as e:
        console.print(f"[red]Error:[/red] {e}")
        raise typer.Exit(1)
    except ValueError as e:
        console.print(f"[red]Rejected:[/red] {e}")
        raise typer.Exit(1)

    console.print()
    if document:
        if purge_documents:
            from hyperextract.utils.document_store import SourceDocumentStore

            removed_files = SourceDocumentStore(path).purge(document)
            for f in removed_files:
                console.print(f"[dim]Archived document deleted: {f}[/dim]")

        table = Table(title=f"Document Rollback Report — {document}")
        table.add_column("Field")
        table.add_column("Items")
        for field, items in report.items():
            if field in ("index_patched", "source_id", "strategy"):
                continue
            table.add_row(field, "\n".join(items) if items else "—")
        console.print(table)
        changed_any = any(
            report.get(key)
            for key in (
                "removed_nodes",
                "remerged_nodes",
                "removed_edges",
                "remerged_edges",
                "removed_chunks",
                "remerged_chunks",
                "removed_items",
                "remerged_items",
            )
        )
        if not changed_any:
            console.print(
                "[yellow]Nothing matched — this document has no recorded "
                "contributions. Was the KA fed with --source?[/yellow]"
            )
            raise typer.Exit(0)
    elif hard_targets:
        table = Table(title="Removal Report")
        table.add_column("Field")
        table.add_column("Items")
        for field, items in report.items():
            if field == "index_patched":
                continue
            table.add_row(field, "\n".join(items) if items else "—")
        console.print(table)
        removed_any = any(
            report.get(key)
            for key in ("removed_nodes", "removed_edges", "removed_orphan_edges")
        )
        if not removed_any:
            console.print("[yellow]Nothing matched — no changes made.[/yellow]")
            raise typer.Exit(0)
    else:
        changed = report["changed"]
        if not changed:
            console.print(
                "[yellow]No change:[/yellow] the fact was not found in the item "
                "(the LLM returned it unchanged). Nothing was written."
            )
            raise typer.Exit(0)
        console.print(
            f"[bold]Old item:[/bold]\n{report['old'].model_dump_json(indent=2)}"
        )
        console.print()
        console.print(f"[bold]{'Proposed' if dry_run else 'New'} item:[/bold]")
        console.print(report["new"].model_dump_json(indent=2))

    if dry_run:
        console.print(
            "\n[dim]Dry run — nothing was persisted. "
            "Re-run without --dry-run to apply.[/dim]"
        )
        raise typer.Exit(0)

    if backup:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = path / f"data.json.bak.{stamp}"
        shutil.copy2(path / "data.json", backup_path)
        console.print(f"[dim]Backup written: {backup_path}[/dim]")

    ka.dump(path)

    if report.get("index_patched", False):
        # The vector index was patched in place and persisted by dump() —
        # search stays usable without a rebuild.
        console.print("[dim]Search index patched in place — no rebuild needed.[/dim]")
    else:
        # No index was built (or patching fell back): drop any stale on-disk
        # index so search never serves deleted knowledge.
        index_dir = path / "index"
        if index_dir.exists():
            shutil.rmtree(index_dir)
        console.print(
            f"[dim]Rebuild the search index with: he build-index {ka_path}[/dim]"
        )

    console.print(f"[bold green]Done![/bold green] Knowledge Abstract updated: {path}")
