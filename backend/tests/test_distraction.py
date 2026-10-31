from datetime import datetime, timezone

from app.ml.distraction import (
    focus_loss_events, frequent_interruptions, high_switch_hours,
    interruption_events, notification_impact,
)

UTC = timezone.utc


def _t(h, m):
    return datetime(2026, 1, 5, h, m, tzinfo=UTC)


def _row(app, h1, m1, h2, m2, idle=False, fs="x"):
    return {"app_name": app, "is_idle": idle, "focus_session_id": fs,
            "started_at": _t(h1, m1), "ended_at": _t(h2, m2)}


ACT = [
    _row("code", 10, 0, 10, 10),
    _row("chrome", 10, 10, 10, 12),
    _row("code", 10, 12, 10, 20),
    _row("idle", 10, 20, 10, 23, idle=True),
    _row("code", 10, 23, 10, 30),
    _row("chrome", 11, 30, 11, 31),
]


def test_interruptions_and_clusters():
    ev = interruption_events(ACT)
    assert len(ev) == 4
    assert ev[2]["idle"] and ev[2]["to_app"] is None
    cl = frequent_interruptions(ev)
    assert len(cl) == 1 and cl[0]["count"] == 3


def test_high_switch_hours():
    sw = [0] * 24
    sw[14] = 25
    assert high_switch_hours(sw) == [14]


def test_focus_loss():
    fs = [
        {"started_at": _t(9, 0), "ended_at": _t(9, 3), "status": "completed"},
        {"started_at": _t(9, 10), "ended_at": _t(9, 35), "status": "completed"},
    ]
    types = [e["type"] for e in focus_loss_events(ACT, fs)]
    assert sorted(types) == ["long_idle", "short_session"]


def test_notification_impact():
    notifs = [
        {"app_name": "slack", "received_at": _t(10, 9)},
        {"app_name": "mail", "received_at": _t(10, 40)},
    ]
    r = notification_impact(ACT, notifs)
    assert r["total"] == 2 and r["impacted"] == 1
    assert r["impact_rate"] == 0.5 and r["by_app"] == {"slack": 1}


def test_notification_impact_empty():
    assert notification_impact(ACT, [])["impact_rate"] == 0.0