# 🧠 AI-Powered Digital Attention Management System

### Distraction Detection & Focus Enhancement Platform

An intelligent activity-monitoring and focus-management platform designed to help students and professionals understand their digital habits, analyze application usage, monitor focus sessions, and identify potential sources of distraction.

The platform combines a Python-based desktop agent, a FastAPI backend, PostgreSQL storage, and a React dashboard to provide activity insights and personalized focus-management capabilities.

> **Project Type:** Infosys Springboard Internship 7.0  
> **Development Status:** In Progress  
> **Primary Goal:** Understand digital activity patterns and support better focus management.

---

## 📌 Table of Contents

- [Overview](#-overview)
- [Problem Statement](#-problem-statement)
- [Project Objectives](#-project-objectives)
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

The platform is being developed with a modular architecture so that activity collection, backend processing, database storage, and dashboard visualization can evolve independently.

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

This project aims to provide a more informative approach by collecting application activity, recording idle periods, tracking focus sessions, and presenting usage statistics in an accessible dashboard.

The objective is to help users recognize their digital habits and make informed decisions about managing their attention.

---

## 🎯 Project Objectives

The main objectives are:

1. Monitor foreground application usage on Windows.
2. Record application activity as time-based sessions.
3. Detect idle periods using Windows input information.
4. Measure application-switching activity.
5. Store activity records securely in PostgreSQL.
6. Support reliable activity synchronization between the desktop agent and backend.
7. Preserve pending activity locally when the backend is unavailable.
8. Provide APIs for focus sessions, goals, and activity statistics.
9. Visualize daily usage and focus metrics through a React dashboard.
10. Respect user privacy through configurable tracking and window-title storage.

---

## ✨ Key Features

### 🔐 1. User Authentication

The backend provides authentication and user-management functionality.

- User registration and login.
- Password hashing.
- JWT-based authentication.
- Access-token refresh and logout endpoints.
- Protected API endpoints.
- User profile and settings management.

### 🖥️ 2. Desktop Activity Tracking

The Windows desktop agent is designed to collect application activity.

- Foreground application detection.
- Application-name collection.
- Optional window-title collection.
- Activity-session construction.
- Idle-time detection.
- Application-switch monitoring.

**Implementation status:** Foreground application tracking has been implemented and manually tested. The remaining desktop-agent components are under development.

### 📊 3. Activity Analytics

The backend includes endpoints for activity statistics.

- Daily activity summaries.
- Application usage aggregation.
- Hourly activity timelines.
- Active and idle duration calculations.
- Focus-time aggregation.
- Application-switch counts.
- Date-range reports.

The accuracy of these metrics depends on the quality and completeness of the recorded activity data.

### ⏱️ 4. Focus Session Management

The backend supports focus-session operations.

- Start a session.
- Pause a session.
- Resume a session.
- Stop a session.
- Retrieve session history.

### 🎯 5. Goal Management

The backend provides goal-management operations.

- Create goals.
- Retrieve goals.
- Update goals.
- Delete goals.

These operations provide the foundation for future personalized focus-management features.

### 💾 6. Reliable Activity Storage

The planned desktop synchronization architecture includes:

- Local SQLite storage for pending activity.
- Batched API uploads.
- Retry handling.
- Synchronization status tracking.
- Duplicate-resistant database insertion.

The SQLite buffer and complete desktop synchronization workflow are still part of the development roadmap.

### 🔒 7. Privacy Controls

Planned privacy capabilities include:

- Configurable window-title storage.
- Application ignore-list.
- Tracking preferences.
- User data deletion.
- Protection of authentication credentials and sensitive information.

---

## 🏗️ System Architecture

The application is organized into three primary layers.

```text
┌──────────────────────────────────────────┐
│              React Dashboard             │
│                                          │
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
│  Validation and Business Logic           │
└─────────────────────┬────────────────────┘
                      │
                      │ SQLAlchemy
                      ▼
┌──────────────────────────────────────────┐
│               PostgreSQL                 │
│                                          │
│  Users | Devices | Activity Sessions     │
│  Focus Sessions | Goals | Settings        │
└──────────────────────────────────────────┘


┌──────────────────────────────────────────┐
│          Windows Desktop Agent           │
│                                          │
│  Window Tracker                          │
│  Idle Detection                          │
│  Session Builder                         │
│  SQLite Offline Buffer                   │
│  API Client and Sync Worker              │
└─────────────────────┬────────────────────┘
                      │
                      │ Authenticated Batch Uploads
                      ▼
                 FastAPI Backend
```

**Note:** The diagram represents the intended architecture. The complete desktop-to-backend synchronization workflow and React dashboard integration are still under development.

---

## 🛠️ Technology Stack

| Category | Technology | Purpose |
|---|---|---|
| Programming Language | Python | Backend and desktop agent |
| Backend Framework | FastAPI | REST API development |
| ORM | SQLAlchemy | Database operations |
| Database Migrations | Alembic | Schema versioning |
| Database | PostgreSQL | Persistent application data |
| Authentication | JWT | API authentication |
| Password Security | Argon2 | Password hashing |
| Desktop Monitoring | pywin32 | Windows API integration |
| Process Monitoring | psutil | Process information |
| Local Storage | SQLite | Planned offline activity buffer |
| Secure Credential Storage | keyring | Planned token storage |
| Frontend | React | Dashboard interface |
| Frontend Build Tool | Vite | Development and production builds |
| HTTP Client | Axios | Frontend API communication |
| Testing | pytest | Automated testing |
| Version Control | Git and GitHub | Source control |

---

## 📁 Project Structure

The project is organized into separate backend, desktop-agent, frontend, and documentation components.

```text
attention-platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── repositories/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── requirements.txt
│   └── .env
│
├── desktop-agent/
│   ├── app/
│   │   ├── main.py
│   │   ├── tracker.py
│   │   ├── activity_collector.py
│   │   ├── api_client.py
│   │   └── notifications.py
│   │
│   ├── tests/
│   └── requirements.txt
│
├── frontend/
│   └── src/
│
├── docs/
│   ├── tasks.md
│   └── ...
│
├── .gitignore
├── .env.example
└── README.md
```

> **Note:** This is a representative structure. Some directories and modules may change as development progresses. Keep the README synchronized with the actual repository.

---

## ⚙️ Getting Started

### Prerequisites

Install the following tools before starting development:

- Python 3.11 or a compatible project-supported version.
- PostgreSQL.
- Git.
- Visual Studio Code.
- Node.js and npm for the React frontend.
- Windows for the desktop tracking component.

Verify the installations:

```powershell
python --version
git --version
node --version
npm --version
```

Verify PostgreSQL connectivity using your configured PostgreSQL client.

### 1. Clone the Repository

```powershell
git clone https://github.com/Sajalvishwa/AI-Powered-Digital-Attention-Management-System.git
```

Navigate into the project:

```powershell
cd AI-Powered-Digital-Attention-Management-System
```

**Important:** The commands below assume that the repository contains the `backend/` and `desktop-agent/` directories shown in the project structure.

### 2. Configure PostgreSQL

Create the development and test databases:

```sql
CREATE DATABASE attention_dev;
CREATE DATABASE attention_test;
```

Use the development database for local development and the test database for automated integration tests.

Never run destructive test fixtures against the development database.

### 3. Set Up the Backend

Open a PowerShell terminal in the backend directory:

```powershell
cd backend
```

Create a virtual environment if one does not already exist:

```powershell
python -m venv venv
```

Activate it:

```powershell
.\venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Configure the backend environment variables using the project's existing settings configuration and `.env.example`.

After configuring the database, apply the existing migrations:

```powershell
alembic upgrade head
```

Start the development server:

```powershell
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The backend should be available at:

- API base URL: `http://127.0.0.1:8000`
- Interactive API documentation: `http://127.0.0.1:8000/docs`
- OpenAPI schema: `http://127.0.0.1:8000/openapi.json`

Open the API documentation to inspect the endpoints currently registered by the application.

### 4. Set Up the Desktop Agent

Open another PowerShell terminal:

```powershell
cd desktop-agent
```

Create and activate the virtual environment if necessary:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the project's desktop-agent dependencies:

```powershell
python -m pip install -r requirements.txt
```

Run the existing tracker:

```powershell
python -m app.tracker --seconds 20
```

To inspect window titles during local development:

```powershell
python -m app.tracker --seconds 20 --titles
```

**Privacy warning:** Window titles can contain personal information, document names, or other sensitive details. Use title inspection only when appropriate, and do not publish captured titles in logs or screenshots.

The command above tests the tracker. It does not, by itself, prove that activity has been uploaded to the backend or saved in PostgreSQL.

### 5. Set Up the Frontend

Once the React application and its `package.json` are present, open a terminal in the frontend directory:

```powershell
cd frontend
npm install
npm run dev
```

Use the local development URL printed by Vite.

The exact frontend scripts and configuration depend on the current implementation of `frontend/package.json`.

---

## 🔑 Environment Configuration

Create a local `.env` file using the structure supported by the backend configuration.

Example:

```env
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost:5432/attention_dev
JWT_SECRET=REPLACE_WITH_A_SECURE_RANDOM_SECRET
ACCESS_EXPIRE_MIN=15
REFRESH_EXPIRE_DAYS=7
```

These values illustrate the configuration format. Use the exact variable names and types required by the current backend settings.

### Security Guidelines

- Never commit `.env` files containing real credentials.
- Never expose JWT secrets in screenshots, logs, or public repositories.
- Use a strong, randomly generated JWT secret.
- Keep the development and test databases separate.
- Use an appropriately secured database account.
- Rotate any secret that has accidentally been exposed.

---

## 🔌 Backend API

The backend provides REST endpoints for authentication, user management, activity ingestion, focus sessions, goals, and statistics.

The following table summarizes the main endpoints documented by the project.

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/health` | Check backend health |
| POST | `/api/v1/auth/register` | Register a user |
| POST | `/api/v1/auth/login` | Authenticate a user |
| POST | `/api/v1/auth/refresh` | Refresh an access token |
| POST | `/api/v1/auth/logout` | Handle logout |
| GET | `/api/v1/users/me` | Retrieve the current user's profile |
| PUT | `/api/v1/users/me` | Update the current user's profile |
| GET | `/api/v1/users/me/settings` | Retrieve user settings |
| PUT | `/api/v1/users/me/settings` | Update user settings |
| POST | `/api/v1/activity/batch` | Submit a batch of activity sessions |
| GET | `/api/v1/activity/recent` | Retrieve recent activity |
| GET | `/api/v1/stats/today` | Retrieve today's activity statistics |
| GET | `/api/v1/stats/range` | Retrieve statistics for a date range |
| DELETE | `/api/v1/users/me/data` | Delete the current user's data |

Focus-session and goal endpoints are also part of the backend.

Consult the live OpenAPI documentation at `/docs` for their exact paths, request schemas, authentication requirements, and response formats.

### Authentication

Protected endpoints require a valid access token in the authorization header:

```http
Authorization: Bearer YOUR_ACCESS_TOKEN
```

Do not place real tokens in source code, public examples, or Git commits.

---

## 🧪 Testing

Automated testing is performed using `pytest`.

### Backend Tests

Open a terminal in the backend directory and activate the backend virtual environment.

Run:

```powershell
python -m pytest -q
```

The project's progress notes record a backend test run with:

```text
61 passed, 1 warning in 6.13s
```

This result describes a recorded test run, not a guarantee that every future version will produce the same result.

### Desktop Agent Tests

Open a terminal in the desktop-agent directory and activate its virtual environment.

Run:

```powershell
python -m pytest -q
```

A previously recorded desktop-agent test run reported:

```text
32 passed in 0.93s
```

Rerun the tests after making changes.

### Manual Tracker Verification

The existing tracker can be tested using:

```powershell
python -m app.tracker --seconds 20
```

For an additional local inspection:

```powershell
python -m app.tracker --seconds 20 --titles
```

Manual tracker verification and automated unit tests do not replace a full end-to-end test.

---

## 🗺️ Development Roadmap

Development is organized into six phases.

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
- [x] Backend test suite.
- [ ] Additional focus-session ownership and concurrency verification.
- [ ] Optional Docker setup.

### Phase 3 — Desktop Tracker Core

- [x] Desktop-agent skeleton.
- [x] Foreground window tracker.
- [ ] Idle detection.
- [ ] Session builder.
- [ ] SQLite offline buffer.
- [ ] API client and secure token storage.
- [ ] Background synchronization and retry handling.
- [ ] Ignore-list and privacy enforcement.
- [ ] One-hour end-to-end tracking verification.

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
- [ ] Secure file logging.
- [ ] Windows executable packaging.
- [ ] Setup and usage documentation.
- [ ] End-to-end integration tests.
- [ ] Final project documentation and `v0.1.0` release tag.

> Roadmap checkboxes should be updated only after implementation and meaningful verification are complete.

---

## 🔒 Privacy and Security

This project deals with information about how a person uses their computer. Privacy must therefore be considered throughout development.

The following principles guide the implementation:

- Collect only the activity information required by the application.
- Make tracking behavior understandable to the user.
- Avoid collecting actual keyboard keystrokes or mouse-click contents.
- Treat window titles as potentially sensitive information.
- Respect application ignore-lists and title-storage preferences.
- Require authentication for protected API endpoints.
- Validate incoming API requests.
- Avoid exposing credentials and tokens in logs.
- Protect user data through ownership checks.
- Provide a way to delete user data.
- Preserve pending activity safely during temporary connectivity failures.

Activity metrics are indicators of digital behavior, not definitive measurements of attention or mental state.

---

## 🔮 Future Enhancements

Potential improvements include:

- Personalized focus recommendations.
- Intelligent analysis of application-switching patterns.
- Focus-session trend analysis.
- Historical productivity reports.
- Configurable daily focus goals.
- Improved visualization of active and idle periods.
- Secure offline-to-online synchronization.
- Desktop system-tray controls.
- Exportable activity reports.
- Optional machine-learning models for pattern analysis.

These enhancements will be introduced as the underlying tracking, synchronization, and dashboard components become available.

---

## 🤝 Contributing

This project is being developed incrementally, with a focus on modular architecture, testing, privacy, and maintainability.

To contribute:

1. Fork the repository.
2. Create a feature branch.
3. Implement one focused change.
4. Add or update tests.
5. Run the relevant test suite.
6. Submit a pull request describing the change.

Suggested branch naming:

```text
feature/idle-detection
feature/session-builder
feature/offline-buffer
feature/activity-dashboard
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
