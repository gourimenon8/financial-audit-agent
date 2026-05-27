"""
Flexible AI auditor.
Claude inspects the data, decides what analysis to run,
then produces a structured audit — all in two LLM calls.
"""

import json
import anthropic


def inspect_and_plan(file_profile: dict, client: anthropic.Anthropic) -> dict:
    """
    Claude Call 1: Inspect the schema and sample data.
    Returns an analysis plan tailored to this data type.
    """
    prompt = """You are a financial data analyst. You have been given a profile of an uploaded dataset.

Dataset profile:
{}

Your job is to:
1. Identify what kind of financial data this is
2. Decide what analysis would be most valuable
3. Return a structured analysis plan

Respond ONLY with a JSON object like this:
{{
  "data_type": "brief description e.g. 'Bank transaction history', 'Loan default dataset', 'Government procurement data'",
  "key_columns": {{
    "amount_col": "column name with monetary values, or null",
    "date_col": "column name with dates, or null",
    "category_col": "column name for grouping/categories, or null",
    "id_col": "column name for unique identifiers, or null"
  }},
  "analysis_sections": [
    {{
      "title": "section title",
      "description": "what to analyze in this section",
      "type": "overview | distribution | anomalies | risk | patterns | recommendations"
    }}
  ],
  "primary_questions": [
    "specific question 1 this data can answer",
    "specific question 2",
    "specific question 3"
  ],
  "risk_factors": ["what to look for as red flags in this specific data type"]
}}

No explanation, no markdown, just the JSON object.""".format(
        json.dumps(file_profile, indent=2, default=str)
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:])
        raw = raw.rsplit("```", 1)[0].strip()

    return json.loads(raw)


def run_audit(data_summary: dict, analysis_plan: dict, client: anthropic.Anthropic) -> str:
    """
    Claude Call 2: Run the full audit based on the analysis plan.
    Returns a markdown-formatted audit report.
    """
    prompt = """You are a senior financial auditor producing a professional audit report.

Data type: {data_type}

Analysis plan:
{plan}

Data summary and statistics:
{data}

Produce a complete financial audit report with EXACTLY these sections (use markdown):
{sections}

For each section:
- Use specific numbers from the data
- Flag anything unusual or concerning with ⚠️
- Highlight positives with ✅
- Be direct and actionable — no filler text
- Use tables where comparisons are helpful

End with a **Key Takeaways** section: 3-5 bullet points summarizing the most important findings.

Write in plain English — this report will be read by non-technical stakeholders.""".format(
        data_type=analysis_plan.get("data_type", "Financial data"),
        plan=json.dumps(analysis_plan.get("primary_questions", []), indent=2),
        data=json.dumps(data_summary, indent=2, default=str),
        sections="\n".join(
            f"## {s['title']}" for s in analysis_plan.get("analysis_sections", [])
        ),
    )

    message = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )

    return message.content[0].text.strip()
