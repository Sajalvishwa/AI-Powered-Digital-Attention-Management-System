
import pytest

from app.settings import SettingsError, load_settings


def write(tmp_path, text: str) -> None:
    (tmp_path / "config.toml").write_text(text, encoding="utf-8")


def test_first_run_creates_default_config(tmp_path):
    settings = load_settings(tmp_path)

    assert (tmp_path / "config.toml").exists()
    assert settings.api_base_url == "http://127.0.0.1:8000/api/v1"
    assert settings.poll_interval_sec == 1.0
    assert settings.idle_threshold_sec == 120
    assert settings.sync_interval_sec == 30
    assert settings.log_file == tmp_path / "agent.log"
    assert settings.buffer_db == tmp_path / "buffer.db"


def test_values_are_read_from_file(tmp_path):
    write(
        tmp_path,
        'idle_threshold_sec = 300\n'
        'log_level = "debug"\n'
        'poll_interval_sec = 0.5\n',
    )

    settings = load_settings(tmp_path)

    assert settings.idle_threshold_sec == 300
    assert settings.poll_interval_sec == 0.5
    assert settings.log_level == "DEBUG"


def test_http_only_allowed_for_localhost(tmp_path):
    write(tmp_path, 'api_base_url = "http://example.com/api/v1"\n')

    with pytest.raises(SettingsError, match="https"):
        load_settings(tmp_path)

    write(tmp_path, 'api_base_url = "https://example.com/api/v1/"\n')
    assert load_settings(tmp_path).api_base_url == "https://example.com/api/v1"

    write(tmp_path, 'api_base_url = "http://localhost:8000/api/v1"\n')
    assert (
        load_settings(tmp_path).api_base_url
        == "http://localhost:8000/api/v1"
    )


def test_bad_url_rejected(tmp_path):
    write(tmp_path, 'api_base_url = "not a url"\n')

    with pytest.raises(SettingsError):
        load_settings(tmp_path)


@pytest.mark.parametrize(
    "line",
    [
        "idle_threshold_sec = 5",
        "poll_interval_sec = 0",
        "sync_interval_sec = 1000",
        "idle_threshold_sec = true",
        'poll_interval_sec = "fast"',
        "idle_threshold_sec = 60.5",
    ],
)
def test_out_of_range_or_wrong_type_rejected(tmp_path, line):
    write(tmp_path, line + "\n")

    with pytest.raises(SettingsError):
        load_settings(tmp_path)


def test_typos_are_reported(tmp_path):
    write(tmp_path, "idle_treshold_sec = 100\n")

    with pytest.raises(SettingsError, match="idle_treshold_sec"):
        load_settings(tmp_path)


def test_invalid_toml_reported(tmp_path):
    write(tmp_path, "this is = = not toml")

    with pytest.raises(SettingsError, match="TOML"):
        load_settings(tmp_path)


def test_file_saved_with_bom_is_accepted(tmp_path):
    (tmp_path / "config.toml").write_bytes(
        b"\xef\xbb\xbf" + b"idle_threshold_sec = 200\n"
    )

    assert load_settings(tmp_path).idle_threshold_sec == 200


# T3.8: Privacy configuration tests


def test_privacy_settings_default_to_safe_values(tmp_path):
    settings = load_settings(tmp_path)

    assert settings.store_window_titles is False
    assert settings.ignored_apps == ()


def test_privacy_settings_are_loaded_and_ignore_duplicates(tmp_path):
    write(
        tmp_path,
        "store_window_titles = true\n"
        'ignored_apps = ["Chrome.exe", "chrome.EXE", "Discord.exe"]\n',
    )

    settings = load_settings(tmp_path)

    assert settings.store_window_titles is True
    assert settings.ignored_apps == ("Chrome.exe", "Discord.exe")


@pytest.mark.parametrize(
    "config",
    [
        'store_window_titles = "true"\n',
        'ignored_apps = "chrome.exe"\n',
        'ignored_apps = ["chrome.exe", 123]\n',
        'ignored_apps = [""]\n',
    ],
)
def test_invalid_privacy_settings_are_rejected(tmp_path, config):
    write(tmp_path, config)

    with pytest.raises(SettingsError):
        load_settings(tmp_path)
