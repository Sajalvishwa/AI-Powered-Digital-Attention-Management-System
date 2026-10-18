from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import account, activity, analytics, auth, focus, goals, users
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.2.0")

# Dev uses the Vite proxy (no CORS needed). These origins matter for the
# packaged Electron app ("null" = page loaded from file://) and direct access.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "null",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


# recommendations / admin come in later weeks.
for r in (
    auth.router,
    users.router,
    account.router,
    activity.router,
    focus.router,
    analytics.router,
    goals.router,
):
    app.include_router(r, prefix=settings.api_prefix)
