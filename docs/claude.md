# claude.md: Attention Platform (Weeks 3–4 Progress)

## Project Context
- **Stack:** FastAPI + PostgreSQL (sync SQLAlchemy 2.0, Alembic), Python 3.13, Windows, pytest, scikit-learn
- **Parts:** `backend/`, `desktop-agent/`, `frontend/` (React + Electron), `extension/`
- **Timezone:** `Asia/Kolkata` (`DEFAULT_TZ` in `app/ml/features.py`)
- **API prefix:** `/api/v1`
- **Celery:** abhi placeholder (Redis nahi hai). Nightly job plain Python script hai.
- **Insight text language:** English (frontend bhi English me hai)

## Rules for Claude (is project me)
1. **Pehle pucho, assume mat karo.** Existing file ka content na dikhe toh paste karwao.
2. Hinglish me jawab, chhote aur direct. Token kam use karo.
3. Existing files (`stats_service`, `scoring_service`, `analytics.py`) overwrite mat karo. Naye files banao.
4. Logic pure functions me (`app/ml/`), DB access sirf repository me, tests pehle pure logic ke.
5. Har step ke baad `pytest` chalwao aur result pucho.
6. ML results ke baare me sach likho. Demo data synthetic hai, "accuracy achhi hai" jaisa claim mat karo.
7. Bade code edits ke liye downloadable file do (copy-paste me edits chhoot jaate hain).

---

## ✅ Done

| Part | File | Status |
|---|---|---|
| DailyMetric model + migration | `models/daily_metric.py` | ✅ |
| Features | `ml/features.py` | ✅ `test_features.py` |
| Distraction rules | `ml/distraction.py` | ✅ `test_distraction.py` |
| Scoring + `trailing_run` + `is_system_app` | `ml/focus_score.py` | ✅ code diya, tests add karne hain |
| Rule-based predictions | `ml/predictor.py` | ✅ `test_predictor.py` |
| Insights (English) + daily summary | `ml/insights.py` | ✅ `test_insights.py` |
| ML forecast (features + predict) | `ml/forecast.py` | ✅ `test_forecast.py` |
| ML training (Ridge / RF / GBR, baselines) | `ml/train.py` | ✅ run ho chuka |
| Services + repository | `analytics_repository.py`, `analytics_service.py`, `daily_score_service.py`, `prediction_service.py`, `insight_service.py` | ✅ |
| 6 endpoints + `/analytics/trend` | `api/routes/analytics_report.py` | ✅ |
| Nightly job | `jobs/nightly.py` | ✅ |
| Seed demo data | `jobs/seed_demo.py` | ✅ `--days 180` |
| Integration tests | `tests/integration/test_analytics_flow.py` | ⏳ file di gayi, result confirm nahi |
| Frontend Insights page | `frontend/src/App.jsx`, `lib/api.js` | ✅ dikh raha hai (`electron:dev`) |
| Windows installer | `frontend/release/Attention Setup 0.1.0.exe` | ✅ bana, install karke Start Menu se chalta hai |

### ML result (`python -m app.ml.train`, 180 din demo data)
- Task: kal ka focus score (regression), time-based split (141 train / 36 test)
- Baselines MAE: "kal = aaj" 3.92, "average" 4.36
- Ridge 7.88 | RandomForest 3.60 | **GradientBoosting 3.41 (best, R² 0.22)** → beats baselines
- Saved: `app/ml/saved_models/focus_model.joblib`
- **Note:** data synthetic hai (weekday + mood pattern seed me daala). Pipeline validate hota hai, real accuracy nahi. Real data jama hone par retrain karo.
- Forecast card tab dikhega jab asli data ke **3 lagatar din** honge.

### Last confirmed test run
- Full suite: **98 passed** (fixes aur naye tests se pehle)

---

## ⏳ Pending (chhote, pehle karo)

- [ ] `python -m pytest tests -v` dobara chalao (trailing_run, system apps, English insights ke baad)
- [ ] `tests/test_focus_score.py` me `test_trailing_run_ignores_gaps` add karo
- [ ] `tests/test_insights.py`: `test_leaks_ignore_system_apps` add karo, aur `"gir raha"` ko `"dropping"` karo
- [ ] `tests/test_analytics_endpoints.py` ke `PATHS` me `"trend"` add karo
- [ ] `tests/integration/test_analytics_flow.py` chalao (trend endpoint add hona zaroori, warna 2 tests 404)
- [ ] `requirements.txt` me `scikit-learn==1.9.1`
- [ ] `.gitignore` me `backend/app/ml/saved_models/*.joblib`
- [ ] DB me tumhara apna test data (10-11 se 10-19 Oct) `--reset` se delete nahi hota, scores bigaadta hai

## ▶️ Next Work

1. **Insights page ko chhota karo (easy to understand):** score + "kyun" (2–3 insights) + ek tip + kal ka andaza. Chart aur risks "More details" ke peeche.
2. **`start_attention.bat`:** ek double-click me backend start karke app khole.
3. **Installer ko hosted backend se jodna:** abhi `.env.production` me `http://127.0.0.1:8000/api/v1`. Server pe deploy karo toh URL badlo, rebuild karo. CORS ka dhyan rakho.
4. **App icon** (`build.win.icon`, `.ico` file), abhi default Electron icon.
5. **Nightly job schedule:** Windows Task Scheduler me `python -m app.jobs.nightly` daily 00:10.
6. Baad me: Celery + Redis, notification tracking (abhi deferred, `notif_penalty` = 0), thresholds `core/config.py` me, productive/unproductive app lists user-configurable, real data pe retrain.

## ⚠️ Known Notes

- **Installer rebuild:** purani app band karo (`Get-Process Attention, attention-agent | Stop-Process -Force`), `.env.production` check karo, `npm run dist:win`, purani uninstall karke naya install. `npm run electron:dev` dev mode hai, installed app alag hai.
- **Backend manual start:** `uvicorn app.main:app --host 127.0.0.1 --port 8000` (aur PostgreSQL service chalu). App ke saath start nahi hota.
- `explorer.exe` jaise Windows system apps ab leaks me nahi ginte (`is_system_app`).
- Trend sirf lagatar dino pe nikalta hai (gap hone par fake "dropping" alarm nahi aata).
- `GET /analytics/*` har call par us din ka report recompute karke upsert karta hai. Load badhe toh nightly job se compute karo.
- `ml/focus_score.py` me `PRODUCTIVE` / `UNPRODUCTIVE` lists apne apps ke hisaab se edit karo (chrome jaise apps ignore hote hain).
- Windows SmartScreen "unknown publisher" dikha sakta hai (installer signed nahi). "More info → Run anyway".
- Swagger ka Bearer token share mat karo.

## Viva flow
raw activity → features → score → ML model → kal ka prediction → insight
1. `ml/train.py` (3 models, `fit()`, baselines) 2. `python -m app.ml.train` 3. `focus_model.joblib` 4. Swagger `/analytics/predictions` 5. App ka Insights page 6. `pytest tests -v`
- Sach batana: models scikit-learn ke hain, features/dataset/evaluation/integration mera kaam hai; data synthetic hai.

## Definition of Done (Weeks 3–4)

- [x] Dummy data (1000+ rows) pe sab scores generate
- [x] Nightly job chalta hai
- [x] 6 endpoints working
- [x] 3+ type ke readable insights
- [x] ML model trained aur API me integrated
- [x] Frontend Insights page
- [x] Windows installer
- [ ] Saare tests green (pending fixes ke baad confirm)