import pytest
import httpx
from jsonpath_ng import parse
from lib.yaml_loader import load_test_cases, collect_all_test_cases
from lib.auth import AuthManager
from lib.evidence import EvidenceCapture
from lib.results_writer import write_results_json, write_summary_markdown
import json


@pytest.fixture(scope="session")
def test_data(yaml_file):
    return load_test_cases(yaml_file)


@pytest.fixture(scope="session")
def auth_manager(staging_url, test_data):
    manager = AuthManager(base_url=staging_url, auth_profiles=test_data.get("auth_profiles", []))
    manager.login_all()
    return manager


@pytest.fixture(scope="session")
def evidence(test_data, run_id, request):
    ev = EvidenceCapture(ticket=test_data["ticket"], run_id=run_id)
    request.config._evidence = ev
    yield ev

    # Always write results to files after all tests complete
    results = json.loads(ev.to_json())
    write_results_json(results, output_dir="results")
    write_summary_markdown(results, output_dir="results")


@pytest.fixture(scope="session")
def prerequisite_vars(staging_url, auth_manager, test_data):
    """Execute prerequisites and collect extracted variables.

    If a prerequisite fails, log the error and continue with empty variables.
    Tests that depend on missing variables will fail individually.
    """
    variables = {}
    errors = []

    for prereq in test_data.get("prerequisites", []):
        prereq_id = prereq.get("id", prereq.get("description", "unknown"))
        headers = auth_manager.get_headers(prereq.get("auth", "admin"))
        if "_skip" in headers:
            print(f"[prereq] Skipping '{prereq_id}' — auth profile not available")
            continue

        headers["Content-Type"] = "application/json"

        # Resolve {{var}} references in prerequisite paths
        path = prereq["path"]
        for var_name, var_value in variables.items():
            path = path.replace(f"{{{{{var_name}}}}}", str(var_value))

        try:
            response = httpx.request(
                method=prereq["method"],
                url=f"{staging_url}{path}",
                headers=headers,
                json=prereq.get("body"),
            )
            print(f"[prereq] {prereq['method']} {path} → {response.status_code}")

            if response.status_code >= 400:
                body_text = response.text[:500]
                error_msg = f"Prerequisite '{prereq_id}' failed: {response.status_code} — {body_text}"
                print(f"[prereq] ERROR: {error_msg}")
                errors.append(error_msg)
                continue

            body = response.json()
            for var_name, jsonpath_expr in prereq.get("extract", {}).items():
                matches = parse(jsonpath_expr).find(body)
                if matches:
                    variables[var_name] = matches[0].value
                    print(f"[prereq] Extracted {var_name}={matches[0].value}")

        except Exception as e:
            error_msg = f"Prerequisite '{prereq_id}' exception: {e}"
            print(f"[prereq] ERROR: {error_msg}")
            errors.append(error_msg)

    if errors:
        print(f"[prereq] WARNING: {len(errors)} prerequisite(s) failed. Some tests may fail.")

    yield variables

    # Cleanup
    for cleanup_step in test_data.get("cleanup", []):
        path = cleanup_step["path"]
        for var_name, var_value in variables.items():
            path = path.replace(f"{{{{{var_name}}}}}", str(var_value))
        headers = auth_manager.get_headers(cleanup_step.get("auth", "admin"))
        if "_skip" in headers:
            continue
        headers["Content-Type"] = "application/json"
        try:
            resp = httpx.request(
                method=cleanup_step["method"],
                url=f"{staging_url}{path}",
                headers=headers,
                json=cleanup_step.get("body"),
            )
            print(f"[cleanup] {cleanup_step['method']} {path} → {resp.status_code}")
        except Exception as e:
            print(f"[cleanup] ERROR: {e}")
