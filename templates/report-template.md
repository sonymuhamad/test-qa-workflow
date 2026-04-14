# {TICKET} — {ENDPOINT} — Test Cases

## Endpoint under test
- `{METHOD} {PATH}`
- **Permission:** `{PERMISSION_NAME}`

## Pre-requisites
- {List what must exist before tests run}
- {e.g., "Bearer token with INSURANCE_RULE editor permission"}
- {e.g., "At least 1 ACTIVE insurance rule and 1 INACTIVE insurance rule in DB"}

## Test Run Info
- **Test Date:** {YYYY-MM-DD}
- **Server:** {STAGING_BASE_URL}
- **Auth user:** {email} (id {user_id})
- **Token:** {first 8 chars}...
- **Test fixtures:** {List any data created/used during prerequisites}
  - {e.g., "INACTIVE rule: id=5 (Benefit NONE Test)"}
  - {e.g., "ACTIVE rule: id=51 (U3 Only Voucher)"}

## Results

{TOTAL} scenarios. **{PASS_COUNT} PASS, {FAIL_COUNT} FAIL, {SKIP_COUNT} SKIP.**

### Authentication & Authorization

| # | Scenario | Request Body | Expected | Actual Evidence | Status |
|---|---|---|---|---|---|
| S1 | No bearer token | `{full request body JSON}` | 401, `"bearer token needed"` | HTTP 401; `{"errors":[{"message":"bearer token needed"}]}` | PASS |
| S2 | Invalid bearer token | `{full request body JSON}` | 401, `"bearer token invalid"` | HTTP 401; `{"errors":[{"message":"bearer token invalid"}]}` | PASS |
| S3 | User without {PERMISSION} permission | `{full request body JSON}` | 403 | HTTP 403; `{"errors":[{"message":"forbidden"}]}` | PASS |

### Validation Errors

| # | Scenario | Request Body | Expected | Actual Evidence | Status |
|---|---|---|---|---|---|
| S4 | Empty body `{}` | `{}` | 400, validation error on status | HTTP 400; `{"errors":[{"field":"status","message":"status is a required field"}]}` | PASS |
| S5 | Invalid enum value `{"status":"DELETED"}` | `{"status":"DELETED"}` | 400, oneof validation | HTTP 400; `{"errors":[{"field":"status","message":"status must be one of [ACTIVE INACTIVE]"}]}` | PASS |

### Business Rule Conflicts

| # | Scenario | Request Body | Expected | Actual Evidence | Status |
|---|---|---|---|---|---|
| S10 | Activate already ACTIVE rule (id={X}) | `{"status":"ACTIVE","ordering":1}` | 422, `"Rule sudah aktif"` | HTTP 422; `{"errors":[{"message":"Rule sudah aktif"}]}` | PASS |

### Happy Path

| # | Scenario | Request Body | Expected | Actual Evidence | Status |
|---|---|---|---|---|---|
| S12 | Activate INACTIVE rule (id={X}) with ordering=1 | `{"status":"ACTIVE","ordering":1}` | 200, status=ACTIVE | HTTP 200; `{"data":{"id":{X},"status":"ACTIVE","ordering":2},"meta":{"http_code":200}}` | PASS |

### Edge Cases

| # | Scenario | Request Body | Expected | Actual Evidence | Status |
|---|---|---|---|---|---|
| S15 | Non-existent rule ID (999999) | `{"status":"ACTIVE","ordering":1}` | 404 | HTTP 404; `{"errors":[{"field":"insurance_rule","message":"Insurance Rule not found"}]}` | PASS |

## Cleanup
- {What was done to restore staging state}
- {e.g., "Rules 4 and 5 were deactivated back to INACTIVE"}

## Summary

| Category | Total | PASS | FAIL | SKIP |
|---|---|---|---|---|
| Auth & Authorization | 3 | 3 | 0 | 0 |
| Validation Errors | 6 | 6 | 0 | 0 |
| Business Rule Conflicts | 2 | 2 | 0 | 0 |
| Happy Path | 4 | 4 | 0 | 0 |
| Edge Cases | 3 | 3 | 0 | 0 |
| **TOTAL** | **18** | **18** | **0** | **0** |

### Skip Reasons
- **S{X}** — {Why this test was skipped, e.g., "No test user without permission available"}

### Fail Details
- **S{X}** — Expected {X}, got {Y}. {Root cause analysis if possible}

## Notes
- Spec source: {link to Jira ticket or implementation doc}
- {Any observations, edge cases discovered, etc.}

**Tested on:** {YYYY-MM-DD}
**Environment:** Staging ({STAGING_BASE_URL})
**Tester:** Claude (automated via curl)
