import sys
import os
import pytest

# Add project root to path
sys.path.insert(0, os.path.dirname(__file__))


def pytest_addoption(parser):
    parser.addoption("--yaml-file", action="store", default=None, help="Path to YAML test case file")
    parser.addoption("--run-id", action="store", default=None, help="Unique run identifier")


@pytest.fixture(scope="session")
def yaml_file(request):
    path = request.config.getoption("--yaml-file")
    if not path:
        pytest.skip("No --yaml-file provided")
    return path


@pytest.fixture(scope="session")
def run_id(request):
    rid = request.config.getoption("--run-id")
    if not rid:
        import uuid
        rid = f"run-{uuid.uuid4().hex[:8]}"
    return rid


@pytest.fixture(scope="session")
def staging_url():
    url = os.environ.get("STAGING_BASE_URL")
    if not url:
        pytest.skip("STAGING_BASE_URL not set")
    return url


def pytest_configure(config):
    config._evidence = None
