# Satu Dental QA

Automated QA system for Satu Dental CMS backend. Uses Claude Code to generate test cases from code changes, Playwright (Python) to execute them against staging, and reports results to Google Sheets and Jira.

## How It Works

1. **Trigger:** Developer deploys to staging, then manually triggers the GitHub Actions workflow
2. **Phase 1 (Claude):** Reads PR diff + Swagger docs + codebase, generates YAML test cases
3. **Phase 2 (Playwright):** Executes tests against staging, captures evidence
4. **Phase 3 (Reporting):** Uploads results to Google Sheets, comments on Jira ticket

## Local Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium

# Run unit tests
pytest tests/ -v

# Run against staging (requires env vars)
export STAGING_BASE_URL=https://staging.satudental.com
export QA_ADMIN_EMAIL=...
export QA_ADMIN_PASSWORD=...
pytest tests/api/test_runner.py --yaml-file=test_cases/SD-XXXX.yaml -v
```

## Triggering a QA Run

Go to GitHub Actions > QA Test Run > Run workflow:
- **jira_ticket:** The Jira ticket ID (e.g., SD-3309)
- **pr_number:** (Optional) PR number for diff context
- **scope:** `changed_only`, `changed_and_related`, or `full_regression`

## Adding Test Cases Manually

Create a YAML file in `test_cases/` following the schema in `test_cases/_schema.yaml`.

## Secrets Required

| Secret | Purpose |
|--------|---------|
| `ANTHROPIC_API_KEY` | Claude Code API access |
| `STAGING_BASE_URL` | Staging server URL |
| `QA_ADMIN_EMAIL` | Admin test account email |
| `QA_ADMIN_PASSWORD` | Admin test account password |
| `QA_READER_EMAIL` | Reader test account email |
| `QA_READER_PASSWORD` | Reader test account password |
| `QA_NOPERM_EMAIL` | No-permission test account email |
| `QA_NOPERM_PASSWORD` | No-permission test account password |
| `GOOGLE_SERVICE_ACCOUNT_KEY` | Google Sheets API service account JSON |
| `QA_SPREADSHEET_ID` | Google Sheets spreadsheet ID |
| `JIRA_API_TOKEN` | Jira API token for commenting |
| `JIRA_EMAIL` | Jira account email |
| `BE_REPO_TOKEN` | GitHub PAT to checkout BE repo (if private) |
