"""Post test report markdown to Confluence under QA Reports.

Usage:
    python scripts/post_confluence_report.py <TICKET> <report.md> --sprint SD-26-4-1

Reads JIRA_EMAIL and JIRA_API_TOKEN from environment.
Creates/updates page under: Engineering > QA Reports > <sprint> > <ticket>
"""

import os
import re
import sys
import html
import requests

CONFLUENCE_BASE = "https://techsatudental.atlassian.net/wiki"
SPACE_KEY = "TD"
SPACE_ID = "44793860"
QA_REPORTS_PAGE_ID = "632553480"


def get_auth():
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        return None
    return (email, token)


def list_children_v2(auth, parent_id):
    """List child pages using v2 API."""
    url = f"{CONFLUENCE_BASE}/api/v2/pages/{parent_id}/children"
    resp = requests.get(url, params={"limit": 100}, auth=auth)
    resp.raise_for_status()
    return resp.json().get("results", [])


def find_page_by_title_v1(auth, title):
    """Find page by exact title in space."""
    url = f"{CONFLUENCE_BASE}/rest/api/content"
    params = {"spaceKey": SPACE_KEY, "title": title, "expand": "version"}
    resp = requests.get(url, params=params, auth=auth)
    resp.raise_for_status()
    results = resp.json().get("results", [])
    if results:
        return results[0]["id"], results[0]["version"]["number"]
    return None, None


def create_page_v1(auth, parent_id, title, html_body):
    """Create page using v1 API with storage format."""
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
    if resp.status_code >= 400:
        print(f"[confluence] Create failed ({resp.status_code}): {resp.text[:500]}")
    resp.raise_for_status()
    return resp.json()["id"]


def update_page_v1(auth, page_id, title, html_body, version_number):
    """Update page using v1 API."""
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
    if resp.status_code >= 400:
        print(f"[confluence] Update failed ({resp.status_code}): {resp.text[:500]}")
    resp.raise_for_status()
    return page_id


def markdown_to_html(md_content):
    """Convert markdown to Confluence storage format (XHTML)."""
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

        # Table separator rows
        if line.strip().startswith("|") and re.match(r'^\|[\s\-:|]+\|$', line.strip()):
            table_header_done = True
            i += 1
            continue

        # Table rows
        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]

            if not in_table:
                result.append('<table><colgroup></colgroup><tbody>')
                in_table = True

            if not table_header_done:
                row = "<tr>" + "".join(f"<th><p>{_inline(html.escape(c))}</p></th>" for c in cells) + "</tr>"
            else:
                row = "<tr>" + "".join(f"<td><p>{_inline(html.escape(c))}</p></td>" for c in cells) + "</tr>"
            result.append(row)
            i += 1
            continue

        # Headings
        for level in [4, 3, 2, 1]:
            prefix = "#" * level + " "
            if line.startswith(prefix):
                result.append(f"<h{level}>{_inline(html.escape(line[len(prefix):]))}</h{level}>")
                break
        else:
            # List items
            if line.startswith("  - "):
                items = []
                while i < len(lines) and lines[i].startswith("  - "):
                    items.append(lines[i][4:])
                    i += 1
                result.append("<ul>" + "".join(f"<li><p>{_inline(html.escape(item))}</p></li>" for item in items) + "</ul>")
                continue
            elif line.startswith("- "):
                items = []
                while i < len(lines) and lines[i].startswith("- "):
                    items.append(lines[i][2:])
                    i += 1
                result.append("<ul>" + "".join(f"<li><p>{_inline(html.escape(item))}</p></li>" for item in items) + "</ul>")
                continue
            elif line.strip() == "---":
                result.append("<hr/>")
            elif line.strip() == "":
                pass  # skip empty
            else:
                result.append(f"<p>{_inline(html.escape(line))}</p>")

        i += 1

    if in_table:
        result.append("</tbody></table>")

    return "\n".join(result)


def _inline(text):
    """Process inline markdown: **bold**, `code`."""
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)
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

    html_body = markdown_to_html(md_content)

    # 1. Find or create sprint page
    sprint_id = None
    for child in list_children_v2(auth, QA_REPORTS_PAGE_ID):
        if child["title"] == sprint:
            sprint_id = child["id"]
            break

    if not sprint_id:
        print(f"[confluence] Creating sprint page '{sprint}'...")
        sprint_id = create_page_v1(auth, QA_REPORTS_PAGE_ID, sprint,
                                   f"<p>Sprint {html.escape(sprint)} — Automated QA test reports.</p>")
        print(f"[confluence] Created: {sprint_id}")
    else:
        print(f"[confluence] Found sprint page: {sprint_id}")

    # 2. Extract title from markdown first line
    first_line = md_content.split("\n")[0].lstrip("# ").strip()
    title = first_line if first_line else f"{ticket} — Test Cases"

    # 3. Check if page for this ticket already exists under sprint
    existing_id = None
    existing_ver = None
    for child in list_children_v2(auth, sprint_id):
        if child["title"].startswith(ticket):
            # Found existing page — get version number via v1 API
            existing_id = child["id"]
            _, existing_ver = find_page_by_title_v1(auth, child["title"])
            if not existing_ver:
                existing_ver = 1
            print(f"[confluence] Found existing page: {existing_id} (v{existing_ver})")
            break

    if existing_id:
        print(f"[confluence] Updating page '{title}'...")
        update_page_v1(auth, existing_id, title, html_body, existing_ver)
        page_id = existing_id
    else:
        print(f"[confluence] Creating page '{title}'...")
        page_id = create_page_v1(auth, sprint_id, title, html_body)

    page_url = f"{CONFLUENCE_BASE}/spaces/{SPACE_KEY}/pages/{page_id}"
    print(f"[confluence] Done: {page_url}")


if __name__ == "__main__":
    main()
