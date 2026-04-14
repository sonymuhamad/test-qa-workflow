"""Generic YAML-driven API test executor."""

import time
import pytest
import httpx
from lib.yaml_loader import load_test_cases, resolve_variables, collect_all_test_cases
from lib.evidence import TestCaseResult


def pytest_generate_tests(metafunc):
    """Dynamically parametrize test cases from YAML file."""
    if "test_case" in metafunc.fixturenames:
        yaml_file = metafunc.config.getoption("--yaml-file")
        if not yaml_file:
            return
        data = load_test_cases(yaml_file)
        cases = collect_all_test_cases(data)
        ids = [f"TC{c['id']}-{c['category']}-{c['description'][:40]}" for c in cases]
        metafunc.parametrize("test_case", cases, ids=ids)


class TestAPIRunner:
    def test_execute(self, staging_url, auth_manager, prerequisite_vars, evidence, test_case):
        # 1. Build headers
        headers = auth_manager.get_headers(test_case.get("auth", "admin"))
        if "_skip" in headers:
            pytest.skip(headers["_skip"])
        headers["Content-Type"] = "application/json"

        # 2. Resolve path
        try:
            path = resolve_variables(
                test_case["path"],
                test_case.get("path_params"),
                prerequisite_vars,
            )
        except KeyError as e:
            pytest.skip(f"Missing prerequisite variable: {e}")
        url = f"{staging_url}{path}"

        # 3. Execute request
        start = time.time()
        response = httpx.request(
            method=test_case["method"],
            url=url,
            headers=headers,
            json=test_case.get("body"),
            params=test_case.get("query_params"),
        )
        duration_ms = int((time.time() - start) * 1000)

        # 4. Capture evidence
        request_evidence = {
            "method": test_case["method"],
            "url": url,
            "headers": {k: "***" if k == "Authorization" else v for k, v in headers.items()},
            "body": test_case.get("body"),
        }
        response_evidence = {
            "status_code": response.status_code,
            "body": response.json() if response.headers.get("content-type", "").startswith("application/json") else response.text,
            "duration_ms": duration_ms,
        }

        # 5. Assert status code
        expected = test_case["expected"]
        failure_reason = None
        status = "PASS"

        if response.status_code != expected["status_code"]:
            failure_reason = f"Expected status {expected['status_code']}, got {response.status_code}"
            status = "FAIL"

        # 6. Assert body_contains
        if status == "PASS" and "body_contains" in expected:
            body = response.json()
            try:
                _assert_contains(body, expected["body_contains"])
            except AssertionError as e:
                failure_reason = str(e)
                status = "FAIL"

        # 7. Record evidence
        evidence.add_result(TestCaseResult(
            test_case_id=test_case["id"],
            category=test_case["category"],
            description=test_case["description"],
            status=status,
            duration_ms=duration_ms,
            request=request_evidence,
            response=response_evidence,
            failure_reason=failure_reason,
        ))

        # 8. Fail the pytest test if needed
        if status == "FAIL":
            pytest.fail(failure_reason)


def _assert_contains(actual: dict, expected: dict, path: str = ""):
    """Recursively assert that actual dict contains all keys/values from expected."""
    for key, expected_value in expected.items():
        current_path = f"{path}.{key}" if path else key
        assert key in actual, f"Missing key '{current_path}' in response"

        if isinstance(expected_value, dict):
            assert isinstance(actual[key], dict), f"Expected dict at '{current_path}', got {type(actual[key])}"
            _assert_contains(actual[key], expected_value, current_path)
        elif isinstance(expected_value, list):
            assert isinstance(actual[key], list), f"Expected list at '{current_path}', got {type(actual[key])}"
            for i, item in enumerate(expected_value):
                if isinstance(item, dict):
                    found = False
                    for actual_item in actual[key]:
                        try:
                            _assert_contains(actual_item, item, f"{current_path}[{i}]")
                            found = True
                            break
                        except AssertionError:
                            continue
                    assert found, f"No matching item for expected[{i}] at '{current_path}'"
        else:
            assert actual[key] == expected_value, (
                f"At '{current_path}': expected {expected_value!r}, got {actual[key]!r}"
            )
