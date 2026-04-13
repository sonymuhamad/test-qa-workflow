import pytest
from unittest.mock import patch, MagicMock
from lib.auth import AuthManager


@pytest.fixture
def auth_profiles():
    return [
        {"name": "admin", "email_secret": "QA_ADMIN_EMAIL", "password_secret": "QA_ADMIN_PASSWORD"},
        {"name": "reader", "email_secret": "QA_READER_EMAIL", "password_secret": "QA_READER_PASSWORD"},
    ]


@pytest.fixture
def env_vars():
    return {
        "QA_ADMIN_EMAIL": "admin@test.com",
        "QA_ADMIN_PASSWORD": "admin123",
        "QA_READER_EMAIL": "reader@test.com",
        "QA_READER_PASSWORD": "reader123",
    }


class TestAuthManager:
    @patch("lib.auth.httpx.post")
    def test_login_all_profiles(self, mock_post, auth_profiles, env_vars):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"token": "fake-token-123"}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", env_vars):
            manager = AuthManager(base_url="http://localhost:8100", auth_profiles=auth_profiles)
            manager.login_all()

        assert manager.get_token("admin") == "fake-token-123"
        assert manager.get_token("reader") == "fake-token-123"
        assert mock_post.call_count == 2

    @patch("lib.auth.httpx.post")
    def test_get_headers_with_auth(self, mock_post, auth_profiles, env_vars):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"data": {"token": "my-token"}}
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with patch.dict("os.environ", env_vars):
            manager = AuthManager(base_url="http://localhost:8100", auth_profiles=auth_profiles)
            manager.login_all()

        headers = manager.get_headers("admin")
        assert headers["Authorization"] == "Bearer my-token"

    def test_get_headers_none_auth(self, auth_profiles):
        manager = AuthManager(base_url="http://localhost:8100", auth_profiles=auth_profiles)
        headers = manager.get_headers("none")
        assert "Authorization" not in headers

    def test_get_headers_invalid_auth(self, auth_profiles):
        manager = AuthManager(base_url="http://localhost:8100", auth_profiles=auth_profiles)
        headers = manager.get_headers("invalid")
        assert headers["Authorization"] == "Bearer invalid-token"

    def test_get_token_unknown_profile_raises(self, auth_profiles):
        manager = AuthManager(base_url="http://localhost:8100", auth_profiles=auth_profiles)
        with pytest.raises(KeyError):
            manager.get_token("nonexistent")

    @patch("lib.auth.httpx.post")
    def test_login_failure_raises(self, mock_post, auth_profiles, env_vars):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        with patch.dict("os.environ", env_vars):
            manager = AuthManager(base_url="http://localhost:8100", auth_profiles=auth_profiles)
            with pytest.raises(Exception, match="401 Unauthorized"):
                manager.login_all()
