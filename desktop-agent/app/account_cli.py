"""Commands that talk to the account: login, logout, status."""
import getpass
import sys
from collections.abc import Callable

from app.api_client import ApiClient, ApiError, NetworkError, RateLimited
from app.offline_buffer import SQLiteBuffer
from app.settings import AgentSettings
from app.token_store import TokenStore, TokenStoreUnavailable


def run_account_command(
    command: str,
    settings: AgentSettings,
    store: TokenStore | None = None,
    input_fn: Callable[[str], str] = input,
    password_fn: Callable[[str], str] = getpass.getpass,
) -> int:
    try:
        store = store if store is not None else TokenStore()
    except TokenStoreUnavailable as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 3
    client = ApiClient(settings.api_base_url, store)
    if command == "login":
        return _login(client, input_fn, password_fn)
    if command == "logout":
        client.logout()
        print("Logged out. Local tokens removed.")
        return 0
    return _status(settings, client)


def _login(client: ApiClient, input_fn, password_fn) -> int:
    email = input_fn("Email: ").strip()
    password = password_fn("Password: ")
    try:
        client.login(email, password)
    except RateLimited:
        print("Too many attempts. Wait a minute and try again.", file=sys.stderr)
        return 1
    except (ApiError, NetworkError) as exc:
        print(f"Login failed: {exc}", file=sys.stderr)
        return 1
    print(f"Logged in as {email}. Tokens are stored in the Windows Credential Manager.")
    return 0


def _status(settings: AgentSettings, client: ApiClient) -> int:
    reachable = "reachable" if client.health() else "NOT reachable"
    logged = f"yes, as {client.email()}" if client.is_logged_in() else "NO (run: python -m app.main login)"
    waiting = SQLiteBuffer(settings.buffer_db).count_pending()
    print(f"Data folder      : {settings.data_dir}")
    print(f"Log file         : {settings.log_file}")
    print(f"Server           : {settings.api_base_url}  ({reachable})")
    print(f"Logged in        : {logged}")
    print(f"Waiting to upload: {waiting} session(s)")
    return 0
