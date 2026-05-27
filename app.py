import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import os
import json
import tempfile
from datetime import datetime
from pathlib import Path
import anthropic

from src.financial_audit.parsers.file_loader import (
    load_any_file, get_file_profile, aggregate_large_file,
    LARGE_FILE_THRESHOLD, MAX_ROWS_FOR_CLAUDE,
)
from src.financial_audit.analyzers.flexible_auditor import inspect_and_plan, run_audit

st.set_page_config(
    page_title="AI Financial Audit Assistant",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Minimal Streamlit chrome styling
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
  html, body, [class*="css"] { font-family: 'Inter', sans-serif; background: #0a0a0f; }
  .main .block-container { padding: 2rem 2rem; max-width: 100%; background: #0a0a0f; }
  .stApp { background: #0a0a0f; }
  section[data-testid="stSidebar"] { display: none; }
  header { background: transparent !important; }
  .stButton > button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important; border: none !important;
    border-radius: 12px !important; font-size: 16px !important;
    font-weight: 600 !important; padding: 16px !important;
    width: 100% !important; letter-spacing: 0.02em !important;
    transition: all 0.2s !important;
  }
  .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(99,102,241,0.4) !important; }
  .stFileUploader { background: transparent !important; }
  div[data-testid="stFileUploader"] > div {
    background: rgba(255,255,255,0.03) !important;
    border: 1.5px dashed rgba(99,102,241,0.4) !important;
    border-radius: 16px !important; padding: 2rem !important;
  }
  .stAlert { border-radius: 12px !important; }
  p, span, label, div { color: #e2e8f0; }
</style>
""", unsafe_allow_html=True)


def get_api_key():
    try:
        if "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return os.getenv("ANTHROPIC_API_KEY", "")


def render_dashboard(plan: dict, report: str, df: pd.DataFrame, filename: str):
    """Render the full results as a custom HTML/JS dashboard."""

    numeric_cols = df.select_dtypes(include="number").columns.tolist()
    amt_col = plan.get("key_columns", {}).get("amount_col")

    # Build category data for chart
    cat_col = plan.get("key_columns", {}).get("category_col")
    chart_labels, chart_values, chart_colors = [], [], []
    palette = ["#6366f1","#8b5cf6","#ec4899","#f59e0b","#10b981","#3b82f6","#ef4444","#14b8a6","#f97316","#a855f7"]

    if cat_col and cat_col in df.columns and amt_col and amt_col in df.columns:
        breakdown = df.groupby(cat_col)[amt_col].sum().abs().sort_values(ascending=False).head(8)
        chart_labels = list(breakdown.index)
        chart_values = [round(float(v), 2) for v in breakdown.values]
        chart_colors = palette[:len(chart_labels)]
    elif numeric_cols:
        col = amt_col if amt_col in df.columns else numeric_cols[0]
        vc = df[col].describe()
        chart_labels = ["min", "25%", "50%", "75%", "max"]
        chart_values = [round(float(vc.get(k, 0)), 2) for k in ["min", "25%", "50%", "75%", "max"]]
        chart_colors = palette[:5]

    # Compute key metrics
    total_records = len(df)
    total_cols = len(df.columns)
    null_pct = round(df.isna().sum().sum() / (len(df) * len(df.columns)) * 100, 1)
    data_type = plan.get("data_type", "Financial Data")

    primary_val = ""
    primary_label = ""
    if amt_col and amt_col in df.columns:
        primary_val = f"{df[amt_col].sum():,.2f}"
        primary_label = f"Total {amt_col}"
    elif numeric_cols:
        col = numeric_cols[0]
        primary_val = f"{df[col].sum():,.2f}"
        primary_label = f"Total {col}"

    sections = plan.get("analysis_sections", [])
    questions = plan.get("primary_questions", [])
    risk_factors = plan.get("risk_factors", [])

    # Escape report for JS
    report_escaped = report.replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")

    sections_json = json.dumps(sections)
    questions_json = json.dumps(questions)
    risk_factors_json = json.dumps(risk_factors[:4])
    chart_labels_json = json.dumps(chart_labels)
    chart_values_json = json.dumps(chart_values)
    chart_colors_json = json.dumps(chart_colors)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/marked/9.1.6/marked.min.js"></script>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: 'Inter', -apple-system, sans-serif;
    background: #0a0a0f;
    color: #e2e8f0;
    min-height: 100vh;
  }}

  .dashboard {{
    padding: 0;
    max-width: 1400px;
    margin: 0 auto;
  }}

  /* ── Hero header ── */
  .hero {{
    background: linear-gradient(135deg, #0f0f1a 0%, #1a1035 50%, #0f0f1a 100%);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 20px;
    padding: 36px 40px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
  }}

  .hero::before {{
    content: '';
    position: absolute;
    top: -100px; right: -100px;
    width: 300px; height: 300px;
    background: radial-gradient(circle, rgba(99,102,241,0.15) 0%, transparent 70%);
    border-radius: 50%;
  }}

  .hero-badge {{
    display: inline-flex; align-items: center; gap: 8px;
    background: rgba(99,102,241,0.15);
    border: 1px solid rgba(99,102,241,0.3);
    border-radius: 20px;
    padding: 6px 16px;
    font-size: 13px; font-weight: 600; color: #a5b4fc;
    margin-bottom: 16px;
  }}

  .hero-badge .dot {{
    width: 8px; height: 8px;
    background: #6366f1;
    border-radius: 50%;
    animation: pulse 2s infinite;
  }}

  @keyframes pulse {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.5; transform: scale(0.8); }}
  }}

  .hero-title {{
    font-size: 32px; font-weight: 700;
    background: linear-gradient(135deg, #fff 0%, #a5b4fc 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin-bottom: 8px;
  }}

  .hero-sub {{
    font-size: 15px; color: #64748b;
  }}

  /* ── Metric cards ── */
  .metrics-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
  }}

  .metric-card {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 24px;
    transition: all 0.3s;
    position: relative;
    overflow: hidden;
  }}

  .metric-card::after {{
    content: '';
    position: absolute;
    bottom: 0; left: 0;
    height: 3px; width: 100%;
    border-radius: 0 0 16px 16px;
  }}

  .metric-card.purple::after {{ background: linear-gradient(90deg, #6366f1, #8b5cf6); }}
  .metric-card.green::after {{ background: linear-gradient(90deg, #10b981, #34d399); }}
  .metric-card.amber::after {{ background: linear-gradient(90deg, #f59e0b, #fcd34d); }}
  .metric-card.blue::after {{ background: linear-gradient(90deg, #3b82f6, #60a5fa); }}

  .metric-card:hover {{
    border-color: rgba(99,102,241,0.3);
    transform: translateY(-2px);
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  }}

  .metric-icon {{
    font-size: 24px; margin-bottom: 12px;
  }}

  .metric-label {{
    font-size: 11px; font-weight: 600;
    color: #64748b; text-transform: uppercase;
    letter-spacing: 0.08em; margin-bottom: 8px;
  }}

  .metric-value {{
    font-size: 30px; font-weight: 700;
    color: #f8fafc; line-height: 1;
    margin-bottom: 6px;
  }}

  .metric-sub {{ font-size: 12px; color: #475569; }}

  /* ── Main grid ── */
  .main-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 20px;
    margin-bottom: 24px;
  }}

  .card {{
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 24px;
  }}

  .card-title {{
    font-size: 14px; font-weight: 600; color: #e2e8f0;
    margin-bottom: 20px;
    display: flex; align-items: center; gap: 10px;
  }}

  .card-badge {{
    font-size: 11px; font-weight: 600;
    background: rgba(99,102,241,0.15);
    color: #a5b4fc;
    padding: 3px 10px; border-radius: 20px;
  }}

  /* ── Chart ── */
  .chart-wrap {{
    position: relative; height: 220px;
  }}

  /* ── Analysis plan ── */
  .plan-item {{
    display: flex; gap: 14px; align-items: flex-start;
    padding: 14px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}

  .plan-item:last-child {{ border-bottom: none; padding-bottom: 0; }}

  .plan-num {{
    width: 28px; height: 28px; flex-shrink: 0;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; color: white;
  }}

  .plan-title {{ font-size: 13px; font-weight: 600; color: #e2e8f0; margin-bottom: 3px; }}
  .plan-desc {{ font-size: 12px; color: #64748b; line-height: 1.5; }}

  /* ── Risk factors ── */
  .risk-item {{
    display: flex; align-items: flex-start; gap: 12px;
    background: rgba(239,68,68,0.07);
    border: 1px solid rgba(239,68,68,0.2);
    border-radius: 12px;
    padding: 14px;
    margin-bottom: 10px;
    transition: all 0.2s;
  }}

  .risk-item:hover {{
    background: rgba(239,68,68,0.12);
    border-color: rgba(239,68,68,0.35);
  }}

  .risk-icon {{ font-size: 18px; flex-shrink: 0; }}
  .risk-text {{ font-size: 13px; color: #fca5a5; line-height: 1.5; }}

  /* ── Questions ── */
  .question-item {{
    display: flex; gap: 12px; align-items: flex-start;
    padding: 12px 0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }}

  .question-item:last-child {{ border-bottom: none; }}

  .q-icon {{ color: #6366f1; font-size: 16px; flex-shrink: 0; margin-top: 1px; }}
  .q-text {{ font-size: 13px; color: #94a3b8; line-height: 1.5; }}

  /* ── Full report ── */
  .report-wrap {{
    background: rgba(255,255,255,0.02);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 20px;
    padding: 40px;
    margin-bottom: 24px;
  }}

  .report-header {{
    display: flex; align-items: center; gap: 16px;
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid rgba(255,255,255,0.08);
  }}

  .report-icon {{
    width: 48px; height: 48px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    font-size: 22px;
  }}

  .report-title {{ font-size: 20px; font-weight: 700; color: #f8fafc; }}
  .report-sub {{ font-size: 13px; color: #64748b; margin-top: 2px; }}

  .report-body h1, .report-body h2, .report-body h3 {{
    color: #e2e8f0; margin: 24px 0 12px; font-weight: 600;
  }}

  .report-body h1 {{ font-size: 22px; }}
  .report-body h2 {{
    font-size: 17px;
    padding-bottom: 8px;
    border-bottom: 1px solid rgba(99,102,241,0.2);
  }}
  .report-body h3 {{ font-size: 15px; color: #a5b4fc; }}

  .report-body p {{
    font-size: 14px; color: #94a3b8;
    line-height: 1.8; margin-bottom: 14px;
  }}

  .report-body li {{
    font-size: 14px; color: #94a3b8;
    line-height: 1.8; margin-bottom: 6px;
    margin-left: 20px;
  }}

  .report-body strong {{ color: #e2e8f0; font-weight: 600; }}

  .report-body table {{
    width: 100%; border-collapse: collapse;
    margin: 16px 0; font-size: 13px;
  }}

  .report-body th {{
    background: rgba(99,102,241,0.15);
    color: #a5b4fc; padding: 10px 16px;
    text-align: left; font-weight: 600;
    border-bottom: 1px solid rgba(99,102,241,0.2);
  }}

  .report-body td {{
    padding: 10px 16px;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    color: #94a3b8;
  }}

  .report-body tr:hover td {{
    background: rgba(255,255,255,0.02);
    color: #e2e8f0;
  }}

  .report-body blockquote {{
    border-left: 3px solid #6366f1;
    padding: 12px 20px;
    background: rgba(99,102,241,0.08);
    border-radius: 0 12px 12px 0;
    margin: 16px 0;
    color: #a5b4fc;
    font-size: 14px;
  }}

  .report-body code {{
    background: rgba(255,255,255,0.08);
    padding: 2px 8px; border-radius: 6px;
    font-size: 12px; color: #a5b4fc;
    font-family: monospace;
  }}

  /* ── Download button ── */
  .dl-btn {{
    display: block; width: 100%;
    background: rgba(99,102,241,0.1);
    border: 1.5px solid rgba(99,102,241,0.4);
    border-radius: 14px;
    padding: 18px;
    text-align: center;
    font-size: 15px; font-weight: 600; color: #a5b4fc;
    cursor: pointer; transition: all 0.2s;
    text-decoration: none;
  }}

  .dl-btn:hover {{
    background: rgba(99,102,241,0.2);
    border-color: rgba(99,102,241,0.6);
    color: white;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99,102,241,0.2);
  }}

  /* ── Counter animation ── */
  @keyframes fadeInUp {{
    from {{ opacity: 0; transform: translateY(20px); }}
    to {{ opacity: 1; transform: translateY(0); }}
  }}

  .metric-card {{ animation: fadeInUp 0.5s ease both; }}
  .metric-card:nth-child(1) {{ animation-delay: 0.1s; }}
  .metric-card:nth-child(2) {{ animation-delay: 0.2s; }}
  .metric-card:nth-child(3) {{ animation-delay: 0.3s; }}
  .metric-card:nth-child(4) {{ animation-delay: 0.4s; }}

  .card {{ animation: fadeInUp 0.5s ease 0.3s both; }}
  .report-wrap {{ animation: fadeInUp 0.5s ease 0.5s both; }}
</style>
</head>
<body>
<div class="dashboard">

  <!-- Hero -->
  <div class="hero">
    <div class="hero-badge">
      <span class="dot"></span>
      Audit Complete
    </div>
    <div class="hero-title">Financial Audit Report</div>
    <div class="hero-sub" id="hero-sub">Loading...</div>
  </div>

  <!-- Metrics -->
  <div class="metrics-grid">
    <div class="metric-card purple">
      <div class="metric-icon">📊</div>
      <div class="metric-label">Records Analyzed</div>
      <div class="metric-value" id="metric-records">0</div>
      <div class="metric-sub" id="metric-cols"></div>
    </div>
    <div class="metric-card green">
      <div class="metric-icon">💵</div>
      <div class="metric-label" id="primary-label">Primary Metric</div>
      <div class="metric-value" id="metric-primary">—</div>
      <div class="metric-sub">from dataset</div>
    </div>
    <div class="metric-card amber">
      <div class="metric-icon">⚠️</div>
      <div class="metric-label">Data Quality</div>
      <div class="metric-value" id="metric-nulls">0%</div>
      <div class="metric-sub">missing values</div>
    </div>
    <div class="metric-card blue">
      <div class="metric-icon">🔍</div>
      <div class="metric-label">Analysis Sections</div>
      <div class="metric-value" id="metric-sections">0</div>
      <div class="metric-sub">tailored to your data</div>
    </div>
  </div>

  <!-- Main grid -->
  <div class="main-grid">

    <!-- Chart -->
    <div class="card">
      <div class="card-title">
        📈 Data Distribution
        <span class="card-badge" id="chart-label">Overview</span>
      </div>
      <div class="chart-wrap">
        <canvas id="mainChart"></canvas>
      </div>
    </div>

    <!-- Analysis plan -->
    <div class="card">
      <div class="card-title">
        🗂 Analysis Plan
        <span class="card-badge" id="plan-count">0 sections</span>
      </div>
      <div id="plan-items"></div>
    </div>

    <!-- Risk factors -->
    <div class="card">
      <div class="card-title">
        🚨 Risk Factors Examined
      </div>
      <div id="risk-items"></div>
    </div>

    <!-- Key questions -->
    <div class="card">
      <div class="card-title">
        💡 Key Questions Answered
      </div>
      <div id="question-items"></div>
    </div>

  </div>

  <!-- Full report -->
  <div class="report-wrap">
    <div class="report-header">
      <div class="report-icon">📋</div>
      <div>
        <div class="report-title">Full AI Audit Report</div>
        <div class="report-sub" id="report-sub">Generated by Claude</div>
      </div>
    </div>
    <div class="report-body" id="report-body"></div>
  </div>

  <!-- Download -->
  <a class="dl-btn" id="dl-btn" href="#" download>
    ⬇ Download Full Report (.md)
  </a>

</div>

<script>
const sections = {sections_json};
const questions = {questions_json};
const riskFactors = {risk_factors_json};
const chartLabels = {chart_labels_json};
const chartValues = {chart_values_json};
const chartColors = {chart_colors_json};
const reportMd = `{report_escaped}`;
const dataType = {json.dumps(data_type)};
const totalRecords = {total_records};
const totalCols = {total_cols};
const nullPct = {null_pct};
const primaryVal = {json.dumps(primary_val)};
const primaryLabel = {json.dumps(primary_label)};
const filename = {json.dumps(filename)};

// Counter animation
function animateCount(el, target, prefix='', suffix='', duration=1200) {{
  const isFloat = String(target).includes('.');
  const start = performance.now();
  const from = 0;
  function update(now) {{
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    const val = from + (target - from) * ease;
    el.textContent = prefix + (isFloat ? val.toFixed(2) : Math.floor(val).toLocaleString()) + suffix;
    if (p < 1) requestAnimationFrame(update);
  }}
  requestAnimationFrame(update);
}}

// Hero
document.getElementById('hero-sub').textContent =
  `${{dataType}} · ${{totalRecords.toLocaleString()}} records · ${{filename}}`;
document.getElementById('report-sub').textContent =
  `${{dataType}} · Generated ${{new Date().toLocaleDateString('en-US', {{month:'long', day:'numeric', year:'numeric'}})}}`;

// Metrics
setTimeout(() => {{
  animateCount(document.getElementById('metric-records'), totalRecords);
  document.getElementById('metric-cols').textContent = totalCols + ' columns';
  document.getElementById('metric-nulls').textContent = nullPct + '%';
  document.getElementById('metric-sections').textContent = sections.length;

  if (primaryVal) {{
    document.getElementById('primary-label').textContent = primaryLabel;
    document.getElementById('metric-primary').textContent = primaryVal;
  }}
}}, 200);

// Plan items
const planEl = document.getElementById('plan-items');
document.getElementById('plan-count').textContent = sections.length + ' sections';
sections.forEach((s, i) => {{
  planEl.innerHTML += `
    <div class="plan-item">
      <div class="plan-num">${{i+1}}</div>
      <div>
        <div class="plan-title">${{s.title}}</div>
        <div class="plan-desc">${{s.description}}</div>
      </div>
    </div>`;
}});

// Risk factors
const riskEl = document.getElementById('risk-items');
const riskIcons = ['🔴','🟠','🟡','⚪'];
riskFactors.forEach((r, i) => {{
  riskEl.innerHTML += `
    <div class="risk-item">
      <span class="risk-icon">${{riskIcons[i] || '🔴'}}</span>
      <span class="risk-text">${{r}}</span>
    </div>`;
}});

// Questions
const qEl = document.getElementById('question-items');
questions.forEach(q => {{
  qEl.innerHTML += `
    <div class="question-item">
      <span class="q-icon">→</span>
      <span class="q-text">${{q}}</span>
    </div>`;
}});

// Chart
const ctx = document.getElementById('mainChart').getContext('2d');
if (chartLabels.length > 0) {{
  document.getElementById('chart-label').textContent = chartLabels.length + ' categories';
  new Chart(ctx, {{
    type: chartLabels.length <= 6 ? 'doughnut' : 'bar',
    data: {{
      labels: chartLabels,
      datasets: [{{
        data: chartValues,
        backgroundColor: chartColors.map(c => c + 'cc'),
        borderColor: chartColors,
        borderWidth: 2,
        borderRadius: chartLabels.length > 6 ? 8 : 0,
      }}]
    }},
    options: {{
      responsive: true, maintainAspectRatio: false,
      plugins: {{
        legend: {{
          labels: {{ color: '#94a3b8', font: {{ size: 11 }}, boxWidth: 12 }}
        }},
        tooltip: {{
          backgroundColor: 'rgba(15,15,26,0.95)',
          titleColor: '#e2e8f0',
          bodyColor: '#94a3b8',
          borderColor: 'rgba(99,102,241,0.3)',
          borderWidth: 1,
          padding: 12,
        }}
      }},
      scales: chartLabels.length > 6 ? {{
        x: {{ ticks: {{ color: '#64748b', font: {{ size: 10 }} }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }},
        y: {{ ticks: {{ color: '#64748b' }}, grid: {{ color: 'rgba(255,255,255,0.05)' }} }}
      }} : {{}},
    }}
  }});
}}

// Render markdown report
document.getElementById('report-body').innerHTML = marked.parse(reportMd);

// Download button
const fullReport = `# AI Financial Audit Report\\n_Generated: ${{new Date().toLocaleString()}}_\\n_Data: ${{dataType}}_\\n_Records: ${{totalRecords.toLocaleString()}}_\\n\\n---\\n\\n${{reportMd}}`;
const blob = new Blob([fullReport], {{type: 'text/markdown'}});
const url = URL.createObjectURL(blob);
document.getElementById('dl-btn').href = url;
document.getElementById('dl-btn').download = `audit_${{new Date().toISOString().slice(0,10)}}.md`;
</script>
</body>
</html>
"""
    components.html(html, height=3200, scrolling=True)


# ─────────────────────────────────────────────────────────────────────────────
# STREAMLIT UI (upload + trigger only)
# ─────────────────────────────────────────────────────────────────────────────

api_key = get_api_key()
if not api_key:
    st.error("No Anthropic API key found. Add `ANTHROPIC_API_KEY` to `.streamlit/secrets.toml`.")
    st.stop()

if "request_count" not in st.session_state:
    st.session_state["request_count"] = 0
if st.session_state["request_count"] >= 5:
    st.warning("Demo limit reached — 5 audits per session.")
    st.stop()

# Header
st.markdown("""
<div style="padding: 2.5rem 0 1.5rem; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 2rem;">
  <h1 style="font-size:32px; font-weight:700; background:linear-gradient(135deg,#fff,#a5b4fc); -webkit-background-clip:text; -webkit-text-fill-color:transparent; margin:0 0 8px;">
    💰 AI Financial Audit Assistant
  </h1>
  <p style="color:#64748b; font-size:15px; margin:0;">
    Upload any financial dataset — Claude identifies the data type and produces a tailored audit
  </p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "📂 Drop any financial file here — CSV, XLSX, XLS, TXT",
    type=["csv", "xlsx", "xls", "txt"],
)

if not uploaded_file:
    st.markdown("""
    <div style="margin-top:1rem; padding:20px; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.06); border-radius:14px;">
      <p style="color:#64748b; font-size:13px; margin:0 0 10px; font-weight:600;">Works with any financial data:</p>
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px;">
        <span style="color:#94a3b8; font-size:13px;">🏦 Bank statements</span>
        <span style="color:#94a3b8; font-size:13px;">📋 Loan / credit data</span>
        <span style="color:#94a3b8; font-size:13px;">🏛 Government spending</span>
        <span style="color:#94a3b8; font-size:13px;">💼 Payroll data</span>
        <span style="color:#94a3b8; font-size:13px;">📈 Sales / revenue</span>
        <span style="color:#94a3b8; font-size:13px;">💹 Investment data</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# Load file
suffix = Path(uploaded_file.name).suffix.lower()
with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
    tmp.write(uploaded_file.getbuffer())
    tmp_path = tmp.name

try:
    df = load_any_file(tmp_path, uploaded_file.name)
except Exception as e:
    st.error(f"Could not read file: {e}")
    st.stop()
finally:
    os.unlink(tmp_path)

if df.empty:
    st.error("File appears empty.")
    st.stop()

is_large = len(df) > LARGE_FILE_THRESHOLD
st.success(f"✓ **{len(df):,} rows × {len(df.columns)} columns** loaded from `{uploaded_file.name}`" +
           (" · Large file — will use aggregated analysis" if is_large else ""))

with st.expander("Preview data"):
    st.dataframe(df.head(10), use_container_width=True, hide_index=True)

st.button("🔍 Run AI Audit", use_container_width=True)

if st.session_state.get("run_clicked") or st.button("Run Audit ", key="run2", use_container_width=False):
    pass

run = st.button("  Run Full Audit  ", type="primary", use_container_width=True, key="main_run")

if run:
    st.session_state["request_count"] += 1
    client = anthropic.Anthropic(api_key=api_key)

    with st.status("Claude is analyzing your data...", expanded=True) as status:
        st.write("Profiling dataset...")
        if is_large:
            file_profile = get_file_profile(df.head(100))
            data_for_audit = aggregate_large_file(df, {})
        else:
            file_profile = get_file_profile(df)
            data_for_audit = {
                "total_rows": len(df),
                "columns": list(df.columns),
                "sample_rows": df.head(MAX_ROWS_FOR_CLAUDE).fillna("").to_dict(orient="records"),
                "numeric_summary": df.describe().round(4).to_dict() if not df.select_dtypes(include="number").empty else {},
            }

        st.write("Identifying data type and planning analysis...")
        analysis_plan = inspect_and_plan(file_profile, client)
        st.write(f"Identified: **{analysis_plan.get('data_type', 'Financial data')}**")

        st.write("Running full audit...")
        report = run_audit(data_for_audit, analysis_plan, client)
        status.update(label="Audit complete!", state="complete")

    st.session_state["audit_results"] = {
        "analysis_plan": analysis_plan,
        "report": report,
        "df": df,
        "filename": uploaded_file.name,
    }

if "audit_results" in st.session_state:
    r = st.session_state["audit_results"]
    st.divider()
    render_dashboard(r["analysis_plan"], r["report"], r["df"], r["filename"])
