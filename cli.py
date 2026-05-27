"""
Financial Audit Agent — CLI entry point.

Usage:
    python cli.py ./sample_data
    python cli.py ./my_statements --output report.md
    python cli.py ./my_statements --output report.md --api-key sk-ant-...
"""

import typer
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer(
    help="Financial Audit Agent — analyze bank statement CSVs with Claude.",
    add_completion=False,
)


@app.command()
def audit(
    folder: str = typer.Argument(
        ...,
        help="Path to folder containing bank statement CSV files",
    ),
    output: str = typer.Option(
        None,
        "--output", "-o",
        help="Output path for the markdown report (default: financial_audit_<timestamp>.md)",
    ),
    api_key: str = typer.Option(
        None,
        "--api-key",
        help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var)",
        envvar="ANTHROPIC_API_KEY",
    ),
):
    """Run a full financial audit on all CSV files in FOLDER."""
    folder_path = Path(folder)
    if not folder_path.exists():
        typer.echo(f"Error: folder '{folder}' does not exist.", err=True)
        raise typer.Exit(1)

    from src.financial_audit.agent import run_audit
    run_audit(folder=folder, output=output, api_key=api_key)


if __name__ == "__main__":
    app()
