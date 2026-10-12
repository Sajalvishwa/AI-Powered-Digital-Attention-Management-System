# memory.md — Project Memory (Living Context)

> Ye file project ka "dimaag" hai. Naye chat/AI assistant/Copilot ko pehle ye file dikhao.
> **Har task ke baad update karo.**

## 1. Project Snapshot
- **Name:** AI-Powered Digital Attention Management System
- **Goal:** Desktop pe user ki digital activity track karke distraction detect karna aur focus improve karna.
- **Current Phase:** Weeks 1–2 → User Activity Monitoring & Data Collection.
- **Owner:** Sajal Vishwakarma (CSE 3rd year, product-based companies ki prep)
- **Platform target:** Windows desktop app (whole desktop tracking).

## 2. Locked Decisions
| # | Decision | Reason |
|---|---|---|
| 1 | UI = React web dashboard + headless Python desktop-agent (replaces PySide6) | Owner's chosen structure, MERN skills reuse |
| 2 | Backend = FastAPI + PostgreSQL | Project requirement |
| 3 | Auth = JWT access + rotating refresh | Standard, secure |
| 4 | Offline buffer = SQLite | Data loss avoid |
| 5 | Window titles OFF by default | Privacy |
| 6 | Idempotent sync via `client_id` | Duplicate uploads safe |
| 7 | Notification tracking deferred | WinRT complexity, table ready only |
| 8 | Time = UTC in DB, convert in UI | Consistency |
| 9 | Keep `repositories/` layer (router→service→repository) | rules.md |
| 10 | ml/, tasks(Celery), extension, admin, analytics, recommendations = placeholders until their week | Scope control |
| 11 | Postgres via docker-compose, backend runs locally | Simple dev loop |

## 3. Doc Map
- `design.md` → UI/UX, tokens, screens
- `architecture.md` → components, folder structure, API list
- `database.md` → PostgreSQL schema & queries
- `security.md` → auth, privacy, threats
- `rules.md` → coding & git rules
- `tasks.md` → step-by-step work list

## 4. Current State
- [x] Requirements understood
- [x] Docs written (design, architecture, database, security, rules, memory, tasks)
- [x] Backend skeleton (T0.x, T1.1)
- [x] Models written (T1.3), Alembic configured (T1.2)
- [ ] DB + migrations
- [ ] Auth APIs
- [ ] Activity batch API
- [ ] Desktop tracker
- [ ] Desktop UI

**Last worked on:** (update here)
**Next task:** T1.4 (run migration), then T1.6 register API

## 5. Environment Notes
- OS: Windows 10/11
- Python: 3.11+
- PostgreSQL: 16 (local or Docker)
- Editor: VS Code
- Dev DB name: `attention_dev`, test DB: `attention_test`

## 6. Known Issues / Open Questions
- Notification tracking Windows pe kaise karenge? (Week 5+ pe decide)
- Mac/Linux support chahiye ya nahi? (abhi nahi)
- Cloud hosting provider? (Week 7–8)

## 7. Learnings / Gotchas
- `GetLastInputInfo` + `GetTickCount` 49 days baad overflow karta hai → `GetTickCount64` consider karo.
- Qt UI sirf main thread se update hota hai → worker se signal emit karo.
- Window title me sensitive data ho sakta hai → default store mat karo.

## 8. Changelog
| Date | Change |
|---|---|
| (today) | Initial docs created |
| (today) | Structure revised: React frontend + desktop-agent; project scaffold generated |



## T2.8 — Rate Limiting (Completed)

- Implemented sliding-window rate limiter in `app/core/rate_limit.py`.
- Register: 3 requests/minute/IP.
- Login: 20 requests/minute/IP and 5 requests/minute/email.
- Refresh: 30 requests/minute/IP.
- Activity batch: 30 requests/minute/user.
- Added endpoint-level tests in `tests/test_rate_limit_endpoints.py`.
- Endpoint tests: 5 passed.
- Full test suite: 39 passed, 0 failed.
- Warning: Starlette/AnyIO deprecation warning; tests unaffected.

Status: COMPLETE.
Next: T2.9 — API validation, duplicate handling, edge cases, and ownership isolation.


### Latest Verification — 12 October 2026

- Backend virtual environment: `backend/venv`
- Full test suite: 61 passed, 1 Starlette/AnyIO deprecation warning.
- Stats range tests: 4 passed.
- Verified reversed date rejection and maximum 92-calendar-day range.
- Verified empty daily buckets, active time, idle time, focus time and app-switch calculations.
- Integration tests use the dedicated `attention_test` database.
- Docker setup deferred as optional.
- Next task: T3.1 — desktop-agent skeleton and entry point.

### Desktop Agent Progress

- T3.1: Agent startup, tracking loop, and shutdown verified.
- T3.2: Foreground application tracking manually verified.
- Detected Code.exe, chrome.exe, explorer.exe, WINWORD.EXE, and pgAdmin4.exe.
- Window titles are available in the manual tracker test with --titles.
- Full agent debug logs show process names without window titles.
- Automated tests: 32 passed.
- Next task: T3.3 — Idle Detection using GetLastInputInfo.

## T3.3 — Windows Idle Detection

- Implemented `desktop-agent/app/idle.py`.
- Added Windows idle detection using GetLastInputInfo and GetTickCount64.
- Added configurable idle threshold and status monitoring.
- Added unit tests for idle calculation and threshold validation.
- Idle detection tests: 17 passed.
- Full desktop-agent test suite: 49 passed.
- Windows API manual verification: Pending.

### Next Task
T3.4 — Session Builder.