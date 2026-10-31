from datetime import datetime, timezone

from app.ml.predictor import attention_fatigue, focus_degradation, productivity_risk

UTC = timezone.utc


def _row(app, h1, m1, h2, m2, fs="x", idle=False):
    return {"app_name": app, "is_idle": idle, "focus_session_id": fs,
            "started_at": datetime(2026, 1, 5, h1, m1, tzinfo=UTC),
            "ended_at": datetime(2026, 1, 5, h2, m2, tzinfo=UTC)}


def test_focus_degradation():
    assert focus_degradation([70, 68, 66])["status"] == "warning"   # slope -2
    assert focus_degradation([70, 65, 60])["status"] == "high"      # slope -5
    assert focus_degradation([60, 62, 64])["status"] == "ok"
    assert focus_degradation([60, 62])["status"] == "insufficient_data"


def test_productivity_risk_low_days():
    r = productivity_risk([80, 45, 40, 30])
    assert r["at_risk"] and len(r["reasons"]) == 2  # low 3 days + slope


def test_productivity_risk_ok():
    assert not productivity_risk([60, 65, 70])["at_risk"]
    assert not productivity_risk([40, 45])["at_risk"]  # <3 days, <3 points


def test_fatigue_detected():
    rows = [
        _row("code", 10, 0, 10, 30), _row("chrome", 10, 30, 11, 0),
        _row("code", 11, 0, 11, 30),                       # 2 switches before 90 min
        _row("chrome", 11, 30, 11, 45), _row("code", 11, 45, 12, 0),
        _row("chrome", 12, 0, 12, 15), _row("code", 12, 15, 12, 30),  # 4 after
    ]
    r = attention_fatigue(rows)
    assert len(r) == 1 and r[0]["fatigued"]
    assert r[0]["before_rate_per_hr"] == 1.33 and r[0]["after_rate_per_hr"] == 4.0


def test_fatigue_short_session_skipped():
    rows = [_row("code", 10, 0, 10, 30), _row("chrome", 10, 30, 11, 0)]
    assert attention_fatigue(rows) == []


def test_fatigue_not_detected_when_steady():
    rows = [
        _row("code", 10, 0, 11, 30),                       # no switches before
        _row("chrome", 11, 30, 12, 30),                    # 1 switch after only
    ]
    r = attention_fatigue(rows)
    assert len(r) == 1 and not r[0]["fatigued"]