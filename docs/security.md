# security.md — Security Plan

Activity data = sensitive personal data. Security aur privacy first-class requirements hain.

## 1. Threat Model (short)
| Threat | Mitigation |
|---|---|
| Stolen credentials | argon2 hashing, rate limiting, strong password policy |
| Token theft | short-lived access token, refresh rotation, OS keyring storage |
| Man-in-the-middle | HTTPS/TLS only in prod |
| SQL injection | SQLAlchemy parameterized queries only |
| Data leak between users | every query filtered by `user_id` from token (never from request body) |
| Malicious batch payload | Pydantic validation, size & count limits |
| Local data theft | no secrets in SQLite, optional title storage OFF by default |
| Secrets in git | `.env` in `.gitignore`, `.env.example` only |

## 2. Authentication
- Passwords: **argon2id** (or bcrypt cost ≥ 12). Never store/log plaintext.
- Password policy: min 8 chars, upper+lower+digit, check against common-password list.
- JWT access token: 15 min, HS256 (or RS256 later), claims: `sub`, `exp`, `iat`, `role`.
- Refresh token: random 256-bit, 7 days, **stored hashed** in DB, rotated on every use; reuse of old token → revoke all user tokens.
- Logout: revoke refresh token.

## 3. Authorization
- Role-based: `user`, `admin` (admin routes for later weeks).
- Dependency `get_current_user` on every non-public route.
- Ownership check on resource access (focus session, goal) → 404 if not owner (avoid leaking existence).

## 4. API Security
- CORS: allow only known origins (desktop app doesn't need browser CORS; keep restrictive).
- Rate limit: login 5/min/IP+email, register 3/min/IP, batch 30/min/user (slowapi).
- Request limits: batch ≤ 500 sessions, body ≤ 1 MB.
- Validate: `ended_at >= started_at`, timestamps not > 1 day in future, app_name length ≤ 255.
- Generic error messages for auth ("Invalid email or password").
- Security headers (when served over web): HSTS, X-Content-Type-Options, X-Frame-Options.
- Never return `password_hash`, tokens in logs or responses beyond login.

## 5. Desktop Client Security
- Tokens stored in **Windows Credential Manager** via `keyring`, not in files.
- API base URL must be `https://` in production builds (reject http).
- Local SQLite buffer contains only activity data; delete rows after sync.
- Single-instance lock; no admin privileges required.
- Code signing for `.exe` (later) to avoid SmartScreen warnings.
- Never read keystrokes content, clipboard, screenshots — **only** foreground app name, optional title, idle time.

## 6. Privacy & Consent
- First-run consent screen listing exactly what is collected.
- Window titles OFF by default.
- Ignore-list: apps never tracked (e.g. password managers, banking).
- Pause tracking anytime from tray.
- Export / delete my data available in Settings.
- Data minimization: collect only what features need.

## 7. Database Security
- App uses a dedicated DB user with least privilege (no superuser).
- Passwords/URL in env vars only.
- TLS for DB connection in prod; backups encrypted.
- Alembic for schema; no raw string-formatted SQL.

## 8. Secrets Management
- `.env` (local), Docker secrets / cloud secret manager (prod).
- Rotate JWT secret if leaked (forces re-login).
- Pre-commit hook: `detect-secrets` or `gitleaks`.

## 9. Logging & Monitoring
- Log: auth failures, rate-limit hits, 5xx errors. Include request id.
- Never log passwords, tokens, window titles.
- Keep logs 30 days.

## 10. Dependency Security
- Pin versions in requirements. Run `pip-audit` weekly / in CI.
- Dependabot enabled on GitHub.

## 11. Security Test Checklist (Week 7–8 prep)
- [ ] SQL injection attempts on all string params
- [ ] Access another user's resource by ID → must fail
- [ ] Expired / tampered JWT rejected
- [ ] Refresh token reuse detected
- [ ] Rate limits trigger
- [ ] Oversized batch rejected
- [ ] No secrets in repo history
