"""
Financial Audit Agent.
Orchestrates the full audit pipeline: load → categorize → analyze → report.
"""

import anthropic
import pandas as pd

from .parsers.csv_parser import load_transactions, summarize
from .analyzers.categorizer import categorize_transactions
from .analyzers.anomaly import detect_anomalies
from .analyzers.subscriptions import detect_subscriptions
from .analyzers.summary import generate_summary
from .report import terminal as term
from .report.markdown_writer import save_report


def run_audit(folder: str, output: str = None, api_key: str = None):
    """
    Run the full financial audit pipeline.

    Args:
        folder:  Path to folder containing bank statement CSVs
        output:  Optional output path for the markdown report
        api_key: Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
    """
    client = anthropic.Anthropic(api_key=api_key) if api_key else anthropic.Anthropic()

    term.print_header()

    # Step 1: Load transactions
    term.print_step(1, 4, "Loading transactions")
    df = load_transactions(folder)
    if df is None or df.empty:
        term.console.print("[red]No transactions found. Check your CSV files.[/red]")
        return

    stats = summarize(df)
    term.console.print(f"  [green]Loaded {stats['total_transactions']} transactions[/green] "
                       f"({stats['date_range']})")

    # Step 2: Categorize
    term.print_step(2, 4, "Categorizing transactions with Claude")
    df = categorize_transactions(df, client)
    term.console.print(f"  [green]Categorized into {df['category'].nunique()} categories[/green]")

    # Build category breakdown
    expense_df = df[df["amount"] < 0]
    category_breakdown = (
        expense_df.groupby("category")["amount"]
        .agg(["count", "sum", "mean"])
        .round(2)
        .rename(columns={"count": "count", "sum": "total", "mean": "avg"})
        .to_dict(orient="index")
    )

    # Step 3: Detect anomalies and subscriptions
    term.print_step(3, 4, "Detecting anomalies and subscriptions with Claude")
    anomalies = detect_anomalies(df, client)
    subscriptions = detect_subscriptions(df, client)
    term.console.print(
        f"  [green]Found {len(anomalies)} anomalies, "
        f"{len(subscriptions)} subscriptions[/green]"
    )

    # Step 4: Generate summary
    term.print_step(4, 4, "Generating financial summary with Claude")
    summary = generate_summary(df, stats, category_breakdown, anomalies, subscriptions, client)
    term.console.print("  [green]Summary complete[/green]")

    # Print full report to terminal
    term.print_stats(stats)
    term.print_categories(category_breakdown)
    term.print_subscriptions(subscriptions)
    term.print_anomalies(anomalies)
    term.print_summary(summary)

    # Save markdown report
    saved_path = save_report(stats, category_breakdown, subscriptions, anomalies, summary, output)
    term.print_saved(saved_path)
