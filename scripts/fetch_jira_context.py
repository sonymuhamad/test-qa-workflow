"""Fetch Jira ticket context for Claude test case generation.

Usage:
    python scripts/fetch_jira_context.py SD-3311

Reads JIRA_EMAIL and JIRA_API_TOKEN from environment.
Writes context to jira_context/<ticket>.md
"""

import os
import re
import sys
import json
import requests
from datetime import datetime


JIRA_BASE_URL = "https://techsatudental.atlassian.net"


def fetch_issue(ticket: str, email: str, api_token: str) -> dict:
    """Fetch Jira issue details."""
    url = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket}"
    params = {"fields": "summary,description,status,assignee,comment,issuelinks,labels,priority"}
    response = requests.get(url, params=params, auth=(email, api_token))
    response.raise_for_status()
    return response.json()


def adf_to_text(node: dict | list | str | None, depth: int = 0) -> str:
    """Convert Atlassian Document Format (ADF) to plain text."""
    if node is None:
        return ""
    if isinstance(node, str):
        return node
    if isinstance(node, list):
        return "".join(adf_to_text(n, depth) for n in node)
    if not isinstance(node, dict):
        return str(node)

    node_type = node.get("type", "")
    content = node.get("content", [])
    text = node.get("text", "")

    if node_type == "text":
        return text
    if node_type == "paragraph":
        return adf_to_text(content, depth) + "\n"
    if node_type == "heading":
        level = node.get("attrs", {}).get("level", 1)
        return "#" * level + " " + adf_to_text(content, depth) + "\n"
    if node_type == "bulletList":
        return "".join(adf_to_text(item, depth) for item in content)
    if node_type == "orderedList":
        return "".join(adf_to_text(item, depth) for item in content)
    if node_type == "listItem":
        return "  " * depth + "- " + adf_to_text(content, depth + 1).strip() + "\n"
    if node_type == "codeBlock":
        code = adf_to_text(content, depth)
        return f"```\n{code}```\n"
    if node_type == "table":
        rows = []
        for row in content:
            cells = []
            for cell in row.get("content", []):
                cells.append(adf_to_text(cell.get("content", []), depth).strip())
            rows.append(" | ".join(cells))
        return "\n".join(rows) + "\n"
    if node_type == "inlineCard" or node_type == "blockCard":
        url = node.get("attrs", {}).get("url", "")
        return url
    if node_type == "mediaSingle" or node_type == "media":
        return "[media attachment]\n"
    if node_type == "doc":
        return adf_to_text(content, depth)

    return adf_to_text(content, depth)


def extract_spreadsheet_urls(text: str) -> list[str]:
    """Extract Google Sheets URLs from text."""
    pattern = r"https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+[^\s\)\]\|]*"
    return list(set(re.findall(pattern, text)))


def format_context(issue: dict, ticket: str) -> str:
    """Format Jira issue data as markdown context for Claude."""
    fields = issue.get("fields", {})

    lines = [
        f"# Jira Ticket: {ticket}",
        "",
        f"**Summary:** {fields.get('summary', 'N/A')}",
        f"**Status:** {fields.get('status', {}).get('name', 'N/A')}",
        f"**Priority:** {fields.get('priority', {}).get('name', 'N/A')}",
        f"**Assignee:** {fields.get('assignee', {}).get('displayName', 'Unassigned') if fields.get('assignee') else 'Unassigned'}",
        "",
    ]

    # Labels
    labels = fields.get("labels", [])
    if labels:
        lines.append(f"**Labels:** {', '.join(labels)}")
        lines.append("")

    # Linked issues
    issue_links = fields.get("issuelinks", [])
    if issue_links:
        lines.append("## Linked Issues")
        for link in issue_links:
            link_type = link.get("type", {}).get("outward", "relates to")
            if "outwardIssue" in link:
                linked = link["outwardIssue"]
                lines.append(f"- {link_type}: {linked['key']} — {linked['fields']['summary']}")
            elif "inwardIssue" in link:
                link_type = link.get("type", {}).get("inward", "relates to")
                linked = link["inwardIssue"]
                lines.append(f"- {link_type}: {linked['key']} — {linked['fields']['summary']}")
        lines.append("")

    # Description
    description = fields.get("description")
    if description:
        lines.append("## Description")
        lines.append(adf_to_text(description))
        lines.append("")

    # Comments
    comments_data = fields.get("comment", {}).get("comments", [])
    if comments_data:
        lines.append("## Comments")
        for comment in comments_data:
            author = comment.get("author", {}).get("displayName", "Unknown")
            created = comment.get("created", "")[:10]
            body_text = adf_to_text(comment.get("body", {}))
            lines.append(f"### {author} ({created})")
            lines.append(body_text)
            lines.append("")

    # Extract spreadsheet URLs
    full_text = "\n".join(lines)
    spreadsheet_urls = extract_spreadsheet_urls(full_text)
    if spreadsheet_urls:
        lines.append("## QA Spreadsheet URLs Found")
        for url in spreadsheet_urls:
            lines.append(f"- {url}")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/fetch_jira_context.py <TICKET>")
        sys.exit(1)

    ticket = sys.argv[1]
    email = os.environ.get("JIRA_EMAIL", "")
    api_token = os.environ.get("JIRA_API_TOKEN", "")

    if not email or not api_token:
        print("[jira] JIRA_EMAIL or JIRA_API_TOKEN not set — skipping Jira context fetch")
        os.makedirs("jira_context", exist_ok=True)
        with open(f"jira_context/{ticket}.md", "w") as f:
            f.write(f"# Jira Ticket: {ticket}\n\nNo Jira context available (credentials not set).\n")
        sys.exit(0)

    print(f"[jira] Fetching ticket {ticket}...")
    issue = fetch_issue(ticket, email, api_token)

    context = format_context(issue, ticket)

    os.makedirs("jira_context", exist_ok=True)
    output_path = f"jira_context/{ticket}.md"
    with open(output_path, "w") as f:
        f.write(context)

    print(f"[jira] Context written to {output_path}")

    # Also output spreadsheet URLs for downstream use
    spreadsheet_urls = extract_spreadsheet_urls(context)
    if spreadsheet_urls:
        urls_path = f"jira_context/{ticket}-spreadsheet-urls.json"
        with open(urls_path, "w") as f:
            json.dump(spreadsheet_urls, f)
        print(f"[jira] Found {len(spreadsheet_urls)} spreadsheet URL(s)")


if __name__ == "__main__":
    main()
