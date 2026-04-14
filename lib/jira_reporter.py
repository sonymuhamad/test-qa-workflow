"""Post test results as rich Jira ticket comments using Atlassian Document Format (ADF)."""

import json
import requests
from datetime import datetime


def _text(content: str, marks: list | None = None) -> dict:
    """Create an ADF text node."""
    node = {"type": "text", "text": content}
    if marks:
        node["marks"] = marks
    return node


def _bold(content: str) -> dict:
    return _text(content, marks=[{"type": "strong"}])


def _code(content: str) -> dict:
    return _text(content, marks=[{"type": "code"}])


def _link(content: str, href: str) -> dict:
    return _text(content, marks=[{"type": "link", "attrs": {"href": href}}])


def _paragraph(*children) -> dict:
    return {"type": "paragraph", "content": list(children)}


def _heading(text: str, level: int = 3) -> dict:
    return {"type": "heading", "attrs": {"level": level}, "content": [_text(text)]}


def _code_block(code: str, language: str = "json") -> dict:
    return {
        "type": "codeBlock",
        "attrs": {"language": language},
        "content": [_text(code)],
    }


def _table_row(cells: list[dict], header: bool = False) -> dict:
    cell_type = "tableHeader" if header else "tableCell"
    return {
        "type": "tableRow",
        "content": [
            {"type": cell_type, "content": [c] if c.get("type") != "paragraph" else [c]}
            for c in cells
        ],
    }


def _table(rows: list[dict]) -> dict:
    return {
        "type": "table",
        "attrs": {"isNumberColumnEnabled": False, "layout": "default"},
        "content": rows,
    }


def _rule() -> dict:
    return {"type": "rule"}


def _status(text: str, color: str) -> dict:
    """Create an ADF status lozenge."""
    return {
        "type": "status",
        "attrs": {"text": text, "color": color, "style": ""},
    }


def _expand(title: str, content: list[dict]) -> dict:
    """Create an ADF expand (collapsible) section."""
    return {
        "type": "expand",
        "attrs": {"title": title},
        "content": content,
    }


def build_adf_comment(results: dict, sheets_url: str = "") -> dict:
    """Build a rich ADF document for Jira comment."""
    summary = results["summary"]
    ticket = results["ticket"]
    run_id = results["run_id"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")

    doc_content = []

    # Header
    doc_content.append(_heading("Automated QA Report", level=2))

    # Run info table
    doc_content.append(_table([
        _table_row([_paragraph(_bold("Ticket")), _paragraph(_text(ticket))]),
        _table_row([_paragraph(_bold("Run ID")), _paragraph(_code(run_id))]),
        _table_row([_paragraph(_bold("Date")), _paragraph(_text(now))]),
        _table_row([_paragraph(_bold("Environment")), _paragraph(_text("Staging"))]),
    ]))

    doc_content.append(_rule())

    # Results summary
    doc_content.append(_heading("Results Summary", level=3))

    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    skipped = summary.get("skipped", 0)

    summary_rows = [
        _table_row([_paragraph(_bold("Status")), _paragraph(_bold("Count"))], header=True),
        _table_row([
            _paragraph(_status("PASS", "green")),
            _paragraph(_text(str(passed))),
        ]),
        _table_row([
            _paragraph(_status("FAIL", "red")),
            _paragraph(_text(str(failed))),
        ]),
        _table_row([
            _paragraph(_status("SKIP", "yellow")),
            _paragraph(_text(str(skipped))),
        ]),
        _table_row([
            _paragraph(_bold("Total")),
            _paragraph(_bold(str(total))),
        ]),
    ]
    doc_content.append(_table(summary_rows))

    doc_content.append(_rule())

    # Failed test cases detail
    failed_cases = [tc for tc in results["test_cases"] if tc["status"] == "FAIL"]
    if failed_cases:
        doc_content.append(_heading("Failed Test Cases", level=3))

        # Summary table of failures
        fail_header = _table_row([
            _paragraph(_bold("#")),
            _paragraph(_bold("Category")),
            _paragraph(_bold("Description")),
            _paragraph(_bold("Expected")),
            _paragraph(_bold("Actual")),
        ], header=True)

        fail_rows = [fail_header]
        for tc in failed_cases:
            expected_code = ""
            if "request" in tc:
                pass
            response = tc.get("response", {})
            actual_code = str(response.get("status_code", ""))

            fail_rows.append(_table_row([
                _paragraph(_text(str(tc["id"]))),
                _paragraph(_text(tc.get("category", ""))),
                _paragraph(_text(tc["description"])),
                _paragraph(_text(tc.get("failure_reason", ""))),
                _paragraph(_text(actual_code)),
            ]))

        doc_content.append(_table(fail_rows))

        # Expand sections for each failed test with request/response detail
        for tc in failed_cases:
            request_data = tc.get("request", {})
            response_data = tc.get("response", {})

            expand_content = []

            # Request detail
            method = request_data.get("method", "")
            url = request_data.get("url", "")
            expand_content.append(_paragraph(_bold("Request: "), _code(f"{method} {url}")))

            req_body = request_data.get("body")
            if req_body:
                expand_content.append(_code_block(json.dumps(req_body, indent=2)))

            # Response detail
            status_code = response_data.get("status_code", "")
            expand_content.append(_paragraph(_bold("Response: "), _text(f"Status {status_code}")))

            resp_body = response_data.get("body")
            if resp_body:
                resp_str = json.dumps(resp_body, indent=2)
                if len(resp_str) > 2000:
                    resp_str = resp_str[:2000] + "\n... (truncated)"
                expand_content.append(_code_block(resp_str))

            # Failure reason
            reason = tc.get("failure_reason", "")
            if reason:
                expand_content.append(_paragraph(_bold("Reason: "), _text(reason)))

            title = f"TC#{tc['id']} - {tc['description']}"
            doc_content.append(_expand(title, expand_content))
    else:
        doc_content.append(_paragraph(
            _status("ALL PASSED", "green"),
            _text(f" — all {total} test cases passed"),
        ))

    # Sheets link
    if sheets_url:
        doc_content.append(_rule())
        doc_content.append(_paragraph(
            _bold("Full Results: "),
            _link("Google Sheets", sheets_url),
        ))

    return {
        "version": 1,
        "type": "doc",
        "content": doc_content,
    }


def format_comment(results: dict, sheets_url: str = "") -> str:
    """Format test results as a plain text Jira comment (legacy fallback)."""
    summary = results["summary"]
    run_id = results["run_id"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")

    lines = [
        f"Automated QA Report - Run #{run_id}",
        "",
        f"PASSED: {summary['passed']} | FAILED: {summary['failed']} | SKIPPED: {summary['skipped']} | Total: {summary['total']}",
        f"Tested at: {now}",
        "",
    ]

    failed = [tc for tc in results["test_cases"] if tc["status"] == "FAIL"]
    if failed:
        lines.append("Failed Test Cases:")
        for tc in failed:
            lines.append(f"  #{tc['id']} [{tc['category']}] {tc['description']} - {tc.get('failure_reason', '')}")
        lines.append("")

    if sheets_url:
        lines.append(f"Full Results: {sheets_url}")

    return "\n".join(lines)


class JiraReporter:
    """Post comments on Jira tickets."""

    def __init__(self, base_url: str, email: str, api_token: str):
        self.base_url = base_url.rstrip("/")
        self.auth = (email, api_token)

    def post_comment(self, ticket: str, results: dict, sheets_url: str = ""):
        """Post a rich ADF comment on the Jira ticket."""
        adf_body = build_adf_comment(results, sheets_url=sheets_url)

        url = f"{self.base_url}/rest/api/3/issue/{ticket}/comment"
        payload = {"body": adf_body}

        response = requests.post(
            url, json=payload, auth=self.auth,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
