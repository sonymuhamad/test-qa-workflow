"""Post rich ADF test results comment on a Jira ticket.

Usage:
    python scripts/post_jira_comment.py <TICKET> <results.json> [--sheets-url URL]

Reads JIRA_EMAIL and JIRA_API_TOKEN from environment.
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from lib.jira_reporter import JiraReporter


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/post_jira_comment.py <TICKET> <results.json> [--sheets-url URL]")
        sys.exit(1)

    ticket = sys.argv[1]
    results_path = sys.argv[2]
    sheets_url = ""
    if "--sheets-url" in sys.argv:
        idx = sys.argv.index("--sheets-url")
        if idx + 1 < len(sys.argv):
            sheets_url = sys.argv[idx + 1]

    email = os.environ.get("JIRA_EMAIL", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")

    if not email or not api_token:
        print("[jira] JIRA_EMAIL or JIRA_API_TOKEN not set — skipping")
        sys.exit(0)

    with open(results_path) as f:
        results = json.load(f)

    # If no sheets URL provided, try default spreadsheet
    if not sheets_url:
        spreadsheet_id = os.environ.get("QA_SPREADSHEET_ID", "")
        if spreadsheet_id:
            sheets_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"

    reporter = JiraReporter(
        base_url="https://techsatudental.atlassian.net",
        email=email,
        api_token=api_token,
    )

    print(f"[jira] Posting comment on {ticket}...")
    reporter.post_comment(ticket, results, sheets_url=sheets_url)
    print(f"[jira] Done (sheets_url={sheets_url})")


if __name__ == "__main__":
    main()
