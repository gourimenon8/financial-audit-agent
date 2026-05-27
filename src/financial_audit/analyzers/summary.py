"""
Financial summary generator.
Claude writes the final audit narrative and recommendations.
"""

import json
import anthropic
import pandas as pd


def generate_summary(
    df: pd.DataFrame,
    stats: dict,
    category_breakdown: dict,
    anomalies: list[dict],
    subscriptions: list[dict],
    client: anthropic.Anthropic,
) -> str:
    """
    Generate a financial health summary with actionable recommendations.
    Returns a markdown-formatted string.
    """
    prompt = """You are a personal finance advisor writing a financial health audit report.

## Spending Overview
{}

## Spending by Category
{}

## Flagged Anomalies
{}

## Detected Subscriptions
{}

Write a concise financial health audit with these sections:
1. **Executive Summary** (3-4 sentences on overall financial health)
2. **Key Insights** (3-5 bullet points on notable patterns)
3. **Subscription Audit** (total monthly subscription spend, any worth reconsidering)
4. **Savings Opportunities** (3 specific, actionable recommendations)
5. **Risk Flags** (anything that needs immediate attention)

Be direct, specific, and use actual numbers from the data.
Format your response in clean markdown.""".format(
        json.dumps(stats, indent=2),
        json.dumps(category_breakdown, indent=2),
        json.dumps(anomalies, indent=2) if anomalies else "None detected",
        json.dumps(subscriptions, indent=2) if subscriptions else "None detected",
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
