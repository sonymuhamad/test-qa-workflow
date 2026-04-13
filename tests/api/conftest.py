import pytest
import httpx
from jsonpath_ng import parse
from lib.yaml_loader import load_test_cases, collect_all_test_cases
from lib.auth import AuthManager
from lib.evidence import EvidenceCapture


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


@pytest.fixture(scope="session")
def prerequisite_vars(staging_url, auth_manager, test_data):
    """Execute prerequisites and collect extracted variables."""
    variables = {}
    for prereq in test_data.get("prerequisites", []):
        headers = auth_manager.get_headers(prereq.get("auth", "admin"))
        response = httpx.request(
            method=prereq["method"],
            url=f"{staging_url}{prereq['path']}",
            headers=headers,
            json=prereq.get("body"),
        )
        response.raise_for_status()
        body = response.json()

        for var_name, jsonpath_expr in prereq.get("extract", {}).items():
            matches = parse(jsonpath_expr).find(body)
            if matches:
                variables[var_name] = matches[0].value

    yield variables

    # Cleanup
    for cleanup_step in test_data.get("cleanup", []):
        path = cleanup_step["path"]
        for var_name, var_value in variables.items():
            path = path.replace(f"{{{{{var_name}}}}}", str(var_value))
        headers = auth_manager.get_headers(cleanup_step.get("auth", "admin"))
        try:
            httpx.request(method=cleanup_step["method"], url=f"{staging_url}{path}", headers=headers)
        except Exception:
            pass
