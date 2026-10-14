"""Login tokens live in the OS keyring (Windows Credential Manager), never in files."""
import json
from dataclasses import dataclass

SERVICE = "AttentionAgent"
KEY = "tokens"


class TokenStoreUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class Tokens:
    access: str
    refresh: str
    email: str = ""


class TokenStore:
    def __init__(self, backend=None) -> None:
        """backend: anything with get_password / set_password / delete_password (default: keyring)."""
        if backend is None:
            try:
                import keyring
            except ImportError as exc:
                raise TokenStoreUnavailable(
                    "The 'keyring' package is missing (run: pip install -r requirements.txt)"
                ) from exc
            backend = keyring
        self._kr = backend

    def load(self) -> Tokens | None:
        raw = self._kr.get_password(SERVICE, KEY)
        if not raw:
            return None
        try:
            data = json.loads(raw)
            return Tokens(access=data["access"], refresh=data["refresh"], email=data.get("email", ""))
        except (ValueError, KeyError, TypeError):
            return None  # damaged entry -> treat as logged out

    def save(self, tokens: Tokens) -> None:
        payload = {"access": tokens.access, "refresh": tokens.refresh, "email": tokens.email}
        self._kr.set_password(SERVICE, KEY, json.dumps(payload))

    def clear(self) -> None:
        try:
            self._kr.delete_password(SERVICE, KEY)
        except Exception:  # noqa: BLE001 - "nothing stored" is reported as an error by keyring
            pass
