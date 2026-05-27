# Financial Audit Agent

A CLI agent that audits your bank statements using Claude. Drop in a folder of CSV exports, get back a full financial health report — in your terminal and as a markdown file.

```
$ python cli.py ./my_statements

  Financial Audit Agent
  Powered by Claude

Step 1/4 Loading transactions...
  Loaded 58 transactions (2024-01-02 to 2024-02-28)
Step 2/4 Categorizing transactions with Claude...
  Categorized into 12 categories
Step 3/4 Detecting anomalies and subscriptions with Claude...
  Found 2 anomalies, 7 subscriptions
Step 4/4 Generating financial summary with Claude...

  Spending Overview ...
  Spending by Category ...
  Subscriptions: $136.93/mo ...
  AI Financial Analysis ...

  Report saved to: financial_audit_20240301_143022.md
```

---

## What It Does

The agent runs 4 sequential Claude API calls:

| Step | Task | What Claude Does |
|------|------|-----------------|
| 1 | Load | Reads + normalizes CSVs (no LLM) |
| 2 | Categorize | Labels every transaction (Groceries, Subscriptions, etc.) |
| 3 | Analyze | Flags anomalies + detects recurring charges |
| 4 | Summarize | Writes narrative insights + savings recommendations |

---

## Architecture

```
financial-audit-agent/
├── cli.py                          # Entry point (typer CLI)
├── src/financial_audit/
│   ├── agent.py                    # Orchestrator — runs the full pipeline
│   ├── parsers/
│   │   └── csv_parser.py          # CSV loading + normalization
│   ├── analyzers/
│   │   ├── categorizer.py         # LLM: transaction categorization
│   │   ├── anomaly.py             # LLM: anomaly detection
│   │   ├── subscriptions.py       # LLM: recurring charge detection
│   │   └── summary.py             # LLM: financial narrative + advice
│   └── report/
│       ├── terminal.py            # Rich terminal output
│       └── markdown_writer.py     # Markdown report writer
└── sample_data/
    └── transactions.csv           # Sample data to test with
```

---

## CSV Format

The agent auto-detects common bank export formats. Your CSV needs at minimum:

| Column | Required | Notes |
|--------|----------|-------|
| `date` | Yes | Any common date format |
| `description` | Yes | Merchant / transaction name |
| `amount` | Yes | Negative = expense, positive = income |
| `type` | No | debit / credit — used to infer sign if needed |

Common aliases are handled automatically (`transaction date`, `payee`, `merchant`, etc.).

---

## Installation

**Requirements:** Python 3.11+

```bash
git clone https://github.com/yourhandle/financial-audit-agent.git
cd financial-audit-agent
python3.11 -m venv venv
source venv/bin/activate    # Mac/Linux
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

---

## Configuration

Copy `.env.example` to `.env` and add your Anthropic API key:

```bash
cp .env.example .env
```

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

---

## Usage

```bash
# Run on the included sample data
python cli.py ./sample_data

# Run on your own statements
python cli.py ./my_bank_exports

# Specify output file
python cli.py ./my_bank_exports --output my_report.md

# Pass API key directly
python cli.py ./my_bank_exports --api-key sk-ant-...
```

---

## Tech Stack

- [`anthropic`](https://github.com/anthropics/anthropic-sdk-python) — Claude API SDK
- [`pandas`](https://pandas.pydata.org/) — CSV parsing and data aggregation
- [`rich`](https://github.com/Textualize/rich) — terminal formatting
- [`typer`](https://typer.tiangolo.com/) — CLI interface
- [`python-dotenv`](https://pypi.org/project/python-dotenv/) — environment config

---

## License

MIT

---

## Web App (Streamlit)

A browser-based version is also included — no terminal needed.

### Run locally

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# add your API key to .streamlit/secrets.toml
streamlit run app.py
```

### Deploy free on Streamlit Community Cloud

1. Push this repo to GitHub (public)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **New app** → select your repo → set main file to `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
5. Click **Deploy** — live in ~2 minutes

Your app will be available at `https://yourname-financial-audit-agent.streamlit.app`
