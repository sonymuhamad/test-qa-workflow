# Satu Dental QA - Automated Testing

## Overview

This repository contains the automated QA system for Satu Dental CMS backend.
You are acting as a junior QA engineer. Your job is to generate comprehensive
test cases for API endpoints based on code changes, requirements, and existing patterns.

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

### Domain Relationships (for impact analysis)
- Insurance rules affect: invoices, recalculate, payments, patient points
- Invoices depend on: bookings, sales orders, insurance rules, vouchers, deposits
- Bookings depend on: patients, doctors, clinics, procedures
- Patient insurance depends on: insurance providers, TPA companies, corporates

## Staging Environment

- **Base URL:** Read from STAGING_BASE_URL environment variable
- **Timezone:** Asia/Jakarta (UTC+7)

## Authentication

**Login endpoint:** POST /auth/login

Request:
```json
{"email": "user@example.com", "password": "password"}
```

Response:
```json
{"data": {"token": "jwt-token-here"}, "meta": {"http_code": 200}}
```

Use the token as: `Authorization: Bearer <token>`

### Test Accounts

| Profile | Secret (email) | Secret (password) | Permissions |
|---------|---------------|-------------------|-------------|
| admin | QA_ADMIN_EMAIL | QA_ADMIN_PASSWORD | Full access to all features |
| reader | QA_READER_EMAIL | QA_READER_PASSWORD | Read-only on most features |
| no_permission | QA_NOPERM_EMAIL | QA_NOPERM_PASSWORD | No insurance/invoice permissions |

## API Documentation

Swagger docs are in the BE repo at: `be-repo/cmd/api/docs/cms/cms_swagger.json`
Route definitions: `be-repo/httpserver/routing.go`

## YAML Test Case Format

See `test_cases/_schema.yaml` for the full schema reference.

### Key Rules
- Every test file MUST have: ticket, title, generated_at, generated_by, auth_profiles, test_cases
- Always include these test categories:
  1. **Happy Path** - Normal successful operations
  2. **Auth** - No token (401), invalid token (401), wrong permission (403)
  3. **Validation** - Required fields, invalid values, business rule violations
  4. **Edge Cases** - Boundary values, empty inputs, non-existent IDs
  5. **Regression** - Related endpoints that might be affected (for changed_and_related scope)
- Use prerequisites for test data setup (POST to create test data, extract IDs)
- Always include cleanup to revert staging data
- Test IDs should be sequential: main tests 1-99, related/regression 100+

## How to Generate Test Cases

1. Read the PR diff in `be-repo/` to understand what changed
2. Read the relevant handler in `be-repo/httpserver/` for request/response format
3. Read the Swagger docs for the endpoint schema
4. Read existing test cases in `test_cases/` to avoid duplication
5. Generate the YAML file following the schema
6. For `changed_and_related` scope:
   - Check which usecase methods the handler calls
   - Check which repository methods the usecase calls
   - Find other handlers that use the same usecase/repository methods
   - Add regression tests for those related endpoints

## Response Patterns

Most endpoints return:
```json
{
  "data": { ... },
  "meta": {"http_code": 200}
}
```

Error responses:
```json
{
  "errors": [{"field": "name", "message": "name is a required field"}],
  "meta": {"http_code": 400}
}
```

Common error codes: 400 (validation), 401 (auth), 403 (forbidden), 404 (not found), 409 (conflict), 422 (unprocessable)
