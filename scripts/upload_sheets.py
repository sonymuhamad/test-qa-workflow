"""Upload test results JSON to Google Sheets via Apps Script.

Usage:
    python scripts/upload_sheets.py <results.json> [--dev-pic NAME]

Reads SHEETS_WEBAPP_URL and SHEETS_WEBAPP_TOKEN from environment.
"""

import json
import os
import sys
import requests
from datetime import datetime


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/upload_sheets.py <results.json> [--dev-pic NAME]")
        sys.exit(1)

    results_path = sys.argv[1]
    dev_pic = ""
    if "--dev-pic" in sys.argv:
        idx = sys.argv.index("--dev-pic")
        if idx + 1 < len(sys.argv):
            dev_pic = sys.argv[idx + 1]

    webapp_url = os.environ.get("SHEETS_WEBAPP_URL", "")
    secret_token = os.environ.get("SHEETS_WEBAPP_TOKEN", "")

    if not webapp_url or not secret_token:
        print("[sheets] SHEETS_WEBAPP_URL or SHEETS_WEBAPP_TOKEN not set — skipping")
        sys.exit(0)

    with open(results_path) as f:
        results = json.load(f)

    testing_date = datetime.now().strftime("%d/%m/%Y")

    payload = {
        "token": secret_token,
        "ticket": results["ticket"],
        "summary": results["summary"],
        "test_cases": results["test_cases"],
        "testing_date": testing_date,
        "dev_pic": dev_pic,
    }

    print(f"[sheets] Uploading {len(results['test_cases'])} test cases for {results['ticket']}...")
    response = requests.post(webapp_url, json=payload)
    response.raise_for_status()
    result = response.json()
    print(f"[sheets] Done: {result}")


if __name__ == "__main__":
    main()
