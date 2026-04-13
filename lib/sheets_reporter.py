"""Upload test results to Google Sheets in the QA spreadsheet format."""

import json
from datetime import datetime
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def format_header_stats(summary: dict) -> list[list]:
    """Format the header stats rows matching QA spreadsheet format."""
    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    defect_pct = f"{(failed / total * 100):.2f}%" if total > 0 else "0.00%"

    return [
        ["PASS", "", passed],
        ["FAILED", "", failed],
        ["Number Of Test Case", "", total],
        ["Bug Fixed", "", 0],
        ["Postponed", "", 0],
        ["Staging Defect Percentage", "", defect_pct],
    ]


def format_test_case_row(tc: dict, dev_pic: str = "", testing_date: str = "") -> list:
    """Format a single test case as a spreadsheet row."""
    request = tc.get("request", {})
    response = tc.get("response", {})

    url = request.get("url", "")
    method = request.get("method", "")
    path = url.split("//", 1)[-1].split("/", 1)[-1] if "//" in url else url
    if path and not path.startswith("/"):
        path = "/" + path
    endpoint = f"{method}\n/{path}" if method else ""

    body = request.get("body")
    body_str = json.dumps(body, indent=2) if body else ""

    resp_body = response.get("body")
    resp_str = json.dumps(resp_body, indent=2) if resp_body else ""

    status = "PASS" if tc["status"] == "PASS" else "FAILED"
    feedback = tc.get("failure_reason", "") or ""
    has_auth = "YES" if "Authorization" in request.get("headers", {}) else "NO"

    severity_map = {
        "Auth": "Critical",
        "Happy Path": "High",
        "Validation": "Medium",
        "Edge Case": "Low",
        "Regression": "High",
    }
    severity = severity_map.get(tc.get("category", ""), "Medium")

    return [
        tc["id"],
        endpoint,
        tc["description"],
        body_str,
        "",
        response.get("status_code"),
        resp_str,
        feedback,
        status,
        dev_pic,
        "Claude (automated)",
        tc.get("category", ""),
        has_auth,
        testing_date,
        "",
        severity,
    ]


class SheetsReporter:
    """Upload test results to Google Sheets."""

    def __init__(self, spreadsheet_id: str, credentials_json: str):
        creds_dict = json.loads(credentials_json)
        creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
        self.service = build("sheets", "v4", credentials=creds)
        self.spreadsheet_id = spreadsheet_id

    def upload(self, results: dict, dev_pic: str = ""):
        """Create a new sheet tab and write results."""
        ticket = results["ticket"]
        testing_date = datetime.now().strftime("%d/%m/%Y")

        sheet_name = ticket
        body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
        try:
            self.service.spreadsheets().batchUpdate(
                spreadsheetId=self.spreadsheet_id, body=body
            ).execute()
        except Exception:
            self.service.spreadsheets().values().clear(
                spreadsheetId=self.spreadsheet_id, range=f"{sheet_name}!A:P"
            ).execute()

        header_stats = format_header_stats(results["summary"])
        column_headers = [
            "No.", "Endpoint", "Case Description", "Request Body",
            "Query Param", "Response Code", "Response", "Feedback",
            "Status", "Dev PIC", "QA PIC", "Note", "Authorization",
            "Testing Date", "Re-Testing Date", "Severity",
        ]
        rows = []
        for tc in results["test_cases"]:
            rows.append(format_test_case_row(tc, dev_pic=dev_pic, testing_date=testing_date))

        all_data = header_stats + [[]] + [column_headers] + rows

        self.service.spreadsheets().values().update(
            spreadsheetId=self.spreadsheet_id,
            range=f"{sheet_name}!A1",
            valueInputOption="RAW",
            body={"values": all_data},
        ).execute()
