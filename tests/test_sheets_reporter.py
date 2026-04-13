import pytest
from unittest.mock import patch, MagicMock
from lib.sheets_reporter import SheetsReporter, format_header_stats, format_test_case_row


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


class TestFormatHeaderStats:
    def test_formats_stats(self, sample_results):
        rows = format_header_stats(sample_results["summary"])
        assert rows[0] == ["PASS", "", 2]
        assert rows[1] == ["FAILED", "", 1]
        assert rows[2] == ["Number Of Test Case", "", 3]
        assert rows[4] == ["Postponed", "", 0]

    def test_defect_percentage(self, sample_results):
        rows = format_header_stats(sample_results["summary"])
        assert rows[5] == ["Staging Defect Percentage", "", "33.33%"]


class TestFormatTestCaseRow:
    def test_pass_row(self, sample_results):
        tc = sample_results["test_cases"][0]
        row = format_test_case_row(tc, dev_pic="Sony", testing_date="13/04/2026")
        assert row[0] == 1
        assert row[2] == "Basic GET"
        assert row[5] == 200
        assert row[8] == "PASS"
        assert row[9] == "Sony"
        assert row[10] == "Claude (automated)"

    def test_fail_row(self, sample_results):
        tc = sample_results["test_cases"][2]
        row = format_test_case_row(tc, dev_pic="Sony", testing_date="13/04/2026")
        assert row[8] == "FAILED"
        assert "Expected status 400, got 200" in row[7]


class TestSheetsReporter:
    @patch("lib.sheets_reporter.build")
    @patch("lib.sheets_reporter.service_account.Credentials.from_service_account_info")
    def test_upload_creates_sheet_and_writes(self, mock_creds, mock_build, sample_results):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        mock_sheets = mock_service.spreadsheets.return_value
        mock_sheets.batchUpdate.return_value.execute.return_value = {
            "replies": [{"addSheet": {"properties": {"sheetId": 12345}}}]
        }
        mock_sheets.values.return_value.update.return_value.execute.return_value = {}

        reporter = SheetsReporter(
            spreadsheet_id="fake-id",
            credentials_json='{"type": "service_account"}',
        )
        reporter.upload(sample_results, dev_pic="Sony")

        mock_sheets.batchUpdate.assert_called_once()
        assert mock_sheets.values.return_value.update.call_count >= 1
