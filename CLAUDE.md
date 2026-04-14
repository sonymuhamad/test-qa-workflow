# Satu Dental QA - Automated Testing

## Overview

This repository contains the automated QA system for Satu Dental CMS backend.
You are acting as a QA engineer. Your job is to:
1. Generate test cases for API endpoints based on code changes and requirements
2. Execute those test cases against staging
3. Write structured results and trigger reporting

## Application Context

Satu Dental CMS is a dental clinic and lab management SaaS platform.
The backend is a Go API using Chi router with PostgreSQL, Redis, and Meilisearch.

### Key Domains
- Patient Management (patients, insurance, credits, loyalty points)
- Bookings & Scheduling (appointments, booking plans)
- Medical Records & Treatment Plans
- Invoicing & POS (invoices, payments, insurance integration)
- Insurance Rules V2 (rules, benefits, simulations, snapshots)
- Inventory & Stock Management
- Doctor Commissions & Settlements

## Staging Environment

- **Base URL:** Read from STAGING_BASE_URL environment variable
- **Timezone:** Asia/Jakarta (UTC+7)

## Authentication

**Login endpoint:** `POST /admin/auth/login`

Request:
```json
{"email": "user@example.com", "password": "password"}
```

Response:
```json
{
  "data": {
    "id": 191,
    "access_token": "1c474a8b-92b8-48ca-91a1-355d33b7e0a7"
  },
  "meta": {"http_code": 200}
}
```

Use the token as: `Authorization: Bearer <access_token>`

### Test Accounts

| Profile | Secret (email) | Secret (password) | Permissions |
|---------|---------------|-------------------|-------------|
| admin | QA_ADMIN_EMAIL | QA_ADMIN_PASSWORD | Full access to all features |
| reader | QA_READER_EMAIL | QA_READER_PASSWORD | Read-only on most features |
| no_permission | QA_NOPERM_EMAIL | QA_NOPERM_PASSWORD | No insurance/invoice permissions |

## Workflow: Generate → Execute → Report

### Step 1: Gather Context
1. Read this file (CLAUDE.md) for QA guidelines
2. Read `test_cases/_schema.yaml` for YAML format reference
3. Read `test_cases/example-SD-0000.yaml` for an example
4. Read `jira_context/<ticket>.md` if available (Jira ticket details)
5. In `be-repo/`, find the relevant handler:
   - Read `be-repo/httpserver/routing.go` to find the route
   - Read the handler file for request/response structs
   - Read the usecase file for business logic and validations
6. If PR number is provided: `cd be-repo && git diff main...HEAD -- '*.go'`

**IMPORTANT:**
- Do NOT read Swagger JSON files (too large)
- Do NOT explore the entire codebase — only read files relevant to the endpoint

### Step 2: Generate Test Cases YAML
Write test cases to `test_cases/<ticket>.yaml` following `_schema.yaml`.

Always include these categories:
1. **Auth** — No token (401), invalid token (401), wrong permission (403)
2. **Validation** — Required fields, invalid values, business rule violations
3. **Happy Path** — Normal successful operations
4. **Edge Cases** — Boundary values, non-existent IDs, etc.

### Step 3: Execute Test Cases

**Login first** to get auth tokens:
```bash
# Login as admin
curl -s -X POST "$STAGING_BASE_URL/admin/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "'$QA_ADMIN_EMAIL'", "password": "'$QA_ADMIN_PASSWORD'"}' | jq -r '.data.access_token'
```

**Execute prerequisites** from the YAML (create test data, extract IDs):
- Run each prerequisite request in order
- Extract variables from responses using the jsonpath expressions
- If a prerequisite fails, read the error response and fix the request body
- Log what you extract: `Extracted rule_a_id=123`

**Execute each test case:**
- Use curl with the appropriate auth headers
- Compare actual status code with expected
- Check body_contains assertions if specified
- Record: PASS, FAIL (with reason), or SKIP

**Execute cleanup** steps after all tests complete.

### Step 4: Write Results

Write results to `results/<ticket>-results.json`:
```json
{
  "ticket": "SD-3311",
  "run_id": "run-20260414-150000",
  "summary": {"total": 15, "passed": 12, "failed": 2, "skipped": 1},
  "test_cases": [
    {
      "id": 1,
      "category": "Auth",
      "description": "No bearer token returns 401",
      "status": "PASS",
      "duration_ms": 150,
      "request": {"method": "PATCH", "url": "...", "headers": {}, "body": {}},
      "response": {"status_code": 401, "body": {...}, "duration_ms": 120},
      "failure_reason": null
    }
  ]
}
```

### Step 5: Report Results

Run these scripts to upload results:

```bash
# Upload to Google Sheets
python scripts/upload_sheets.py results/<ticket>-results.json

# Post rich comment on Jira ticket
python scripts/post_jira_comment.py <ticket> results/<ticket>-results.json
```

## YAML Test Case Format

See `test_cases/_schema.yaml` for the full schema reference.

### Key Rules
- Every test file MUST have: ticket, title, generated_at, generated_by, auth_profiles, test_cases
- Test IDs should be sequential: main tests 1-99, related/regression 100+
- **Test ordering matters:** Tests execute in ID order. If a test mutates state, subsequent tests must account for that state change.
- **All endpoints are under `/admin/`**
- Include prerequisites for test data setup and cleanup to revert staging data

## Response Patterns

Success:
```json
{"data": {...}, "meta": {"http_code": 200}}
```

Error:
```json
{"errors": [{"field": "name", "message": "name is a required field"}], "meta": {"http_code": 400}}
```

Common codes: 400 (validation), 401 (auth), 403 (forbidden), 404 (not found), 409 (conflict), 422 (unprocessable)
