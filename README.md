# Attention Platform

AI-Powered Digital Attention Management System.
Docs: see `docs/` (read `memory.md` first).

## Quick start (Windows, PowerShell)
```powershell
copy .env.example .env          # then edit passwords/secret
docker compose up -d db

cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
alembic revision --autogenerate -m "initial tables"
alembic upgrade head
uvicorn app.main:app --reload
# open http://127.0.0.1:8000/docs
```
