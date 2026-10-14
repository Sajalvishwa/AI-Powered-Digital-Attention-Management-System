"""A tiny REAL HTTP server that behaves like our FastAPI backend, plus an in-memory keyring.
Used by the API client and login tests. Needs no internet and no PostgreSQL."""
import json
import threading
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


def payload(i: int = 0, app: str = "Code.exe", title=None) -> dict:
    """A session dictionary like ActivitySession.to_payload() produces."""
    data = {
        "client_id": f"00000000-0000-4000-8000-{i:012d}",
        "app_name": app,
        "is_idle": False,
        "started_at": "2026-10-12T09:00:00+00:00",
        "ended_at": "2026-10-12T09:01:00+00:00",
    }
    if title is not None:
        data["window_title"] = title
    return data


class MemoryKeyring:
    """Same three methods as the real keyring module."""

    def __init__(self):
        self.data = {}

    def get_password(self, service, key):
        return self.data.get((service, key))

    def set_password(self, service, key, value):
        self.data[(service, key)] = value

    def delete_password(self, service, key):
        if (service, key) not in self.data:
            raise KeyError("nothing stored")
        del self.data[(service, key)]


class FakeBackend:
    """A tiny real HTTP server that behaves like our FastAPI backend."""

    def __init__(self):
        self.password = "Strong123"
        self.access, self.refresh, self._n = "acc-0", "ref-0", 0
        self.batches = []
        self.force_status = None  # e.g. 500 or 429 for /activity/batch
        self.retry_after = "7"
        self.reject_app = None  # sessions with this app_name get a 422 that echoes the data
        self.settings = {"store_window_titles": False, "ignored_apps": [], "idle_threshold_sec": 120}
        self.logout_calls = 0

    def expire_access(self):
        self._n += 1
        self.access = f"acc-expired-{self._n}"

    def start(self):
        backend = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _reply(self, status, body=None, headers=None):
                raw = json.dumps(body).encode() if body is not None else b""
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(raw)

            def _body(self):
                length = int(self.headers.get("Content-Length", "0"))
                return json.loads(self.rfile.read(length)) if length else {}

            def _authorized(self):
                return self.headers.get("Authorization") == f"Bearer {backend.access}"

            def do_GET(self):
                if self.path == "/health":
                    return self._reply(200, {"status": "ok"})
                if self.path == "/api/v1/users/me/settings":
                    return self._reply(200, backend.settings) if self._authorized() else self._reply(401, {"detail": "no"})
                self._reply(404, {"detail": "nope"})

            def do_POST(self):
                body = self._body()
                if self.path == "/api/v1/auth/login":
                    if body.get("password") == backend.password:
                        return self._reply(200, {"access_token": backend.access, "refresh_token": backend.refresh,
                                                 "token_type": "bearer"})
                    return self._reply(401, {"detail": "Invalid email or password"})
                if self.path == "/api/v1/auth/refresh":
                    if body.get("refresh_token") == backend.refresh:
                        backend._n += 1
                        backend.access, backend.refresh = f"acc-{backend._n}", f"ref-{backend._n}"
                        return self._reply(200, {"access_token": backend.access, "refresh_token": backend.refresh,
                                                 "token_type": "bearer"})
                    return self._reply(401, {"detail": "Invalid refresh token"})
                if self.path == "/api/v1/auth/logout":
                    backend.logout_calls += 1
                    return self._reply(204)
                if self.path == "/api/v1/activity/batch":
                    if not self._authorized():
                        return self._reply(401, {"detail": "Not authenticated"})
                    if backend.force_status:
                        headers = {"Retry-After": backend.retry_after} if backend.force_status == 429 else {}
                        return self._reply(backend.force_status, {"detail": "forced"}, headers)
                    sessions = body.get("sessions", [])
                    if backend.reject_app and any(s["app_name"] == backend.reject_app for s in sessions):
                        return self._reply(422, {"detail": [{"input": sessions}]})  # echoes the data, like pydantic
                    backend.batches.append(sessions)
                    return self._reply(200, {"received": len(sessions), "inserted": len(sessions),
                                             "duplicates": 0, "skipped": 0})
                self._reply(404, {"detail": "nope"})

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self._server.server_address[1]}/api/v1"
        threading.Thread(target=self._server.serve_forever, daemon=True).start()
        return self

    def stop(self):
        self._server.shutdown()
        self._server.server_close()

    @property
    def all_sessions(self):
        return [s for batch in self.batches for s in batch]


@contextmanager
def running_backend():
    backend = FakeBackend().start()
    try:
        yield backend
    finally:
        backend.stop()
