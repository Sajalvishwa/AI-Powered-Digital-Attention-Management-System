"""Rule-based distraction detection. Pure functions, no DB."""
from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True)
class Thresholds:
    interruption_window_min: int = 30
    interruption_min_count: int = 3
    high_switches_per_hour: int = 20
    notif_window_min: int = 5
    short_session_min: int = 5
    long_idle_sec: int = 120


TH = Thresholds()


def _sorted(activity):
    return sorted(activity, key=lambda r: r["started_at"])


def interruption_events(activity):
    """App switch or idle start right after a row that was inside a focus session."""
    out, prev = [], None
    for r in _sorted(activity):
        if (
            prev is not None
            and prev["focus_session_id"]
            and not prev["is_idle"]
            and (r["is_idle"] or r["app_name"] != prev["app_name"])
        ):
            out.append({
                "at": r["started_at"],
                "from_app": prev["app_name"],
                "to_app": None if r["is_idle"] else r["app_name"],
                "idle": r["is_idle"],
            })
        prev = r
    return out


def frequent_interruptions(events, th=TH):
    """Clusters where >= min_count interruptions happen within the window."""
    ev = sorted(events, key=lambda e: e["at"])
    win = timedelta(minutes=th.interruption_window_min)
    ranges = []
    for i in range(len(ev)):
        j = i
        while j + 1 < len(ev) and ev[j + 1]["at"] - ev[i]["at"] <= win:
            j += 1
        if j - i + 1 >= th.interruption_min_count:
            s, e = ev[i]["at"], ev[j]["at"]
            if ranges and s <= ranges[-1][1]:
                ranges[-1][1] = max(ranges[-1][1], e)
            else:
                ranges.append([s, e])
    return [
        {"start": s, "end": e, "count": sum(1 for x in ev if s <= x["at"] <= e)}
        for s, e in ranges
    ]


def high_switch_hours(hourly_switches, th=TH):
    """Hours (0-23) where app switches exceed the threshold."""
    return [h for h, c in enumerate(hourly_switches) if c > th.high_switches_per_hour]


def focus_loss_events(activity, focus_sessions, th=TH):
    """Short focus sessions (< 5 min) and long idle gaps (> 2 min)."""
    out = []
    for f in focus_sessions:
        if f["ended_at"] and f["status"] in ("completed", "cancelled"):
            sec = (f["ended_at"] - f["started_at"]).total_seconds()
            if sec / 60 < th.short_session_min:
                out.append({"type": "short_session", "at": f["started_at"], "duration_sec": int(sec)})
    for r in activity:
        if r["is_idle"]:
            sec = (r["ended_at"] - r["started_at"]).total_seconds()
            if sec > th.long_idle_sec:
                out.append({"type": "long_idle", "at": r["started_at"], "duration_sec": int(sec)})
    return sorted(out, key=lambda x: x["at"])


def notification_impact(activity, notifications, th=TH):
    """Notification counts as impactful if an app switch follows within the window."""
    switches, prev = [], None
    for r in _sorted(activity):
        if r["is_idle"]:
            continue
        if prev is not None and r["app_name"] != prev:
            switches.append(r["started_at"])
        prev = r["app_name"]

    win = timedelta(minutes=th.notif_window_min)
    impacted, by_app = 0, {}
    for n in notifications:
        t = n["received_at"]
        if any(t < s <= t + win for s in switches):
            impacted += 1
            by_app[n["app_name"]] = by_app.get(n["app_name"], 0) + 1
    total = len(notifications)
    return {
        "total": total,
        "impacted": impacted,
        "impact_rate": round(impacted / total, 2) if total else 0.0,
        "by_app": by_app,
    }