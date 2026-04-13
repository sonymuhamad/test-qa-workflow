import pytest
import yaml
from lib.yaml_loader import load_test_cases, resolve_variables, collect_all_test_cases


@pytest.fixture
def sample_yaml(tmp_path):
    content = {
        "ticket": "SD-0000",
        "title": "GET /admin/test",
        "generated_at": "2026-04-13T10:00:00+07:00",
        "generated_by": "claude",
        "auth_profiles": [
            {"name": "admin", "email_secret": "QA_ADMIN_EMAIL", "password_secret": "QA_ADMIN_PASSWORD"},
        ],
        "test_cases": [
            {
                "id": 1,
                "category": "Happy Path",
                "description": "Basic GET",
                "auth": "admin",
                "method": "GET",
                "path": "/admin/test",
                "expected": {"status_code": 200},
            },
            {
                "id": 2,
                "category": "Auth",
                "description": "No auth",
                "auth": "none",
                "method": "GET",
                "path": "/admin/test",
                "expected": {"status_code": 401},
            },
        ],
    }
    filepath = tmp_path / "SD-0000.yaml"
    filepath.write_text(yaml.dump(content))
    return str(filepath)


@pytest.fixture
def yaml_with_prerequisites(tmp_path):
    content = {
        "ticket": "SD-0001",
        "title": "POST /admin/test",
        "generated_at": "2026-04-13T10:00:00+07:00",
        "generated_by": "claude",
        "prerequisites": [
            {
                "id": "create_item",
                "description": "Create test item",
                "method": "POST",
                "path": "/admin/items",
                "auth": "admin",
                "body": {"name": "test"},
                "extract": {"item_id": "$.data.id"},
            }
        ],
        "auth_profiles": [
            {"name": "admin", "email_secret": "QA_ADMIN_EMAIL", "password_secret": "QA_ADMIN_PASSWORD"},
        ],
        "test_cases": [
            {
                "id": 1,
                "category": "Happy Path",
                "description": "Get created item",
                "auth": "admin",
                "method": "GET",
                "path": "/admin/items/{item_id}",
                "path_params": {"item_id": "$item_id"},
                "expected": {"status_code": 200},
            }
        ],
        "cleanup": [
            {
                "description": "Delete test item",
                "method": "DELETE",
                "path": "/admin/items/{{item_id}}",
                "auth": "admin",
            }
        ],
    }
    filepath = tmp_path / "SD-0001.yaml"
    filepath.write_text(yaml.dump(content))
    return str(filepath)


@pytest.fixture
def yaml_with_related(tmp_path):
    content = {
        "ticket": "SD-0002",
        "title": "PATCH /admin/test/{ID}",
        "generated_at": "2026-04-13T10:00:00+07:00",
        "generated_by": "claude",
        "auth_profiles": [
            {"name": "admin", "email_secret": "QA_ADMIN_EMAIL", "password_secret": "QA_ADMIN_PASSWORD"},
        ],
        "test_cases": [
            {
                "id": 1,
                "category": "Happy Path",
                "description": "Update item",
                "auth": "admin",
                "method": "PATCH",
                "path": "/admin/test/1",
                "body": {"name": "updated"},
                "expected": {"status_code": 200},
            }
        ],
        "related_endpoints": [
            {
                "path": "GET /admin/test",
                "reason": "List should reflect update",
                "test_cases": [
                    {
                        "id": 100,
                        "category": "Regression",
                        "description": "List reflects update",
                        "auth": "admin",
                        "method": "GET",
                        "path": "/admin/test",
                        "expected": {"status_code": 200},
                    }
                ],
            }
        ],
    }
    filepath = tmp_path / "SD-0002.yaml"
    filepath.write_text(yaml.dump(content))
    return str(filepath)


class TestLoadTestCases:
    def test_loads_basic_yaml(self, sample_yaml):
        data = load_test_cases(sample_yaml)
        assert data["ticket"] == "SD-0000"
        assert len(data["test_cases"]) == 2
        assert data["test_cases"][0]["method"] == "GET"

    def test_loads_prerequisites(self, yaml_with_prerequisites):
        data = load_test_cases(yaml_with_prerequisites)
        assert len(data["prerequisites"]) == 1
        assert data["prerequisites"][0]["id"] == "create_item"
        assert "item_id" in data["prerequisites"][0]["extract"]

    def test_loads_cleanup(self, yaml_with_prerequisites):
        data = load_test_cases(yaml_with_prerequisites)
        assert len(data["cleanup"]) == 1

    def test_loads_related_endpoints(self, yaml_with_related):
        data = load_test_cases(yaml_with_related)
        assert len(data["related_endpoints"]) == 1
        assert len(data["related_endpoints"][0]["test_cases"]) == 1

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            load_test_cases("/nonexistent/path.yaml")

    def test_invalid_yaml_raises(self, tmp_path):
        filepath = tmp_path / "bad.yaml"
        filepath.write_text(": invalid: yaml: [")
        with pytest.raises(yaml.YAMLError):
            load_test_cases(str(filepath))


class TestResolveVariables:
    def test_resolves_path_params(self):
        path = "/admin/items/{item_id}"
        params = {"item_id": "$item_id"}
        variables = {"item_id": 42}
        result = resolve_variables(path, params, variables)
        assert result == "/admin/items/42"

    def test_no_params_returns_path(self):
        path = "/admin/items"
        result = resolve_variables(path, None, {})
        assert result == "/admin/items"

    def test_missing_variable_raises(self):
        path = "/admin/items/{item_id}"
        params = {"item_id": "$missing_var"}
        variables = {}
        with pytest.raises(KeyError):
            resolve_variables(path, params, variables)


class TestCollectAllTestCases:
    def test_collects_main_and_related(self, yaml_with_related):
        data = load_test_cases(yaml_with_related)
        all_cases = collect_all_test_cases(data)
        assert len(all_cases) == 2
        assert all_cases[0]["id"] == 1
        assert all_cases[1]["id"] == 100
        assert all_cases[1]["category"] == "Regression"

    def test_collects_main_only(self, sample_yaml):
        data = load_test_cases(sample_yaml)
        all_cases = collect_all_test_cases(data)
        assert len(all_cases) == 2
