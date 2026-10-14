from fastapi import FastAPI

from app.api.routes import account, activity, analytics, auth, focus, goals, users
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.2.0")


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
