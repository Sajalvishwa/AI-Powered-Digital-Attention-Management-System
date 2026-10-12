# rules.md — Project Rules & Conventions

Ye rules developers (aur AI assistants jaise Copilot/Claude) dono ko follow karne hain.

## 1. General
1. Pehle `docs/` padho (design, architecture, database, security) phir code likho.
2. Ek time pe ek task (`tasks.md`). Task complete → checkbox tick → commit.
3. Docs se bahar kuch change karna ho toh pehle doc update karo.
4. Simple code > clever code. Chhote functions (< 40 lines).
5. Koi hardcoded secret, URL ya password nahi.

## 2. Python Style
- Python 3.11+. Type hints **mandatory** on all functions.
- Formatter: `black` (line 100). Linter: `ruff`. Types: `mypy` (backend strict).
- Naming: `snake_case` functions/vars, `PascalCase` classes, `UPPER_CASE` constants.
- Imports order: stdlib → third-party → local (ruff handles).
- Docstrings: short, for public functions/classes.
- No `print()` — use `logging`.
- No bare `except:` — catch specific exceptions.

## 3. Backend Rules
- Layering: **router → service → repository**. Router mein DB query nahi, repository mein business logic nahi.
- Pydantic schemas for all request/response. Never return ORM models directly.
- `user_id` hamesha JWT se lo, request body se kabhi nahi.
- DB changes sirf Alembic migration se.
- All timestamps UTC (`datetime.now(timezone.utc)`).
- Errors: raise `HTTPException` with proper status code (400/401/403/404/409/422).
- API versioned under `/api/v1`.
- Every endpoint has at least 1 happy-path + 1 failure test.

## 4. Desktop Rules
- Agent ka tracker loop aur sync alag thread mein; UI (frontend) sirf API se baat kare.
- Tracker sirf: foreground app name, (optional) title, idle time. Nothing else.
- Tokens → `keyring`. Files mein nahi.
- Tracker crash hua toh UI crash nahi hona chahiye (try/except + log + restart).
- UI strings ek jagah (constants) rakho, styles CSS variables mein; hardcode colors nahi — `design.md` tokens use karo.
- Offline-first: pehle SQLite mein save, phir sync.

## 5. Git Rules
- Branches: `main` (stable), `dev`, `feat/<name>`, `fix/<name>`.
- Commit format (Conventional Commits):
  - `feat: add activity batch endpoint`
  - `fix: handle idle detection overflow`
  - `docs: update database.md`
  - `test:`, `refactor:`, `chore:`
- Small commits. Direct push to `main` nahi.
- `.gitignore`: `.env`, `__pycache__/`, `venv/`, `*.db`, `dist/`, `build/`.

## 6. Testing
- Backend: `pytest` + `httpx`. Test DB alag (not dev DB).
- Target coverage: services ≥ 80%.
- Tracker logic (session builder) pure function rakho taaki easily testable ho.
- Test pass kiye bina task complete mat karo.

## 7. API Response Format
Success: JSON of the resource. Error:
```json
{ "detail": "Human readable message", "code": "SOME_ERROR_CODE" }
```

## 8. Dependencies
- Naya package add karne se pehle socho: kya stdlib se ho sakta hai?
- Versions pin karo. `requirements.txt` update karo same commit mein.

## 9. Do / Don't
| Do | Don't |
|---|---|
| Validate all input | Trust client data |
| Log errors with context | Log passwords / tokens / titles |
| Write small PRs | Giant commits |
| Update docs with code | Leave docs outdated |
| Ask when requirement unclear | Guess silently |

## 10. Definition of Done (per task)
- [ ] Code works locally
- [ ] Tests written & passing
- [ ] Lint/format clean
- [ ] Docs updated if needed
- [ ] `tasks.md` updated
- [ ] Committed with proper message
