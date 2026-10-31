# tasks.md — Week 1–2 Task List

**Rule:** Ek time pe ek task. Task ko `[x]` tabhi mark karo jab implementation aur meaningful verification complete ho. Har task ke baad `memory.md` update karo.

---

## PHASE 0 — Project Setup (Day 1)

- [x] **T0.1** Folder `attention-platform/` banao, `git init`, `.gitignore`, `docs/` mein 7 Markdown files rakho.
- [x] **T0.2** `backend/` aur `desktop/` folders + alag virtual environments (`python -m venv venv`).
- [x] **T0.3** VS Code extensions: Python, Pylance, Ruff, Black, Docker, SQLTools (PostgreSQL), GitLens verify karo.
- [x] **T0.4** PostgreSQL install/configure karo; `attention_dev` + `attention_test` databases banao aur connectivity verify karo.
- [x] **T0.5** `.env.example` banao (`DATABASE_URL`, `JWT_SECRET`, `ACCESS_EXPIRE_MIN`, `REFRESH_EXPIRE_DAYS`).
- [x] **T0.6** Initial Git commit: `chore: project scaffolding`.

## PHASE 1 — Backend Foundation (Days 2–4)

- [x] **T1.1** FastAPI app (`main.py`) + `/health` endpoint + config loader (`pydantic-settings`).
- [x] **T1.2** SQLAlchemy session/base + Alembic initialization.
- [x] **T1.3** Models: users, user_settings, devices (`database.md` ke according).
- [x] **T1.4** Migration #1 run karo aur tables verify karo.
- [x] **T1.5** Security utilities: password hashing (Argon2), JWT create/verify.
- [x] **T1.6** `POST /api/v1/auth/register` — user creation + default settings.
- [x] **T1.7** `POST /api/v1/auth/login`, `/refresh`, `/logout`.
- [x] **T1.8** `get_current_user` dependency.
- [x] **T1.9** `GET/PUT /api/v1/users/me`, `GET/PUT /api/v1/users/me/settings`.
- [x] **T1.10** Pytest tests for authentication, profile and settings — separate task completion verification pending.

## PHASE 2 — Activity Data APIs (Days 5–7)

- [x] **T2.1** Models + migration: `activity_sessions`, `focus_sessions`, `goals`, `notification_events`.
- [x] **T2.2** `POST /api/v1/activity/batch` — validation, limits, idempotent insert using `ON CONFLICT DO NOTHING`.
- [x] **T2.3** Focus session APIs — start, pause, resume, stop and list. Swagger smoke tests pass; one-running-session rule and ownership tests remain to be verified separately.
- [x] **T2.4** `GET /api/v1/stats/today` — basic screen-time, top-app usage and hourly timeline verified. Focus-time and task-switch calculations are also covered by the new stats integration test.
- [x] **T2.5** `GET /api/v1/stats/range` — date-range aggregation, reversed-date rejection, 92-calendar-day limit, empty daily buckets, active/idle/focus totals and app-switch calculations tested.
- [x] **T2.6** Goals CRUD — create, read, update and delete goals.
- [x] **T2.7** `DELETE /api/v1/users/me/data` — safely delete the current user's data.
- [x] **T2.8** Rate limiting on authentication and activity batch endpoints — register (3/min/IP), login (20/min/IP + 5/min/email), refresh (30/min/IP), activity batch (30/min/user). Core and endpoint-level rate-limit tests are included in the passing suite.
- [x] **T2.9** Pytest coverage for APIs, validation, duplicates, edge cases, ownership isolation and stats. Full backend test suite: **61 passed**.

## PHASE 3 — Desktop Tracker Core (Days 8–10)

- [x] **T3.1** `desktop-agent/app/...` skeleton and entry point verify/scaffold karo.
- [x] **T3.2** `window_tracker.py` — foreground application name and title (`pywin32` + `psutil`).
- [x] **T3.3** `idle.py` — idle detection (`GetLastInputInfo` / `GetTickCount64`).
- [x] **T3.4** `session_builder.py` — pure logic: events → sessions; unit tests likho.
- [x] **T3.5** SQLite offline buffer (`pending_sessions`) — save, read and mark synced.
- [x] **T3.6** API client + secure token storage using `keyring`.
- [x] **T3.7** Sync worker — batch upload every 30 seconds with retry and backoff.
- [x] **T3.8** Ignore-list + `store_window_titles` privacy setting enforce karo.
- [x] **T3.9** Tracker ko headless mode mein 1 hour chalao; PostgreSQL data, idle time aur app-switch counts verify karo.

## PHASE 4 — Frontend: React Dashboard (Days 11–13)

- [x] **T4.1** Vite + React setup, `design.md` CSS-variable theme tokens aur Axios client.
- [x] **T4.2** Login + Register screens.
- [x] **T4.3** Onboarding — focus goal, idle threshold aur privacy consent.
- [x] **T4.4** Main shell — top bar + sidebar navigation.
- [x] **T4.5** Today dashboard — stat cards, timeline chart aur top apps.
- [x] **T4.6** Focus Session screen — ring timer + mini floating widget.
- [x] **T4.7** Apps screen + Goals screen.
- [x] **T4.8** Settings screen — tracking, theme, export/delete data.
- [x] **T4.9** Desktop agent tray icon (`pystray`) with status and pause menu.
- [x] **T4.10** Loading, empty, offline and error states.

## PHASE 5 — Polish & Package (Day 14)

- [x] **T5.1** Windows startup option + single-instance lock.
- [x] **T5.2** File logging; passwords, tokens, window titles aur other sensitive data logs mein nahi hone chahiye.
- [x] **T5.3** PyInstaller se `.exe` build karo aur clean Windows environment par test karo.
- [x] **T5.4** README mein setup, configuration aur run instructions likho.
- [x] **T5.5** End-to-end test: register → login → track → focus session → stats.
- [x] **T5.6** `memory.md` ka final update aur release tag `v0.1.0`.

---

## Week 1–2 Exit Criteria

- [x] User desktop application se register/login kar sake.
- [x] Tracker foreground app usage, idle time aur task switches record kare.
- [x] Data PostgreSQL mein safely store ho aur offline hone par data loss na ho.
- [x] Focus session start/stop ho aur history mein record ho.
- [x] Dashboard mein aaj ka accurate summary dikhe.
- [x] Settings mein focus goal aur privacy configuration kaam kare.
- [x] Automated tests pass hon aur clean setup instructions verify hon.

# Weeks 3–4: Attention Analysis & Distraction Detection Engine

**Stack:** FastAPI + PostgreSQL (SQLAlchemy + Alembic) + Celery + Python ML (pandas, numpy, scikit-learn)
**Approach:** Pehle rule-based + statistics (no training data chahiye). ML sirf prediction me, jab data ho.

> Note: `ml/` aur `services/` me kuch files already hain (`distraction.py`, `features.py`, `focus_score.py`, `predictor.py`, `scoring_service.py`, etc.). Naya banane se pehle **existing code check karo aur extend karo**, overwrite nahi.

---

## 0. Input Data (Week 1–2 se already available)

| Table (models/) | Use |
|---|---|
| `activity_log.py` | app name, start/end, duration, idle |
| `focus_session.py` | focus start/end sessions |
| `notification_event.py` | notification timestamps/app |
| `score.py` | daily scores store karne ke liye |

- [ ] Check karo `score.py` me kya columns hain; zarurat ho to Alembic migration add karo (`alembic revision --autogenerate -m "analytics_tables"`)
- [ ] Naye tables (agar chahiye): `daily_metrics`, `insights`

---

## 1. Behavioral Analytics Engine
**Files:** `ml/features.py`, `services/stats_service.py`, `repositories/stats_repository.py`

| Task | Logic |
|---|---|
| Focus Session Analysis | Per day: total focus min, avg session, longest, count |
| Attention Pattern | Hour-wise (0–23) focus minutes → best/worst hour |
| Distraction Frequency | `distractions / focus_hours` per day |
| Productivity Trend | 7-day moving average (pandas `rolling(7)`) |

- [ ] `features.py` → `build_daily_features(user_id, date)` returns dict/DataFrame
- [ ] Repository me SQL aggregation (`GROUP BY date_trunc('hour', ...)`)

## 2. Distraction Detection
**File:** `ml/distraction.py`

| Task | Rule |
|---|---|
| Frequent Interruption | 30 min window me ≥ 3 interruptions |
| Context Switching | app switches/hour; `> 20/hr` = high |
| Notification Impact | Notification ke 5 min ke andar app switch / focus break → impact++ |
| Focus Loss | Session < 5 min ya idle > 2 min |

- [ ] Functions: `detect_interruptions()`, `context_switch_rate()`, `notification_impact()`, `focus_loss_events()`
- [ ] Thresholds `core/config.py` me (env se tunable)

## 3. AI-Based Focus Scoring (0–100)
**Files:** `ml/focus_score.py`, `services/scoring_service.py`

```python
focus_score = (0.4*focus_ratio + 0.3*avg_session_score
               + 0.2*(100 - switch_penalty) + 0.1*(100 - notif_penalty))

productivity_score = productive_time / total_active_time * 100
attention_stability = 100 - normalize(np.std(session_lengths))
concentration_trend = np.polyfit(range(7), last_7_scores, 1)[0]   # slope
```

- [ ] Weights config me
- [ ] Productive/unproductive app categories (simple dict ya DB table)
- [ ] Daily score `score` table me save (upsert)

## 4. Predictive Analytics
**Files:** `ml/predictor.py`, `ml/train.py`

| Task | Phase 1 (rules) | Phase 2 (ML, optional) |
|---|---|---|
| Focus Degradation | 7-day slope negative → warning | `LinearRegression` |
| Productivity Risk | score < 50 for 3 days ya slope < -3 | `RandomForest` |
| Attention Fatigue | 90 min ke baad switches 2x | feature: time-in-session vs switches |

- [ ] Phase 1 pehle complete karo
- [ ] Phase 2 tabhi jab 30+ days data ho; model `ml/saved_models/` me save (joblib)

## 5. Insight Generation
**File:** `services/recommendation_service.py`

- [ ] **Attention Leak:** top 3 apps jinse sabse zyada focus loss
- [ ] **Personalized Insight:** template based (*"Tumhara best focus 10–12 AM hai"*)
- [ ] **Daily Summary:** score + best hour + top distraction + 1 suggestion
- [ ] (Optional) LLM se polish — sirf final metrics bhejo, raw events nahi

## 6. Background Job
**File:** `tasks/celery_app.py`

- [ ] Celery beat task: har raat sab users ke liye features → scores → insights → DB save

## 7. API Endpoints
**Files:** `api/routes/analytics.py`, `api/routes/recommendations.py`, `schemas/stats.py`

```
GET /analytics/daily?date=
GET /analytics/focus-score
GET /analytics/distractions
GET /analytics/predictions
GET /analytics/insights
GET /analytics/summary
```

- [ ] Pydantic response schemas
- [ ] Auth dependency (`deps.py`) + ownership check (existing pattern follow karo)

## 8. Tests
- [ ] `tests/test_distraction.py`, `test_focus_score.py`, `test_predictor.py` (pure unit, dummy data)
- [ ] `tests/integration/test_analytics_endpoints.py`

---

## Timeline

| Day | Work |
|---|---|
| 1–3 | Migration + features + session/pattern analytics |
| 4–6 | Distraction rules (4 functions) + tests |
| 7–9 | Scoring formulas + save to `score` table |
| 10–12 | Predictions (rules → optional ML) |
| 13–14 | Insights + Celery job + APIs + integration tests |

## Definition of Done

- [ ] Dummy data (1000+ activity rows) pe sab scores generate hote hain
- [ ] Celery nightly job chalta hai
- [ ] 6 endpoints working + tested
- [ ] 3+ type ke readable insights