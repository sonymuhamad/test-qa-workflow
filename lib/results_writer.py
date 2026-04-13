"""Write test results to JSON and Markdown files."""

import json
from pathlib import Path
from datetime import datetime
from collections import Counter


def write_results_json(results: dict, output_dir: str) -> str:
    """Write results as a JSON file. Returns the file path."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    filepath = output / f"{results['ticket']}-results.json"
    filepath.write_text(json.dumps(results, indent=2))
    return str(filepath)


def write_summary_markdown(results: dict, output_dir: str) -> str:
    """Write results as a summary Markdown file. Returns the file path."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    ticket = results["ticket"]
    run_id = results["run_id"]
    summary = results["summary"]
    test_cases = results["test_cases"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")

    lines = [
        f"# {ticket} - Automated Test Results",
        "",
        "## Run Info",
        f"- **Run ID:** {run_id}",
        f"- **Date:** {now}",
        f"- **Environment:** staging",
        "",
        "## Results",
        "",
        "| # | Category | Case Description | Expected | Actual | Status |",
        "|---|----------|-----------------|----------|--------|--------|",
    ]

    for tc in test_cases:
        actual_code = tc.get("response", {}).get("status_code", "")
        status = tc["status"]
        lines.append(f"| {tc['id']} | {tc['category']} | {tc['description']} | | {actual_code} | {status} |")

    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append("| Category | Total | Pass | Fail |")
    lines.append("|----------|-------|------|------|")

    category_stats = Counter()
    category_pass = Counter()
    category_fail = Counter()
    for tc in test_cases:
        cat = tc["category"]
        category_stats[cat] += 1
        if tc["status"] == "PASS":
            category_pass[cat] += 1
        else:
            category_fail[cat] += 1

    for cat in category_stats:
        lines.append(f"| {cat} | {category_stats[cat]} | {category_pass[cat]} | {category_fail[cat]} |")

    lines.append(f"| **Total** | **{summary['total']}** | **{summary['passed']}** | **{summary['failed']}** |")
    lines.append("")

    filepath = output / f"{ticket}-summary.md"
    filepath.write_text("\n".join(lines))
    return str(filepath)
