import pytest
import json
from pathlib import Path
from lib.results_writer import write_results_json, write_summary_markdown


@pytest.fixture
def sample_results():
    return {
        "ticket": "SD-0000",
        "run_id": "run-abc123",
        "summary": {"total": 2, "passed": 1, "failed": 1, "skipped": 0},
        "test_cases": [
            {
                "id": 1, "category": "Happy Path", "description": "Basic GET",
                "status": "PASS", "duration_ms": 150,
                "request": {"method": "GET", "url": "http://staging/test", "headers": {}, "body": None},
                "response": {"status_code": 200, "body": {}, "duration_ms": 120},
                "failure_reason": None,
            },
            {
                "id": 2, "category": "Validation", "description": "Invalid body",
                "status": "FAIL", "duration_ms": 80,
                "request": {"method": "POST", "url": "http://staging/test", "headers": {}, "body": {"name": ""}},
                "response": {"status_code": 200, "body": {}, "duration_ms": 60},
                "failure_reason": "Expected 400, got 200",
            },
        ],
    }


class TestWriteResultsJson:
    def test_writes_json_file(self, tmp_path, sample_results):
        output_path = write_results_json(sample_results, output_dir=str(tmp_path))
        assert Path(output_path).exists()
        data = json.loads(Path(output_path).read_text())
        assert data["ticket"] == "SD-0000"
        assert len(data["test_cases"]) == 2


class TestWriteSummaryMarkdown:
    def test_writes_markdown_file(self, tmp_path, sample_results):
        output_path = write_summary_markdown(sample_results, output_dir=str(tmp_path))
        assert Path(output_path).exists()
        content = Path(output_path).read_text()
        assert "# SD-0000" in content
        assert "PASS" in content
        assert "FAIL" in content

    def test_markdown_contains_table(self, tmp_path, sample_results):
        output_path = write_summary_markdown(sample_results, output_dir=str(tmp_path))
        content = Path(output_path).read_text()
        assert "| # |" in content
        assert "| 1 |" in content
        assert "| 2 |" in content

    def test_markdown_contains_summary_table(self, tmp_path, sample_results):
        output_path = write_summary_markdown(sample_results, output_dir=str(tmp_path))
        content = Path(output_path).read_text()
        assert "| Category |" in content
        assert "**Total**" in content
