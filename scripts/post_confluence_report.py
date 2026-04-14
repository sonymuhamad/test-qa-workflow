"""Post test report markdown to Confluence under QA Reports.

Usage:
    python scripts/post_confluence_report.py <TICKET> <report.md> --sprint SD-26-4-1

Reads JIRA_EMAIL and JIRA_API_TOKEN from environment.
Creates/updates page under: Engineering > QA Reports > <sprint> > <ticket>
"""

import os
import sys
import requests

CONFLUENCE_BASE = "https://techsatudental.atlassian.net/wiki"
SPACE_ID = "44793860"  # Engineering space
QA_REPORTS_PAGE_ID = "632553480"


def get_auth():
    email = os.environ.get("JIRA_EMAIL", "")
    token = os.environ.get("JIRA_API_TOKEN", "")
    if not email or not token:
        return None
    return (email, token)


def list_children(auth, parent_id):
    """List all child pages."""
    url = f"{CONFLUENCE_BASE}/api/v2/pages/{parent_id}/children"
    resp = requests.get(url, params={"limit": 100}, auth=auth)
    resp.raise_for_status()
    return resp.json().get("results", [])


def find_child_by_title(auth, parent_id, title):
    """Find a child page by exact title."""
    for child in list_children(auth, parent_id):
        if child["title"] == title:
            return child["id"]
    return None


def find_child_by_prefix(auth, parent_id, prefix):
    """Find a child page whose title starts with prefix."""
    for child in list_children(auth, parent_id):
        if child["title"].startswith(prefix):
            return child["id"], child["title"]
    return None, None


def create_page(auth, parent_id, title, body, content_format="wiki"):
    """Create a Confluence page."""
    url = f"{CONFLUENCE_BASE}/api/v2/pages"
    payload = {
        "spaceId": SPACE_ID,
        "parentId": parent_id,
        "title": title,
        "status": "current",
        "body": {
            "representation": content_format,
            "value": body,
        },
    }
    resp = requests.post(url, json=payload, auth=auth,
                         headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return resp.json()["id"]


def update_page(auth, page_id, title, body, content_format="wiki"):
    """Update an existing Confluence page."""
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
            "representation": content_format,
            "value": body,
        },
    }
    resp = requests.put(url, json=payload, auth=auth,
                        headers={"Content-Type": "application/json"})
    resp.raise_for_status()
    return page_id


def markdown_to_confluence_wiki(md_content):
    """Convert markdown to Confluence wiki markup.

    Handles the subset of markdown used in our test reports:
    - # headings -> h1., h2., h3.
    - | tables | -> || header || and | cell |
    - `code` -> {{code}}
    - **bold** -> *bold*
    - ```code blocks``` -> {code}...{code}
    - - list items -> * list items
    """
    lines = md_content.split("\n")
    result = []
    in_code_block = False
    prev_was_table_header = False

    for i, line in enumerate(lines):
        # Code blocks
        if line.strip().startswith("```"):
            if in_code_block:
                result.append("{code}")
                in_code_block = False
            else:
                lang = line.strip().replace("```", "").strip()
                if lang:
                    result.append(f"{{code:language={lang}}}")
                else:
                    result.append("{code}")
                in_code_block = True
            continue

        if in_code_block:
            result.append(line)
            continue

        # Headings
        if line.startswith("# "):
            result.append(f"h1. {line[2:]}")
            continue
        if line.startswith("## "):
            result.append(f"h2. {line[3:]}")
            continue
        if line.startswith("### "):
            result.append(f"h3. {line[4:]}")
            continue
        if line.startswith("#### "):
            result.append(f"h4. {line[5:]}")
            continue

        # Table separator rows (|---|---|) - skip
        if line.strip().startswith("|") and set(line.replace("|", "").replace("-", "").replace(":", "").strip()) == set():
            # Next: check if previous line was a header row
            prev_was_table_header = True
            continue

        # Table rows
        if line.strip().startswith("|") and line.strip().endswith("|"):
            cells = [c.strip() for c in line.strip().split("|")[1:-1]]
            if prev_was_table_header:
                # The row BEFORE the separator was the header — already added, need to re-format it
                # Pop the last added line and re-add as header
                if result and result[-1].startswith("|"):
                    header_line = result.pop()
                    header_cells = [c.strip() for c in header_line.split("|")[1:-1]]
                    result.append("||" + "||".join(header_cells) + "||")
                prev_was_table_header = False
                # Current line is first data row
                result.append("|" + "|".join(cells) + "|")
            else:
                result.append("|" + "|".join(cells) + "|")
            continue

        prev_was_table_header = False

        # List items
        if line.startswith("- "):
            result.append(f"* {line[2:]}")
            continue
        if line.startswith("  - "):
            result.append(f"** {line[4:]}")
            continue

        # Inline formatting
        processed = line
        # Bold: **text** -> *text*
        import re
        processed = re.sub(r'\*\*(.+?)\*\*', r'*\1*', processed)
        # Inline code: `text` -> {{text}}
        processed = re.sub(r'`(.+?)`', r'{{\1}}', processed)

        result.append(processed)

    return "\n".join(result)


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/post_confluence_report.py <TICKET> <report.md> --sprint SD-26-4-1")
        sys.exit(1)

    ticket = sys.argv[1]
    report_path = sys.argv[2]
    sprint = "SD-26-4-1"  # default
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

    # Convert markdown to Confluence wiki markup
    wiki_content = markdown_to_confluence_wiki(md_content)

    # 1. Find or create sprint page under QA Reports
    sprint_page_id = find_child_by_title(auth, QA_REPORTS_PAGE_ID, sprint)
    if not sprint_page_id:
        print(f"[confluence] Creating sprint page '{sprint}'...")
        sprint_page_id = create_page(auth, QA_REPORTS_PAGE_ID, sprint,
                                     f"Sprint {sprint} — Automated QA test reports.")
        print(f"[confluence] Created sprint page: {sprint_page_id}")
    else:
        print(f"[confluence] Found sprint page '{sprint}': {sprint_page_id}")

    # 2. Find existing page for this ticket or create new
    # Extract title from first line of markdown
    first_line = md_content.split("\n")[0].lstrip("# ").strip()
    title = first_line if first_line else f"{ticket} — Test Cases"

    existing_id, existing_title = find_child_by_prefix(auth, sprint_page_id, ticket)

    if existing_id:
        print(f"[confluence] Updating existing page '{existing_title}'...")
        update_page(auth, existing_id, title, wiki_content)
        page_id = existing_id
    else:
        print(f"[confluence] Creating report page '{title}'...")
        page_id = create_page(auth, sprint_page_id, title, wiki_content)

    page_url = f"{CONFLUENCE_BASE}/spaces/TD/pages/{page_id}"
    print(f"[confluence] Report posted: {page_url}")


if __name__ == "__main__":
    main()
