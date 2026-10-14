# 🧠 AI-Powered Digital Attention Management System

### Distraction Detection & Focus Enhancement Platform

An intelligent activity-monitoring and focus-management platform designed to help students and professionals understand their digital habits, analyze application usage, monitor focus sessions, and identify potential sources of distraction.

The platform combines a Python-based desktop agent, a FastAPI backend, PostgreSQL storage, and a React dashboard to provide activity insights and personalized focus-management capabilities.

> **Project Type:** Infosys Springboard Internship 7.0  
> **Development Status:** In Progress (backend and desktop agent complete; React dashboard next)  
> **Primary Goal:** Understand digital activity patterns and support better focus management.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Project Objectives](#-project-objectives)
- [Current Status](#-current-status)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [Environment Configuration](#-environment-configuration)
- [Backend API](#-backend-api)
- [Testing](#-testing)
- [Development Roadmap](#-development-roadmap)
- [Privacy and Security](#-privacy-and-security)
- [Future Enhancements](#-future-enhancements)
- [Contributing](#-contributing)
- [Author](#-author)
- [License](#-license)

---

## 🚀 Overview

The AI-Powered Digital Attention Management System is a productivity-focused platform that helps users understand how they interact with their computers throughout the day.

Traditional screen-time tools primarily report how long applications are used. This project aims to go further by analyzing activity sessions, idle time, application switching, and focus-session history.

The collected information can be used to generate meaningful activity summaries and, as the project develops, support personalized focus-improvement recommendations.

The platform is built with a modular architecture so that activity collection, backend processing, database storage, and dashboard visualization can evolve independently.

### 🎯 Target Users

- Students preparing for examinations.
- Software developers and other professionals.
- Remote workers.
- Individuals interested in improving their digital habits.
- Knowledge workers who want to understand their focus patterns.

---

## ❓ Problem Statement

Digital distractions, frequent application switching, and unstructured computer usage can make it difficult to understand how time is spent during work or study sessions.

Existing screen-time and application-blocking tools may show usage duration, but usage duration alone does not explain every interruption or indicate whether a person was genuinely distracted.

This project provides a more informative approach by collecting application activity, recording idle periods, tracking focus sessions, and presenting usage statistics in an accessible dashboard.

The objective is to help users recognize their digital habits and make informed decisions about managing their attention.

---

## 🎯 Project Objectives

1. Monitor foreground application usage on Windows.
2. Record application activity as time-based sessions.
3. Detect idle periods using Windows input information.
4. Measure application-switching activity.
5. Store activity records securely in PostgreSQL.
6. Synchronize activity reliably between the desktop agent and backend.
7. Preserve pending activity locally when the backend is unavailable.
8. Provide APIs for focus sessions, goals, and activity statistics.
9. Visualize daily usage and focus metrics through a React dashboard.
10. Respect user privacy through configurable tracking and window-title storage.

---

## ✅ Current Status

| Component | Status |
|---|---|
| Backend API (auth, activity, focus, goals, stats) | Implemented and tested |
| PostgreSQL schema and Alembic migrations | Implemented |
| Desktop agent: window tracker, idle detection, session builder | Implemented |
| Desktop agent: SQLite offline buffer, API client, token storage, sync worker | Implemented |
| Desktop agent: login / logout / status commands | Implemented |
| End-to-end verification (agent → backend → PostgreSQL) | Verified with a 64-minute headless run |
| React dashboard | Not started (Phase 4) |
| System-tray controls, packaging | Not started (Phase 4–5) |

**Verification summary (14 Oct 2026):** the agent ran headless for about 64 minutes, uploaded sessions to the backend every 30 seconds, and the local pending queue returned to zero. Expired access tokens were refreshed automatically. Idle sessions were recorded after the configured threshold and ended when input resumed. Application switches produced separate session rows. The exact application-switch count was verified by behaviour, not matched manually against a hand count.

---

## ✨ Key Features

### 🔐 1. User Authentication

- User registration and login.
- Argon2 password hashing.
- JWT access tokens with rotating refresh tokens and reuse detection.
- Logout that revokes refresh tokens.
- Protected API endpoints and per-user data isolation.
- User profile and settings management.
- Rate limiting on registration, login, refresh and activity upload.

### 🖥️ 2. Desktop Activity Tracking

The Windows desktop agent runs headless in the background.

- Foreground application detection (`pywin32` + `psutil`).
- Optional window-title collection (off by default).
- Idle detection using `GetLastInputInfo` and `GetTickCount64`.
- Session builder that converts observations into continuous sessions with unique `client_id` values.
- Application-switch tracking through session boundaries.
- Clean shutdown that saves the final session (`Ctrl+C`).

### 💾 3. Reliable Offline-First Synchronization

- Every finished session is written to a local SQLite buffer first.
- A sync worker uploads pending sessions in batches (default every 30 seconds).
- Retry handling when the backend is unreachable.
- Idempotent uploads: the backend ignores duplicates using `(user_id, client_id)`.
- Automatic token refresh when the access token expires.
- Tokens are kept in the Windows Credential Manager via `keyring`, never in plain files.

### 📊 4. Activity Analytics

- Daily activity summaries and hourly timelines.
- Application usage aggregation.
- Active, idle and focus-time calculations.
- Application-switch counts.
- Date-range reports (up to 92 calendar days).

Metric accuracy depends on the quality and completeness of the recorded activity data.

### ⏱️ 5. Focus Session Management

- Start, pause, resume and stop sessions.
- Only one running or paused session per user.
- Session history.

### 🎯 6. Goal Management

- Create, read, update and delete goals.
- Duplicate-goal and ownership rules enforced by the backend.

### 🔒 7. Privacy Controls

- Window-title storage is disabled by default and enforced on the server.
- Application ignore-list.
- Delete-my-data endpoint that removes collected data but keeps the account.
- Logs never contain passwords, tokens or window titles.

---

## 🏗️ System Architecture

```text
┌──────────────────────────────────────────┐
│              React Dashboard             │
│        (Phase 4 - not started yet)       │
│  Dashboard | Focus | Apps | Goals        │
│                 Settings                 │
└─────────────────────┬────────────────────┘
                      │
                      │ HTTP / REST API
                      ▼
┌──────────────────────────────────────────┐
│             FastAPI Backend              │
│                                          │
│  Authentication and User Management      │
│  Activity and Focus Session APIs         │
│  Goals and Statistics APIs               │
│  Validation, Rate Limiting, Ownership    │
└─────────────────────┬────────────────────┘
                      │
                      │ SQLAlchemy
                      ▼
┌──────────────────────────────────────────┐
│               PostgreSQL                 │
│                                          │
│  Users | Devices | Activity Sessions     │
│  Focus Sessions | Goals | Settings       │
└──────────────────────────────────────────┘


┌──────────────────────────────────────────┐
│          Windows Desktop Agent           │
│                                          │
│  Window Tracker  →  Idle Detection       │
│        ↓                                 │
│  Session Builder                         │
│        ↓                                 │
│  SQLite Offline Buffer                   │
│        ↓                                 │
│  Sync Worker + API Client (keyring)      │
└─────────────────────┬────────────────────┘
                      │
                      │ Authenticated Batch Uploads (every 30s)
                      ▼
                 FastAPI Backend
```

---

## 🛠️ Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Programming Language | Python | Backend and desktop agent |
| Backend Framework | FastAPI | REST API development |
| ORM | SQLAlchemy 2.x | Database operations |
| Database Migrations | Alembic | Schema versioning |
| Database | PostgreSQL 16+ | Persistent application data |
| Authentication | JWT (PyJWT) | API authentication |
| Password Security | Argon2 | Password hashing |
| Desktop Monitoring | pywin32, ctypes | Windows API integration |
| Process Monitoring | psutil | Process information |
| Local Storage | SQLite | Offline activity buffer |
| Secure Credential Storage | keyring | Token storage in Windows Credential Manager |
| HTTP Client (agent) | requests | Agent-to-backend communication |
| Frontend | React | Dashboard interface (planned) |
| Frontend Build Tool | Vite | Development and production builds (planned) |
| Testing | pytest, httpx | Automated testing |
| Version Control | Git and GitHub | Source control |

---

## 📁 Project Structure

```text
attention-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/            # routers and dependencies
│   │   ├── core/           # config, database, security, rate limiter
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/   # database queries only
│   │   ├── services/       # business logic
│   │   └── main.py
│   ├── alembic/
│   ├── tests/              # unit tests + integration tests
│   └── requirements.txt
│
├── desktop-agent/
│   ├── app/
│   │   ├── main.py             # entry point: run / login / logout / status
│   │   ├── agent.py            # main loop
│   │   ├── tracker.py          # foreground window tracking
│   │   ├── idle.py             # idle detection
│   │   ├── session_builder.py  # observations → sessions
│   │   ├── sync_worker.py      # batch upload with retry
│   │   ├── api_client.py       # HTTP client + token refresh
│   │   ├── token_store.py      # keyring token storage
│   │   ├── account_cli.py      # login / logout / status commands
│   │   ├── settings.py         # config.toml loader
│   │   └── ...                 # SQLite offline buffer and helpers
│   ├── tests/
│   └── requirements.txt
│
├── frontend/               # React dashboard (Phase 4)
├── extension/              # browser extension (placeholder)
├── docs/                   # design, architecture, database, security, tasks
├── docker/
├── docker-compose.yml      # optional PostgreSQL container
├── .env.example
└── README.md
```

> The structure is representative and may change as development progresses.

---

## ⚙️ Getting Started

### Prerequisites

- Python 3.11 or newer.
- PostgreSQL.
- Git.
- Visual Studio Code (recommended).
- Node.js and npm (for the React frontend, once it is added).
- Windows (required for the desktop agent).

```powershell
python --version
git --version
node --version
npm --version
```

### 1. Clone the Repository

```powershell
git clone https://github.com/Sajalvishwa/AI-Powered-Digital-Attention-Management-System.git
cd AI-Powered-Digital-Attention-Management-System
```

### 2. Configure PostgreSQL

Create the development and test databases (names use underscores):

```sql
CREATE DATABASE attention_dev;
CREATE DATABASE attention_test;
```

Alternatively, start PostgreSQL with Docker from the project root:

```powershell
copy .env.example .env
docker compose up -d db
```

Use the development database for local work and the test database only for automated integration tests. Never run destructive test fixtures against the development database.

### 3. Set Up the Backend

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
alembic upgrade head
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend is then available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

Create a user through `POST /api/v1/auth/register` (for example from the `/docs` page) before logging in from the agent.

### 4. Set Up the Desktop Agent

Open a second PowerShell terminal:

```powershell
cd desktop-agent
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

**Log in once** (the backend must be running). Tokens are stored in the Windows Credential Manager:

```powershell
python -m app.main login
```

**Check the agent's state:**

```powershell
python -m app.main status
```

This shows the data folder, log file, server reachability, login state and how many sessions are waiting to upload.

**Start tracking** (runs until you press `Ctrl+C`):

```powershell
python -m app.main run
```

Press `Ctrl+C` once to stop. The agent saves the final session and uploads it before exiting.

**Other commands and options:**

```powershell
python -m app.main logout          # remove stored tokens
python -m app.main run --debug     # verbose logging (large log files)
python -m app.main --data-dir .\somefolder run   # keep config, log and buffer elsewhere
```

**Agent files:** on Windows the agent stores `config.toml`, `agent.log` and `buffer.db` in `%APPDATA%\AttentionAgent`. A default `config.toml` is created on the first run:

```toml
api_base_url = "http://127.0.0.1:8000/api/v1"
poll_interval_sec = 1.0
idle_threshold_sec = 120
sync_interval_sec = 30
log_level = "INFO"
```

`http://` is accepted only for localhost; any other server must use `https://`.

**Manual tracker check (does not upload anything):**

```powershell
python -m app.tracker --seconds 20
```

Add `--titles` to also print window titles in the console. Window titles can contain personal information, so do not publish them in logs or screenshots.

### 5. Verify the Pipeline

1. Start the backend and run `python -m app.main status` (it should say the server is reachable and you are logged in).
2. Run `python -m app.main run` and work normally for a few minutes. Look for `Sync successful` lines in the console.
3. Stop with `Ctrl+C` and run `status` again. `Waiting to upload` should be `0`.
4. In PostgreSQL, confirm the rows arrived:

```sql
SELECT COUNT(*) AS total,
       COUNT(*) FILTER (WHERE is_idle) AS idle_rows,
       MIN(started_at) AS first_start,
       MAX(ended_at) AS last_end
FROM activity_sessions;
```

### 6. Set Up the Frontend

The React dashboard has not been created yet. Once `frontend/package.json` exists:

```powershell
cd frontend
npm install
npm run dev
```

---

## 🔑 Environment Configuration

Create a local `.env` file in the project root (see `.env.example`):

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/attention_dev
JWT_SECRET=REPLACE_WITH_A_SECURE_RANDOM_SECRET
ACCESS_EXPIRE_MIN=15
REFRESH_EXPIRE_DAYS=7
```

Use the exact variable names required by the backend settings. When using Docker, `.env` also provides the PostgreSQL container's credentials.

The integration tests derive the test database by replacing a trailing `_dev` in `DATABASE_URL` with `_test`, or use `TEST_DATABASE_URL` when it is set. They refuse to run against any database whose name does not end in `_test`.

### Security Guidelines

- Never commit `.env` files containing real credentials.
- Never expose JWT secrets in screenshots, logs, or public repositories.
- Use a strong, randomly generated JWT secret.
- Keep the development and test databases separate.
- Do not commit large generated files (project dumps, `.db` files, virtual environments). GitHub rejects files over 100 MB.
- Rotate any secret that has been exposed.

---

## 🔌 Backend API

All paths below are under `/api/v1` unless noted.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` (no prefix) | Check backend health |
| POST | `/auth/register` | Register a user |
| POST | `/auth/login` | Authenticate and receive tokens |
| POST | `/auth/refresh` | Rotate tokens |
| POST | `/auth/logout` | Revoke a refresh token |
| GET / PUT | `/users/me` | Read or update profile |
| GET / PUT | `/users/me/settings` | Read or update settings |
| POST | `/activity/batch` | Upload up to 500 sessions (idempotent) |
| GET | `/activity/recent` | Recent activity |
| POST | `/focus-sessions` | Start a focus session |
| GET | `/focus-sessions/active` | Current active session |
| PATCH | `/focus-sessions/{id}` | Pause, resume, stop or cancel |
| GET | `/focus-sessions` | Session history |
| GET | `/stats/today` | Today's statistics |
| GET | `/stats/range` | Statistics for a date range |
| POST / GET | `/goals` | Create or list goals |
| PATCH / DELETE | `/goals/{id}` | Update or delete a goal |
| DELETE | `/users/me/data?confirm=true` | Delete the current user's collected data |

See the live OpenAPI documentation at `/docs` for request and response schemas.

### Authentication

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Do not place real tokens in source code, public examples, or Git commits.

### Rate Limits

| Endpoint | Limit |
|---|---|
| Register | 3 per minute per IP |
| Login | 20 per minute per IP and 5 per minute per email |
| Refresh | 30 per minute per IP |
| Activity batch | 30 per minute per user |

---

## 🧪 Testing

### Backend

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m pytest tests -q
```

Last recorded run: `61 passed, 1 warning`. The warning is a Starlette/AnyIO deprecation notice and does not affect results. Integration tests need the `attention_test` database.

### Desktop Agent

```powershell
cd desktop-agent
.\venv\Scripts\Activate.ps1
python -m pytest -q
```

Run the full suite after any change. Make sure the correct virtual environment is active; running tests with a different Python installation fails with missing-module errors.

### End-to-End Check

Automated tests do not replace a real run. Follow [Verify the Pipeline](#5-verify-the-pipeline) after changes to the agent or the sync flow.

---

## 🗺️ Development Roadmap

### Phase 0 — Project Setup

- [x] Project structure and documentation foundation.
- [x] Backend and desktop-agent environments.
- [ ] Development tools verification.
- [ ] PostgreSQL setup verification.
- [x] Environment-variable template.
- [ ] Initial Git commit verification.

### Phase 1 — Backend Foundation

- [x] FastAPI application and configuration.
- [x] Database session and migration setup.
- [x] Core database models.
- [x] Initial migration.
- [x] Password hashing and JWT utilities.
- [x] Authentication endpoints.
- [x] User profile and settings APIs.
- [ ] Explicit authentication, profile, and settings test review.

### Phase 2 — Activity Data APIs

- [x] Activity and focus-session models.
- [x] Activity batch ingestion.
- [x] Focus-session API implementation.
- [x] Daily statistics.
- [x] Date-range statistics.
- [x] Goal CRUD operations.
- [x] User data deletion endpoint.
- [x] Rate limiting.
- [x] Backend test suite (61 passing).
- [ ] Optional Docker setup for the API.

### Phase 3 — Desktop Tracker Core ✅

- [x] Desktop-agent skeleton.
- [x] Foreground window tracker.
- [x] Idle detection.
- [x] Session builder.
- [x] SQLite offline buffer.
- [x] API client and secure token storage.
- [x] Background synchronization and retry handling.
- [x] Ignore-list and privacy enforcement.
- [x] One-hour headless run verified against PostgreSQL.

### Phase 4 — React Dashboard

- [ ] Vite and React setup.
- [ ] Login and registration.
- [ ] User onboarding.
- [ ] Main application layout.
- [ ] Daily activity dashboard.
- [ ] Focus-session interface.
- [ ] Applications and goals screens.
- [ ] Settings and privacy controls.
- [ ] Desktop system-tray controls.
- [ ] Loading, empty, offline, and error states.

### Phase 5 — Polish and Release

- [ ] Windows startup and single-instance support.
- [ ] Secure file logging review.
- [ ] Windows executable packaging.
- [ ] Setup and usage documentation.
- [ ] End-to-end integration tests.
- [ ] Final project documentation and `v0.1.0` release tag.

> Update checkboxes only after implementation and meaningful verification are complete.

---

## 🔒 Privacy and Security

This project deals with information about how a person uses their computer, so privacy is considered throughout development.

- Collect only the activity information the application needs.
- Never record keystroke contents, mouse-click contents, clipboard data or screenshots.
- Treat window titles as sensitive: they are off by default, not read unless enabled, and dropped by the server unless the user opts in.
- Respect application ignore-lists.
- Require authentication on all private endpoints and enforce ownership checks (another user's resource returns 404).
- Store refresh tokens only as hashes on the server and in the OS credential store on the client.
- Detect refresh-token reuse and revoke all of that user's tokens.
- Mask secrets in logs and never log window titles.
- Provide a way to delete collected data.
- Keep pending activity safe in the local buffer during connectivity failures.

Activity metrics are indicators of digital behaviour, not definitive measurements of attention or mental state.

---

## 🔮 Future Enhancements

- Personalized focus recommendations.
- Analysis of application-switching patterns.
- Focus-session trend analysis.
- Historical productivity reports.
- Configurable daily focus goals.
- Improved visualization of active and idle periods.
- Desktop system-tray controls.
- Exportable activity reports.
- Optional machine-learning models for pattern analysis.
- Notification tracking.

---

## 🤝 Contributing

This project is developed incrementally, with a focus on modular architecture, testing, privacy, and maintainability.

1. Fork the repository.
2. Create a feature branch.
3. Implement one focused change.
4. Add or update tests.
5. Run the relevant test suite.
6. Submit a pull request describing the change.

Suggested branch naming:

```text
feature/react-dashboard
feature/tray-controls
feature/startup-and-single-instance
```

---

## 👨‍💻 Author

**Sajal Vishwakarma**

B.Tech Computer Science and Engineering  
Full Stack Web Developer | Python | FastAPI | React

- **GitHub:** [Sajalvishwa](https://github.com/Sajalvishwa)
- **LinkedIn:** [Connect on LinkedIn](https://www.linkedin.com/in/sajal-vishwakarma-b2008b27b/)

---

## 📜 License

A license has not yet been specified for this repository.

Before distributing or reusing the project, choose an appropriate open-source or proprietary license and add the corresponding `LICENSE` file.

---

<p align="center">
  <b>Building better digital habits through activity insights and focus management.</b>
</p>
