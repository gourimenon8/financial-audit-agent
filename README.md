# AI Financial Audit Assistant

A Streamlit-based AI agent that audits **any financial dataset** using Claude. Upload a CSV, XLSX, or TXT file — the agent identifies the data type, runs a tailored analysis, and presents findings in a dark, interactive dashboard with downloadable reports.

**[Live Demo →](https://gourimenon8-financial-audit-agent.streamlit.app)**

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=flat-square)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?style=flat-square)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-purple?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

---

## Overview

Most financial audit tools are hardcoded for one data format. This one isn't.

Upload bank statements, loan data, government procurement records, payroll exports, or any tabular financial file — Claude inspects the schema, decides what analysis makes sense for that specific data type, and produces a structured report with findings, risk flags, and recommendations.

```
Upload any file (CSV · XLSX · XLS · TXT)
         │
         ▼
   Smart file loader
   (normalizes any format)
         │
         ▼
  Claude Call 1: Schema inspection
  → Identifies data type
  → Builds tailored analysis plan
         │
         ▼
  Claude Call 2: Full audit
  → Runs analysis based on plan
  → Flags anomalies and risks
  → Writes recommendations
         │
         ▼
  Interactive dashboard + downloadable report
```

---

## Features

- **Universal file support** — CSV, XLSX, XLS, TXT with automatic separator detection
- **Data-type aware** — Claude identifies what it's looking at before analyzing it
- **Large file handling** — files over 10,000 rows are aggregated statistically before analysis, keeping costs low and performance fast
- **Interactive dark dashboard** — animated metrics, Chart.js visualizations, styled report rendering
- **Downloadable report** — full audit exported as markdown, generated client-side
- **CLI mode** — also runs as a terminal agent for bank statement CSVs

---

## Supported Data Types

| Data Type | Examples |
|-----------|---------|
| Bank statements | Transaction history, spending exports |
| Loan / credit data | Default risk, balance data, credit scores |
| Government spending | Procurement, grants, federal awards |
| Payroll data | Salaries, departments, pay periods |
| Sales / revenue | Invoices, products, regional breakdown |
| Investment data | Portfolio holdings, trade history |

---

## Architecture

```
financial-audit-agent/
├── app.py                              # Streamlit entry point + custom HTML/JS dashboard
├── cli.py                              # Terminal CLI for bank statement CSVs
├── src/financial_audit/
│   ├── parsers/
│   │   ├── csv_parser.py              # Bank statement normalizer (CLI mode)
│   │   └── file_loader.py             # Universal loader — any format, large file aggregation
│   ├── analyzers/
│   │   ├── flexible_auditor.py        # Schema inspection + flexible audit (web mode)
│   │   ├── categorizer.py             # Transaction categorization (CLI mode)
│   │   ├── anomaly.py                 # Anomaly detection (CLI mode)
│   │   ├── subscriptions.py           # Recurring charge detection (CLI mode)
│   │   └── summary.py                 # Financial narrative generation (CLI mode)
│   └── report/
│       ├── terminal.py                # Rich terminal output
│       └── markdown_writer.py         # Markdown report writer
└── sample_data/
    └── transactions.csv               # Sample bank statement for testing
```

---

## Installation

**Requirements:** Python 3.11+

```bash
git clone https://github.com/gourimenon8/financial-audit-agent.git
cd financial-audit-agent

python3.11 -m venv venv
source venv/bin/activate       # Mac/Linux
venv\Scripts\activate          # Windows

pip install -r requirements.txt
```

---

## Configuration

Copy the example secrets file and add your Anthropic API key:

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
```

Edit `.streamlit/secrets.toml`:
```toml
ANTHROPIC_API_KEY = "sk-ant-your-key-here"
```

Get a key at [console.anthropic.com](https://console.anthropic.com). The `.streamlit/secrets.toml` file is gitignored and will never be committed.

---

## Usage

### Web app (Streamlit)

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`. Upload any financial file and click **Run AI Audit**.

### CLI agent (bank statements only)

```bash
# Run on sample data
python cli.py ./sample_data

# Run on your own bank exports
python cli.py ./my_statements

# Specify output file
python cli.py ./my_statements --output report.md
```

---

## Deployment

### Free hosting on Streamlit Community Cloud

1. Fork this repo on GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub
3. Click **New app** → select your fork → set main file to `app.py`
4. Under **Advanced settings → Secrets**, add:
   ```toml
   ANTHROPIC_API_KEY = "sk-ant-your-key-here"
   ```
5. Click **Deploy** — live URL in ~2 minutes

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| [Anthropic Claude](https://anthropic.com) | Schema inspection, audit analysis, report generation |
| [Streamlit](https://streamlit.io) | Web framework and file upload |
| [Chart.js](https://chartjs.org) | Interactive data visualizations |
| [pandas](https://pandas.pydata.org) | Data loading, aggregation, statistical profiling |
| [Rich](https://github.com/Textualize/rich) | Terminal formatting (CLI mode) |
| [Typer](https://typer.tiangolo.com) | CLI interface |
| [python-dotenv](https://pypi.org/project/python-dotenv) | Environment configuration |

---

## License

MIT
