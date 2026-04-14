"""Post test results as a Confluence page under QA Reports.

Usage:
    python scripts/post_confluence_report.py <TICKET> <results.json> --sprint SD-26-4-1

Reads JIRA_EMAIL and JIRA_API_TOKEN from environment.
Creates page under: Engineering > QA Reports > <sprint> > <ticket>

Structure:
  QA Reports (id: 632553480)
    └── SD-26-4-1 (sprint page, created if not exists)
          └── SD-3311 (test report page)
"""

import json
import os
import sys
import requests
from datetime import datetime

CONFLUENCE_BASE = "https://techsatudental.atlassian.net/wiki"
CLOUD_ID = "techsatudental.atlassian.net"
SPACE_ID = "44793860"  # Engineering space
QA_REPORTS_PAGE_ID = "632553480"


def get_auth():
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        return None
    return (email, token)


def find_child_page(auth, parent_id, title):
    """Find a child page by title under a parent."""
    url = f"{CONFLUENCE_BASE}/api/v2/pages/{parent_id}/children"
    params = {"limit": 100}
    resp = requests.get(url, params=params, auth=auth)
    resp.raise_for_status()
    for page in resp.json().get("results", []):
        if page["title"] == title:
            return page["id"]
    return None


def create_page(auth, parent_id, title, body_markdown):
    """Create a Confluence page with markdown content."""
    url = f"{CONFLUENCE_BASE}/api/v2/pages"
    payload = {
        "spaceId": SPACE_ID,
        "parentId": parent_id,
        "title": title,
        "status": "current",
        "body": {
            "representation": "wiki",
            "value": body_markdown,
        },
    }
    resp = requests.post(url, json=payload, auth=auth,
                         headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    page = resp.json()
    return page["id"]


def update_page(auth, page_id, title, body_markdown):
    """Update an existing Confluence page."""
    # Get current version
    url = f"{CONFLUENCE_BASE}/api/v2/pages/{page_id}"
    resp = requests.get(url, auth=auth)
    resp.raise_for_status()
    current_version = resp.json()["version"]["number"]

    payload = {
        "id": page_id,
        "title": title,
        "spaceId": SPACE_ID,
        "status": "current",
        "version": {"number": current_version + 1, "message": "Updated by QA Bot"},
        "body": {
            "representation": "wiki",
            "value": body_markdown,
        },
    }
    resp = requests.put(url, json=payload, auth=auth,
                        headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return page_id


def format_report_wiki(results: dict) -> str:
    """Format test results as Confluence wiki markup."""
    ticket = results["ticket"]
    run_id = results["run_id"]
    summary = results["summary"]
    test_cases = results["test_cases"]
    now = datetime.now().strftime("%Y-%m-%d %H:%M WIB")

    lines = []

    # Header info panel
    lines.append("{info:title=Test Run Info}")
    lines.append(f"*Ticket:* {ticket}")
    lines.append(f"*Run ID:* {{{{monospace:{run_id}}}}}")
    lines.append(f"*Date:* {now}")
    lines.append(f"*Environment:* Staging")
    lines.append(f"*Tester:* Claude (automated)")
    lines.append("{info}")
    lines.append("")

    # Summary panel
    total = summary["total"]
    passed = summary["passed"]
    failed = summary["failed"]
    skipped = summary.get("skipped", 0)

    if failed == 0:
        lines.append("{panel:bgColor=#dff0d8}")
        lines.append(f"h3. (/) All {total} test cases PASSED")
        lines.append("{panel}")
    else:
        lines.append("{panel:bgColor=#f2dede}")
        lines.append(f"h3. (x) {failed} of {total} test cases FAILED")
        lines.append("{panel}")

    lines.append("")
    lines.append("h2. Summary")
    lines.append("")
    lines.append("||Status||Count||")
    lines.append(f"|(/)(green) PASS|{passed}|")
    lines.append(f"|(x)(red) FAIL|{failed}|")
    if skipped > 0:
        lines.append(f"|(!) SKIP|{skipped}|")
    lines.append(f"|*Total*|*{total}*|")
    lines.append("")

    # Group test cases by category
    categories = {}
    for tc in test_cases:
        cat = tc.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(tc)

    # Results by category
    for cat, cases in categories.items():
        lines.append(f"h2. {cat}")
        lines.append("")
        lines.append("||#||Scenario||Expected||Actual||Status||")

        for tc in cases:
            tc_id = tc["id"]
            desc = tc["description"]
            resp = tc.get("response", {})
            actual_code = resp.get("status_code", "")
            status = tc["status"]
            reason = tc.get("failure_reason", "")

            # Status icon
            if status == "PASS":
                status_icon = "(/)"
            elif status == "FAIL":
                status_icon = "(x)"
            else:
                status_icon = "(!)"

            # Expected from description or failure reason
            expected = ""
            if reason:
                # Extract expected from failure reason like "Expected status 400, got 200"
                expected = reason
            else:
                expected = str(actual_code)

            lines.append(f"|{tc_id}|{desc}|{expected}|{actual_code}|{status_icon} {status}|")

        lines.append("")

    # Failed test details
    failed_cases = [tc for tc in test_cases if tc["status"] == "FAIL"]
    if failed_cases:
        lines.append("h2. Failed Test Details")
        lines.append("")

        for tc in failed_cases:
            lines.append(f"h3. TC#{tc['id']} — {tc['description']}")
            lines.append("")

            req = tc.get("request", {})
            resp = tc.get("response", {})

            lines.append(f"*Request:* {{{{monospace:{req.get('method', '')} {req.get('url', '')}}}}}")

            req_body = req.get("body")
            if req_body:
                lines.append("{code:json}")
                lines.append(json.dumps(req_body, indent=2))
                lines.append("{code}")

            lines.append(f"*Response:* Status {resp.get('status_code', '')}")
            resp_body = resp.get("body")
            if resp_body:
                resp_str = json.dumps(resp_body, indent=2)
                if len(resp_str) > 2000:
                    resp_str = resp_str[:2000] + "\n... (truncated)"
                lines.append("{code:json}")
                lines.append(resp_str)
                lines.append("{code}")

            if tc.get("failure_reason"):
                lines.append(f"*Reason:* {tc['failure_reason']}")
            lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/post_confluence_report.py <TICKET> <results.json> --sprint SD-26-4-1")
        sys.exit(1)

    ticket = sys.argv[1]
    results_path = sys.argv[2]
    sprint = "SD-26-4-1"  # default
    if "--sprint" in sys.argv:
        idx = sys.argv.index("--sprint")
        if idx + 1 < len(sys.argv):
            sprint = sys.argv[idx + 1]

    auth = get_auth()
    if not auth:
        print("[confluence] JIRA_EMAIL or JIRA_API_TOKEN not set — skipping")
        sys.exit(0)

    with open(results_path) as f:
        results = json.load(f)

    # 1. Find or create sprint page under QA Reports
    sprint_page_id = find_child_page(auth, QA_REPORTS_PAGE_ID, sprint)
    if not sprint_page_id:
        print(f"[confluence] Creating sprint page '{sprint}'...")
        sprint_page_id = create_page(auth, QA_REPORTS_PAGE_ID, sprint,
                                     f"Sprint {sprint} — Automated QA test reports.")
        print(f"[confluence] Created sprint page: {sprint_page_id}")
    else:
        print(f"[confluence] Found sprint page '{sprint}': {sprint_page_id}")

    # 2. Format report
    wiki_body = format_report_wiki(results)

    # 3. Find or create/update ticket report page
    summary = results["summary"]
    title = f"{ticket} — {summary['passed']}/{summary['total']} PASSED"

    existing_page_id = find_child_page(auth, sprint_page_id, None)
    # Search for any page starting with ticket name
    for child in _list_children(auth, sprint_page_id):
        if child["title"].startswith(ticket):
            existing_page_id = child["id"]
            break
    else:
        existing_page_id = None

    if existing_page_id:
        print(f"[confluence] Updating existing page for {ticket}...")
        update_page(auth, existing_page_id, title, wiki_body)
        page_id = existing_page_id
    else:
        print(f"[confluence] Creating report page for {ticket}...")
        page_id = create_page(auth, sprint_page_id, title, wiki_body)

    page_url = f"{CONFLUENCE_BASE}/spaces/TD/pages/{page_id}"
    print(f"[confluence] Report posted: {page_url}")
    print(f"[confluence] Done")


def _list_children(auth, parent_id):
    """List all child pages."""
    url = f"{CONFLUENCE_BASE}/api/v2/pages/{parent_id}/children"
    resp = requests.get(url, params={"limit": 100}, auth=auth)
    resp.raise_for_status()
    return resp.json().get("results", [])


if __name__ == "__main__":
    main()
