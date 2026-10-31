from datetime import date

from app.ml.insights import attention_leaks, build_insights, daily_summary

FEAT = {"focus_min": 90, "active_min": 200,
        "hourly_focus_min": [0] * 10 + [60, 30] + [0] * 12,
        "hourly_active_min": [0] * 10 + [60, 30] + [0] * 12}
PRED_OK = {"focus_degradation": {"status": "ok", "slope": 1.0},
           "productivity_risk": {"at_risk": False, "reasons": []},
           "attention_fatigue": {"fatigued_sessions": 0}}
NO_NOTIF = {"total": 0, "impact_rate": 0.0}


def test_leaks():
    ev = [{"to_app": "youtube", "idle": False}, {"to_app": "youtube", "idle": False},
          {"to_app": "chrome", "idle": False}, {"to_app": None, "idle": True}]
    assert attention_leaks(ev) == [{"app": "youtube", "interruptions": 2},
                                   {"app": "chrome", "interruptions": 1}]


def test_insights_multiple_types():
    leaks = [{"app": "youtube", "interruptions": 4}]
    pred = {**PRED_OK, "focus_degradation": {"status": "warning", "slope": -2.0},
            "attention_fatigue": {"fatigued_sessions": 1}}
    ins = build_insights(FEAT, {"focus_score": 75}, leaks, [{"count": 3}], [14],
                         {"total": 4, "impact_rate": 0.75}, pred)
    types = {i["type"] for i in ins}
    assert {"pattern", "leak", "switching", "interruptions", "notification",
            "warning", "fatigue", "positive"} <= types
    assert "10:00-11:00" in next(i["text"] for i in ins if i["type"] == "pattern")


def test_summary_suggestion_priority():
    leaks = [{"app": "youtube", "interruptions": 4}]
    pred = {**PRED_OK, "focus_degradation": {"status": "high", "slope": -4.0}}
    ins = build_insights(FEAT, {"focus_score": 50}, leaks, [], [], NO_NOTIF, pred)
    s = daily_summary(date(2026, 1, 5), {"focus_score": 50}, FEAT, leaks, ins)
    assert "dropping" in s["suggestion"]          # warning beats leak         # warning beats leak
    assert s["top_distraction"] == "youtube" and s["best_hour"] == "10:00-11:00"


def test_empty_day():
    empty = {"focus_min": 0, "active_min": 0,
             "hourly_focus_min": [0] * 24, "hourly_active_min": [0] * 24}
    ins = build_insights(empty, {"focus_score": None}, [], [], [], NO_NOTIF, PRED_OK)
    assert ins == []
    s = daily_summary(date(2026, 1, 5), {}, empty, [], ins)
    assert s["best_hour"] is None and "focus session" in s["suggestion"]

def test_leaks_ignore_productive_apps():
    ev = [{"to_app": "Code.exe", "idle": False}, {"to_app": "youtube", "idle": False}]
    assert attention_leaks(ev) == [{"app": "youtube", "interruptions": 1}]

def test_leaks_ignore_system_apps():
    ev = [{"to_app": "explorer.exe", "idle": False}, {"to_app": "youtube", "idle": False}]
    assert attention_leaks(ev) == [{"app": "youtube", "interruptions": 1}]