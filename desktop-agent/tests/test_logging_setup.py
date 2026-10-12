from app.logging_setup import close_logging, redact, setup_logging
from app.settings import AgentSettings


def test_redact_masks_tokens_and_passwords():
    assert redact("Authorization: Bearer abc.def.ghi") == "Authorization: Bearer ***"
    assert redact("refresh_token=abc123") == "refresh_token=***"
    assert redact('{"password": "hunter2"}') == '{"password": "***"}'
    assert redact("nothing secret here") == "nothing secret here"


def test_secrets_never_reach_the_log_file(tmp_path):
    settings = AgentSettings(data_dir=tmp_path)
    log = setup_logging(settings, console=False)
    try:
        log.info("sending Authorization: Bearer abc.def.ghi to server")
        log.info("login password=hunter2")
    finally:
        close_logging()
    text = settings.log_file.read_text(encoding="utf-8")
    assert "abc.def.ghi" not in text and "hunter2" not in text
    assert "Bearer ***" in text
