"""Load and parse YAML test case files."""

import yaml
from pathlib import Path


def load_test_cases(filepath: str) -> dict:
    """Load a YAML test case file and return parsed data.

    Raises:
        FileNotFoundError: If the file does not exist.
        yaml.YAMLError: If the YAML is invalid.
    """
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Test case file not found: {filepath}")

    with open(path) as f:
        data = yaml.safe_load(f)

    # Ensure defaults for optional fields
    data.setdefault("prerequisites", [])
    data.setdefault("related_endpoints", [])
    data.setdefault("cleanup", [])
    data.setdefault("auth_profiles", [])

    return data


def resolve_variables(path: str, path_params: dict | None, variables: dict) -> str:
    """Resolve path parameters and variable references.

    Path params with $ prefix are looked up in the variables dict.
    E.g., path="/admin/items/{item_id}", params={"item_id": "$item_id"},
    variables={"item_id": 42} -> "/admin/items/42"

    Raises:
        KeyError: If a variable reference is not found.
    """
    if not path_params:
        return path

    resolved = path
    for param_name, param_value in path_params.items():
        if isinstance(param_value, str) and param_value.startswith("$"):
            var_name = param_value[1:]
            if var_name not in variables:
                raise KeyError(f"Variable '{var_name}' not found. Available: {list(variables.keys())}")
            param_value = variables[var_name]
        resolved = resolved.replace(f"{{{param_name}}}", str(param_value))

    return resolved


def collect_all_test_cases(data: dict) -> list[dict]:
    """Collect all test cases including related endpoint tests.

    Returns a flat list of all test case dicts.
    """
    cases = list(data.get("test_cases", []))

    for related in data.get("related_endpoints", []):
        for tc in related.get("test_cases", []):
            cases.append(tc)

    return cases
