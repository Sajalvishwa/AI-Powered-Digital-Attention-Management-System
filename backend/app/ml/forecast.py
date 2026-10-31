
"""Next-day focus score forecasting. Feature building shared by train + predict."""

from datetime import timedelta
from pathlib import Path
from statistics import mean

import joblib


MODEL_PATH = Path(__file__).parent / "saved_models" / "focus_model.joblib"

FEATURES = [
    "focus_score",
    "prod_score",
    "stability",
    "focus_min",
    "active_min",
    "avg_session_min",
    "switch_count",
    "session_count",
    "focus_lag1",
    "focus_mean3",
    "focus_trend3",
    "target_weekday",
    "target_weekend",
]


def merge_row(m, s):
    """DailyMetric + DailyScore -> one plain dict."""
    return {
        "day": m.day,
        "focus_score": s.focus_score,
        "productivity_score": s.productivity_score,
        "stability_score": s.stability_score,
        "focus_min": m.focus_min,
        "active_min": m.active_min,
        "avg_session_min": m.avg_session_min,
        "switch_count": m.switch_count,
        "session_count": m.session_count,
    }


def _v(x, default):
    return default if x is None else x


def row_features(rows):
    """Build features from the last 3 consecutive days, oldest to newest."""
    if len(rows) < 3:
        return None

    last3 = rows[-3:]

    if (last3[-1]["day"] - last3[0]["day"]).days != 2:
        return None

    f = [r["focus_score"] for r in last3]

    if any(x is None for x in f):
        return None

    t = last3[-1]

    return {
        "focus_score": f[-1],
        "prod_score": _v(t["productivity_score"], 50.0),
        "stability": _v(t["stability_score"], 50.0),
        "focus_min": t["focus_min"],
        "active_min": t["active_min"],
        "avg_session_min": t["avg_session_min"],
        "switch_count": t["switch_count"],
        "session_count": t["session_count"],
        "focus_lag1": f[-2],
        "focus_mean3": mean(f),
        "focus_trend3": f[-1] - f[0],
        "target_weekday": (
            t["day"].weekday() + 1
            if t["day"].weekday() < 6
            else 0
        ),
        "target_weekend": (
            1 if (t["day"].weekday() + 1) % 7 >= 5 else 0
        ),
    }


def build_dataset(rows_by_user):
    """Build training samples with next-day focus scores as targets.

    Returns samples containing:
        x: feature vector
        y: next day's focus score
        day: target day
        last: current day's focus score
    """
    samples = []

    for rows in rows_by_user.values():
        rows = sorted(rows, key=lambda r: r["day"])

        for i in range(2, len(rows) - 1):
            nxt = rows[i + 1]

            if (
                (nxt["day"] - rows[i]["day"]).days != 1
                or nxt["focus_score"] is None
            ):
                continue

            feats = row_features(rows[i - 2 : i + 1])

            if feats is None:
                continue

            samples.append({
                "x": [feats[k] for k in FEATURES],
                "y": nxt["focus_score"],
                "day": nxt["day"],
                "last": rows[i]["focus_score"],
            })

    return sorted(samples, key=lambda s: s["day"])


def load_bundle():
    """Load the trained forecasting model, if available."""
    return joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


def predict_next(history, bundle=None):
    """Predict the next day's focus score from merged historical rows."""
    bundle = bundle or load_bundle()

    if bundle is None:
        return {
            "available": False,
            "reason": "model not trained yet (run: python -m app.ml.train)",
        }

    feats = row_features(history)

    if feats is None:
        return {
            "available": False,
            "reason": "need 3 consecutive days of scores",
        }

    pred = float(
        bundle["model"].predict([
            [feats[k] for k in FEATURES]
        ])[0]
    )

    return {
        "available": True,
        "for_day": (
            history[-1]["day"] + timedelta(days=1)
        ).isoformat(),
        "predicted_focus_score": round(
            max(0.0, min(100.0, pred)), 2
        ),
        "model_mae": bundle["metrics"]["mae"],
    }
