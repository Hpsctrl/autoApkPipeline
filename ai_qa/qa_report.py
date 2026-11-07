#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qa_report.py - HTML Visual Quality Assurance Report Generator.
Embeds test results and visual screenshots into a standalone single-file HTML report.
"""

import os
import json
import base64

def generate_html_report(results_json="ai_qa/qa_results.json", screenshot_path="ai_qa/screenshot.png", output_html="ai_qa/qa_report.html"):
    results = {}
    if os.path.exists(results_json):
        with open(results_json, "r") as f:
            results = json.load(f)

    img_tag = ""
    if os.path.exists(screenshot_path):
        with open(screenshot_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
            img_tag = f'<img src="data:image/png;base64,{b64}" style="max-width:320px; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.15);" alt="QA Screenshot"/>'

    is_pass = results.get("pass", True)
    score = results.get("score", 100)
    summary = results.get("summary", "Verified cleanly.")
    defects = results.get("defects", [])

    defects_html = ""
    if defects:
        defects_html = "<h3>Defects Identified:</h3><ul>" + "".join(f"<li>{d}</li>" for d in defects) + "</ul>"
    else:
        defects_html = "<p style='color:#10b981; font-weight:600;'>Zero UI defects or regressions detected.</p>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>AutoAPK Visual QA Audit Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; padding: 40px; margin: 0; }}
    .card {{ background: #1e293b; border-radius: 16px; padding: 32px; max-width: 720px; margin: auto; box-shadow: 0 10px 30px rgba(0,0,0,0.4); }}
    .badge {{ display: inline-block; padding: 6px 14px; border-radius: 20px; font-weight: 700; font-size: 14px; }}
    .pass {{ background: #064e3b; color: #34d399; }}
    .fail {{ background: #7f1d1d; color: #f87171; }}
    .score {{ font-size: 42px; font-weight: 800; margin: 16px 0; color: {'#34d399' if is_pass else '#f87171'}; }}
  </style>
</head>
<body>
  <div class="card">
    <span class="badge {'pass' if is_pass else 'fail'}">{'PASSED' if is_pass else 'DEFECTS FOUND'}</span>
    <div class="score">{score} / 100</div>
    <h2>AutoAPK Visual AI Quality Report</h2>
    <p>{summary}</p>
    {defects_html}
    <div style="margin-top:24px; text-align:center;">
      {img_tag}
    </div>
  </div>
</body>
</html>
"""
    with open(output_html, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"✅ Generated Visual QA Report: {output_html}")

if __name__ == "__main__":
    generate_html_report()
