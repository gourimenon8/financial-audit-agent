"""
Markdown report writer.
Saves the full audit to a .md file.
"""

from datetime import datetime
from pathlib import Path


def save_report(
    stats: dict,
    category_breakdown: dict,
    subscriptions: list[dict],
    anomalies: list[dict],
    summary: str,
    output_path: str = None,
) -> str:
    """
    Write the full audit report to a markdown file.
    Returns the path of the saved file.
    """
    if output_path is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = f"financial_audit_{timestamp}.md"

    lines = []
    lines.append("# Financial Audit Report")
    lines.append(f"\n_Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}_\n")
    lines.append("---\n")

    # Overview
    lines.append("## Spending Overview\n")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Date Range | {stats['date_range']} |")
    lines.append(f"| Total Transactions | {stats['total_transactions']} |")
    lines.append(f"| Total Income | +${stats['total_income']:,.2f} |")
    lines.append(f"| Total Spent | ${stats['total_spent']:,.2f} |")
    lines.append(f"| Net | ${stats['net']:,.2f} |")
    lines.append(f"| Largest Single Expense | ${abs(stats['largest_expense']):,.2f} |")
    lines.append("")

    # Categories
    lines.append("## Spending by Category\n")
    lines.append("| Category | Transactions | Total Spent | Avg per Transaction |")
    lines.append("|----------|-------------|-------------|---------------------|")

    sorted_cats = sorted(
        category_breakdown.items(),
        key=lambda x: abs(x[1]["total"]),
        reverse=True,
    )
    for cat, data in sorted_cats:
        if cat in ("Income", "Transfer"):
            continue
        lines.append(
            f"| {cat} | {data['count']} | ${abs(data['total']):,.2f} | ${abs(data['avg']):,.2f} |"
        )
    lines.append("")

    # Subscriptions
    lines.append("## Detected Subscriptions\n")
    if subscriptions:
        lines.append("| Service | Frequency | Per Charge | Monthly Cost |")
        lines.append("|---------|-----------|------------|--------------|")
        total_monthly = 0.0
        for sub in subscriptions:
            monthly = sub.get("estimated_monthly_cost", sub.get("amount_per_charge", 0))
            total_monthly += monthly
            lines.append(
                f"| {sub['name']} | {sub.get('frequency', 'monthly')} "
                f"| ${sub['amount_per_charge']:,.2f} | ${monthly:,.2f} |"
            )
        lines.append(f"\n**Total Monthly Subscriptions: ${total_monthly:,.2f}/mo**\n")
    else:
        lines.append("_No recurring subscriptions detected._\n")

    # Anomalies
    lines.append("## Flagged Anomalies\n")
    if anomalies:
        for a in anomalies:
            lines.append(f"- **{a['description']}** — ${abs(a['amount']):,.2f}: {a['reason']}")
        lines.append("")
    else:
        lines.append("_No anomalies detected._\n")

    # AI Summary
    lines.append("## AI Financial Analysis\n")
    lines.append(summary)
    lines.append("")

    content = "\n".join(lines)
    Path(output_path).write_text(content, encoding="utf-8")
    return output_path
