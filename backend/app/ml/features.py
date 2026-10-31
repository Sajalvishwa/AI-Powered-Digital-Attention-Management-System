from collections import defaultdict
from datetime import timedelta
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Kolkata"


def _split_hours(start, end):
    """Yield (hour, seconds) pieces so a session crossing an hour is split."""
    cur = start
    while cur < end:
        nxt = min(cur.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1), end)
        yield cur.hour, (nxt - cur).total_seconds()
        cur = nxt


def build_daily_features(activity, focus_sessions, tz=DEFAULT_TZ):
    """activity: list of dicts (app_name,is_idle,started_at,ended_at,focus_session_id)
    focus_sessions: list of dicts (started_at,ended_at,status)"""
    zone = ZoneInfo(tz)
    h_active, h_focus, h_sw = [0.0] * 24, [0.0] * 24, [0] * 24
    app_sec, idle_sec, prev_app = defaultdict(float), 0.0, None

    for r in sorted(activity, key=lambda r: r["started_at"]):
        s, e = r["started_at"].astimezone(zone), r["ended_at"].astimezone(zone)
        if r["is_idle"]:
            idle_sec += (e - s).total_seconds()
            continue
        for h, sec in _split_hours(s, e):
            h_active[h] += sec / 60
            if r["focus_session_id"]:
                h_focus[h] += sec / 60
        app_sec[r["app_name"]] += (e - s).total_seconds()
        if prev_app is not None and r["app_name"] != prev_app:
            h_sw[s.hour] += 1
        prev_app = r["app_name"]

    durs = [
        (f["ended_at"] - f["started_at"]).total_seconds() / 60
        for f in focus_sessions
        if f["ended_at"] and f["status"] == "completed"
    ]
    top = sorted(app_sec.items(), key=lambda x: -x[1])[:5]
    return {
        "active_min": round(sum(h_active), 2),
        "idle_min": round(idle_sec / 60, 2),
        "focus_min": round(sum(h_focus), 2),
        "session_count": len(durs),
        "avg_session_min": round(sum(durs) / len(durs), 2) if durs else 0.0,
        "longest_session_min": round(max(durs), 2) if durs else 0.0,
        "switch_count": sum(h_sw),
        "hourly_active_min": [round(x, 2) for x in h_active],
        "hourly_focus_min": [round(x, 2) for x in h_focus],
        "hourly_switches": h_sw,
        "top_apps": {a: round(s / 60, 2) for a, s in top},
    }


def best_hour(hourly):
    """Hour (0-23) with most minutes, None if no data."""
    return max(range(24), key=lambda h: hourly[h]) if any(hourly) else None


def moving_average(values, window=7):
    """Trailing moving average; early days use whatever data exists."""
    return [
        round(sum(values[max(0, i - window + 1): i + 1]) / len(values[max(0, i - window + 1): i + 1]), 2)
        for i in range(len(values))
    ]