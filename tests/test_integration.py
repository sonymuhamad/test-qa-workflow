"""Verify the full pipeline works with the example test case file."""
import pytest
import json
from lib.yaml_loader import load_test_cases, collect_all_test_cases
from lib.evidence import EvidenceCapture, TestCaseResult
from lib.results_writer import write_results_json, write_summary_markdown
from lib.sheets_reporter import format_header_stats, format_test_case_row
from lib.jira_reporter import format_comment


def test_full_pipeline_dry_run(tmp_path):
    """Test the full pipeline without hitting any external services."""
    # 1. Load YAML
    data = load_test_cases("test_cases/example-SD-0000.yaml")
    assert data["ticket"] == "SD-0000"
    cases = collect_all_test_cases(data)
    assert len(cases) == 5

    # 2. Simulate evidence capture
    evidence = EvidenceCapture(ticket="SD-0000", run_id="run-test")
    for tc in cases:
        evidence.add_result(TestCaseResult(
            test_case_id=tc["id"],
            category=tc["category"],
            description=tc["description"],
            status="PASS",
            duration_ms=100,
            request={"method": tc["method"], "url": f"http://staging{tc['path']}", "headers": {}, "body": tc.get("body")},
            response={"status_code": tc["expected"]["status_code"], "body": {}, "duration_ms": 80},
        ))

    # 3. Write results
    results = json.loads(evidence.to_json())
    json_path = write_results_json(results, output_dir=str(tmp_path))
    md_path = write_summary_markdown(results, output_dir=str(tmp_path))
    assert json_path.endswith(".json")
    assert md_path.endswith(".md")

    # 4. Format for sheets
    header_rows = format_header_stats(results["summary"])
    assert header_rows[0][2] == 5  # 5 passed

    # 5. Format for Jira
    comment = format_comment(results, sheets_url="https://sheets.example.com")
    assert "PASSED: 5" in comment
    assert "FAILED: 0" in comment
