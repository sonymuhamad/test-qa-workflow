"""Post test results as Jira ticket comments."""

import requests
from datetime import datetime


def format_comment(results: dict, sheets_url: str = "") -> str:
    """Format test results as a Jira comment."""
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
        """Post a formatted comment on the Jira ticket."""
        comment_body = format_comment(results, sheets_url=sheets_url)

        url = f"{self.base_url}/rest/api/3/issue/{ticket}/comment"
        payload = {
            "body": {
                "type": "doc",
                "version": 1,
                "content": [
                    {
                        "type": "codeBlock",
                        "content": [{"type": "text", "text": comment_body}],
                    }
                ],
            }
        }

        response = requests.post(
            url, json=payload, auth=self.auth,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
