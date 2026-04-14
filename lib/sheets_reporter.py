"""Upload test results to Google Sheets via Apps Script Web App."""

import json
import requests
from datetime import datetime


class SheetsReporter:
    """Upload test results to Google Sheets via Apps Script."""

    def __init__(self, webapp_url: str, secret_token: str):
        self.webapp_url = webapp_url
        self.secret_token = secret_token

    def upload(self, results: dict, dev_pic: str = ""):
        """Post results to the Apps Script web app."""
        testing_date = datetime.now().strftime("%d/%m/%Y")

        payload = {
            "token": self.secret_token,
            "ticket": results["ticket"],
            "summary": results["summary"],
            "test_cases": results["test_cases"],
            "testing_date": testing_date,
            "dev_pic": dev_pic,
        }

        response = requests.post(
            self.webapp_url,
            json=payload,
            headers={"Content-Type": "application/json"},
        )
        response.raise_for_status()
        return response.json()
