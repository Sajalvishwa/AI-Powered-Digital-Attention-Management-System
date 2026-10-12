import pytest

import app.main as main_module
from app.main import main
from app.tracker import ForegroundWindow, TrackerUnavailable
from tests.helpers import FakeTracker


def test_main_runs_and_logs_app_name_but_never_the_title(tmp_path):
    (tmp_path / "config.toml").write_text("poll_interval_sec = 0.1\n", encoding="utf-8")
    tracker = FakeTracker([ForegroundWindow("Code.exe", "SECRET TITLE", 1)])
    assert main(["--data-dir", str(tmp_path), "--debug", "--max-ticks", "2"], tracker=tracker) == 0
    log_text = (tmp_path / "agent.log").read_text(encoding="utf-8")
    assert "starting" in log_text
    assert "foreground app = Code.exe" in log_text
    assert "Agent stopped after 2 ticks" in log_text
    assert "SECRET TITLE" not in log_text


def test_bad_config_returns_exit_code_2(tmp_path, capsys):
    (tmp_path / "config.toml").write_text('api_base_url = "http://example.com"\n', encoding="utf-8")
    assert main(["--data-dir", str(tmp_path), "--max-ticks", "1"], tracker=FakeTracker()) == 2
    assert "Config error" in capsys.readouterr().err


def test_missing_windows_support_returns_exit_code_3(tmp_path, capsys, monkeypatch):
    def unavailable(*args, **kwargs):
        raise TrackerUnavailable("pywin32 missing")

    monkeypatch.setattr(main_module, "WindowTracker", unavailable)
    assert main(["--data-dir", str(tmp_path), "--max-ticks", "1"]) == 3
    assert "pywin32 missing" in capsys.readouterr().err


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--version"])
    assert exc.value.code == 0
    assert "attention-agent" in capsys.readouterr().out
