"""
Subscription detector.
Identifies recurring charges and estimates monthly cost.
"""

import json
import anthropic
import pandas as pd


def detect_subscriptions(df: pd.DataFrame, client: anthropic.Anthropic) -> list[dict]:
    """
    Ask Claude to identify recurring subscription charges.
    Returns a list of detected subscriptions with frequency and monthly cost.
    """
    expense_df = df[df["amount"] < 0].copy()

    transactions = []
    for _, row in expense_df.iterrows():
        transactions.append({
            "id": int(row.name),
            "date": str(row["date"].date()),
            "description": str(row["description"]),
            "amount": float(row["amount"]),
        })

    prompt = """You are a financial analyst identifying subscription and recurring charges.

Expense transactions:
{}

Identify all recurring subscriptions or memberships. Look for:
- Streaming services (Netflix, Hulu, Spotify, Disney+, etc.)
- SaaS tools (Adobe, ChatGPT, Notion, etc.)
- Cloud storage (iCloud, Google One, Dropbox)
- Gym or fitness memberships
- Any charge appearing multiple times at the same or similar amount

Respond ONLY with a JSON array:
[{{
  "name": "<service name>",
  "amount_per_charge": <amount as positive number>,
  "frequency": "monthly" or "annual" or "weekly",
  "estimated_monthly_cost": <number>,
  "transaction_ids": [<id>, <id>, ...]
}}]

If no subscriptions found, return [].
No explanation, no markdown, just the JSON array.""".format(
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
