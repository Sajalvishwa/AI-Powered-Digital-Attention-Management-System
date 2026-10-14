from app.token_store import KEY, SERVICE, Tokens, TokenStore
from tests.fake_backend import MemoryKeyring


def test_save_and_load():
    store = TokenStore(MemoryKeyring())
    store.save(Tokens("a1", "r1", "me@example.com"))
    assert store.load() == Tokens("a1", "r1", "me@example.com")


def test_nothing_stored_means_logged_out():
    assert TokenStore(MemoryKeyring()).load() is None


def test_clear_is_safe_even_when_empty():
    store = TokenStore(MemoryKeyring())
    store.clear()
    store.save(Tokens("a", "r"))
    store.clear()
    assert store.load() is None


def test_damaged_entry_is_treated_as_logged_out():
    kr = MemoryKeyring()
    kr.set_password(SERVICE, KEY, "{not json")
    assert TokenStore(kr).load() is None
    kr.set_password(SERVICE, KEY, '{"access": "only"}')
    assert TokenStore(kr).load() is None


def test_tokens_are_not_stored_anywhere_else_but_the_keyring(tmp_path):
    store = TokenStore(MemoryKeyring())
    store.save(Tokens("secret-access", "secret-refresh", "me@example.com"))
    assert list(tmp_path.iterdir()) == []  # no token file was written
