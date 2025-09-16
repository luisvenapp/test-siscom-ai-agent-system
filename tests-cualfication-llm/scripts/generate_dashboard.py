#!/usr/bin/env python3
import os
import sys
import json
import argparse

# Allow running from repo root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BASE_DIR)
sys.path.append(REPO_ROOT)

from tests-cualfication-llm.src.reporting.plotly_charts import export_plotly_dashboard_html  # type: ignore


def main():
    parser = argparse.ArgumentParser(description="Generate Plotly dashboard from a summary JSON")
    parser.add_argument("--summary", required=True, help="Path to summary__<timestamp>.json")
    args = parser.parse_args()

    summary_path = os.path.abspath(args.summary)
    if not os.path.exists(summary_path):
        print(f"Summary not found: {summary_path}")
        sys.exit(1)

    with open(summary_path, 'r', encoding='utf-8') as f:
        summary = json.load(f)

    out_dir = os.path.dirname(summary_path)
    ts = os.path.basename(summary_path).split("summary__", 1)[-1].split(".json", 1)[0]
    html_path = os.path.join(out_dir, f"dashboard__{ts}.html")

    export_plotly_dashboard_html(html_path, summary, title=f"LLM Benchmark Dashboard — {ts}")
    print(f"Dashboard written: {html_path}")

if __name__ == "__main__":
    main()
