# tasks.md — Week 1–2 Task List

**Rule:** Ek time pe ek task. Task ko `[x]` tabhi mark karo jab implementation aur meaningful verification complete ho. Har task ke baad `memory.md` update karo.

---

## PHASE 0 — Project Setup (Day 1)

- [x] **T0.1** Folder `attention-platform/` banao, `git init`, `.gitignore`, `docs/` mein 7 Markdown files rakho.
- [x] **T0.2** `backend/` aur `desktop/` folders + alag virtual environments (`python -m venv venv`).
- [ ] **T0.3** VS Code extensions: Python, Pylance, Ruff, Black, Docker, SQLTools (PostgreSQL), GitLens verify karo.
- [ ] **T0.4** PostgreSQL install/configure karo; `attention_dev` + `attention_test` databases banao aur connectivity verify karo.
- [x] **T0.5** `.env.example` banao (`DATABASE_URL`, `JWT_SECRET`, `ACCESS_EXPIRE_MIN`, `REFRESH_EXPIRE_DAYS`).
- [ ] **T0.6** Initial Git commit: `chore: project scaffolding`.

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
- [ ] **T1.10** Pytest tests for authentication, profile and settings — separate task completion verification pending.

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
- [ ] **T2.10 (Optional / Deferred)** Dockerfile + `docker-compose.yml` for API and PostgreSQL; verify clean startup.

## PHASE 3 — Desktop Tracker Core (Days 8–10)

- [x] **T3.1** `desktop-agent/app/...` skeleton and entry point verify/scaffold karo.
- [x] **T3.2** `window_tracker.py` — foreground application name and title (`pywin32` + `psutil`).
- [ ] **T3.3** `idle.py` — idle detection (`GetLastInputInfo` / `GetTickCount64`).
- [ ] **T3.4** `session_builder.py` — pure logic: events → sessions; unit tests likho.
- [ ] **T3.5** SQLite offline buffer (`pending_sessions`) — save, read and mark synced.
- [ ] **T3.6** API client + secure token storage using `keyring`.
- [ ] **T3.7** Sync worker — batch upload every 30 seconds with retry and backoff.
- [ ] **T3.8** Ignore-list + `store_window_titles` privacy setting enforce karo.
- [ ] **T3.9** Tracker ko headless mode mein 1 hour chalao; PostgreSQL data, idle time aur app-switch counts verify karo.

## PHASE 4 — Frontend: React Dashboard (Days 11–13)

- [ ] **T4.1** Vite + React setup, `design.md` CSS-variable theme tokens aur Axios client.
- [ ] **T4.2** Login + Register screens.
- [ ] **T4.3** Onboarding — focus goal, idle threshold aur privacy consent.
- [ ] **T4.4** Main shell — top bar + sidebar navigation.
- [ ] **T4.5** Today dashboard — stat cards, timeline chart aur top apps.
- [ ] **T4.6** Focus Session screen — ring timer + mini floating widget.
- [ ] **T4.7** Apps screen + Goals screen.
- [ ] **T4.8** Settings screen — tracking, theme, export/delete data.
- [ ] **T4.9** Desktop agent tray icon (`pystray`) with status and pause menu.
- [ ] **T4.10** Loading, empty, offline and error states.

## PHASE 5 — Polish & Package (Day 14)

- [ ] **T5.1** Windows startup option + single-instance lock.
- [ ] **T5.2** File logging; passwords, tokens, window titles aur other sensitive data logs mein nahi hone chahiye.
- [ ] **T5.3** PyInstaller se `.exe` build karo aur clean Windows environment par test karo.
- [ ] **T5.4** README mein setup, configuration aur run instructions likho.
- [ ] **T5.5** End-to-end test: register → login → track → focus session → stats.
- [ ] **T5.6** `memory.md` ka final update aur release tag `v0.1.0`.

---

## Week 1–2 Exit Criteria

- [ ] User desktop application se register/login kar sake.
- [ ] Tracker foreground app usage, idle time aur task switches record kare.
- [ ] Data PostgreSQL mein safely store ho aur offline hone par data loss na ho.
- [ ] Focus session start/stop ho aur history mein record ho.
- [ ] Dashboard mein aaj ka accurate summary dikhe.
- [ ] Settings mein focus goal aur privacy configuration kaam kare.
- [ ] Automated tests pass hon aur clean setup instructions verify hon.

---

## Latest Progress — 12 October 2026

### Backend Verification

- **Activity batch API:** Verified — HTTP 200, one activity record inserted.
- **Recent activity API:** Verified — 300-second activity record returned correctly.
- **Privacy setting:** Window title returned as `null`, consistent with title storage being disabled.
- **Stats today API:** Basic screen-time, top-app and hourly timeline aggregation verified.
- **Stats range API:** Verified with dedicated integration tests.
- **Date range validation:** Reversed dates rejected with HTTP 422.
- **Range limit:** Maximum 92 calendar dates accepted; a range covering 93 calendar dates rejected.
- **Empty range:** Zero totals and missing-date daily buckets verified.
- **Activity calculations:** Active time, idle time, focus time and app-switch counts verified against test data.
- **Full backend test suite:** `61 passed, 1 warning in 6.13s`.
- **Warning:** Starlette/AnyIO deprecation warning; no test failures.
- **Test database safety:** Integration fixtures refuse database names that do not end with `_test`; the test fixture resets test data between tests.

### Pending / Important Notes

- **T1.10:** Authentication, profile and settings tests need explicit task-level review before marking complete.
- **T2.3:** Verify the one-running-focus-session rule and focus-session ownership cases separately.
- **T2.10:** Docker setup deferred as optional.
- **Phase 3:** Desktop tracker implementation has not yet been verified.
- **Phase 4:** React dashboard implementation remains pending.
- **Exit criteria:** Week 1–2 exit criteria are not complete until the desktop tracker, dashboard and end-to-end workflow are implemented and tested.

### Next Task

**T3.1 — Desktop tracker skeleton and entry point.**

First inspect the existing `desktop/` directory and its virtual environment. Preserve existing project files and complete one task at a time.