"""
Claude-powered transaction categorizer.
One LLM call to categorize all transactions at once.
"""

import json
import anthropic
import pandas as pd


CATEGORIES = [
    "Groceries",
    "Dining & Restaurants",
    "Coffee & Cafes",
    "Transport & Ride-share",
    "Gas & Auto",
    "Subscriptions & Streaming",
    "Shopping & Retail",
    "Health & Pharmacy",
    "Fitness",
    "Rent & Housing",
    "Utilities",
    "Income",
    "Transfer",
    "Entertainment",
    "Travel",
    "Other",
]


def categorize_transactions(df: pd.DataFrame, client: anthropic.Anthropic) -> pd.DataFrame:
    """
    Use Claude to categorize all transactions in a single API call.
    Returns the DataFrame with a new 'category' column.
    """
    transactions = []
    for _, row in df.iterrows():
        transactions.append({
            "id": int(row.name),
            "description": str(row["description"]),
            "amount": float(row["amount"]),
        })

    prompt = """You are a financial analyst categorizing bank transactions.

Given these transactions, assign each one a category from this list:
{}

Transactions:
{}

Rules:
- Positive amounts are income or credits — use "Income" or "Transfer"
- Negative amounts are expenses
- Be consistent: all Starbucks entries should be "Coffee & Cafes"
- Subscriptions include streaming, SaaS, cloud storage, membership services

Respond ONLY with a JSON array like:
[{{"id": 0, "category": "Groceries"}}, ...]

No explanation, no markdown, just the JSON array.""".format(
        json.dumps(CATEGORIES, indent=2),
        json.dumps(transactions, indent=2),
    )

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        raw = raw.rsplit("```", 1)[0].strip()

    results = json.loads(raw)
    id_to_category = {item["id"]: item["category"] for item in results}
    df["category"] = df.index.map(lambda i: id_to_category.get(i, "Other"))
    return df
