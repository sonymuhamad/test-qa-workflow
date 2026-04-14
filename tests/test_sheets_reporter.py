import pytest
from unittest.mock import patch, MagicMock
from lib.sheets_reporter import SheetsReporter


@pytest.fixture
def sample_results():
    return {
        "ticket": "SD-0000",
        "run_id": "run-abc123",
        "summary": {"total": 3, "passed": 2, "failed": 1, "skipped": 0},
        "test_cases": [
            {
                "id": 1, "category": "Happy Path", "description": "Basic GET",
                "status": "PASS", "duration_ms": 150,
                "request": {"method": "GET", "url": "http://staging/admin/test", "headers": {}, "body": None},
                "response": {"status_code": 200, "body": {"data": []}, "duration_ms": 120},
                "failure_reason": None,
            },
            {
                "id": 2, "category": "Auth", "description": "No auth returns 401",
                "status": "PASS", "duration_ms": 50,
                "request": {"method": "GET", "url": "http://staging/admin/test", "headers": {}, "body": None},
                "response": {"status_code": 401, "body": {"errors": [{"message": "bearer token needed"}]}, "duration_ms": 30},
                "failure_reason": None,
            },
            {
                "id": 3, "category": "Validation", "description": "Invalid body returns 400",
                "status": "FAIL", "duration_ms": 80,
                "request": {"method": "POST", "url": "http://staging/admin/test", "headers": {}, "body": {"name": ""}},
                "response": {"status_code": 200, "body": {}, "duration_ms": 60},
                "failure_reason": "Expected status 400, got 200",
            },
        ],
    }


class TestSheetsReporter:
    @patch("lib.sheets_reporter.requests.post")
    def test_upload_posts_to_webapp(self, mock_post, sample_results):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok", "sheet": "SD-0000", "rows": 3}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        reporter = SheetsReporter(
            webapp_url="https://script.google.com/macros/s/fake/exec",
            secret_token="test-token",
        )
        result = reporter.upload(sample_results, dev_pic="Sony")

        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "https://script.google.com/macros/s/fake/exec"

        payload = call_args[1]["json"]
        assert payload["token"] == "test-token"
        assert payload["ticket"] == "SD-0000"
        assert payload["summary"]["total"] == 3
        assert len(payload["test_cases"]) == 3
        assert payload["dev_pic"] == "Sony"
        assert result["status"] == "ok"

    @patch("lib.sheets_reporter.requests.post")
    def test_upload_raises_on_http_error(self, mock_post, sample_results):
        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = Exception("500 Server Error")
        mock_post.return_value = mock_response

        reporter = SheetsReporter(
            webapp_url="https://script.google.com/macros/s/fake/exec",
            secret_token="test-token",
        )
        with pytest.raises(Exception, match="500 Server Error"):
            reporter.upload(sample_results)
