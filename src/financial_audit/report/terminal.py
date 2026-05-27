"""
Rich terminal output for the financial audit report.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from rich import box
from rich.text import Text

console = Console()


def print_header():
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Financial Audit Agent[/bold cyan]\n"
        "[dim]Powered by Claude[/dim]",
        border_style="cyan",
    ))
    console.print()


def print_step(step: int, total: int, message: str):
    console.print(f"[dim]Step {step}/{total}[/dim] [bold]{message}[/bold]...")


def print_stats(stats: dict):
    console.print()
    console.print("[bold underline]Spending Overview[/bold underline]")

    table = Table(box=box.SIMPLE, show_header=False, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold")

    table.add_row("Date Range", stats["date_range"])
    table.add_row("Total Transactions", str(stats["total_transactions"]))
    table.add_row("Total Income", f"[green]+${stats['total_income']:,.2f}[/green]")
    table.add_row("Total Spent", f"[red]${stats['total_spent']:,.2f}[/red]")
    table.add_row("Net", (
        f"[green]+${stats['net']:,.2f}[/green]"
        if stats["net"] >= 0
        else f"[red]${stats['net']:,.2f}[/red]"
    ))
    table.add_row("Largest Single Expense", f"[red]${abs(stats['largest_expense']):,.2f}[/red]")

    console.print(table)


def print_categories(category_breakdown: dict):
    console.print()
    console.print("[bold underline]Spending by Category[/bold underline]")

    table = Table(box=box.SIMPLE, padding=(0, 2))
    table.add_column("Category", style="cyan")
    table.add_column("Transactions", justify="right")
    table.add_column("Total Spent", justify="right")
    table.add_column("Avg per Transaction", justify="right")

    sorted_cats = sorted(
        category_breakdown.items(),
        key=lambda x: abs(x[1]["total"]),
        reverse=True,
    )

    for cat, data in sorted_cats:
        if cat in ("Income", "Transfer"):
            continue
        table.add_row(
            cat,
            str(data["count"]),
            f"[red]${abs(data['total']):,.2f}[/red]",
            f"${abs(data['avg']):,.2f}",
        )

    console.print(table)


def print_subscriptions(subscriptions: list[dict]):
    console.print()
    console.print("[bold underline]Detected Subscriptions[/bold underline]")

    if not subscriptions:
        console.print("[dim]  No recurring subscriptions detected.[/dim]")
        return

    table = Table(box=box.SIMPLE, padding=(0, 2))
    table.add_column("Service", style="cyan")
    table.add_column("Frequency")
    table.add_column("Per Charge", justify="right")
    table.add_column("Monthly Cost", justify="right")

    total_monthly = 0.0
    for sub in subscriptions:
        monthly = sub.get("estimated_monthly_cost", sub.get("amount_per_charge", 0))
        total_monthly += monthly
        table.add_row(
            sub["name"],
            sub.get("frequency", "monthly"),
            f"${sub['amount_per_charge']:,.2f}",
            f"[yellow]${monthly:,.2f}[/yellow]",
        )

    table.add_section()
    table.add_row(
        "[bold]TOTAL[/bold]", "", "",
        f"[bold yellow]${total_monthly:,.2f}/mo[/bold yellow]",
    )

    console.print(table)


def print_anomalies(anomalies: list[dict]):
    console.print()
    console.print("[bold underline]Flagged Anomalies[/bold underline]")

    if not anomalies:
        console.print("[dim]  No anomalies detected.[/dim]")
        return

    for a in anomalies:
        console.print(
            f"  [red]⚠[/red]  [bold]{a['description']}[/bold] "
            f"[red]${abs(a['amount']):,.2f}[/red] — [dim]{a['reason']}[/dim]"
        )


def print_summary(summary_md: str):
    console.print()
    console.print("[bold underline]AI Financial Analysis[/bold underline]")
    console.print()
    console.print(Markdown(summary_md))


def print_saved(path: str):
    console.print()
    console.print(Panel(
        f"[green]Report saved to:[/green] [bold]{path}[/bold]",
        border_style="green",
    ))
    console.print()
