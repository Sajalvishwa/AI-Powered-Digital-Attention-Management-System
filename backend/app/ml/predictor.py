"""Rule-based predictions. Pure functions, no DB."""
from collections import defaultdict
from dataclasses import dataclass

from app.ml.focus_score import trend_slope


@dataclass(frozen=True)
class PredThresholds:
    degrade_warn_slope: float = -1.0   # focus pts/day
    degrade_high_slope: float = -3.0
    risk_low_score: float = 50.0
    risk_low_days: int = 3
    risk_slope: float = -3.0
    fatigue_after_min: int = 90
    fatigue_min_before_min: int = 30
    fatigue_min_after_min: int = 15
    fatigue_ratio: float = 2.0
    fatigue_min_switches: int = 2
    fatigue_baseline_rate: float = 1.0  # switches/hour floor


PT = PredThresholds()


def focus_degradation(focus_scores, th=PT):
    """focus_scores: oldest->newest, None already removed."""
    slope = trend_slope(focus_scores)
    if slope is None:
        return {"status": "insufficient_data", "slope": None}
    if slope <= th.degrade_high_slope:
        status = "high"
    elif slope <= th.degrade_warn_slope:
        status = "warning"
    else:
        status = "ok"
    return {"status": status, "slope": slope}


def productivity_risk(prod_scores, th=PT):
    """prod_scores: oldest->newest, None already removed."""
    reasons = []
    last = prod_scores[-th.risk_low_days:]
    if len(last) == th.risk_low_days and all(s < th.risk_low_score for s in last):
        reasons.append(f"score < {th.risk_low_score:g} for {th.risk_low_days} days")
    slope = trend_slope(prod_scores)
    if slope is not None and slope < th.risk_slope:
        reasons.append(f"falling {slope} pts/day")
    return {"at_risk": bool(reasons), "reasons": reasons, "slope": slope}


def attention_fatigue(activity, th=PT):
    """Per focus session: do app switches speed up after the 90-min mark?"""
    groups = defaultdict(list)
    for r in activity:
        if r["focus_session_id"]:
            groups[r["focus_session_id"]].append(r)

    out = []
    for sid, rows in groups.items():
        rows.sort(key=lambda r: r["started_at"])
        start = rows[0]["started_at"]
        dur = (max(r["ended_at"] for r in rows) - start).total_seconds() / 60
        before_min = min(dur, th.fatigue_after_min)
        after_min = dur - th.fatigue_after_min
        if before_min < th.fatigue_min_before_min or after_min < th.fatigue_min_after_min:
            continue

        before_sw = after_sw = 0
        prev = None
        for r in rows:
            if r["is_idle"]:
                continue
            if prev is not None and r["app_name"] != prev:
                off = (r["started_at"] - start).total_seconds() / 60
                if off < th.fatigue_after_min:
                    before_sw += 1
                else:
                    after_sw += 1
            prev = r["app_name"]

        before_rate = before_sw / (before_min / 60)
        after_rate = after_sw / (after_min / 60)
        fatigued = (
            after_sw >= th.fatigue_min_switches
            and after_rate >= th.fatigue_ratio * max(before_rate, th.fatigue_baseline_rate)
        )
        out.append({
            "focus_session_id": sid,
            "duration_min": round(dur, 1),
            "before_rate_per_hr": round(before_rate, 2),
            "after_rate_per_hr": round(after_rate, 2),
            "fatigued": fatigued,
        })
    return out