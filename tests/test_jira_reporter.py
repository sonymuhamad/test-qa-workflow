import pytest
from unittest.mock import patch, MagicMock
from lib.jira_reporter import JiraReporter, format_comment


@pytest.fixture
def sample_results():
    return {
        "ticket": "SD-0000",
        "run_id": "run-abc123",
        "summary": {"total": 3, "passed": 2, "failed": 1, "skipped": 0},
        "test_cases": [
            {"id": 1, "category": "Happy Path", "description": "Basic GET", "status": "PASS", "failure_reason": None},
            {"id": 2, "category": "Auth", "description": "No auth", "status": "PASS", "failure_reason": None},
            {"id": 3, "category": "Validation", "description": "Invalid body", "status": "FAIL", "failure_reason": "Expected 400, got 200"},
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

    def test_all_pass_no_failed_section(self):
        results = {
            "ticket": "SD-0000", "run_id": "run-abc",
            "summary": {"total": 2, "passed": 2, "failed": 0, "skipped": 0},
            "test_cases": [
                {"id": 1, "category": "Happy Path", "description": "Test", "status": "PASS", "failure_reason": None},
                {"id": 2, "category": "Auth", "description": "Test", "status": "PASS", "failure_reason": None},
            ],
        }
        comment = format_comment(results, sheets_url="")
        assert "Failed Test Cases" not in comment


class TestJiraReporter:
    @patch("lib.jira_reporter.requests.post")
    def test_post_comment(self, mock_post, sample_results):
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
