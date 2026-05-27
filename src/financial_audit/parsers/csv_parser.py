"""
CSV parser and transaction normalizer.
Reads bank statement CSVs from a folder and returns a unified DataFrame.
"""

import os
import pandas as pd
from pathlib import Path
from typing import Optional


# Common column name mappings across different bank export formats
COLUMN_ALIASES = {
    "date": ["date", "transaction date", "trans date", "posted date", "value date"],
    "description": ["description", "merchant", "payee", "memo", "details", "name"],
    "amount": ["amount", "transaction amount", "debit", "value"],
    "type": ["type", "transaction type", "credit/debit"],
}


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Remap varied column names to a standard schema."""
    col_map = {}
    for standard, aliases in COLUMN_ALIASES.items():
        for col in df.columns:
            if col.strip().lower() in aliases:
                col_map[col] = standard
                break
    return df.rename(columns=col_map)


def _normalize_amounts(df: pd.DataFrame) -> pd.DataFrame:
    """Ensure amounts are floats; infer sign from type column if needed."""
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce")

    if "type" in df.columns:
        # Some banks export positive numbers with a type column
        debit_mask = df["type"].str.lower().str.contains("debit", na=False)
        df.loc[debit_mask & (df["amount"] > 0), "amount"] *= -1

    return df


def load_transactions(folder: str) -> Optional[pd.DataFrame]:
    """
    Load all CSV files from a folder and return a unified, normalized DataFrame.

    Args:
        folder: Path to folder containing bank statement CSVs

    Returns:
        DataFrame with columns: date, description, amount, type, source_file
        Returns None if no valid CSVs found.
    """
    folder_path = Path(folder)
    if not folder_path.exists():
        raise FileNotFoundError(f"Folder not found: {folder}")

    csv_files = list(folder_path.glob("*.csv"))
    if not csv_files:
        raise ValueError(f"No CSV files found in {folder}")

    frames = []
    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.strip()
            df = _normalize_columns(df)

            required = {"date", "description", "amount"}
            if not required.issubset(df.columns):
                print(f"  Warning: {csv_path.name} missing columns {required - set(df.columns)}, skipping")
                continue

            df = _normalize_amounts(df)
            df["source_file"] = csv_path.name
            df["date"] = pd.to_datetime(df["date"], infer_datetime_format=True, errors="coerce")
            df = df.dropna(subset=["date", "amount"])
            frames.append(df)

        except Exception as e:
            print(f"  Warning: could not read {csv_path.name}: {e}")

    if not frames:
        return None

    combined = pd.concat(frames, ignore_index=True)
    combined = combined.sort_values("date").reset_index(drop=True)
    return combined


def summarize(df: pd.DataFrame) -> dict:
    """Compute basic stats for the agent context."""
    debits = df[df["amount"] < 0]
    credits = df[df["amount"] > 0]

    return {
        "total_transactions": len(df),
        "date_range": f"{df['date'].min().date()} to {df['date'].max().date()}",
        "total_spent": round(debits["amount"].sum(), 2),
        "total_income": round(credits["amount"].sum(), 2),
        "net": round(df["amount"].sum(), 2),
        "largest_expense": round(debits["amount"].min(), 2),
        "avg_daily_spend": round(debits.groupby(df["date"].dt.date)["amount"].sum().mean(), 2),
    }
