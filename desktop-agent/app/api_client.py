"""HTTP client for the backend (standard library only, no extra packages).

* login / logout
* automatic token refresh: once per expired token, thread-safe (refresh tokens work only
  once, so two threads refreshing at the same time would log the user out)
* batch upload of sessions (accepts dicts or objects with .to_payload())

Error messages never contain request data, because the server's validation errors can
echo window titles.
"""
import json
import threading
import urllib.error
import urllib.request
import uuid
from collections.abc import Mapping
from datetime import datetime
from urllib.parse import urlparse

from app.token_store import Tokens, TokenStore

MAX_BATCH = 500  # backend limit per request


class ApiError(Exception):
    def __init__(self, status: int, message: str) -> None:
        super().__init__(message)
        self.status = status


class AuthRequired(ApiError):
    """Not logged in, or the session expired. The user must run: python -m app.main login"""


class RateLimited(ApiError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(429, "Too many requests")
        self.retry_after = retry_after


class ServerError(ApiError):
    """HTTP 5xx: the server has a problem, retry later."""


class NetworkError(Exception):
    """Server not reachable (offline, wrong address, timeout)."""


def _to_payload(item) -> dict:
    if isinstance(item, Mapping):
        return dict(item)
    to_payload = getattr(item, "to_payload", None)
    if callable(to_payload):
        return to_payload()
    raise TypeError("sessions must be dicts or objects with a to_payload() method")


def _json_default(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    raise TypeError(f"Cannot send {type(value).__name__} as JSON")


class ApiClient:
    def __init__(self, base_url: str, store: TokenStore, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._store = store
        self._tokens: Tokens | None = None
        self._refresh_lock = threading.Lock()

    # ---- login state ------------------------------------------------------
    def _current(self) -> Tokens | None:
        if self._tokens is None:
            self._tokens = self._store.load()
        return self._tokens

    def is_logged_in(self) -> bool:
        return self._current() is not None

    def email(self) -> str:
        tokens = self._current()
        return tokens.email if tokens else ""

    def login(self, email: str, password: str) -> None:
        status, data, headers = self._send("POST", "/auth/login", {"email": email, "password": password})
        if status == 401:
            raise ApiError(401, "Wrong email or password")
        data = self._check(status, data, headers)
        tokens = Tokens(access=data["access_token"], refresh=data["refresh_token"], email=email)
        self._store.save(tokens)
        self._tokens = tokens

    def logout(self) -> None:
        tokens = self._current()
        if tokens:
            try:  # best effort: revoke on the server too
                self._send("POST", "/auth/logout", {"refresh_token": tokens.refresh})
            except NetworkError:
                pass
        self._store.clear()
        self._tokens = None

    # ---- calls ------------------------------------------------------------
    def upload_batch(self, sessions) -> dict:
        items = [_to_payload(s) for s in sessions]
        if not 1 <= len(items) <= MAX_BATCH:
            raise ValueError(f"A batch must contain 1 to {MAX_BATCH} sessions")
        return self._call("POST", "/activity/batch", {"sessions": items})

    def get_settings(self) -> dict:
        return self._call("GET", "/users/me/settings")

    def get_active_focus(self) -> dict:
        """The running/paused focus session, or {} when there is none."""
        return self._call("GET", "/focus-sessions/active")

    def health(self) -> bool:
        parsed = urlparse(self.base_url)
        try:
            status, _, _ = self._send("GET", "", url=f"{parsed.scheme}://{parsed.netloc}/health")
        except NetworkError:
            return False
        return status == 200

    # ---- internals --------------------------------------------------------
    def _call(self, method: str, path: str, body: dict | None = None) -> dict:
        tokens = self._current()
        if tokens is None:
            raise AuthRequired(401, "Not logged in. Run: python -m app.main login")
        status, data, headers = self._send(method, path, body, tokens.access)
        if status == 401:
            self._refresh(tokens)
            status, data, headers = self._send(method, path, body, self._tokens.access)
        return self._check(status, data, headers)

    def _refresh(self, stale: Tokens) -> None:
        with self._refresh_lock:
            current = self._current()
            if current is None:
                raise AuthRequired(401, "Not logged in. Run: python -m app.main login")
            if current.access != stale.access:
                return  # another thread already refreshed
            status, data, headers = self._send("POST", "/auth/refresh", {"refresh_token": current.refresh})
            if status == 200:
                tokens = Tokens(data["access_token"], data["refresh_token"], current.email)
                self._store.save(tokens)
                self._tokens = tokens
                return
            if status == 401:
                self._store.clear()
                self._tokens = None
                raise AuthRequired(401, "Session expired. Run: python -m app.main login")
            self._check(status, data, headers)  # 429 / 5xx -> transient errors

    @staticmethod
    def _check(status: int, data, headers) -> dict:
        if 200 <= status < 300:
            return data or {}
        if status == 401:
            raise AuthRequired(401, "Session expired. Run: python -m app.main login")
        if status == 429:
            try:
                retry = int(headers.get("Retry-After", "60"))
            except (TypeError, ValueError):
                retry = 60
            raise RateLimited(retry)
        if status >= 500:
            raise ServerError(status, f"Server error (HTTP {status})")
        raise ApiError(status, f"Server rejected the request (HTTP {status})")

    def _send(self, method: str, path: str, body: dict | None = None, access: str | None = None,
              url: str | None = None):
        data = json.dumps(body, default=_json_default).encode("utf-8") if body is not None else None
        headers = {"Accept": "application/json"}
        if data is not None:
            headers["Content-Type"] = "application/json"
        if access:
            headers["Authorization"] = f"Bearer {access}"
        request = urllib.request.Request(url or self.base_url + path, data=data, method=method, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                status, raw, resp_headers = response.status, response.read(), response.headers
        except urllib.error.HTTPError as err:
            status, raw, resp_headers = err.code, err.read(), err.headers
            err.close()
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as err:
            raise NetworkError(f"Cannot reach the server ({type(err).__name__})") from err
        try:
            parsed = json.loads(raw) if raw else None
        except ValueError:
            parsed = None
        return status, parsed, resp_headers
