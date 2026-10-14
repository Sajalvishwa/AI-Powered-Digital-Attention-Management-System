import pytest

from app.main import main
from app.token_store import Tokens, TokenStore
from tests.fake_backend import MemoryKeyring, running_backend


def write_config(tmp_path, url):
    (tmp_path / "config.toml").write_text(f'api_base_url = "{url}"\n', encoding="utf-8")


def test_login_stores_tokens(tmp_path):
    with running_backend() as backend:
        write_config(tmp_path, backend.url)
        store = TokenStore(MemoryKeyring())
        code = main(["--data-dir", str(tmp_path), "login"], token_store=store,
                    input_fn=lambda _: "me@example.com", password_fn=lambda _: "Strong123")
        assert code == 0 and store.load().email == "me@example.com"


def test_login_with_wrong_password_fails(tmp_path, capsys):
    with running_backend() as backend:
        write_config(tmp_path, backend.url)
        store = TokenStore(MemoryKeyring())
        code = main(["--data-dir", str(tmp_path), "login"], token_store=store,
                    input_fn=lambda _: "me@example.com", password_fn=lambda _: "wrong")
        assert code == 1 and store.load() is None
        assert "Wrong email or password" in capsys.readouterr().err


def test_login_when_server_is_down(tmp_path, capsys):
    write_config(tmp_path, "http://127.0.0.1:9/api/v1")
    code = main(["--data-dir", str(tmp_path), "login"], token_store=TokenStore(MemoryKeyring()),
                input_fn=lambda _: "me@example.com", password_fn=lambda _: "Strong123")
    assert code == 1 and "Cannot reach the server" in capsys.readouterr().err


def test_logout_removes_tokens(tmp_path):
    with running_backend() as backend:
        write_config(tmp_path, backend.url)
        store = TokenStore(MemoryKeyring())
        store.save(Tokens("acc-0", "ref-0", "me@example.com"))
        assert main(["--data-dir", str(tmp_path), "logout"], token_store=store) == 0
        assert store.load() is None


def test_status_never_prints_tokens(tmp_path, capsys):
    with running_backend() as backend:
        write_config(tmp_path, backend.url)
        store = TokenStore(MemoryKeyring())
        store.save(Tokens("acc-0", "ref-0", "me@example.com"))
        assert main(["--data-dir", str(tmp_path), "status"], token_store=store) == 0
        out = capsys.readouterr().out
        assert "reachable" in out and "me@example.com" in out and "Waiting to upload: 0" in out
        assert "acc-0" not in out and "ref-0" not in out


def test_status_when_logged_out(tmp_path, capsys):
    write_config(tmp_path, "http://127.0.0.1:9/api/v1")
    assert main(["--data-dir", str(tmp_path), "status"], token_store=TokenStore(MemoryKeyring())) == 0
    out = capsys.readouterr().out
    assert "NOT reachable" in out and "NO (run: python -m app.main login)" in out


def test_default_command_is_still_run(tmp_path):
    # the old way of starting the agent keeps working: no command word needed
    class Tracker:
        include_title = False
        def current(self):
            return None
    assert main(["--data-dir", str(tmp_path), "--max-ticks", "1"], tracker=Tracker()) == 0
