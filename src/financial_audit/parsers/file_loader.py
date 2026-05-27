"""
Universal file loader.
Handles CSV, XLSX, XLS, TXT in any format.
Aggregates large files before analysis.
"""

import pandas as pd
import numpy as np
from pathlib import Path


MAX_ROWS_FOR_CLAUDE = 500  # rows sent directly to Claude
LARGE_FILE_THRESHOLD = 10_000  # rows above this get aggregated first


def load_any_file(path: str, filename: str) -> pd.DataFrame:
    """
    Load any tabular financial file regardless of format.
    Returns a clean DataFrame.
    """
    suffix = Path(filename).suffix.lower()

    if suffix in (".xlsx", ".xls"):
        df = pd.read_excel(path)
    elif suffix == ".txt":
        # Try tab-separated, then comma, then any whitespace
        for sep in ["\t", ",", ";"]:
            try:
                df = pd.read_csv(path, sep=sep)
                if len(df.columns) > 1:
                    break
            except Exception:
                continue
        else:
            df = pd.read_csv(path, sep=None, engine="python")
    else:
        # CSV — try common separators
        for sep in [",", ";", "\t", "|"]:
            try:
                df = pd.read_csv(path, sep=sep)
                if len(df.columns) > 1:
                    break
            except Exception:
                continue

    # Clean up
    df.columns = df.columns.str.strip().str.replace("\n", " ")
    df = df.dropna(how="all").reset_index(drop=True)
    return df


def get_file_profile(df: pd.DataFrame) -> dict:
    """
    Generate a statistical profile of the dataframe.
    Used to give Claude context without sending all rows.
    """
    profile = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "columns": [],
        "sample_rows": df.head(10).fillna("").to_dict(orient="records"),
    }

    for col in df.columns:
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isna().sum()),
            "unique_count": int(df[col].nunique()),
        }

        if pd.api.types.is_numeric_dtype(df[col]):
            col_info.update({
                "min": round(float(df[col].min()), 4) if not df[col].isna().all() else None,
                "max": round(float(df[col].max()), 4) if not df[col].isna().all() else None,
                "mean": round(float(df[col].mean()), 4) if not df[col].isna().all() else None,
                "std": round(float(df[col].std()), 4) if not df[col].isna().all() else None,
                "sample_values": df[col].dropna().head(5).tolist(),
            })
        else:
            col_info["sample_values"] = df[col].dropna().head(5).tolist()
            col_info["top_values"] = df[col].value_counts().head(5).to_dict()

        profile["columns"].append(col_info)

    return profile


def aggregate_large_file(df: pd.DataFrame, analysis_plan: dict) -> dict:
    """
    For large files, compute aggregations instead of sampling.
    Returns a dict of summary statistics Claude can analyze.
    """
    aggregation = {
        "total_rows": len(df),
        "columns": list(df.columns),
    }

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()

    # Numeric summaries
    if numeric_cols:
        aggregation["numeric_summary"] = (
            df[numeric_cols]
            .describe()
            .round(4)
            .to_dict()
        )

        # Distribution info
        aggregation["outliers"] = {}
        for col in numeric_cols:
            q1 = df[col].quantile(0.25)
            q3 = df[col].quantile(0.75)
            iqr = q3 - q1
            outlier_count = int(((df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)).sum())
            if outlier_count > 0:
                aggregation["outliers"][col] = {
                    "count": outlier_count,
                    "pct": round(outlier_count / len(df) * 100, 2),
                    "threshold_low": round(q1 - 1.5 * iqr, 4),
                    "threshold_high": round(q3 + 1.5 * iqr, 4),
                }

    # Categorical summaries
    if categorical_cols:
        aggregation["categorical_summary"] = {}
        for col in categorical_cols[:10]:  # cap at 10 cols
            vc = df[col].value_counts()
            aggregation["categorical_summary"][col] = {
                "unique_values": int(df[col].nunique()),
                "top_10": vc.head(10).to_dict(),
                "null_count": int(df[col].isna().sum()),
            }

    # Correlations between numeric columns
    if len(numeric_cols) > 1:
        corr = df[numeric_cols].corr().round(3)
        # Only keep strong correlations
        strong = {}
        for i, row in corr.iterrows():
            for j, val in row.items():
                if i != j and abs(val) > 0.5:
                    strong[f"{i} vs {j}"] = float(val)
        if strong:
            aggregation["strong_correlations"] = strong

    aggregation["sample_rows"] = df.head(20).fillna("").to_dict(orient="records")

    return aggregation
