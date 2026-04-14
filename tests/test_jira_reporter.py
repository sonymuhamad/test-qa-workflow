import pytest
from unittest.mock import patch, MagicMock
from lib.jira_reporter import JiraReporter, format_comment, build_adf_comment


@pytest.fixture
def sample_results():
    return {
        "ticket": "SD-0000",
        "run_id": "run-abc123",
        "summary": {"total": 3, "passed": 2, "failed": 1, "skipped": 0},
        "test_cases": [
            {"id": 1, "category": "Happy Path", "description": "Basic GET", "status": "PASS", "failure_reason": None},
            {"id": 2, "category": "Auth", "description": "No auth", "status": "PASS", "failure_reason": None},
            {
                "id": 3, "category": "Validation", "description": "Invalid body", "status": "FAIL",
                "failure_reason": "Expected 400, got 200",
                "request": {"method": "POST", "url": "http://staging/admin/test", "headers": {}, "body": {"name": ""}},
                "response": {"status_code": 200, "body": {"data": {}}, "duration_ms": 60},
            },
        ],
    }


@pytest.fixture
def all_pass_results():
    return {
        "ticket": "SD-0000",
        "run_id": "run-abc",
        "summary": {"total": 2, "passed": 2, "failed": 0, "skipped": 0},
        "test_cases": [
            {"id": 1, "category": "Happy Path", "description": "Test", "status": "PASS", "failure_reason": None},
            {"id": 2, "category": "Auth", "description": "Test", "status": "PASS", "failure_reason": None},
        ],
    }


class TestFormatComment:
    def test_includes_summary(self, sample_results):
        comment = format_comment(sample_results, sheets_url="https://sheets.google.com/xxx")
        assert "PASSED: 2" in comment
        assert "FAILED: 1" in comment
        assert "Total: 3" in comment

    def test_includes_failed_cases(self, sample_results):
        comment = format_comment(sample_results, sheets_url="https://sheets.google.com/xxx")
        assert "#3" in comment
        assert "Invalid body" in comment
        assert "Expected 400, got 200" in comment

    def test_includes_sheets_link(self, sample_results):
        comment = format_comment(sample_results, sheets_url="https://sheets.google.com/xxx")
        assert "https://sheets.google.com/xxx" in comment

    def test_all_pass_no_failed_section(self, all_pass_results):
        comment = format_comment(all_pass_results, sheets_url="")
        assert "Failed Test Cases" not in comment


class TestBuildAdfComment:
    def test_returns_valid_adf_doc(self, sample_results):
        adf = build_adf_comment(sample_results, sheets_url="https://sheets.google.com/xxx")
        assert adf["type"] == "doc"
        assert adf["version"] == 1
        assert len(adf["content"]) > 0

    def test_contains_summary_heading(self, sample_results):
        adf = build_adf_comment(sample_results)
        headings = [n for n in adf["content"] if n.get("type") == "heading"]
        heading_texts = [n["content"][0]["text"] for n in headings]
        assert "Automated QA Report" in heading_texts
        assert "Results Summary" in heading_texts

    def test_contains_failed_heading_when_failures(self, sample_results):
        adf = build_adf_comment(sample_results)
        headings = [n for n in adf["content"] if n.get("type") == "heading"]
        heading_texts = [n["content"][0]["text"] for n in headings]
        assert "Failed Test Cases" in heading_texts

    def test_no_failed_heading_when_all_pass(self, all_pass_results):
        adf = build_adf_comment(all_pass_results)
        headings = [n for n in adf["content"] if n.get("type") == "heading"]
        heading_texts = [n["content"][0]["text"] for n in headings]
        assert "Failed Test Cases" not in heading_texts

    def test_all_pass_shows_status_lozenge(self, all_pass_results):
        adf = build_adf_comment(all_pass_results)
        paragraphs = [n for n in adf["content"] if n.get("type") == "paragraph"]
        has_status = any(
            any(c.get("type") == "status" and c["attrs"]["text"] == "ALL PASSED" for c in p.get("content", []))
            for p in paragraphs
        )
        assert has_status

    def test_contains_expand_for_failed_cases(self, sample_results):
        adf = build_adf_comment(sample_results)
        expands = [n for n in adf["content"] if n.get("type") == "expand"]
        assert len(expands) == 1
        assert "TC#3" in expands[0]["attrs"]["title"]

    def test_contains_sheets_link(self, sample_results):
        adf = build_adf_comment(sample_results, sheets_url="https://sheets.google.com/xxx")
        # Find the paragraph with the link
        found_link = False
        for node in adf["content"]:
            if node.get("type") == "paragraph":
                for child in node.get("content", []):
                    marks = child.get("marks", [])
                    for mark in marks:
                        if mark.get("type") == "link" and "sheets.google.com" in mark.get("attrs", {}).get("href", ""):
                            found_link = True
        assert found_link

    def test_no_sheets_link_when_empty(self, sample_results):
        adf = build_adf_comment(sample_results, sheets_url="")
        found_link = False
        for node in adf["content"]:
            if node.get("type") == "paragraph":
                for child in node.get("content", []):
                    for mark in child.get("marks", []):
                        if mark.get("type") == "link":
                            found_link = True
        assert not found_link


class TestJiraReporter:
    @patch("lib.jira_reporter.requests.post")
    def test_post_comment_sends_adf(self, mock_post, sample_results):
        mock_response = MagicMock()
        mock_response.status_code = 201
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        reporter = JiraReporter(
            base_url="https://techsatudental.atlassian.net",
            email="qa@test.com", api_token="fake-token",
        )
        reporter.post_comment("SD-0000", sample_results, sheets_url="https://sheets.google.com/xxx")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "SD-0000" in call_args[0][0]

        # Verify ADF body structure
        payload = call_args[1]["json"]
        assert payload["body"]["type"] == "doc"
        assert payload["body"]["version"] == 1
