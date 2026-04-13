"""Authentication helper for QA test execution."""

import os
import httpx


class AuthManager:
    """Manages authentication tokens for multiple test profiles."""

    def __init__(self, base_url: str, auth_profiles: list[dict]):
        self.base_url = base_url
        self.auth_profiles = auth_profiles
        self._tokens: dict[str, str] = {}

    def login_all(self):
        """Login all auth profiles and cache their tokens.

        Skips profiles whose env vars are not set.

        Raises:
            Exception: If a login request fails for a profile that has credentials.
        """
        for profile in self.auth_profiles:
            name = profile["name"]
            email = os.environ.get(profile["email_secret"], "")
            password = os.environ.get(profile["password_secret"], "")

            if not email or not password:
                print(f"[auth] Skipping profile '{name}' — secrets not set")
                continue

            response = httpx.post(
                f"{self.base_url}/admin/auth/login",
                json={"email": email, "password": password},
            )
            response.raise_for_status()

            token = response.json()["data"]["access_token"]
            self._tokens[name] = token
            print(f"[auth] Logged in as '{name}'")

    def get_token(self, profile_name: str) -> str:
        """Get the cached token for a profile.

        Raises:
            KeyError: If the profile has not been logged in.
        """
        if profile_name not in self._tokens:
            raise KeyError(f"No token for profile '{profile_name}'. Available: {list(self._tokens.keys())}")
        return self._tokens[profile_name]

    def get_headers(self, auth_name: str) -> dict:
        """Get request headers for a test case auth profile.

        - "none": no Authorization header
        - "invalid": Authorization with a known-bad token
        - anything else: look up cached token
        """
        if auth_name == "none":
            return {}
        if auth_name == "invalid":
            return {"Authorization": "Bearer invalid-token"}
        if auth_name not in self._tokens:
            return {"_skip": f"Profile '{auth_name}' not available"}
        return {"Authorization": f"Bearer {self._tokens[auth_name]}"}
