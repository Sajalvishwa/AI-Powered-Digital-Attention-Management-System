from datetime import date, timedelta

from app.ml.forecast import FEATURES, build_dataset, predict_next, row_features


def _row(d, fs):
    return {"day": d, "focus_score": fs, "productivity_score": None, "stability_score": None,
            "focus_min": 60, "active_min": 200, "avg_session_min": 25,
            "switch_count": 10, "session_count": 3}


MON = date(2026, 1, 5)  # a Monday


def _rows(offsets, scores):
    return [_row(MON + timedelta(days=o), s) for o, s in zip(offsets, scores)]


def test_row_features_values():
    f = row_features(_rows([0, 1, 2], [50, 52, 56]))
    assert f["focus_trend3"] == 6 and f["focus_lag1"] == 52
    assert f["target_weekday"] == 3          # today Wed -> target Thu
    assert f["prod_score"] == 50.0           # None filled


def test_row_features_gap_or_short():
    assert row_features(_rows([0, 1, 3], [50, 52, 56])) is None
    assert row_features(_rows([0, 1], [50, 52])) is None


def test_build_dataset():
    rows = _rows(range(6), [50, 52, 54, 56, 58, 60])
    s = build_dataset({"u": rows})
    assert len(s) == 3 and len(s[0]["x"]) == len(FEATURES)
    assert s[0]["y"] == 56 and s[0]["last"] == 54


def test_build_dataset_skips_gaps():
    rows = _rows([0, 1, 2, 3, 5, 6, 7], [50] * 7)
    assert len(build_dataset({"u": rows})) == 1


class _Fake:
    def predict(self, X):
        return [123.0]


def test_predict_next_clamps_and_reports():
    r = predict_next(_rows([0, 1, 2], [50, 52, 56]),
                     bundle={"model": _Fake(), "metrics": {"mae": 2.5}})
    assert r["available"] and r["predicted_focus_score"] == 100.0
    assert r["for_day"] == "2026-01-08" and r["model_mae"] == 2.5


def test_predict_next_not_enough_history():
    r = predict_next(_rows([0, 1], [50, 52]), bundle={"model": _Fake(), "metrics": {"mae": 1}})
    assert not r["available"]