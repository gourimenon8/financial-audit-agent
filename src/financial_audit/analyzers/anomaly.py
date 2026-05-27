"""
Anomaly detector.
Uses Claude to flag unusual transactions given spending context.
"""

import json
import anthropic
import pandas as pd


def detect_anomalies(df: pd.DataFrame, client: anthropic.Anthropic) -> list[dict]:
    """
    Ask Claude to identify anomalous transactions.
    Returns a list of flagged transactions with reasons.
    """
    # Give Claude category-level stats for context
    expense_df = df[df["amount"] < 0].copy()
    category_stats = (
        expense_df.groupby("category")["amount"]
        .agg(["count", "sum", "mean", "min"])
        .round(2)
        .reset_index()
        .rename(columns={"count": "num_transactions", "sum": "total", "mean": "avg", "min": "largest"})
    )

    transactions = []
    for _, row in expense_df.iterrows():
        transactions.append({
            "id": int(row.name),
            "date": str(row["date"].date()),
            "description": str(row["description"]),
            "amount": float(row["amount"]),
            "category": str(row["category"]),
        })

    prompt = """You are a financial analyst reviewing bank transactions for anomalies.

Category spending summary:
{}

All expense transactions:
{}

Identify transactions that are anomalous. Look for:
- Amounts significantly higher than the category average
- One-off large purchases that stand out
- Suspicious or unclear merchant names
- Duplicate or near-duplicate charges

Respond ONLY with a JSON array of flagged transactions:
[{{
  "id": <transaction id>,
  "description": "<merchant>",
  "amount": <amount>,
  "reason": "<brief explanation of why it is anomalous>"
}}]

If nothing is anomalous, return an empty array [].
No explanation, no markdown, just the JSON array.""".format(
        category_stats.to_string(index=False),
        json.dumps(transactions, indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)
