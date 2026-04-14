"""Post test report markdown to Confluence under QA Reports.

Usage:
    python scripts/post_confluence_report.py <TICKET> <report.md> --sprint SD-26-4-1

Reads JIRA_EMAIL and JIRA_API_TOKEN from environment.
Creates/updates page under: Engineering > QA Reports > <sprint> > <ticket>

Uses Confluence v1 REST API with storage (XHTML) format for reliability.
"""

import os
import re
import sys
import html
import requests

CONFLUENCE_BASE = "https://techsatudental.atlassian.net/wiki"
SPACE_KEY = "TD"
QA_REPORTS_PAGE_ID = "632553480"


def get_auth():
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        return None
    return (email, token)


def find_child_page_v1(auth, parent_id, title):
    """Find a child page by title using v1 API."""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {
        "spaceKey": SPACE_KEY,
        "title": title,
        "expand": "version",
    }
    resp = requests.get(url, params=params, auth=auth)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    for page in results:
        if page["title"] == title:
            return page["id"], page["version"]["number"]
    return None, None


def create_page_v1(auth, parent_id, title, html_body):
    """Create a page using v1 API with storage format."""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": SPACE_KEY},
        "ancestors": [{"id": str(parent_id)}],
        "body": {
            "storage": {
                "value": html_body,
                "representation": "storage",
            }
        },
    }
    resp = requests.post(url, json=payload, auth=auth,
                         headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    data = resp.json()
    return data["id"]


def update_page_v1(auth, page_id, title, html_body, version_number):
    """Update a page using v1 API."""
    url = f"{CONFLUENCE_BASE}/rest/api/content/{page_id}"
    payload = {
        "type": "page",
        "title": title,
        "version": {"number": version_number + 1},
        "body": {
            "storage": {
                "value": html_body,
                "representation": "storage",
            }
        },
    }
    resp = requests.put(url, json=payload, auth=auth,
                        headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return page_id


def markdown_to_html(md_content):
    """Convert markdown to Confluence storage format (XHTML).

    Handles: headings, tables, bold, inline code, code blocks, lists.
    """
    lines = md_content.split("\n")
    result = []
    in_code_block = False
    in_table = False
    table_header_done = False
    i = 0

    while i < len(lines):
        line = lines[i]

        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                result.append("]]></ac:plain-text-body></ac:structured-macro>")
                in_code_block = False
            else:
                lang = line.strip().replace("```", "").strip() or "json"
                result.append(f'<ac:structured-macro ac:name="code"><ac:parameter ac:name="language">{lang}</ac:parameter><ac:plain-text-body><![CDATA[')
                in_code_block = True
            i += 1
            continue

        if in_code_block:
            result.append(line)
            i += 1
            continue

        # Close table if needed
        if in_table and not line.strip().startswith("|"):
            result.append("</tbody></table>")
            in_table = False
            table_header_done = False

        # Table separator rows (|---|---|) - skip
        if line.strip().startswith("|") and re.match(r'^\|[\s\-:|]+\|$', line.strip()):
            table_header_done = True
            i += 1
            continue

        # Table rows
        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]

            if not in_table:
                result.append('<table><tbody>')
                in_table = True

            if not table_header_done:
                # This is the header row
                row = "<tr>" + "".join(f"<th><p>{_inline(html.escape(c))}</p></th>" for c in cells) + "</tr>"
            else:
                row = "<tr>" + "".join(f"<td><p>{_inline(html.escape(c))}</p></td>" for c in cells) + "</tr>"
            result.append(row)
            i += 1
            continue

        # Headings
        if line.startswith("#### "):
            result.append(f"<h4>{_inline(html.escape(line[5:]))}</h4>")
            i += 1
            continue
        if line.startswith("### "):
            result.append(f"<h3>{_inline(html.escape(line[4:]))}</h3>")
            i += 1
            continue
        if line.startswith("## "):
            result.append(f"<h2>{_inline(html.escape(line[3:]))}</h2>")
            i += 1
            continue
        if line.startswith("# "):
            result.append(f"<h1>{_inline(html.escape(line[2:]))}</h1>")
            i += 1
            continue

        # List items
        if line.startswith("- "):
            # Collect all list items
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(lines[i][2:])
                i += 1
            result.append("<ul>" + "".join(f"<li><p>{_inline(html.escape(item))}</p></li>" for item in items) + "</ul>")
            continue

        # Empty line
        if line.strip() == "":
            i += 1
            continue

        # Horizontal rule
        if line.strip() == "---":
            result.append("<hr/>")
            i += 1
            continue

        # Regular paragraph
        result.append(f"<p>{_inline(html.escape(line))}</p>")
        i += 1

    # Close any open table
    if in_table:
        result.append("</tbody></table>")

    return "\n".join(result)


def _inline(text):
    """Process inline markdown: **bold**, `code`."""
    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
    # Inline code
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    return text


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/post_confluence_report.py <TICKET> <report.md> --sprint SD-26-4-1")
        sys.exit(1)

    ticket = sys.argv[1]
    report_path = sys.argv[2]
    sprint = "SD-26-4-1"
    if "--sprint" in sys.argv:
        idx = sys.argv.index("--sprint")
        if idx + 1 < len(sys.argv):
            sprint = sys.argv[idx + 1]

    auth = get_auth()
    if not auth:
        print("[confluence] JIRA_EMAIL or JIRA_API_TOKEN not set — skipping")
        sys.exit(0)

    with open(report_path) as f:
        md_content = f.read()

    # Convert to HTML storage format
    html_body = markdown_to_html(md_content)

    # 1. Find or create sprint page
    sprint_id, sprint_ver = find_child_page_v1(auth, QA_REPORTS_PAGE_ID, sprint)
    if not sprint_id:
        print(f"[confluence] Creating sprint page '{sprint}'...")
        sprint_id = create_page_v1(auth, QA_REPORTS_PAGE_ID, sprint,
                                   f"<p>Sprint {html.escape(sprint)} — Automated QA test reports.</p>")
        print(f"[confluence] Created: {sprint_id}")
    else:
        print(f"[confluence] Found sprint page: {sprint_id}")

    # 2. Extract title from first line
    first_line = md_content.split("\n")[0].lstrip("# ").strip()
    title = first_line if first_line else f"{ticket} — Test Cases"

    # 3. Find existing page for this ticket
    existing_id, existing_ver = find_child_page_v1(auth, sprint_id, title)

    # Also search by ticket prefix in case title changed
    if not existing_id:
        url = f"{CONFLUENCE_BASE}/rest/api/content"
        params = {"spaceKey": SPACE_KEY, "title": ticket, "expand": "version"}
        resp = requests.get(url, params=params, auth=auth)
        if resp.ok:
            for page in resp.json().get("results", []):
                if page["title"].startswith(ticket):
                    existing_id = page["id"]
                    existing_ver = page["version"]["number"]
                    break

    if existing_id:
        print(f"[confluence] Updating existing page {existing_id}...")
        update_page_v1(auth, existing_id, title, html_body, existing_ver)
        page_id = existing_id
    else:
        print(f"[confluence] Creating page '{title}'...")
        page_id = create_page_v1(auth, sprint_id, title, html_body)

    page_url = f"{CONFLUENCE_BASE}/spaces/TD/pages/{page_id}"
    print(f"[confluence] Done: {page_url}")


if __name__ == "__main__":
    main()
