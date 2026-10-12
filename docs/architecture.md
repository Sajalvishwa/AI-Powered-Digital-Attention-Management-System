# architecture.md — System Architecture (Week 1–2)

> **Revision 2:** Desktop UI is now a **React web frontend** (`frontend/`) + headless `desktop-agent/` (Python, no Qt UI). Browser `extension/`, `ml/`, Celery are scaffolded but implemented in later weeks. Backend keeps `repositories/` layer. Table `activity_log.py` model = `activity_sessions` table.

## 1. Overview
Desktop-first data collection platform. Two deployables:
1. **Desktop Agent** (Python, headless) — background tracking + sync. Dashboard = React web app.
2. **Backend API** (FastAPI + PostgreSQL).

```
┌──────────────────────── Windows PC ────────────────────────┐
│  ┌──────────────┐    ┌───────────────┐   ┌──────────────┐  │
│  │  Tracker     │──► │ Local Buffer  │──►│ Sync Worker  │──┼──HTTPS+JWT──┐
│  │ (window/idle)│    │ (SQLite)      │   │ (batch 30s)  │  │             │
│  └──────────────┘    └───────────────┘   └──────────────┘  │             ▼
│  ┌──────────────┐    ┌───────────────┐                     │   ┌──────────────────┐
│  │ Tray / Config│◄──►│ API Client    │─────────────────────┼──►│  FastAPI Backend │
│  │ + Tray       │    │ (auth/stats)  │                     │   │  routers→services│
│  └──────────────┘    └───────────────┘                     │   │  →repositories   │
└────────────────────────────────────────────────────────────┘   └────────┬─────────┘
                                                                          ▼
                                                                 ┌──────────────────┐
                                                                 │   PostgreSQL     │
                                                                 └──────────────────┘
```

## 2. Tech Stack
| Layer | Tech |
|---|---|
| Dashboard UI | React + Vite (web) |
| Desktop agent | Python headless (tray optional) |
| Tracking | psutil, pywin32, ctypes (GetLastInputInfo) |
| Local buffer | SQLite (stdlib sqlite3) |
| Backend | FastAPI, Uvicorn, SQLAlchemy 2.x, Alembic, Pydantic v2 |
| DB | PostgreSQL 16 |
| Auth | JWT (access 15m + refresh 7d), argon2/bcrypt |
| Packaging | PyInstaller (.exe), Docker (backend) |
| Testing | pytest, httpx, pytest-qt |

## 3. Repository Structure
```
attention-platform/
├── backend/
│   ├── alembic/                 # migrations
│   ├── app/
│   │   ├── api/  deps.py, routes/ (auth, users, activity, goals | later: analytics, recommendations, admin)
│   │   ├── core/ config.py, database.py, security.py
│   │   ├── models/ user, device, refresh_token, activity_log, focus_session, goal, notification_event, score
│   │   ├── schemas/ user, activity, goal
│   │   ├── repositories/        # DB queries only
│   │   ├── services/            # business logic (ingestion, scoring, recommendation, notification)
│   │   ├── ml/                  # Weeks 3-4
│   │   ├── tasks/               # Celery (later, needs Redis)
│   │   └── main.py
│   ├── tests/, Dockerfile, requirements.txt
├── desktop-agent/app/           # tracker, activity_collector, api_client, settings, main
├── frontend/src/                # React: pages, components, context, api
├── extension/                   # browser extension (later)
├── docs/
├── docker/init-db.sql
├── docker-compose.yml
└── .env.example
```

## 4. Backend Layering
`Router → Service → Repository → DB`
- Router: HTTP only, validation via Pydantic.
- Service: business rules (e.g. merge overlapping sessions).
- Repository: SQL only. No business logic.

## 5. Desktop Internals
- **Tracker thread**: polls every 1s → detects window change / idle → builds `ActivitySession`.
- **Buffer**: every finished session saved to local SQLite (`synced=0`).
- **Sync worker**: every 30s sends unsynced rows to `POST /activity/batch`, marks `synced=1` on 2xx. Retries with exponential backoff.
- **UI thread**: never blocks; calls API via worker (QThreadPool).
- **Single instance**: lock file/mutex to prevent two agents.

## 6. API Contract (v1)
Base: `/api/v1`
| Method | Path | Purpose |
|---|---|---|
| POST | /auth/register | create user |
| POST | /auth/login | returns access+refresh |
| POST | /auth/refresh | rotate tokens |
| GET/PUT | /users/me | profile |
| GET/PUT | /users/me/settings | goals, idle threshold, privacy |
| POST | /activity/batch | bulk insert sessions (idempotent via client_id) |
| POST | /focus-sessions | start |
| PATCH | /focus-sessions/{id} | stop/pause |
| GET | /focus-sessions | history |
| GET | /stats/today | totals, top apps, switches, hourly timeline |
| GET | /stats/range?from&to | range stats |
| POST/GET | /goals | goal CRUD |
| POST | /notifications/events | (stub in Week 1–2) |
| DELETE | /users/me/data | delete all my data |
| GET | /health | liveness |

## 7. Key Flows
**Login**: UI → /auth/login → tokens stored in Windows Credential Manager (keyring) → tracker starts.
**Tracking**: window change → session closed → SQLite → batch sync → Postgres.
**Idempotency**: each session has `client_id` (UUID); unique per user → duplicate uploads ignored.

## 8. Config & Environments
`.env` for backend (DB URL, JWT secret). Desktop reads `config.toml` (API base URL). Envs: dev / prod.

## 9. Non-Functional Targets
- Tracker CPU < 1%, RAM < 80MB.
- Batch API p95 < 300ms for 100 rows.
- No data loss offline up to 7 days of buffer.

## 10. Future Hooks (not now)
Notification tracking (WinRT), ML engine (Weeks 3–4) will read from `activity_sessions` — keep schema stable.
