"""Train next-day focus score models and keep the best.   Run: python -m app.ml.train"""
from collections import defaultdict
from datetime import datetime, timezone

import joblib
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sqlalchemy import and_, select

from app.core.database import SessionLocal
from app.ml.forecast import FEATURES, MODEL_PATH, build_dataset, merge_row
from app.models.daily_metric import DailyMetric
from app.models.score import DailyScore

MIN_SAMPLES = 30


def load_rows(db):
    q = (
        select(DailyMetric, DailyScore)
        .join(DailyScore, and_(DailyScore.user_id == DailyMetric.user_id,
                               DailyScore.day == DailyMetric.day))
        .order_by(DailyMetric.user_id, DailyMetric.day)
    )
    by_user = defaultdict(list)
    for m, s in db.execute(q):
        by_user[m.user_id].append(merge_row(m, s))
    return by_user


def candidates():
    return {
        "ridge": make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
        "random_forest": RandomForestRegressor(n_estimators=300, min_samples_leaf=3, random_state=42),
        "gradient_boosting": GradientBoostingRegressor(n_estimators=150, max_depth=2,
                                                       learning_rate=0.05, random_state=42),
    }


def main():
    with SessionLocal() as db:
        samples = build_dataset(load_rows(db))
    if len(samples) < MIN_SAMPLES:
        raise SystemExit(f"Only {len(samples)} samples (need {MIN_SAMPLES}+). "
                         "Run: python -m app.jobs.seed_demo --reset --days 120")

    cut = int(len(samples) * 0.8)            # time-based split: train on past, test on future
    tr, te = samples[:cut], samples[cut:]
    X_tr, y_tr = [s["x"] for s in tr], [s["y"] for s in tr]
    X_te, y_te = [s["x"] for s in te], [s["y"] for s in te]

    mean_tr = sum(y_tr) / len(y_tr)
    base_yday = mean_absolute_error(y_te, [s["last"] for s in te])
    base_mean = mean_absolute_error(y_te, [mean_tr] * len(y_te))
    print(f"samples: {len(tr)} train / {len(te)} test")
    print(f"baseline 'kal = aaj'  MAE: {base_yday:.2f}")
    print(f"baseline 'average'    MAE: {base_mean:.2f}\n")

    results = {}
    for name, model in candidates().items():
        model.fit(X_tr, y_tr)                # <-- training
        pred = model.predict(X_te)
        results[name] = (model, mean_absolute_error(y_te, pred), r2_score(y_te, pred))
        print(f"{name:18s} MAE {results[name][1]:.2f} | R2 {results[name][2]:.2f}")

    best = min(results, key=lambda k: results[k][1])
    model, mae, r2 = results[best]
    best_base = min(base_yday, base_mean)
    print(f"\nbest: {best} | beats baselines: {mae < best_base}")

    imp = getattr(model, "feature_importances_", None)
    if imp is not None:
        print("top features:", sorted(zip(FEATURES, map(float, imp)), key=lambda x: -x[1])[:4])

    joblib.dump({
        "model": model, "name": best, "features": FEATURES,
        "metrics": {"mae": round(mae, 2), "r2": round(r2, 2),
                    "baseline_mae": round(best_base, 2), "beats_baseline": bool(mae < best_base)},
        "trained_on": len(samples),
        "trained_at": datetime.now(timezone.utc).isoformat(),
    }, MODEL_PATH)
    print("saved:", MODEL_PATH)


if __name__ == "__main__":
    main()